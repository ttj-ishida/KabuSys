# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従ってバージョニングしています。  

- リリース日付はソースコードから推測して付与しています。  
- 記載内容は提示されたコードベースの実装内容から推測して記述しています（明示的なコミット履歴ではありません）。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-22

### 追加
- パッケージ基本情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
- 設定・環境変数管理
  - Settings クラスを実装（src/kabusys/config.py）。環境変数から各種設定（J-Quants トークン、kabu API パスワード、DB パス、PID/Kill フラグパス、しきい値など）を取得可能。
  - .env 自動ロード機能を実装（プロジェクトルートの .env / .env.local を読み込み）。OS 環境変数を保護して上書き制御可能。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルのパース実装を強化（クォート、エスケープ、コメントの扱いに対応）。
  - PAPER_FILL_MODE 等の検証を実装（不正値は ValueError を送出）。
  - Settings インスタンスをモジュールレベルで提供（settings）。

- 設定支援 CLI（ウィザード）
  - 対話式 .env 作成/更新ウィザードを実装（src/kabusys/config_setup.py）。
  - 主要設定項目を定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 通知、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）。
  - 既存 .env 読み込み、シークレットは表示をマスク、デフォルト値提示、保存前確認などの対話式機能を提供。
  - .env 書き込み時にヘッダコメントで Git にコミットしない旨を明記。

- 設定検証 CLI
  - 起動前に .env および config/*.yaml の簡易検証を行う CLI を追加（src/kabusys/validate_config.py）。
  - 必須環境変数の存在チェック、プレースホルダ値の警告、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在確認および PyYAML があればパース検証を実施。
  - KABUSYS_ENV=live に対する本番用ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
  - --strict オプションで警告も失敗（exit code 1）扱いにできる。

- 実行用スクリプト
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値の場合はデフォルトにフォールバックし警告。
    - stop_requested.flag を検知して安全に終了。
    - DuckDB / SQLite 接続初期化と Monitoring DB 初期化処理を呼び出す。
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（settings.paper_sqlite_path）を使用し本番 DB と分離。
    - stop_requested.flag 検出による起動スキップ、実行中検出でエンジン停止。
    - PID ファイルのパス、プロセス優先度高設定等の起動手順を実装。

- 実行エンジン・発注関連
  - ExecutionEngine を実装（src/kabusys/execution/execution_engine.py）。
    - シグナル処理（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）を想定したセッションモデル。
    - kill_switch による全 active 注文キャンセル、PID ファイル管理、kill.flag の起動時挙動（KILL_FLAG_CLEAR_ON_START による自動クリア制御）を実装。
    - Gate 1 (シグナルレベル)、Gate 2 (エグゼキューションレベル、レート制限・サーキットブレーカー)、Gate 3 (ドローダウン監視) を通す発注フローを実装。Gate 2 は最大リトライ、CB オープン時はシグナルループを停止。
    - WebSocket スレッドは broker が stream_push を提供する場合のみ起動し、受信 payload をキューへ投入。
    - push ハンドリングでは broker_order_id -> client_order_id の同期（sync_order）を行い、ポートフォリオ評価を用いた Gate 3 判定も行う。
    - 発注時の監視 DB へのログ書き込み（latency 等）をサポート（監視 DB が渡された場合）。

  - OrderRecord（状態遷移モデル）を実装（src/kabusys/execution/order_record.py）。
    - OrderState 列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）と許容遷移マップを定義。
    - transition_to による検証付き状態遷移、更新時刻自動更新、オプションフィールド（broker_order_id, filled_qty, avg_fill_price, error_message）更新を実装。
    - 不正遷移時に InvalidStateTransitionError を送出。

  - OrderManager を実装（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id 単位の重複防止（既存 active 注文のチェック）。DB の一部ユニーク制約違反は DuplicateOrderError に変換。
    - send_order: クラッシュ安全性を考慮した二相的永続化フローを実装（OrderCreated→OrderSent を永続化後に broker 呼び出し、broker_order_id を先に保存 → OrderAccepted へ遷移）。
      - OrderRejectedError は Rejected に遷移して保存。
      - OrderSentPendingError（broker が注文番号発行後に確定状態を返さないケース）は broker_order_id を保持したまま OrderSent のままにして呼び出し元へ伝播（Reconciliation 対象）。
      - その他の例外は捕捉せず OrderSent のまま残す（list_uncertain で検出可能な設計）。
    - sync_order: broker 側の状態照会による同期処理（部分約定の進行は差分更新）。OrderSent→Filled/PartialFill の場合は中間状態 OrderAccepted を経由して遷移させる等の安全策を実装。
    - cancel_order: 終端状態ではキャンセル不可として InvalidStateTransitionError を発生させる。broker_order_id がある場合は API を呼び Cancelled に遷移。

  - ブローカー／リコンシリエーション
    - Reconciler の呼び出しポイントが ExecutionEngine に追加（起動時リコンシリエーション。実装が外部にある想定）。
    - OrderRepository/MonitoringDB などと連携する設計に対応。

- ブローカークライアント（kabu station）
  - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
    - httpx（同期）クライアントを使用した REST 実装。
    - トークン取得の遅延初期化と 401 時の自動再取得 + 1 回リトライを実装。
    - レスポンス JSON パース失敗やネットワークエラーを BrokerAPIError 等へ変換。
    - HTTP 429 を RateLimitError として扱う。
    - 内部で kabu ステータスコードを共通ステータス文字列（open/partial/filled/cancelled/rejected）へマップ。

- DB / 監視
  - DuckDB と SQLite を併用する設計（DuckDB は分析/シグナル取得、SQLite は監視・注文履歴）。
  - Monitoring 初期化ユーティリティ呼び出し（init_monitoring_db）を run_* スクリプトで実行するようにした。

- ユーティリティ
  - プロセス優先度設定ユーティリティ呼び出し（set_process_priority）を run_* スクリプトの起動時に実行。
  - ロギングセットアップ（setup_logging）を各 run スクリプトで使用。

### 変更
- なし（初回リリースとしての実装内容の列挙）

### 修正
- なし（初回実装のため特定修正履歴はなし）

### 注意事項 / 破壊的変更
- .env の自動ロードはデフォルトで有効。テストや特殊環境で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ExecutionEngine は起動時に PID ファイルを書き、kill.flag の存在によって起動拒否または自動クリア（KILL_FLAG_CLEAR_ON_START=1）という挙動を持ちます。運用時には KILL_FLAG_CLEAR_ON_START の設定に注意してください。
- validate_config の --strict モードは警告も失敗扱いになるため CI 等で利用する際は意図を確認してください。
- config_setup によって生成される .env はセキュリティ上 Git にコミットしないでください（ファイルヘッダでもその旨を明記しています）。

### 既知の制限 / 想定
- config/*.yaml の内容検証は PyYAML がインストールされている場合のみ行われ、インストールされていない場合はパース検証はスキップされる（警告のみ）。
- KabuStationClient は同期 httpx.Client を使用しており、将来的に非同期対応する場合は AsyncClient へ差し替えが想定されている。
- 一部の外部コンポーネント（BrokerClientFactory、OrderRepository、Reconciler、MonitoringDB 等）はこの差分でインターフェースを用いる前提で設計されており、実運用時はそれらの実装が必要。

---

以上は提示されたソースコードから実装内容をまとめ・推測して作成した CHANGELOG です。必要であれば各項目の文言を運用ルールや実際のコミット履歴に合わせて修正できます。