# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般
- このリポジトリは日本株自動売買システム「KabuSys」の初期実装を含みます。
- 環境変数や設定ファイルを中心に設計されており、実行用の CLI スクリプト（監視/エンジン起動）や発注フローのコアロジックが実装されています。

Unreleased
- なし

0.1.0 - 2026-04-22
------------------

Added
- プロジェクト初期リリース。
- 基本モジュールと CLI を追加：
  - kabusys.config_setup — 対話式 .env 設定ウィザード
    - python -m kabusys.config_setup で実行可能。
    - --env-file オプションで保存先を指定可能。
    - 複数項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 設定等）を対話式に入力して .env を生成。
  - kabusys.validate_config — 起動前の設定検証ツール
    - python -m kabusys.validate_config で実行可能。
    - --strict フラグで警告も FAIL（exit 1）扱いにできる。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および YAML パース検証（PyYAML が利用可能な場合）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の警告）。
- 環境設定と読み込み機構を追加（kabusys.config）：
  - プロジェクトルート探索ロジック（.git または pyproject.toml を基準）により .env / .env.local を自動ロード（OS 環境変数優先、.env.local は上書き）。
  - .env ファイルの柔軟なパース（export 形式、引用符とエスケープ、インラインコメント処理）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスで各種設定をプロパティとして提供（トークン、API パスワード、DB パス、paper_trading 用 DB、PID/KILL フラグパス、閾値、env/log_level バリデーション等）。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
- 実行スクリプトを追加：
  - kabusys.run_execution — ExecutionEngine 起動スクリプト
    - paper_trading 環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し本番 DB と分離。
    - 実行中の停止フラグ（data/stop_requested.flag）検出・PID 管理。
    - プロセス優先度設定、Logging 初期化。
  - kabusys.run_monitoring — SystemMonitor ポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
- 発注サブシステムのコア実装（execution パッケージ）：
  - order_record — 注文状態モデルと状態遷移ロジック
    - OrderState 列挙体の定義（created/sent/accepted/partial/filled/closed/cancelled/rejected）。
    - 許容遷移テーブルと transition_to メソッド（不正遷移で InvalidStateTransitionError を発生）。
    - DB には触れない純粋なビジネスロジックとして実装。
  - order_manager — 注文フロー制御と外向け API
    - create_order で signal_id に対する重複チェック（DB 側のユニーク制約違反を DuplicateOrderError に変換）。
    - send_order はクラッシュ頑健性を考慮した 2 相永続化（OrderSent を先に永続化 → broker 呼び出し → broker_order_id を保存 → OrderAccepted に遷移）。
    - OrderRejectedError、OrderSentPendingError の取り扱い（pending は OrderSent のまま broker_order_id を保持し再照合対象にする）。
    - sync_order は broker 側ステータスを照合して状態/約定数/平均価格を更新。
    - cancel_order は状態チェックのうえキャンセル API 呼び出しと Cancelled 遷移を行う。
  - execution_engine — Signal Queue 方式の発注エンジン
    - セッション制御（signal_send_start/End, market_close）に基づくフロー（シグナル処理 + push drain）。
    - Gate1（シグナルレベル）、Gate2（エグゼキューションレベル・レート制御、回復/サーキットブレーカー対応）、Gate3（ドローダウン監視による kill_switch 発動）。
    - kill_switch により全 active 注文をキャンセル・ループ停止。
    - WebSocket push のドレイン処理と push による同期フロー（_push_queue 経由）。
    - position_entries への書き込み（発注成功時に fill_date=翌営業日で記録）。
    - 監視 DB へのイベントロギング（MonitoringDB が提供されている場合）。
  - kabu_client — kabuステーション REST API クライアント
    - httpx を使った同期クライアント実装、トークン管理（遅延初期化と 401 時の自動再取得＋リトライ）。
    - レスポンス JSON パースのエラーハンドリング、HTTP ステータスに応じた例外変換（401/429/5xx など → BrokerAPIError / RateLimitError）。
    - kabu station の状態コードを内部ステータス（open/partial/filled/cancelled/rejected）へマップ。
    - 将来のストリーム対応（stream_push）を想定した実装（WebSocket サポートのため websocket をインポート）。
- モニタリング周り：
  - monitoring_db:init_monitoring_db 関数参照（監視テーブルの自動初期化を担保する呼び出し）。
  - run_monitoring/run_execution は起動時に init_monitoring_db を呼ぶことで監視テーブル存在を保証。
- ユーティリティ：
  - .env 書き込みテンプレート（config_setup 内で使用）に注意書き（.env を Git にコミットしないように）。
  - process_priority と logging_setup のユーティリティ参照（起動時に呼び出し）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 機密情報は .env に格納する設計。config_setup の出力ではシークレット値をマスクして表示。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。Settings._require で未設定時に例外が発生する。
- 実行前の手順:
  1. python -m kabusys.config_setup を実行して .env を作成。
  2. python -m kabusys.validate_config で設定を検証（--strict オプションで警告も FAIL 扱い）。
  3. 監視プロセス: python -m kabusys.run_monitoring
  4. 実行プロセス: python -m kabusys.run_execution
- config/*.yaml の存在および構文検証は PyYAML がインストールされている場合にのみ行われます。未インストール時は警告を出力して内容検証をスキップします。
- 本番起動時は KABUSYS_ENV=live の設定に慎重になること（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を確認してください）。
- paper_trading モードでは本番監視 DB と物理的に分離された PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用します。

作者連絡
- 変更点やバグ報告はリポジトリの Issue を利用してください。