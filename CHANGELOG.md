CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
新しい項目は Unreleased に先に追加してください。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-22
--------------------

Added
- 基本パッケージの初期実装を追加。
  - kabusys パッケージ本体（__version__ = 0.1.0）。
- 環境設定・読み込み機能を追加。
  - .env ファイル自動読み込み（優先度: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動読み込み無効化。
  - .env のパース機能を実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応）。
  - _load_env_file の protected 引数により OS 環境変数の上書きを制御。
  - Settings クラスを導入し、環境変数経由で各種設定値（J-Quants トークン、kabu API パスワード、DB パス、PID/Kill flag、閾値等）を取得可能に。
  - PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH 等の paper_trading 関連設定を実装。
- 対話式の環境設定ウィザードを追加（python -m kabusys.config_setup）。
  - .env の生成・更新を補助する対話式プロンプト。
  - シークレット入力扱い、選択肢、デフォルト値、保存確認を実装。
  - .env を安全なテンプレート形式で書き出す _write_env を提供。
- 設定検証 CLI を追加（python -m kabusys.validate_config）。
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の未設定検出。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック、live 環境の警告）。
  - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック。
  - config/*.yaml の存在確認と（PyYAML があれば）パース検証。PyYAML 未インストール時は検証をスキップして警告。
  - --strict オプションで警告も失敗扱い（exit 1）にできる。
- 実行用エントリポイントを追加。
  - 実行エンジン起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading 時に paper_trading 専用 SQLite を使用し、本番 DB から分離。
    - PID ファイル管理、停止フラグ（stop_requested.flag / kill.flag）の検出処理。
    - プロセス優先度設定（set_process_priority を使用）。
  - 監視プロセス起動スクリプト: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path を使用。
- 発注・状態管理のコアロジックを実装（execution/*）。
  - OrderRecord: 注文状態列挙（OrderCreated, OrderSent, OrderAccepted, PartialFill, Filled, Closed, Cancelled, Rejected）と遷移検証ロジックを実装。InvalidStateTransitionError を導入。
  - OrderManager: signal_id をキーにした重複検出（DuplicateOrderError）、create/send/sync/cancel の外向き API を提供。
    - send_order はクラッシュ安全性を考慮した 2 相永続化 (OrderSent を先にコミット → broker 呼び出し → broker_order_id を先に保存 → OrderAccepted へ遷移) を実装。
    - OrderSentPendingError, OrderRejectedError を適切に扱う。
    - sync_order は broker 側のステータスを取得してローカル状態へ同期（部分約定の更新処理含む）。
    - cancel_order は終端状態判定と broker キャンセル呼び出しを実装。
  - ExecutionEngine:
    - シグナル処理ループ（signal_send_start ～ signal_send_end）および push ドレイン（WebSocket push）ループを実装。
    - Gate ベースのリスク制御を実装（Gate1: シグナルレベル、Gate2: エグゼキューションレベル（レート制限・サーキットブレーカー）、Gate3: ドローダウン監視による kill_switch 発動）。
    - size_multiplier 適用、発注の遅延/保留処理、position_entries への約定記録、監視 DB へのトレードイベント記録（オプション）を実装。
    - kill_switch により全 active 注文のキャンセルを試行する安全シャットダウン機能を実装。
    - WebSocket を使った push 受信サポート（broker が stream_push を提供する場合に起動）。
- broker 実装（kabu station REST クライアント）の基礎を追加。
  - KabuStationClient:
    - httpx クライアントを用いた同期 REST 実装。
    - トークン取得の遅延初期化と 401 発生時の自動再取得リトライを実装。
    - レスポンス JSON パース失敗・タイムアウト・ネットワークエラーを BrokerAPIError に変換。
    - 429 を RateLimitError にマップ、5xx をサーバーエラー扱いに。
    - kabu の状態コードを内部ステータス（open/partial/filled/cancelled/rejected）へマッピング。
- 監視 DB 初期化ユーティリティ（init_monitoring_db）呼び出しを各起動スクリプト・エンジン開始時に組み込み。
- sqlite3 / duckdb 接続の作成およびクローズ処理を適切に実装。

Changed
- （初期リリースのため特記事項なし）

Fixed
- （初期リリースのため特記事項なし）

Notes / Security / Operational
- .env は絶対に Git にコミットしないようウィザードの出力ヘッダで注意喚起。
- validate_config は live 環境時に通知設定（LINE）の未設定を警告し、KILL_FLAG_CLEAR_ON_START の危険設定も警告するなど運用上の保護を追加。
- ExecutionEngine は起動時に既存の kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START により自動クリアするオプションをサポート。クリアしない設定が推奨（本番安全性）。

開発者向け補足
- .env の行パーサーは引用符内のエスケープや行内コメントの扱いなどを考慮して実装されており、一般的なシェル風 .env フォーマットをサポートします。
- Order の状態モデル（OrderRecord）と OrderManager の実装は DB 層（OrderRepository）と分離されており、状態遷移ロジックは純粋なビジネスロジックとしてテスト可能です。
- KabuStationClient は同期実装ですが、将来的に async 対応が容易になるよう設計されています（httpx.AsyncClient へ置き換え可能）。

---