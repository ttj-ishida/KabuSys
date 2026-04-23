# Changelog

すべての重要な変更をここに時系列で記載します。  
このファイルは Keep a Changelog の形式に準拠しています。セマンティックバージョニングを採用しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

### Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア機能を追加。
- 環境設定/検証ツール
  - python -m kabusys.config_setup: 対話式ウィザードで .env を作成/更新する CLI を追加。
    - 多数の設定項目（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DUCKDB_PATH / SQLITE_PATH / LINE_* / LOG_LEVEL / KILL_FLAG_CLEAR_ON_START など）をサポート。
    - シークレット項目は表示をマスク、選択肢やデフォルト提示、保存前確認を実装。
    - .env ファイルの読み書きロジックを提供（書式テンプレート・注意書きの自動出力）。
  - python -m kabusys.validate_config: 起動前に .env と config/*.yaml の設定不備を検出する検証 CLI を追加。
    - 必須/任意環境変数のチェック、プレースホルダ検出、KABUSYS_ENV の妥当性チェック（development/paper_trading/live）、LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェックなどを実行。
    - PyYAML が存在すれば config/*.yaml をパースして内容検証を行う（未インストール時は警告）。
    - --strict オプションで警告を失敗扱いにして exit(1) にできる。
- 設定管理
  - kabusys.config.Settings クラスを追加（環境変数からの値取得と型/妥当性検証を行う）。
    - 自動 .env 読み込み機能: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動ロード（OS 環境変数優先、.env.local は上書き）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
    - .env の堅牢なパーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント規則を考慮）。
    - 各種プロパティ（jquants_refresh_token, kabu_api_password, duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode, pid_file_path, kill_flag_path, CPU/MEM/DISK threshold, env/log_level 等）を提供。無効値時は ValueError を送出することで早期検出。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時には paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離。
    - 高優先度プロセス設定、PID ファイル管理、stop flag / kill flag の処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。Monitoring は環境にかかわらず本番 sqlite_path を使用。
- Execution エンジンと発注フロー
  - ExecutionEngine を実装（signal queue ベースの発注エンジン）。
    - 発注ウィンドウ（デフォルト 8:50–9:10）とドレインループ（9:10–15:30）をサポート。
    - シグナル読み込み (DuckDB) → Gate1（シグナルレベル）/ Gate2（実行レベル、レート制御、Circuit Breaker）→ 発注 → position_entries 更新 → 監視ログ記録 の処理を実装。
    - WebSocket push を受けるワーカスレッド（broker.stream_push を利用）と push ドレイン処理を実装。
    - Gate3（ドローダウン監視）で閾値超過時に kill_switch を発動して全 active 注文をキャンセル。
    - kill_switch の動作、PID ファイル書き込み・削除、起動時の kill.flag 挙動（KILL_FLAG_CLEAR_ON_START によるクリア可）を実装。
    - セッション中のリコンシリエーション呼び出し（Reconciler）を起動時に実行（存在する場合）。
- 注文管理と状態遷移
  - OrderRecord: 注文状態マシンのデータモデルと状態遷移ロジックを追加。
    - OrderState 列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）と許可遷移テーブルを実装。
    - transition_to() による厳密な遷移検証（不正遷移は InvalidStateTransitionError を発生）と更新時刻自動更新、オプションフィールド更新を実装。
  - OrderManager: OrderRecord と OrderRepository（SQLite）を組み合わせた外向き API を実装。
    - create_order: signal_id の重複チェック（DB 部分ユニークや in-memory による検出）を行い、DuplicateOrderError を定義・送出。
    - send_order: 「OrderCreated → OrderSent を永続化（commit）」してから broker API を呼ぶ二相永続化パターンを実装。broker_order_id を先に保存してから OrderAccepted に遷移することでクラッシュ時のリカバリ性を向上（Reconciliation を容易にする）。
    - send_order は OrderRejectedError / OrderSentPendingError を適切に扱い、pending の場合は broker_order_id を保存して OrderSent のまま残し呼び出し元へ例外伝播。
    - sync_order: broker 側の状態を照会して DB を同期。status から内部 OrderState へマッピングして更新。部分約定の進行（filled_qty/avg_fill_price 更新）を同一状態でも反映。
    - cancel_order: 終端状態判定後に broker cancel を行い、Cancelled に遷移するロジックを実装。
- ブローカークライアント（kabu station）
  - KabuStationClient を実装（httpx 同期クライアント）。
    - トークン取得の遅延初期化、401 発生時のトークン再取得とリトライ、HTTP タイムアウト／ネットワークエラーを BrokerAPIError に変換。
    - 429 レスポンスを RateLimitError として扱う。
    - レスポンス JSON パース失敗のハンドリング等を実装。
    - websocket 経由の push（stream_push）を利用するためのフックを想定（WebSocket ライブラリ利用）。
- 監視（monitoring）統合
  - Monitoring DB 初期化を実装する init_monitoring_db 呼び出しを run_execution/run_monitoring で実行（冪等）。
  - 発注イベント（Sent）を監視 DB に記録する処理を ExecutionEngine の発注フローに組み込み（監視 DB 書き込み失敗時は警告に留め、フローは継続）。
- ユーティリティ
  - .env 読み込み時に OS 環境変数を保護する機構（protected set）を実装。これにより OS 上の変数を .env で不意に上書きしない。
  - process_priority 設定、ログセットアップユーティリティ呼び出しを各 run_* スクリプトで利用。
- ドキュメント的注記
  - __init__.py にパッケージバージョン __version__ = "0.1.0" を追加。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 機密情報表示の抑制（config_setup の出力マスク、Settings は直接トークンを露出しない設計など）に配慮。

---

注記:
- 本 CHANGELOG はコードベースから推測して作成しています。具体的な設計意図・実装の詳細はソースコードとドキュメントを参照してください。