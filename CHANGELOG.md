# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 初回リリース
リリース日: 未設定

### 追加
- 基本パッケージ初期実装を追加
  - パッケージメタ情報: kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) 検出による安全停止に対応。
    - Monitoring は実行環境に依らず本番 sqlite_path を使用するよう実装。
    - 起動時にプロセス優先度を "high" に設定（utils の set_process_priority を使用）。
    - SQLite / DuckDB 接続生成と監視テーブル初期化を行う。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository・OrderManager・RiskManager・Reconciler の組み立てを行う。
    - Engine を別スレッドで実行し、停止フラグで安全に停止・シャットダウン処理を行う。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py: 環境変数/.env 読み込みと Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env/.env.local の自動読み込み（必要に応じて無効化可）。
    - .env パーサの改善: export 形式、クォート文字列（エスケープ対応）、インラインコメントの扱いなどに対応。
    - 環境変数取得ユーティリティ _require と各種設定プロパティ（DB パス、API トークン、監視閾値、環境種別検証など）を提供。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等のバリデーション実装。
    - paper_trading 用 SQLite パス（PAPER_TRADING_SQLITE_PATH）プロパティを追加。

- ポートフォリオ構築関連（純粋関数）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、タイブレークに signal_rank）を実装。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコア0時のフォールバック実装）を実装。
  - portfolio/position_sizing.py
    - position サイズ計算 calc_position_sizes 実装（risk_based / equal / score モード、lot_size やコストバッファ考慮の aggregate cap スケーリング、単元株丸め、max_position_pct/利用率考慮）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap（既存保有エクスポージャーに基づくセクター上限適用。unknown セクターは除外しない仕様）。
    - calc_regime_multiplier（レジームに応じた投下資金乗数。bull/neutral/bear のデフォルト値と未知レジーム時のフォールバック）。

- リサーチ / ファクター計算
  - research/factor_research.py
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20、相対ATR、出来高/売買代金）および Value（PER, ROE）計算関数を追加。
    - DuckDB 接続を受け、prices_daily / raw_financials テーブル参照で純粋関数的に計算。
  - research/feature_exploration.py
    - 将来リターン calc_forward_returns、IC（スピアマンランク相関）calc_ic、ランク関数 rank、factor_summary（基本統計量）を実装。
    - 外部ライブラリに依存せず、標準ライブラリのみで統計量を算出する設計。
  - research/__init__.py エクスポートを整備（zscore_normalize を data.stats から再エクスポート）。

- AI ニュース NLP
  - ai/news_nlp.py（初期実装）
    - raw_news から銘柄ごとに記事を集約し、OpenAI API（gpt-4o-mini）を使ってセンチメントスコア（-1.0〜1.0）を算出して ai_scores テーブルへ書き込むワークフローを追加。
    - 処理仕様: タイムウィンドウ定義（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）、記事トリミング（記事数・文字数制限）、バッチ送信（最大 20 銘柄）、JSON 出力検証、スコアのクリップ、DB 部分更新（成功銘柄のみ差し替え）など。
    - API 呼び出しでの 429/ネットワーク/5xx に対する指数バックオフリトライをサポート。
    - API キー未設定時は ValueError。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（Windows と POSIX を吸収）。
    - set_process_priority(level): "high"/"normal"/"low" をサポート。アクセス権限不足時は警告でスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定するユーティリティを追加。利用不可な環境では警告でスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime)、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、平均/最大/P95 レイテンシなど。
    - P95 計算、日付フィルタ、DB 存在チェック、コマンドライン引数 (--from, --to, --db) に対応。
    - 合格/不合格基準（しきい値）を定義し、判定結果を出力。

- DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を起動スクリプトが呼び出すことで監視テーブルが存在することを保証（冪等処理）。

### 変更
- 設計上の方針・仕様
  - DuckDB を分析用に採用し、research / ai モジュールは DuckDB 接続を受ける設計とした（外部 API への不必要なアクセスを回避）。
  - 主要コンポーネントは「DB 参照を持たない純粋関数」として実装できる部分を分離し、テスト容易性を向上。
  - 起動スクリプトはプロセス優先度を最初に設定することで運用上の安定性を向上。

### 修正（不具合修正 / 安全対策）
- .env パーサ (_parse_env_line) の堅牢化
  - export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応し、誤った行を無視するよう改善。
  - _load_env_file に protected 引数を導入し、OS 環境変数の上書きを防止する挙動を明示化。

- 設定のバリデーション強化
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等で不正値が与えられた場合に ValueError を送出して早期検出するよう修正。

- ポジション計算の安全弁
  - position_sizing.calc_position_sizes に aggregate cap のスケーリングと残余キャッシュを利用した端数調整ロジックを追加し、available_cash を超えないように配慮。

- news_nlp のフェイルセーフ
  - OpenAI API 呼び出し失敗時はそのチャンクをスキップして他の処理を継続する実装（フェイルセーフ）。部分失敗時に既存スコアを保護するため、更新は対象コードで絞って行う。

### ドキュメント補足（コード内コメント）
- 各モジュールに設計方針や参照ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）への言及をコメントとして付与し、将来的な拡張点・注意点（例: lot_size の将来対応、価格欠損時のフォールバック等）を明示。

---

今後の予定／未実装・注意点（コード内コメントに基づく）
- position_sizing: 銘柄別単元（lot_size）を stocks マスタに持たせる拡張。
- risk_adjustment.apply_sector_cap: 価格欠損時のフォールバック（前日終値や取得原価）の導入検討。
- ai/news_nlp: 実際の OpenAI API 呼び出し部の詳細（チャンク組成、リクエスト/レスポンス処理）の完成・テスト運用。
- docs: 外部設計ドキュメント（PortfolioConstruction.md 等）の整備と参照リンクの追加。

（この CHANGELOG はコードベースから推測して作成しています。実際のリリース日や細かいコミット単位の履歴はリポジトリのコミットログを参照してください。）