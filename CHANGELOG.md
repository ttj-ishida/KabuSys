# CHANGELOG

すべての重要な変更はこのファイルに記録します。形式は "Keep a Changelog" に準拠します。

## [Unreleased]

### Added
- なし

### Changed
- なし

### Fixed
- なし

---

## [0.1.0] - 2026-04-23

初回リリース。コードベースから推測される主要な機能・設計を以下に記載します。

### Added
- 全体
  - KabuSys 自動売買システムの基本的なコア機能を実装。
  - パッケージ版のメタ情報を定義（`__version__ = "0.1.0"`）。

- 設定関連
  - 環境変数・設定管理モジュール（kabusys.config）
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）により .env の自動読み込みを実施（OS 環境変数優先）。
    - .env ファイルの堅牢なパース実装（export プレフィックス、シングル/ダブルクォート、エスケープ、コメント処理をサポート）。
    - 自動読み込みを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須環境変数取得時に未設定なら例外を送出するヘルパー `_require`。
    - Settings クラスに各種プロパティを実装（J-Quants トークン、kabu API パスワード、DB パス、ログレベル、環境判定メソッド等）。
    - Paper Trading 用の分離された SQLite パス（PAPER_TRADING_SQLITE_PATH）と PAPER_FILL_MODE の検証。

  - 設定ウィザード CLI（kabusys.config_setup）
    - 対話式に .env を生成・更新するウィザードを追加。
    - 入力項目定義: KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LINE 関連, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等。
    - 既存 .env の読み込み・既存値の再利用・シークレットマスク表示・選択肢チェックをサポート。
    - .env を書き出す際のテンプレートフォーマットを実装（Git にコミットしない旨を明記）。

  - 設定検証 CLI（kabusys.validate_config）
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）およびプレースホルダ検出。
    - KABUSYS_ENV / LOG_LEVEL の妥当性検査（有効な値セットを定義）。
    - DB パス（DUCKDB_PATH / SQLITE_PATH）の親ディレクトリ存在チェック（存在しない場合は警告）。
    - config/*.yaml（system_config.yaml 等）の存在チェックと、PyYAML が存在する場合はパース検証を実施。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定の確認、KILL_FLAG_CLEAR_ON_START の危険値チェック）。
    - --strict フラグで警告も失敗（exit 1）として扱うオプションをサポート。
    - 検証結果を INFO/WARNING/ERROR として出力。

- 実行 / 監視スクリプト
  - Execution 起動スクリプト（kabusys.run_execution）
    - ExecutionEngine を起動する CLI スクリプト。
    - Paper Trading モード時は専用 SQLite（paper_trading.db）を使用して本番 DB と完全分離。
    - プロセス優先度設定と PID/停止フラグ管理（stop_requested.flag、execution.pid）。
    - DAO 初期化（監視 DB 初期化）や DuckDB 接続、スレッドでのセッション実行を実装。

  - Monitoring 起動スクリプト（kabusys.run_monitoring）
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグ検出でループを終了、DB 接続の確実なクローズを実装。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の設計。

- Execution コア
  - ExecutionEngine（kabusys.execution.execution_engine）
    - シグナルプル型発注エンジンを実装（セッション: 8:50 発注開始、9:10 発注締切、15:30 セッション終了）。
    - Reconciler による起動時リコンシリエーション呼び出し（オプション）。
    - kill.flag チェックと KILL_FLAG_CLEAR_ON_START による挙動、PID ファイル管理。
    - WebSocket スレッド（broker に stream_push がある場合のみ）で push を受け入れ `_push_queue` に投入。
    - シグナル処理フロー: シグナル読み出し（DuckDB）→ Gate1（シグナルレベル）→ Gate2（実行レベル、レート制限・サーキットブレーカー）→ 発注 → position_entries 書き込み（買いの entry 登録 / 売りの sell_date 更新）→ 監視 DB へのイベントログ。
    - Gate3（ドローダウン監視）で閾値オーバー時には kill_switch を発動。
    - kill_switch: エンジン停止フラグ設定と全 active 注文のキャンセル処理（例外をハンドルして継続可能な設計）。

- 注文管理
  - OrderRecord（kabusys.execution.order_record）
    - 注文状態を列挙する状態マシン（OrderCreated, OrderSent, OrderAccepted, PartialFill, Filled, Closed, Cancelled, Rejected）。
    - 許可される遷移を明示的に定義し、不正遷移時は InvalidStateTransitionError を送出。
    - transition_to により updated_at を UTC で更新し、付随フィールド（broker_order_id, filled_qty, avg_fill_price, error_message）を安全に更新。

  - OrderManager（kabusys.execution.order_manager）
    - DB（OrderRepository）と OrderRecord を組み合わせた外向き API。
    - create_order: signal_id 重複チェック（活性注文の存在）、UUID による client_order_id 発番、DB の一意制約違反を DuplicateOrderError に変換。
    - send_order: クラッシュ安全性を考慮した 2 相永続化フローを実装（OrderSent への永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted への遷移）。
      - OrderRejectedError の場合は Rejected に遷移。
      - OrderSentPendingError（注文番号は出るが未約定等）は broker_order_id を保存した上で OrderSent のまま残し、呼び出し元へ伝播（Reconciliation 対象）。
    - sync_order: broker の状態取得に基づく同期ロジック（open/partial/filled/cancelled/rejected を内部状態にマップ）。部分約定の進行は差分更新で反映。
    - cancel_order: 終端状態判定（キャンセル不可状態は InvalidStateTransitionError）→ broker cancel を呼び Cancelled に遷移。

  - Reconciliation を想定した設計（OrderSent のまま残るケースや broker_order_id 保存などにより、クラッシュ後の状態回復を意識）。

- ブローカー相互作用
  - KabuStationClient（kabusys.execution.kabu_client）
    - kabu ステーション REST API の同期クライアント実装（httpx を使用）。
    - トークン取得の遅延初期化と 401 発生時のトークン再取得・1 回リトライを実装。
    - レスポンス JSON パース失敗・タイムアウト・ネットワークエラーを BrokerAPIError に変換。
    - HTTP 429 を検出して RateLimitError を送出。
    - WebSocket push 受信用の stream_push（存在する場合）を前提とした設計をサポート。
    - 設計上、非同期化は将来的に httpx.AsyncClient へ差し替えることで容易に可能。

- 監視
  - monitoring_db 初期化関数呼び出しや、ExecutionEngine / run_monitoring での監視 DB ロギングポイントを備える。
  - 監視用メトリクス（発注レイテンシ、状態等）を監視 DB にログ可能（例外発生時は警告を出して発注フローは継続）。

### Changed
- なし（初回リリースのため過去からの変更は無し）。

### Fixed
- なし（初回リリースのためバグ修正履歴は無し）。

### Security
- .env は絶対に Git にコミットしない旨を生成テンプレートに明記（秘匿情報の取り扱いに注意）。

---

注記:
- 本 CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートや変更履歴と差異がある可能性があります。
- 追加の要望があれば、各機能ごとにより詳細な説明や例（使用方法、環境変数一覧、エラー条件と推奨対応手順など）を追記します。