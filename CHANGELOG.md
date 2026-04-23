CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

Unreleased
----------

なし

0.1.0 - 2026-04-23
------------------

Added
- 初期リリース: KabuSys パッケージの基本機能を実装。
- 設定管理
  - .env ファイル / 環境変数からの自動読み込み（プロジェクトルートの .env, .env.local を読み込み、.env.local は上書き）。OS 環境変数は既定で保護され、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - 細かい .env パーサ実装。export プレフィックス、シングル/ダブルクォートおよびバックスラッシュエスケープ、行内コメントルールに対応。
  - Settings クラスを提供し、各種設定値（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、PID/Kill Switch 設定、閾値等）をプロパティとして取得・検証可能。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の値検証を実装（有効値チェック）。
- CLI / ユーティリティ
  - config_setup CLI（python -m kabusys.config_setup）
    - 対話式ウィザードで .env の作成・更新を支援。
    - 用意された設定項目セット（実行環境、API トークン、DB パス、LINE トークン、ログレベル、Kill Switch 等）。
    - 秘密値は表示をマスク、保存時に .env ヘッダを付与（Git にコミットしない旨の警告メッセージを出力）。
  - validate_config CLI（python -m kabusys.validate_config）
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス存在チェック、config/*.yaml の存在と（PyYAML 有りなら）パース検証。
    - --strict オプションで警告を失敗扱い（exit(1)）。
    - プレースホルダ値（末尾が "_here" や "your_value"）の検出と警告。
  - run_execution / run_monitoring スクリプト
    - run_execution: ExecutionEngine 起動用。paper_trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB から分離。
    - run_monitoring: SystemMonitor ポーリングループ起動。MONITOR_POLL_INTERVAL によりポーリング間隔を上書き（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path を使用。
- 実行関連
  - プロセス優先度設定フック（set_process_priority 呼び出し）を起動時に実行。
  - PID ファイル書き込み／削除処理を実装。
  - 停止フラグ（data/stop_requested.flag）検知で安全にループを終了する仕組み。
- 発注・注文管理
  - OrderRecord: 注文状態列挙（OrderCreated, OrderSent, OrderAccepted, PartialFill, Filled, Closed, Cancelled, Rejected）と状態遷移ロジックを実装。InvalidStateTransitionError を提供。
  - OrderManager: DB（OrderRepository）と OrderRecord を組み合わせた外向き API を実装。
    - create_order: signal_id の重複チェック（部分ユニーク制約や DB の UNIQUE 制約も検出して DuplicateOrderError を投げる）。
    - send_order: クラッシュ耐性を考慮した 2 相的永続化（OrderSent 永続化 → broker 呼び出し → broker_order_id 永続化 → OrderAccepted 更新）。OrderRejectedError / OrderSentPendingError などをハンドリング。
    - sync_order: broker 側状態と同期し、filled_qty / avg_fill_price の更新に対応。OrderSent → Filled/PartialFill の場合は OrderAccepted を経由して遷移。
    - cancel_order: 取消不可能な終端状態を検査してから broker の cancel を呼び、Cancelled に遷移。
  - ExecutionEngine: シグナル読み込み（DuckDB）→ Gate1/Gate2 を経て発注、WebSocket push ドレイン（push に基づく sync_order と Gate3 ドローダウン監視）、kill_switch による全 active 注文キャンセル、position_entries の更新（発注成功時に次営業日で記録）を実装。
- Broker クライアント
  - KabuStationClient: httpx を使った kabuステーション REST API クライアント実装。
    - トークン取得の遅延初期化と 401 発生時の再取得・リトライ処理。
    - レスポンス JSON パースのエラーハンドリング、429/5xx の特別扱い（RateLimitError / BrokerAPIError）。
    - kabu ステータスコード → 内部状態マップ実装。
  - WebSocket push の受信をサポートし、on_message コールバックで ExecutionEngine に payload を渡せる設計（stream_push に依存）。
- 監視用 DB
  - monitoring_db 初期化用ヘルパー init_monitoring_db を参照し、run_* スクリプトで起動時に監視テーブルが存在することを保証。

Fixed / Improved
- .env 読み込みの堅牢性向上（IO エラー時の警告発行）。
- .env パース: クォート内のバックスラッシュエスケープや行内コメント処理を正しく扱うよう改善。
- MONITOR_POLL_INTERVAL の不正値に対するフォールバック処理（0 以下や非整数はデフォルトに戻す）。
- validate_config: PyYAML 未インストール時は YAML 内容検証をスキップして警告を出す。
- run_execution / ExecutionEngine:
  - 起動時の kill.flag 処理: KILL_FLAG_CLEAR_ON_START=1 の場合はクリアして起動、未設定の場合は起動拒否（安全策）。
  - スレッド／例外処理の堅牢化（stop フラグ検出、スレッド join、DB 接続の finally での確実クローズ）。
- OrderManager: send_order のクラッシュシナリオ（OrderSent 状態が残る等）を考慮した永続化シーケンスを実装し、Reconciliation での回復性を確保。

Security
- .env ファイルは生成時に Git へのコミット禁止を明記。
- シークレット項目は対話表示でマスクする実装。

Notes / TODOs
- YAML 内容検証は PyYAML に依存するため、環境にインストールされていることが望ましい。validate_config はインストール未検出時に検証をスキップして警告する。
- 将来的に KabuStationClient を async/httpx.AsyncClient へ差し替えることで非同期化が可能な設計。
- リファクタ/拡張ポイントとして BrokerAPI の抽象化とテスト用モックの整備、監視イベントの更なる充実が想定される。

---