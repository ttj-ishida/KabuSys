# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
括弧内は主に変更を加えたファイルを示しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-29
初回リリース。KabuSys のコア CLI / 実行ランタイム / 設定管理 / レポート生成ツール群を追加。

### Added
- 実行エントリポイント・監視プロセス起動スクリプトを追加
  - run_execution: ExecutionEngine の起動とライフサイクル管理、Paper Trading 時の MockBroker 使用と専用 DB 分離（src/kabusys/run_execution.py）。
  - run_monitoring: SystemMonitor のポーリングループ起動、MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応、停止フラグ / PID 管理（src/kabusys/run_monitoring.py）。
  - run_intraday_monitor: ザラ場中監視向け CLI。単発出力 / 監視モード（--watch）を提供（src/kabusys/run_intraday_monitor.py）。
- 各種レポート CLI を追加
  - run_pre_market_report: Pre-Market レポート生成（src/kabusys/run_pre_market_report.py）。
  - run_market_close_report: Market Close Summary（src/kabusys/run_market_close_report.py）。
  - run_position_reconciliation_report: Position Reconciliation View（src/kabusys/run_position_reconciliation_report.py）。
  - run_signal_queue_report: Signal Queue 確認ビュー（src/kabusys/run_signal_queue_report.py）。
- 設定検証 / ウィザード / 共通設定
  - validate_config: .env および config/*.yaml の起動前検証ツール（厳密モード --strict をサポート）（src/kabusys/validate_config.py）。
  - config_setup: .env を対話式に生成・更新するウィザード（src/kabusys/config_setup.py）。
  - config: Settings クラスを中心とした環境変数 / 設定読み込みロジックと自動 .env 読み込み（.env / .env.local）。クォートやエスケープを考慮した .env パーサ実装を含む（src/kabusys/config.py）。
  - 環境自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- 分析・検証ツール
  - tools/paper_verification_report: Paper Trading の検証レポート生成スクリプト（稼働率・注文成功率・レイテンシ等を評価）を追加（src/kabusys/tools/paper_verification_report.py）。
- 内部ユーティリティとの統合
  - DuckDB / SQLite を組み合わせたデータ読み取りを各 CLI で利用（各 run_*.py）。監視用 DB の初期化呼び出しを導入（init_monitoring_db）。
- バージョン情報
  - パッケージバージョンを定義 (__version__ = "0.1.0")（src/kabusys/__init__.py）。

### Changed
- 設定モデル（Settings）を整備し、以下プロパティを提供
  - J-Quants / kabuステーション / LINE / DB パス（duckdb_path, sqlite_path, paper_sqlite_path）やログ・閾値（cpu_threshold_pct 等）を取得するプロパティを追加（src/kabusys/config.py）。
  - PAPER_FILL_MODE の有効値チェック（instant, partial, never, reject）を追加。
  - KABUSYS_ENV と LOG_LEVEL の値検証を厳格化。無効な値は ValueError を投げる。
- run_execution / run_monitoring においてプロセス優先度を "high" に設定するユーティリティ呼び出しを導入（set_process_priority を使用）。
- run_execution
  - Paper Trading 環境では専用の SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
  - 起動時にブローカーから現金・ポジションを取得して起動時総資産を算出し、RiskConfig に渡す流れを確立（リスク設定の initial_portfolio_value を導入）。
  - 起動時リコンシリエーションを行い、Execution Startup Summary を生成・保存する処理を追加（出力に失敗しても起動継続）。
- run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き対応。0 以下や不正値はデフォルト 60 秒にフォールバックし、警告ログを出力。
  - 監視プロセスは環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
- 各種 CLI レポート
  - --date, --save, --json, --watch（定期実行）等のオプションを共通的にサポート。JSON 出力時は出力の汚染を避けるため保存先メッセージを stderr に出力する箇所を追加。
  - 各レポートは状態によって適切な終了コードを返す（例: READY/NOT READY, BLOCKED 等で 0/1 を返す）。
- run_intraday_monitor: 出力フォーマットにステータスラベル（OK/WARNING/CRITICAL）・絵文字と詳細情報（プロセス状態、ドローダウン、注文エラー等）を表示する新しい CLI 形式を実装。

### Fixed
- .env パースの不備を改善
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ対応、インラインコメント処理の改善などを実装（src/kabusys/config.py）。
- DB 接続の読み取り専用 URI 指定や接続時の例外処理を各 run_* スクリプトで強化（SQLite の uri モード使用や接続エラー時の終了コード処理を追加）。

### Security
- 必須環境変数の未設定検出
  - validate_config にて JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD の未設定をエラーとするチェックを実装。プレースホルダ値を検出して警告を出す。
- .env ウィザードの注意喚起
  - .env を Git にコミットしない旨のヘッダを自動生成ファイルに含める。

### Migration notes / 注意事項
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須です。validate_config で事前チェックすることを推奨します。
- KABUSYS_ENV の有効値は "development" / "paper_trading" / "live" のいずれかです。無効値は ValueError を発生させます。
- Paper Trading を使う場合は PAPER_TRADING_SQLITE_PATH（または Settings.paper_sqlite_path のデフォルト data/paper_trading.db）を使用して本番 DB とデータを分離してください。
- MONITOR_POLL_INTERVAL に 0 または負の値、または非数を設定するとデフォルト（60秒）にフォールバックして警告が出ます。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 1 にしないことを推奨（自動クリアは危険）。validate_config は live 環境での注意点を警告します。
- JSON 出力をパイプ等で利用する場合、--save 時の保存先メッセージは --json 時は stderr に出力されます（JSON ストリームが汚染されないようにするため）。
- Settings.log_level / env の検証が厳格化されています。運用環境の .env を確認してください。

もしリリースノートに追記したい項目（特定の不具合修正や開発者向け注記、実際のリリース日付の変更など）があれば教えてください。必要に応じてセクションを分割（Breaking Changes 等）して追記します。