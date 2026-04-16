# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。日本語で記載しています。

現行バージョン: 0.1.0

## [Unreleased]
- 今後のリリースに向けた未確定の改善点・調整点をここに記載します（現時点では特になし）。

## [0.1.0] - 2026-04-16
初回リリース。自動売買システム「KabuSys」の下記主要コンポーネントを実装・追加しました。

### Added
- 全体
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - DuckDB / SQLite を用いたデータ取得・集計処理を中心とした研究・運用用モジュール群を追加。
  - 主要外部依存: duckdb, psutil, openai, sqlite3（標準ライブラリ）など。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクトルート/data/stop_requested.flag を監視。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視テーブルに書き込む仕様。
    - 起動時にプロセス優先度を "high" に設定（utils/process_priority.set_process_priority を使用）。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBroker（BrokerClientFactory 経由）を使用し、paper_trading 専用の SQLite（デフォルト data/paper_trading.db）へ記録して本番 DB と完全分離。
    - 起動前に停止フラグを検出した場合は起動を中止。
    - 実行は別スレッドで行い、停止フラグ検出時に engine.stop() を呼んで安全停止を試みる。
    - PID ファイル（data/execution.pid）を扱う仕組みを導入。

- 設定管理
  - config.py
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env パーサは export 前置、シングル/ダブルクォート、インラインコメント等に耐性を持つ実装。
    - 設定取得用 Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須キー検証、各種パス・閾値・モードの取得）。
    - KABUSYS_ENV / PAPER_FILL_MODE / LOG_LEVEL 等の検証ロジックを実装。
    - PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、SQLITE_PATH 等のデフォルトパスを定義。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア順に選定。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重の重み算出。スコア全0時は等分配へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限に基づく候補除外ロジック（sell_codes を考慮）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマップ、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 重み・候補・利用可能現金等から発注株数を算出。allocation_method="risk_based" / "equal" / "score" をサポート。
    - lot_size（単元）で丸め、max_position_pct, max_utilization, cost_buffer を考慮したスケールダウン処理を実装。
    - aggregate cap を超過する場合はスケールダウンし、残余キャッシュで残差に基づいた追加配分を試みる。

- 研究（Research）モジュール
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離率を計算。
    - calc_volatility: ATR(20), ATR比率、20日平均売買代金、出来高比率を計算。
    - calc_value: EPS/ROE を用いた PER/ROE 計算（raw_financials の最新レコード参照）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する実装。
    - 不足データがある場合は None を返す堅牢な設計。
  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（デフォルト horizons=[1,5,21]）。
    - calc_ic: スピアマンランク相関（IC）計算（有効レコード < 3 の場合は None）。
    - factor_summary / rank: ファクターの基本統計量・ランク付けユーティリティ。
  - research/__init__.py に主要 API をエクスポート（zscore_normalize は data.stats から提供）。

- AI（ニュース NLP）
  - ai/news_nlp.py
    - raw_news を OpenAI API（gpt-4o-mini）でバッチセンチメントスコアリングし、ai_scores テーブルへ書き込む機能（設計・実装の大枠）。
    - 処理は銘柄毎に記事を集約し（最大記事数・文字数制限を設ける）、最大 _BATCH_SIZE 件ずつ API へ送信。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - 出力検証（JSON 構造・既知コード・スコア型）と ±1.0 クリップを実施。
    - news ウィンドウ計算 util（calc_news_window）を提供（JSTベースの開始/終了を UTC に変換して扱う）。
    - 注意: ファイル末尾で未完（コード切れ）が含まれているため、実行前に完全実装の確認が必要。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - CLI 対応 (--from, --to, --db) と PAPER_TRADING_SQLITE_PATH 環境変数対応。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ 等を算出。
    - PASS/FAIL の閾値を定義（稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 <=200ms）。
    - DB にテーブルが存在しない場合に備えた例外吸収ロジックを実装。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority: Windows (psutil.HIGH_PRIORITY_CLASS 等) / POSIX (nice 値) を吸収し、プラットフォーム依存性を隠蔽。
    - set_cpu_affinity: 指定コア数への CPU affinity 固定機能（利用可能コア数を超える場合は全コア使用）。
    - 権限不足や未対応 OS の際は警告ログを出し安全にフォールバック。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で供給。未設定の場合は ValueError を送出して明示的に失敗する仕様。

## 備考 / 運用上の注意
- .env の自動ロードはデフォルトで有効。テスト等で無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は監視データ用に常に本番 sqlite_path を使用します（環境に依らず監視 DB を統一する設計）。
- run_execution は paper_trading 環境時に DB を分離するため、誤って本番 DB を汚染するリスクを下げています。paper_trading での検証は data/paper_trading.db を利用してください。
- ai/news_nlp.py は堅牢化のため多数のバリデーション・リトライ制御を実装していますが、ファイル末尾が不完全な箇所があります。運用時は該当箇所の完成と十分なテストを行ってください。
- position_sizing の価格欠損（0.0）に対する注記（TODO）あり。将来的には前日終値や取得原価でのフォールバックを検討してください。
- 各モジュールはいずれも DuckDB/SQLite のテーブル構造（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, trade_logs, risk_logs, system_status など）を期待しています。初期セットアップ時はテーブル定義の準備が必要です。

---

過去のリリースが追加されるたびに、この CHANGELOG を更新してください。