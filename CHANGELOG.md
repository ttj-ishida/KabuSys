# CHANGELOG

すべての注目すべき変更を記載します。  
このファイルは Keep a Changelog の形式に従います。  

## [Unreleased]

なし

## [0.1.0] - 2026-04-23

初回リリース — KabuSys 基本コンポーネントを追加しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージとバージョン
  - パッケージ初期版として __version__ = "0.1.0" を設定。

- 環境設定 & ユーティリティ
  - 環境変数の自動ロード機能（src/kabusys/config.py）
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索し自動的に .env / .env.local を読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサ実装: export 形式対応、シングル/ダブルクォート内のエスケープ処理、コメントの取り扱いロジック等をサポート。
    - Settings クラスを追加し、アプリケーション側で型付きプロパティ経由で設定を取得可能（トークン、API パスワード、DB パス、PID/kill flag、しきい値、環境判定など）。
    - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）や LOG_LEVEL / KABUSYS_ENV の検証を実装。

  - 環境設定ウィザード CLI（src/kabusys/config_setup.py）
    - 対話式ウィザードで .env を初期作成・更新する機能。
    - シークレット項目をマスク表示、選択肢とデフォルトの提示、キャンセル時の扱い、最終確認および .env テンプレート書き出しを提供。
    - 書き出しテンプレートには注記（.env を Git にコミットしない等）を含む。

  - 設定検証 CLI（src/kabusys/validate_config.py）
    - .env と config/*.yaml の起動前検証を行う CLI。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML 未導入時は警告）。
    - --strict オプションで警告を失敗扱いにして exit(1) を返す。

- 実行用スクリプト
  - Execution 起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine の起動処理ラッパー。プロセス優先度設定、DB 接続（paper_trading 時は専用 SQLite を使用して本番と分離）、停止フラグ検査（stop_requested.flag）、PID 管理を実装。

  - Monitoring 起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB 初期化を行う。

- 発注エンジン周り（execution サブパッケージ）
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）
    - シグナル取得 → Gate1/Gate2（リスク）を経て発注を行う Signal Queue Pull 型エンジン。
    - 発注ウィンドウ（デフォルト 8:50–9:10）と push ドレインループ（9:10–15:30）を実装。
    - WebSocket push の受信を別スレッドで処理し、_push_queue に投入して同期処理を行う。
    - kill_switch 実装：全 active 注文キャンセルとループ停止を行う。
    - 起動時のリコンシリエーション呼び出し（Reconciler）をサポート。
    - PID ファイル管理、kill.flag の取り扱い（KILL_FLAG_CLEAR_ON_START が有効なら自動クリア）を実装。
    - 発注に成功した場合の position_entries 更新、監視 DB への送信（レイテンシ等）を行う。

  - OrderRecord（src/kabusys/execution/order_record.py）
    - 注文状態を表現する状態機械（OrderState enum）と OrderRecord データモデルを提供。
    - 許可遷移を明示（_ALLOWED_TRANSITIONS）し、transition_to により不正遷移時に InvalidStateTransitionError を送出。

  - OrderManager（src/kabusys/execution/order_manager.py）
    - OrderRecord（ビジネスロジック）と OrderRepository（SQLite 永続化）を組み合わせた外向け API。
    - create_order: 同一 signal_id の active 注文がある場合は DuplicateOrderError を送出。DB 制約違反を DuplicateOrderError に変換する処理あり。
    - send_order: 2 相永続化（OrderSent を先にコミット → broker 呼び出し → broker_order_id をコミット → OrderAccepted に遷移）によりクラッシュ回復性を向上。OrderRejected / OrderSentPending の特別扱いを実装。
    - sync_order: broker 側ステータス取得→内部状態へ同期（部分約定の進行は差分更新）。OrderSent→Filled/PartialFill のケースで OrderAccepted を経由する保護ロジックあり。
    - cancel_order: 終端状態はキャンセル不可とし、broker API 呼び出し→Cancelled へ遷移する。

  - Broker クライアント（src/kabusys/execution/kabu_client.py）
    - KabuStation REST API の同期クライアントを実装（httpx 使用）。
    - トークンの自動取得・キャッシュ、401 での再取得リトライ、タイムアウト／ネットワークエラーの BrokerAPIError 変換、429 の RateLimitError 変換、kabu ステータスコードを内部ステータス文字列へマップする処理を実装。
    - 将来の async 対応を見据えた設計（httpx.AsyncClient への置換が容易）。

- 監視 (monitoring)
  - monitoring DB 初期化呼び出し（init_monitoring_db）を run_monitoring/run_execution で実行し、監視テーブルが確実に存在するようにした。

- ユーティリティ
  - ロギングセットアップ、プロセス優先度設定ユーティリティを起動時に利用（setup_logging / set_process_priority）。

### 変更 (Changed)
- N/A（初回リリースのため機能追加が中心）

### 修正 (Fixed)
- N/A（初回リリース）

### 注意事項 / 動作保証
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされる（パッケージ配布後も安全に動作することを意図）。
- config/*.yaml のパース検証は PyYAML が未インストールの場合はスキップされ、警告が出ます。YAML 検証を有効にするには PyYAML を導入してください。
- run_execution/run_monitoring は SQLite / DuckDB の接続を行います。適切なファイルパス（デフォルト: data/monitoring.db, data/kabusys.duckdb）が必要です。
- 本番環境（KABUSYS_ENV=live）では LINE 関連設定や KILL_FLAG_CLEAR_ON_START の値等に注意してください（validate_config にて警告を出します）。

---

このリリースはプロジェクトの最小限の実行基盤（設定管理・検証・発注・監視）を整え、クラッシュ耐性・リコンシリエーション・監視連携を含む実運用に向けた基本設計を提供します。