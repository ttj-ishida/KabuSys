# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。セマンティックバージョニングに従い、現在のパッケージバージョンは src/kabusys/__init__.py に合わせて v0.1.0 としています。

## [0.1.0] - 2026-04-17

### 追加
- 基本パッケージ初期実装を追加。
  - パッケージメタ情報: __version__ = "0.1.0" を設定。
- 環境設定 / ロード
  - kabusys.config.Settings を実装：
    - .env/.env.local からの自動読み込み機能（プロジェクトルート自動検出、OS 環境変数優先）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD を用いて自動ロードを無効化可能。
    - 各種環境変数プロパティを提供（J-Quants、kabu API、LINE API、DB パス、監視設定、閾値など）。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）。
    - KABUSYS_ENV 検証（development / paper_trading / live）と利便性プロパティ（is_live, is_paper, is_dev）。
- 実行スクリプト
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトへフォールバック。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用。
    - 停止制御に data/stop_requested.flag の検出を使用。
    - プロセス優先度を "high" に設定して開始（set_process_priority）。
  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成（paper_trading では MockBrokerClient を想定）。
    - ExecutionEngine の起動・停止制御（data/stop_requested.flag による停止、PID ファイル出力）。
    - 起動時にプロセス優先度を "high" に設定。
- 監視 DB 初期化ユーティリティ
  - init_monitoring_db（監視テーブルの存在保証、冪等）を利用。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: スコア降順（タイブレーク: signal_rank 昇順）で候補抽出。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重（全スコアが 0 の場合は等金額へフォールバック）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限を適用（売却予定銘柄の除外対応、"unknown" セクターは制限を適用しない）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull:1.0 / neutral:0.7 / bear:0.3、未知は警告と 1.0 フォールバック）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: 重み / 候補 / リスクベース等に基づく発注株数計算（単元株ラウンド、max per stock、aggregate cap、cost_buffer 考慮、スケーリングと残差配分）。
    - risk_based / equal / score の allocation_method をサポート。
- 研究（research）モジュール
  - kabusys.research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率。
    - calc_volatility: ATR20、ATR 比率、20日平均売買代金、出来高比率等。
    - calc_value: PER, ROE（raw_financials + prices_daily を結合して算出）。
    - DuckDB を用いた SQL ベースの高効率計算を採用。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を利用）。
    - calc_ic: スピアマンランク相関（IC）計算（結合・欠損除外、3 銘柄未満は None）。
    - rank: 同順位は平均ランクで処理（round による誤差対策）。
    - factor_summary: count/mean/std/min/max/median の統計サマリ。
  - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。
- AI ニュース NLP（下流処理）
  - kabusys.ai.news_nlp:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores に書き込む仕組みを実装（バッチ送信、トリム、リトライ、レスポンス検証、スコアクリッピング）。
    - calc_news_window: 日本時間のニュース収集ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）。
    - score_news: OpenAI API キー解決（引数優先、環境変数 OPENAI_API_KEY を参照）、API エラーに対するエクスポネンシャルバックオフとフェイルセーフ方針。
    - 注意: モジュール末尾が実装途中（コード断片あり）。API キー未設定時は ValueError を送出する仕様。
- ユーティリティ
  - kabusys.utils.process_priority:
    - set_process_priority(level): Windows / POSIX（Linux/Mac/FreeBSD）の差分を吸収してプロセス優先度設定を提供。権限がない場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): プロセスを最初の N コアに固定する処理（許可エラーは警告）。
- ツール
  - kabusys.tools.paper_verification_report:
    - Paper Trading 用検証レポート生成 CLI を追加（--from, --to, --db オプション）。
    - 指標: 稼働率(uptime)、注文成功率(fill_rate)、送信率(send_rate)、P95 レイテンシ等を計算して PASS/FAIL 判定。
    - デフォルト DB は data/paper_trading.db。PAPER_TRADING_SQLITE_PATH で上書き可能。
    - 閾値（PASS 基準）を明示（稼働率 99%、fill_rate 90%、send_rate 95%、P95 200 ms）。
    - DB 内のテーブルが存在しない場合でも例外を捕捉して N/A として扱うフォールトトレラント設計。

### 変更
- （初期リリースのため「変更」はありません）

### 修正（バグ修正）
- （初期リリースのため「修正」はありません）

### 注意事項 / マイグレーションノート
- 環境変数/ファイル
  - .env/.env.local の自動ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml が必要）。プロジェクト配布後は環境変数による設定を推奨します。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用途）。
  - OPENAI_API_KEY が未設定だと news_nlp.score_news は ValueError を出します（API 呼び出しを行う場合は必須）。
  - MONITOR_POLL_INTERVAL に 0 以下や不正な値を設定すると、警告の上でデフォルト 60 秒にフォールバックします。
  - PAPER_FILL_MODE は明示的に検証されます。不正値を設定すると ValueError を送出します。
- DB 分離
  - run_monitoring は環境にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使用します。
  - run_execution は paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番データと完全に分離します。
- プロセス制御
  - 両スクリプト（run_monitoring/run_execution）はプロジェクトの data/stop_requested.flag を見て停止を判定します。外部からの停止にはこのファイルを利用してください。
  - set_process_priority / set_cpu_affinity は権限不足や未対応 OS では警告を出してスキップします。
- 未実装 / 注意点
  - ai/news_nlp モジュールの実装末尾が切れている（このファイルには未完成の断片が存在）。API 呼び出しの完全なフローや DB 書き込み周りは本リリース時点で要確認。
  - position_sizing の一部（lot_size 拡張や price のフォールバック）は TODO コメントで将来の改善が示されています。

---

今後の予定:
- news_nlp の完成（OpenAI レスポンス検証・DB 書き込みの完全実装）。
- テストカバレッジの拡充（特に DB 結合部、リトライロジック、ポジションサイズの境界条件）。
- CLI UX の改善（出力フォーマット: JSON/CSV オプション等）。

もし CHANGELOG に追記してほしい点（特定のコミット、詳細な実装差分、リスク評価など）があれば教えてください。