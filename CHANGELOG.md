CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
並びは重要度順ではなく、機能追加／変更／修正ごとに分類しています。

Unreleased
----------

- なし

0.1.0 - 2026-04-21
------------------

Added
- 基本パッケージ初期実装を追加。
  - パッケージメタ情報: kabusys version 0.1.0。
- 環境設定 / 読み込み
  - .env、自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env のパースロジックを実装（export 形式、クォートされた値、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - _load_env_file に override/protected オプションを実装（OS 環境変数保護のための挙動制御）。
- 設定管理
  - Settings クラスを実装し、環境変数から型安全に設定を取得するプロパティを提供。
  - J-Quants / kabu API / LINE / DB（DuckDB / SQLite）関連の設定取得を実装。
  - PAPER_FILL_MODE の検証（"instant" / "partial" / "never" / "reject"）や閾値（CPU/MEM/DISK）の型変換をサポート。
  - env/log_level の検証ロジックを実装（未定義や不正値で ValueError）。
- CLI ツール
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - シークレット項目はマスク表示。
    - 選択肢／デフォルト値のサポート、既存 .env の読み込みと Enter での再利用。
    - 保存時に .env を生成（テンプレートヘッダを含む）。
  - validate_config: 起動前検証 CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、プレースホルダ検出、ファイルパス親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。
    - --strict オプションで警告も FAIL 扱いにできる。
- 実行用スクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - プロセス優先度設定、PID ファイル管理、停止フラグチェック、paper_trading 用 DB 分離（data/paper_trading.db）をサポート。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。
- 発注・実行基盤
  - OrderRecord: 注文状態マシンとデータモデルを実装（状態遷移検証、updated_at 自動更新、オプションフィールドの更新）。
    - OrderState 列挙と許可遷移マップを定義。InvalidStateTransitionError を導入。
  - OrderManager: 外向き API（create/send/sync/cancel）を実装。
    - DuplicateOrderError（同一 signal_id の active 注文重複防止）。
    - send_order における 2 相永続化戦略（OrderSent を先に永続化 → ブローカ呼び出し → broker_order_id 永続化 → OrderAccepted に遷移）でクラッシュ耐性を確保。
    - OrderSentPendingError の取り扱い（broker_order_id を保存して OrderSent のまま残す → 呼び出し元へ再送出）。
    - sync_order による broker 状態同期、同一状態でも filled_qty/avg_fill_price を更新する処理を実装。
    - cancel_order はキャンセル不可状態の判定（Filled を含む独自のキャンセル不可集合）を行い、API 呼び出し後に Cancelled に遷移。
  - ExecutionEngine: Signal Queue 型発注エンジンを実装。
    - セッションタイムライン（signal_send_start/end、market_close）に沿った処理。
    - kill.flag の検査と KILL_FLAG_CLEAR_ON_START に基づく起動挙動。
    - PID ファイルの書き出し／削除、WebSocket push ドレイン、_push_queue による非同期処理。
    - Gate1/2/3 によるリスクチェック連携（RiskManager）と API レート制御／サーキットブレーカー対応。
    - 発注時の遅延（latency）計測と監視DBへのログ出力（MonitoringDB が提供されている場合）。
    - Reconciler の起動（オプション）と例外ハンドリング。
- ブローカークライアント
  - KabuStationClient（kabu station REST API 実装）を追加。
    - httpx を用いた同期クライアント、トークン取得の遅延初期化、自動再取得（401 リトライ）を実装。
    - レスポンス JSON パースエラーを BrokerAPIError に変換。
    - 429 は RateLimitError を発出、500 系は BrokerAPIError を発出。
    - send_order: 成行注文時に Price=0 を強制してサーバー拒否を防止。
    - cancel_order/get_order_status 等の基本実装を追加（orders API の全件取得後フィルタリング戦略を採用）。
    - kabu の状態コードから内部状態 ("open"/"partial"/"filled"/"cancelled"/"rejected") へのマッピングを追加。
- 監視・DB 初期化
  - monitoring_db.init_monitoring_db の呼び出しを導入して監視テーブルの存在を保証（冪等）。
  - run_monitoring/run_execution で sqlite/duckdb 接続を確立。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security
- .env ファイル生成時に注意喚起ヘッダを追加（.env はコミットしないことを明示）。

Notes / Breaking changes
- Settings のプロパティが環境変数の不正値で ValueError を投げるため、外部から直接環境を操作している場合は例外に注意してください（特に LOG_LEVEL / KABUSYS_ENV / PAPER_FILL_MODE）。
- run_monitoring は常に production 用 sqlite_path を使用する設計のため、監視を検証する際に paper_trading 用 DB とは別扱いになります。
- ExecutionEngine が PID ファイルを生成するため、実行環境でファイルシステム権限に注意してください。

Acknowledgments
- 初期設計は堅牢性（クラッシュ後の再同期）、運用性（kill flag / PID /監視）、およびテスト容易性（paper_trading DB 分離、MockBroker による挙動分離）を意識して実装されています。