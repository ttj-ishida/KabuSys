CHANGELOG
=========

すべての注目すべき変更点をここに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-22
-------------------

Added
- 初回リリース: KabuSys 基本モジュール群を追加。
- パッケージメタ情報
  - バージョンを __version__ = "0.1.0" に設定。

- 設定管理
  - 環境変数 / .env の自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートの判定は .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - .env のパースは export プレフィックス、クォート（シングル／ダブル）、バックスラッシュエスケープ、インラインコメント処理に対応。
    - 自動ロードの順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - _load_env_file の override / protected 引数により OS 環境変数を保護して任意の上書きを制御。
  - Settings クラスを実装し、環境変数からアプリ設定を取得（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、各種閾値など）。
    - env / log_level / PAPER_FILL_MODE 等のバリデーションを行い、不正値は ValueError を送出。
    - paper_trading 用の DB パス分離（PAPER_TRADING_SQLITE_PATH）、kill_flag クリアフラグ等を提供。

- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py に対話式ウィザードを実装。
    - .env ファイルの読み込み・既存値の再利用・選択肢・シークレットマスク表示に対応。
    - .env 書き出しテンプレートを提供（.env を絶対に git にコミットしない旨の注意を含む）。
    - デフォルト値、オプション項目、KILL_FLAG_CLEAR_ON_START 等の項目をサポート。

- 設定検証 CLI
  - src/kabusys/validate_config.py に設定検証ツールを実装。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の存在チェックとプレースホルダ検出。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（許容値: development/paper_trading/live, DEBUG/INFO/...）。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック（起動時自動作成の可能性を警告）。
    - config/*.yaml の存在確認および PyYAML があればパース検証（PyYAML 未インストール時はスキップして警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定検出）。
    - --strict モード: 警告も失敗扱いにして exit(1)。
    - 実行例: python -m kabusys.validate_config

- 実行エントリスクリプト
  - run_execution.py（src/kabusys/run_execution.py）
    - ExecutionEngine の起動ラッパー。プロセス優先度を high に設定（ユーティリティ呼び出し）。
    - stop フラグ / PID ファイル取り扱い、paper_trading の DB 分離、監視テーブル初期化などを行う。
  - run_monitoring.py（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）。
    - monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。

- Execution / 発注ロジック
  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態列挙型 OrderState を定義（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許可される状態遷移を定義し、transition_to による遷移検証を実装。InvalidStateTransitionError を導入。
    - DB に触れない純粋なビジネスロジックとして実装。
  - OrderManager（src/kabusys/execution/order_manager.py）
    - create_order, send_order, sync_order, cancel_order の外向き API を実装。
    - create_order: signal_id の重複する active 注文チェック、UUID による client_order_id 発番、SQLite の一意制約違反を DuplicateOrderError に変換。
    - send_order: クラッシュ耐性を考慮した二相永続化（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を永続化 → OrderAccepted に遷移）を実装。OrderRejectedError / OrderSentPendingError の取り扱いを実装。
    - sync_order: broker 側の状態照合を行い、filled/partial の差分更新、OrderSent→(accepted→)filled の補完処理などを実装。
    - cancel_order: 終端状態でのキャンセル禁止チェック、broker_cancel 呼び出し、Cancelled 遷移を実装。
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - Signal Queue Pull 型発注エンジンを実装。セッションタイミング（8:50-9:10 発注ループ、9:10-15:30 push drain）に対応。
    - Gate1（シグナルレベル）/ Gate2（エグゼキューションレベル; レート制限・サーキットブレーカ）/ Gate3（ドローダウン監視）を実装。Gate2 は最大3回リトライと Circuit Breaker 判定を持つ。
    - kill_switch を実装: 全ループ停止と全 active 注文のキャンセル。外部 stop() は kill_switch の公開エイリアス。
    - WebSocket スレッドを起動して push を _push_queue に入れ、同期処理（sync_order）や Gate3 の評価を実行。broker が stream_push を持たない場合はスキップする。
    - 発注後に position_entries を DuckDB に記録（BUY/pending を考慮、SELL は pending の場合は更新を遅らせる）。
    - 監視 DB が提供されていれば発注イベントを log_trade_event で記録。

- ブローカークライアント（kabu）
  - KabuStationClient（src/kabusys/execution/kabu_client.py）
    - httpx を使った同期 REST クライアント実装。トークン取得（/token）を内部で管理し、401 時はトークン再取得して 1 回リトライする。
    - レスポンス JSON パース失敗やネットワークエラーは BrokerAPIError に変換。
    - 429 を RateLimitError として扱う。kabu の状態コードを内部状態（open/partial/filled/cancelled/rejected 等）にマップ。
    - 将来的な async 対応のために設計上の余地を持たせている（httpx.AsyncClient への置換が想定される）。
    - WebSocket push の利用は broker が stream_push を提供する場合にのみサポート（ExecutionEngine と連携）。

- 監視関連
  - monitoring の初期化関数（init_monitoring_db）を呼び出すことで監視用テーブルを確実に存在させる処理を run_execution/run_monitoring で追加。

- ユーティリティ
  - ロギングセットアップ呼び出し（setup_logging）、プロセス優先度設定（set_process_priority）をエントリスクリプトで使用。

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

Security
- （初回リリースのためなし）

Notes / 備考
- config/*.yaml のパース検証は PyYAML がインストールされている場合のみ実行され、未インストール時は警告してスキップします。
- .env のサンプルや config 生成スクリプト（scripts/generate_config.py を想定）との連携を想定したメッセージを含みます。
- 本リリースでは主要なビジネスロジック（注文状態機械、発注ワークフロー、リコンシリエーションのための二相永続化設計、監視連携）が実装されています。今後は単体テスト／統合テスト、ドキュメント整備、エラー経路の充実などが想定されます。