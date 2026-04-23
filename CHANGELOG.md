# CHANGELOG

すべての注目すべき変更を時系列で記録します。  
このプロジェクトは「Keep a Changelog」形式に準拠しています。  

全般:
- バージョンはパッケージ情報から取得: __version__ = 0.1.0

## [0.1.0] - 2026-04-23

初回公開リリース。

### Added
- 設定 / 起動関連
  - 環境変数管理モジュールを追加（kabusys.config）。
    - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml を基準に探索）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
    - .env パーサーは export 形式、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント（適切な条件下）に対応。
    - _load_env_file による保護付き上書き（protected により OS 環境変数を上書きしない）。
    - Settings クラスを提供し、アプリケーション設定値をプロパティで取得可能（J-Quants トークン、kabu API パスワード、DB パス、ログレベル等）。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）。
    - 環境（KABUSYS_ENV）/ログレベルの検証ロジックを含む。

  - 対話式設定ウィザード（kabusys.config_setup）を追加。
    - python -m kabusys.config_setup で .env の初期作成・更新を支援。
    - 設定項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン等）を用意。
    - 既存 .env の読み込み、入力のデフォルト/マスク表示、確認プロンプト、.env の書き出し機能を実装。
    - .env ファイルに保存後の次ステップ案内（validate_config を推奨）。

  - 設定検証 CLI（kabusys.validate_config）を追加。
    - .env と config/*.yaml の設定不備を起動前に検出。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）とプレースホルダ検出。
    - KABUSYS_ENV、LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認。
    - config/*.yaml の存在確認と（PyYAML がインストールされていれば）パース検証。PyYAML 未インストール時は警告を出力して検証をスキップ。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の警告など）。
    - CLI オプション --strict を追加（警告も FAIL 扱いで exit(1)）。

- 実行ランナー
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加。
    - 設定に応じて paper_trading 時は専用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離。
    - プロセス優先度設定、PID/stop flag の使用、監視 DB 初期化、DuckDB 接続などの起動処理を実装。
    - スレッドで ExecutionEngine.run_session を起動し、停止フラグで安全に終了するフローを実装。

  - 監視ランナー（kabusys.run_monitoring）を追加。
    - SystemMonitor のポーリングループを実行。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視 DB は本番設定を参照）。

- Execution / 注文関連
  - ExecutionEngine（kabusys.execution.execution_engine）を追加。
    - シグナル処理（8:50-9:10）と WebSocket push ドレイン（9:10-15:30）を含むセッション実行フローを実装。
    - kill.flag の検査および KILL_FLAG_CLEAR_ON_START に応じた挙動（起動時クリア or 起動拒否）。
    - PID ファイル操作（作成/削除）と WebSocket スレッドの管理。
    - シグナル読み出しは DuckDB を使用し、portfolio_targets と JOIN して発注量・価格を決定。
    - Gate1/2/3 のリスクチェック、rate limit リトライ、API レイテンシ測定、position_entries の DuckDB 書き込みを実施。
    - 発注成功/保留/失敗時の監視 DB へのイベント書き込み（可能な場合）を行う。

  - 注文状態モデルと状態遷移（kabusys.execution.order_record）を実装。
    - OrderState 列挙型と遷移可能マップを定義。
    - OrderRecord dataclass に transition_to メソッドを実装し、遷移検証・updated_at 自動更新・オプションフィールド更新を行う。
    - 不正遷移時は InvalidStateTransitionError を送出。

  - OrderManager（kabusys.execution.order_manager）を実装。
    - create_order: signal_id の重複チェック（DB とメモリの両面）と部分ユニーク制約違反の DuplicateOrderError 変換。
    - send_order: 2相永続化を用いたクラッシュ耐性（OrderSent の永続化→broker 呼び出し→broker_order_id 永続化→OrderAccepted へ遷移）、OrderRejectedError / OrderSentPendingError の扱いを実装。
    - sync_order: broker の get_order_status と同期、部分約定の進行に対する更新処理、OrderSent→Filled/PartialFill の場合は OrderAccepted を経由する補正。
    - cancel_order: 終端状態の検出（キャンセル不可）と broker 側キャンセル呼び出し・Cancelled への遷移。
    - Cancel 不可状態セットは仕様により Filled も含めて定義（position tracking 的な理由）。

  - 注文リコンシリエーションを意識した設計（reconciler の統合ポイント、send_order の永続化設計など）。
  - ExecutionEngine 内での push 処理:
    - push payload から OrderID を取得し、broker_order_id から client_order_id を検索して sync_order を呼び出す。
    - push 受信時にも Gate 3（ドローダウン）を評価し、NG なら kill_switch を発動する。
    - WebSocket を持たない broker 実装を検出して警告スキップする実装。

- Broker / kabu API クライアント
  - KabuStationClient（kabusys.execution.kabu_client）を追加。
    - httpx を用いた同期 REST クライアント実装。
    - 遅延トークン取得と 401 時の自動再取得・一回リトライ。
    - レスポンス JSON パースエラーを BrokerAPIError に変換。
    - 429 (rate limit) を RateLimitError として扱う。
    - ネットワーク/タイムアウト例外を BrokerAPIError に変換して呼び出し元に伝達。
    - 将来の async 対応を考慮した設計（httpx.AsyncClient へ置換可能）。
    - websocket ライブラリを用いた push ストリーミング（stream_push のインターフェースを想定）。

- モニタリング / DB
  - monitoring 側での初期化を行う init_monitoring_db の呼び出しを各ランナーで実施。
  - 監視は sqlite（監視DB）と duckdb（分析用）両方を活用。

- ユーティリティ
  - ロギングセットアップ（setup_logging）とプロセス優先度設定（set_process_priority）を使用する起動フローを導入（高優先度に設定）。
  - stop/kill フラグファイルを使った安全停止機構を導入。
  - 多数のログ出力（INFO/WARNING/ERROR/CRITICAL）を通じた運用観点の情報提示。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 注意事項
- config/*.yaml の中身検証は PyYAML に依存する。PyYAML が未インストールの場合はパース検証をスキップして警告を出力する。
- .env は絶対にリポジトリにコミットしないでください（config_setup が生成する .env ヘッダに注意書きを追加）。
- ExecutionEngine の時間／挙動（シグナル処理/ドレイン/セッション終了）は運用環境のタイムゾーンや運用ルールに合わせて確認してください。
- PAPER_TRADING（paper_trading 環境）では発注は MockBroker を利用する想定で、監査用の DB は本番 DB と分離されます。

（今後のリリースではテストカバレッジ、ドキュメント、型注釈の強化、より詳細な監視イベント、broker 実装の抽象化改善などを予定）