# Changelog

すべての重要な変更をここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

現在のリリースポリシー:
- バージョンはパッケージの __version__ に合わせています。
- 日付はリリース日を表記しています。

## [Unreleased]

（現状、未リリースの作業はありません。）

## [0.1.0] - 2026-04-23

初回公開リリース。以下の機能と実装を含みます。

### Added
- 基本パッケージ情報
  - パッケージ名: KabuSys、バージョン: 0.1.0。

- 環境・設定管理
  - Settings クラス（kabusys.config）を実装。環境変数からアプリ設定を取得するプロパティ群を提供（J-Quants トークン、kabu API パスワード、DB パス、PID/KILL フラグパス、閾値、環境/ログレベル判定など）。
  - 自動 .env 読み込み機能:
    - プロジェクトルート判定（.git または pyproject.toml を探索）。
    - 読み込み順: OS 環境 > .env > .env.local（.env.local は上書き）。OS 環境変数は保護される。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーの実装:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォート無しの '#' は前が空白/タブの場合にコメントと判定）などを実装。

- 環境設定ウィザード CLI
  - kabusys.config_setup: 対話式ウィザードで .env の初期作成/更新を支援。
  - 入力項目の定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB/SQLITE パス, LINE 通知設定, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）。
  - 既存 .env 読み込み、シークレットマスク表示、保存前の確認を実装。
  - .env 書き出しテンプレート（コメント付き）を提供。

- 設定検証 CLI
  - kabusys.validate_config: .env と config/*.yaml の起動前検証ツールを実装。
  - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス父ディレクトリ存在確認、config/*.yaml の存在確認と（PyYAML があれば）パース検証を実装。
  - --strict オプションで警告を FAIL 扱いにする機能。
  - YAML 未インストール時には警告を出してパース検証をスキップ。

- 実行用スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイント。プロセス優先度設定、DB 接続、broker クライアント生成、ExecutionEngine の起動・監視を行う。
    - paper_trading 環境では paper_trading 用 SQLite を使用して本番 DB と分離。
  - run_monitoring: SystemMonitor のポーリングループを起動するエントリポイント。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可。Monitoring は常に本番 sqlite_path を使用。

- 発注系コア
  - OrderRecord と OrderState（kabusys.execution.order_record）:
    - 注文状態列挙・遷移テーブルと、遷移検証を行う transition_to を実装。InvalidStateTransitionError を定義。
  - OrderManager（kabusys.execution.order_manager）:
    - signal_id 重複検出（DuplicateOrderError）。
    - create_order / send_order / sync_order / cancel_order の実装。
    - send_order におけるクラッシュ安全性を考慮したフロー（OrderSent を先に DB 永続化、broker_order_id の先行保存、OrderAccepted への遷移、OrderSentPendingError のハンドリング等）。
  - ExecutionEngine（kabusys.execution.execution_engine）:
    - シグナル処理ループと WebSocket push ドレインループを持つセッション実装。
    - Gate 1/2/3 によるリスクチェック（シグナルレベル・エグゼキューションレベル・ポートフォリオドローダウン監視）。
    - kill_switch による全 active 注文キャンセル機構、PID/KILL フラグの管理、起動時の kill.flag 処理（KILL_FLAG_CLEAR_ON_START サポート）。
    - WebSocket プッシュ受信を別スレッドで処理する仕組み（_push_queue 経由）。
    - DuckDB を用いたシグナル読み込みと position_entries の更新ロジックを実装（発注成功時に position_entries を記録）。

- ブローカー関連
  - KabuStationClient（kabusys.execution.kabu_client）:
    - httpx を用いた同期 REST 実装。トークン取得（遅延初期化・401 時の再取得）を内包。
    - レスポンス JSON パースエラーや httpx のタイムアウト/ネットワークエラーを BrokerAPIError 等に変換。
    - 429（Rate Limit）を RateLimitError として扱い、401 の再トライ処理を実装。
  - Broker 接続の抽象化（broker_factory, broker_api などを利用）。

- 監視 / ロギング
  - monitoring_db の初期化ユーティリティ呼び出し（init_monitoring_db）。
  - 監視 DB へのイベント記録（monitoring_db.log_trade_event）呼び出し箇所を実装（監視書き込み失敗時は警告で継続）。
  - setup_logging と set_process_priority を使用してログ設定とプロセス優先度操作を行う呼び出しを追加。

### Changed
- n/a（初回リリースのため過去からの変更はありません）

### Fixed
- クラッシュ・再起動後の整合性対策:
  - send_order の2相的永続化（OrderSent → broker_order_id 保存 → OrderAccepted）により、クラッシュ時でも Reconciliation により状態回復可能な設計を採用。
  - OrderSentPendingError の扱いを明確化（broker_order_id を保存して OrderSent のまま残し、呼び出し元へ例外伝播）。
- .env パースの堅牢化:
  - クォート内エスケープやコメント処理の改善により実運用での .env 設定の耐性を向上。

### Security
- 環境変数やシークレットは .env のまま Git 管理しないことを README/テンプレートに明示（.env 書き出しテンプレートのコメントで注意喚起）。

---

（注）
- コード内コメントや docstring から推測して作成しています。実際のリリースノートは運用ポリシーや変更管理に基づき調整してください。