# Changelog

すべての変更は Keep a Changelog のフォーマットに従います。  
このプロジェクトの初回リリースとしてバージョン 0.1.0 を記載します。

## [Unreleased]

## [0.1.0] - 2026-04-23

### Added
- 基本アプリケーションバージョニングを追加（__version__ = "0.1.0"）。
- 設定周り
  - Settings クラスを追加（kabusys.config）。環境変数からアプリ設定を取得する統一 API を提供。
  - 自動 .env ロード機能を追加：
    - プロジェクトルートを .git または pyproject.toml で探索して自動的に .env / .env.local を読み込む。
    - OS 環境変数は保護（上書き回避）され、.env.local は .env を上書きする（override 動作）。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーを実装（引用符、エスケープ、export プレフィックス、インラインコメント処理をサポート）。
  - Settings に各種プロパティを追加:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須、未設定時は例外を投げる）
    - KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH
    - PAPER_FILL_MODE（値検証）、kill_flag_clear_on_start、閾値（CPU/MEM/DISK/MEM）
    - env / log_level（値検証）、is_live / is_paper / is_dev ヘルパー
- CLI ツール
  - 環境設定ウィザード `kabusys.config_setup` を追加（.env の対話的作成/更新を支援）。
    - 対話項目定義、既存 .env 読み込み、シークレットマスク表示、保存時のテンプレート出力を実装。
    - .env の読み書きロジックを提供（テンプレート化された出力、コメント付与）。
  - 設定検証ツール `kabusys.validate_config` を追加。
    - 必須/任意の環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パス（親ディレクトリ存在チェック）、
      config/*.yaml の存在確認と（PyYAML があれば）パース検証、本番環境向け追加ガードを実装。
    - --strict オプションで警告も失敗扱いにできる。
- 実行スクリプト
  - `run_execution.py` を追加：ExecutionEngine の起動スクリプト（プロセス優先度設定、DB 接続、PID/停止フラグ管理、スレッド管理を含む）。
  - `run_monitoring.py` を追加：SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能）。
- 発注 / 実行ロジック
  - OrderRecord（kabusys.execution.order_record）を追加：状態列挙型（OrderState）と状態遷移ロジック、更新タイムスタンプの自動更新。
  - OrderManager（kabusys.execution.order_manager）を追加：signal → 発注フロー（create/send/sync/cancel）用の高レベル API。
    - create_order は signal_id の重複チェック（DB の部分ユニーク制約違反の変換含む）。
    - send_order はクラッシュ安全性を考慮した 2 相永続化（OrderSent 永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 遷移）を実装。
    - OrderSentPendingError（ブローカーが order_id を返すが約定しないケース）を扱う。
    - sync_order によるブローカー照合／状態回復（Reconciliation）を実装。
    - cancel_order はキャンセル不可状態の判定と API 呼び出しを行う。
  - ExecutionEngine（kabusys.execution.execution_engine）を追加：
    - シグナル処理（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）を実装。
    - Gate 1/2/3（シグナル検査・エグゼキューションレベル検査・ドローダウン監視）を統合し、NG の場合は適切に処理（kill_switch 発動等）。
    - push 処理で broker 側の注文状態同期、ポジション評価、監視 DB へのログ記録を行う。
    - kill.flag の存在チェックや KILL_FLAG_CLEAR_ON_START に基づく起動振る舞い、PID ファイル管理を実装。
    - WebSocket 用の _websocket_worker を実装し、broker に stream_push が無ければスキップする互換性考慮。
  - Broker クライアント
    - KabuStationClient（kabusys.execution.kabu_client）を追加：httpx を用いた kabu station REST API クライアント実装。
      - トークン取得（遅延初期化）、401 時の自動再取得＆再試行、429（レート制限）/500 系エラーの扱い、JSON パースエラーを BrokerAPIError に変換。
      - websocket（websocket ライブラリ）を用いた push の受け取り連携を想定（stream_push インターフェースを持つブローカのみ対応）。
- データベース / 監視
  - monitoring_db 初期化の呼び出しを run_monitoring / run_execution に組み込み（SQLite 初期化の冪等性を確保）。
  - DuckDB 接続の利用（分析用 DB）と monitoring DB（SQLite）を分離。paper_trading 時の SQLite は paper 用 DB を使用。

### Changed
- 設定値検証の厳格化：
  - Settings.env / log_level / PAPER_FILL_MODE で不正値があれば ValueError を発生させるようにした（環境設定ミスを早期検出）。
- .env 読み込みの優先順位を明示（OS 環境変数 > .env.local > .env）。
- 実行スクリプト類でプロセス優先度設定フック（set_process_priority）とログセッティング（setup_logging）を標準化して呼び出すようにした。

### Fixed
- （初期リリース）クラッシュ時の注文一貫性を改善：
  - send_order の 2 相永続化戦略により、broker_order_id が DB に残るケースを考慮し、Reconciliation（sync）で状態回復可能にした。
- .env パースの様々なケース（export プレフィックス、クォート中のエスケープ、インラインコメント）に対応して予期しない読み込み結果を防止。

### Security
- .env 出力テンプレートで明示的に「.env を絶対に Git にコミットしないこと」を記載。シークレット項目はウィザード中にマスク表示。

### Notes / Potential breaking changes
- Settings のプロパティは不正な環境変数値で例外を投げます。既存の環境に不正な値（例: LOG_LEVEL="BAD"、KABUSYS_ENV="foo"、PAPER_FILL_MODE の誤値）があると起動時に例外となるため、運用時は .env を見直してください。
- 自動 .env ロードはデフォルトで有効です。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

今後の予定（例）
- ブローカ抽象 API の追加テスト、KabuStationClient のエラーケースの拡充、async 対応の検討
- Reconciler / OrderRepository のテスト充実化、監視周りのメトリクス拡張

