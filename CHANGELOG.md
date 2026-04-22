# CHANGELOG

すべての注目すべき変更を記録します。これは Keep a Changelog の形式に準拠しています。

## [Unreleased]
特になし。

## [0.1.0] - 2026-04-22

### Added
- 初回公開リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）

- 環境変数 / 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。環境変数から各種設定値を取得し、妥当性チェックを行うプロパティを提供。
    - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（_require にて未設定時は ValueError を送出）。
    - env/log_level 等は許容値チェックを行い、不正値は ValueError を送出。
    - Paper Trading 関連設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等）をサポート。
    - 各種閾値（CPU/MEMORY/DISK）や kill flag 等のパスを Path として取得。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み順序: OS 環境 > .env > .env.local（.env.local は override=True で読み込み）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env のパースロジックを詳細に実装（引用符つき値、エスケープ、export プレフィックス、行内コメントの扱いに対応）。

- 対話式設定ウィザード
  - config_setup CLI を実装（src/kabusys/config_setup.py）。.env の初期作成・更新を対話式で補助。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連など）。
    - シークレット項目は画面表示でマスクして取り扱い。
    - .env のテンプレート書き込み（.env に書き込む際のヘッダと推奨注意書きを含む）。

- 設定検証ツール（CLI）
  - validate_config CLI を実装（src/kabusys/validate_config.py）。
    - .env と config/*.yaml の存在や基本的妥当性を起動前に検出。
    - 必須環境変数の未設定やプレースホルダ値を検出してエラー/警告を出力。
    - KABUSYS_ENV、LOG_LEVEL の検証。KABUSYS_ENV=live の際は本番注意喚起を行う追加チェック。
    - YAML パーサ（PyYAML）がインストールされていない場合は YAML 内容検証をスキップして警告。
    - --strict オプションで警告を FAIL（exit code 1）扱いにできる。

- 実行エントリ・監視プロセス
  - run_execution スクリプトを実装（src/kabusys/run_execution.py）。
    - ExecutionEngine の起動フローをセットアップ（プロセス優先度設定、PID ファイル、stop フラグ検出、DB 接続の分離）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（settings.paper_sqlite_path）を使用して本番 DB と分離。
  - run_monitoring スクリプトを実装（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。デフォルト 60 秒。無効値はデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用する旨を明記。

- Execution エンジン本体
  - ExecutionEngine を実装（src/kabusys/execution/execution_engine.py）。
    - シグナル処理と WebSocket push ドレインの二段構成（signal_send_start / signal_send_end / market_close を設定）。
    - セッション開始時に Reconciler による起動時リコンシリエーションを実行（存在する場合）。
    - kill.flag の扱い: 起動時に kill_flag_clear_on_start により自動クリア可能。kill_switch() により全ループ停止とアクティブ注文のキャンセルを実行。
    - PID ファイルの作成と削除処理。
    - push 通知は _push_queue に取り込み、sync_order と Gate 3（ドローダウン監視）を実行。
    - position_entries への書き込み（買いは entry、売りは sell_date 更新）と例外時のログ継続。

- 注文状態管理と OrderManager
  - OrderRecord（状態機械）を実装（src/kabusys/execution/order_record.py）。
    - OrderState 列挙と許可遷移テーブルを定義。遷移検証を行い不正遷移は InvalidStateTransitionError を送出。
    - broker_order_id、filled_qty、avg_fill_price、error_message を遷移時に更新可能。
  - OrderManager を実装（src/kabusys/execution/order_manager.py）。
    - create_order/send_order/sync_order/cancel_order の外向き API を提供。
    - create_order: signal_id に対する active 注文の重複検査（DuplicateOrderError）。
    - send_order: 「OrderCreated → OrderSent を先に永続化」してからブローカー API を呼ぶ2相永続化パターンを採用（クラッシュ復旧と Reconciliation を考慮）。
      - OrderRejectedError / OrderSentPendingError の扱いを明確化。
    - sync_order: broker API の状態を取得してローカル DB に同期。部分約定の進行は差分更新で対応。
    - cancel_order: 終端状態はキャンセル不可として InvalidStateTransitionError を raise、そうでなければ broker cancel を呼ぶ。

- ブローカークライアント（kabu station）
  - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
    - httpx を使用した同期 REST クライアント（将来的に async に置換可能）。
    - トークン取得の遅延初期化と 401 発生時のトークン再取得＋1回リトライロジックを実装。
    - レスポンス JSON パース失敗やネットワーク例外を BrokerAPIError に変換して扱う。
    - HTTP 429 を RateLimitError に対応。
    - kabu station の注文状態コードを内部状態表現にマップする機能を実装。
    - WebSocket push 受信用に stream_push メソッドを期待する設計（存在しない場合は WebSocket スレッドをスキップ）。

- リスク管理 / Reconciliation の土台
  - Execution 側で RiskManager を使用する設計（Gate 1/2/3 のフローを実装）。
    - Gate 1: シグナルレベルチェック（注文値等）。
    - Gate 2: 実行レート制限 / サーキットブレーカー（リトライロジック、CB 発動時はシグナルループを停止）。
    - Gate 3: ドローダウン監視で NG の場合は kill_switch を発動。
  - Reconciler（外部参照）を組み合わせることを前提に設計。起動時に実行して注文同期を補助。

- 監視データベース・ログ
  - monitoring_db 初期化関数を呼び出して監視用テーブルが存在することを保証（init_monitoring_db を各スクリプトで呼ぶ）。
  - ExecutionEngine から監視 DB へ発注イベント（Sent 等）のログ記録を試み、失敗時は警告をログに残して処理継続。

### Notes / 注意事項
- .env は絶対に Git にコミットしないようにする旨を .env テンプレートに記載。
- config/*.yaml の内容検証は PyYAML が必要。PyYAML がない場合は検証をスキップして警告。
- run_monitoring は説明どおり「環境にかかわらず本番 sqlite_path を使用」します（設計上の意図に基づく動作）。
- KabuStationClient は同期 httpx.Client を使う同期実装。将来的な async 対応は容易に可能（httpx.AsyncClient に置換）。
- 本リリースでは多くの機能が初期実装されており、運用前に validate_config による事前チェックと、.env の適切な設定を必ず行ってください。

――以上――