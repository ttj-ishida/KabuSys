# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従い、後方互換性のあるバージョン管理を前提とします。

## [Unreleased]

## [0.1.0] - 2026-04-23
初回リリース。KabuSys の実行環境・設定管理、発注エンジン、監視ループ、kabu station クライアント等のコア機能を実装。

### Added
- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの探索は .git または pyproject.toml を基準に実施）。
    - .env の行パーサを実装（export プレフィックス対応、シングル/ダブルクォートおよびバックスラッシュエスケープ、インラインコメント処理）。
    - OS 環境変数を保護するための上書き制御（override/protected）。
    - Settings クラスを提供し、各種設定値（トークン、パス、閾値、環境種別など）をプロパティとして取得。値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を行い、不正時は例外を送出。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。

- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py
    - ユーザ対話型ウィザードで .env を新規作成 / 更新する機能を実装。
    - 実行時に既存 .env を読み込み、入力フォームではシークレットをマスクして表示。
    - 入力項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を内蔵。
    - .env 書き出しロジックを実装（テンプレート付き、注意文を挿入）。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - .env と config/*.yaml の検証を行う CLI を提供。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）、プレースホルダ検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェックを実装。
    - config/*.yaml の存在確認と（PyYAML が有れば）パース検証を行う。PyYAML 未導入時は警告でスキップ。
    - KABUSYS_ENV=live のときの追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）を実装。
    - --strict オプションで警告を FAIL 扱いにできる exit コード制御。

- 実行エントリ / プロセス管理
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプトを提供。プロセス優先度設定、PID ファイル管理、停止フラグ（data/stop_requested.flag）対応を実装。
    - paper_trading 環境では paper_trading 用 SQLite を使用して本番 DB と分離。

  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL によるポーリング間隔上書き、監視 DB 接続（sqlite + duckdb）を実装。

- 発注エンジン・状態管理
  - src/kabusys/execution/execution_engine.py
    - Signal Queue Pull 型の ExecutionEngine を実装（シグナル処理ウィンドウ、WebSocket push ドレイン、セッション制御）。
    - Gate1/2/3 による多段リスクチェック、発注タイミング制御（signal_send_start/end）、push ドレイン処理、kill_switch による全注文キャンセルを実装。
    - WebSocket スレッド（broker が stream_push を提供する場合）を実装し、受信 payload を内部キューへ格納。
    - position_entries（DuckDB）へのエントリ記録（BUY/SELL の取扱い差分）や監視 DB へのトレードイベント記録（監視 DB がある場合）を実装。
    - セッション開始時の Reconciliation 実行サポート（Reconciler が指定された場合）。

  - src/kabusys/execution/order_record.py
    - OrderRecord データモデルと OrderState 列挙体を実装。状態遷移ルール（許可される遷移集合）を定義し、不正遷移時に InvalidStateTransitionError を送出。
    - 状態遷移時に broker_order_id / filled_qty / avg_fill_price / error_message を安全に更新、updated_at を UTC 現在時刻で自動更新。

  - src/kabusys/execution/order_manager.py
    - OrderManager を実装し、OrderRecord（純粋ロジック）と OrderRepository（SQLite）を組み合わせた外向き API を提供（create_order, send_order, sync_order, cancel_order）。
    - create_order: signal_id の重複チェック、UUID ベースの client_order_id 採番、SQLite の一意制約違反を DuplicateOrderError に変換する処理を実装。
    - send_order: クラッシュ耐性を考慮した 2 段階永続化パターンを採用（OrderSent 保存 → broker 呼び出し → broker_order_id 先コミット → OrderAccepted へ遷移）。OrderRejectedError / OrderSentPendingError の扱いを明確化。
    - sync_order: broker 側ステータス取得による状態同期処理（同一状態でも部分約定の進捗を反映）。
    - cancel_order: 取消不可能な状態判定、broker cancel 呼び出し、Cancelled への遷移。

  - src/kabusys/execution/order_repository.py (参照あり)
    - OrderRepository として SQLite を使った永続化が前提（コード内で利用）。（実装ファイル自体はコード一覧に含まれているが、ここでは OrderManager と連携する形で説明。）

  - src/kabusys/execution/reconciler.py / risk_manager.py / broker_factory 等
    - Execution フローの補助コンポーネント（Reconciler、RiskManager、BrokerClientFactory 等）との連携を行う設計に対応。

- ブローカー API クライアント（kabu station）
  - src/kabusys/execution/kabu_client.py
    - KabuStationClient を実装（httpx 同期クライアント）。
    - トークン取得を内部で管理し、401 受信時は自動でトークンを再取得して 1 回リトライするロジックを実装。
    - レスポンス JSON パース時のエラーハンドリング、タイムアウト・ネットワーク例外の BrokerAPIError 変換、429 を RateLimitError として扱う等のエラーマッピングを実装。
    - WebSocket push 用 websocket モジュールの使用を想定（stream_push 経由）。

- モニタリング
  - src/kabusys/monitoring/*（関連モジュールと DB 初期化）
    - monitoring 用の DB 初期化ユーティリティ（init_monitoring_db）を提供し、run_monitoring、run_execution から呼び出して監視テーブルの存在を保証。

- ユーティリティ
  - src/kabusys/utils/*
    - ロギング初期化（setup_logging）やプロセス優先度設定（set_process_priority）などのユーティリティ関数を使用して、起動時の共通処理を統一。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Design decisions
- 発注フローはクラッシュ耐性を重視して設計。OrderSent 状態の永続化と broker_order_id の先コミットにより、リコンシリエーションで不確定状態を回復可能にしています。
- paper_trading 環境は本番 DB と完全分離されるよう設計されており、paper_trading 用 SQLite パスを用意しています。
- .env の自動読み込みはデフォルトで有効ですが、テストなどで無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を用意しています。
- YAML のパース検証は PyYAML がインストールされている場合のみ実行します（未インストール時は警告に留める）。

---

今後のリリースでは、テストカバレッジの強化、エラーメトリクスの拡充、kabu station クライアントの非同期対応（httpx.AsyncClient への移行）等を予定しています。