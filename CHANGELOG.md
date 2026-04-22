# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルはコード内容から推測して作成しています。

全般的な注意
- 表記は日本語です。  
- バージョン/日付はコードから推測した初回リリース相当の内容として 0.1.0 を記載しています（日付は作成日）。

## [Unreleased]
- （未リリースの変更はここに記載）

## [0.1.0] - 2026-04-22

### Added
- パッケージ初期実装として以下のモジュール・機能を追加。
  - kabusys.config
    - .env ファイルと環境変数の読み込み機能を提供。
    - .env/.env.local を自動で読み込む（プロジェクトルートを .git または pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env の各行を正確にパースする _parse_env_line を実装（export プレフィックス、引用符、バックスラッシュエスケープ、インラインコメントの考慮）。
    - Settings クラスを提供し、アプリケーション全体から設定値を取得可能に（必須変数取得時は未設定で ValueError）。
    - 各種設定プロパティを実装（J-Quants トークン、kabu API パスワード/ベース URL、LINE 設定、DB パス、paper trading 用パス、監視用パス、Kill Flag 設定や閾値、環境/ログレベルのバリデーションなど）。
  - kabusys.config_setup
    - 対話式ウィザードで .env を生成/更新する CLI を追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を用意。
    - 既存 .env 読み込み・既存値の再利用、シークレット表示（マスク）、選択肢チェック、書き込みフォーマットを実装。
    - .env ファイルの安全性に関するコメント（Gitコミット禁止）を出力。
  - kabusys.validate_config
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）とプレースホルダ値の警告。
    - KABUSYS_ENV 値および LOG_LEVEL の検証。
    - DUCKDB/SQLite パスの親ディレクトリ存在チェック（起動時自動作成の可能性を警告）。
    - config/*.yaml の存在確認および PyYAML があればパース検証（未インストール時はスキップ）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 未設定の警告、KILL_FLAG_CLEAR_ON_START の危険設定警告）。
    - --strict オプションで警告も失敗扱いにする機能。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番DB と分離。
      - プロセス優先度設定、PID・停止フラグ管理、DB 初期化（監視テーブル）を実施。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
      - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明示。
  - execution サブシステム
    - OrderRecord（order_record.py）
      - 注文状態を表す OrderState 列挙型と許容遷移テーブルを実装。
      - 状態遷移検証と更新を行う OrderRecord クラス（updated_at 自動更新、オプションフィールドの安全な更新）。
      - 不正遷移時に InvalidStateTransitionError を送出。
    - OrderManager（order_manager.py）
      - signal_queue からのシグナル受け取り、発注、状態管理の外向き API を実装。
      - create_order で signal_id 単位の重複防止（部分ユニークインデックスや DB 制約違反を DuplicateOrderError に変換）。
      - send_order においてクラッシュ安全を考慮した 2 相永続化（OrderSent を先にコミット → broker 呼び出し → broker_order_id をコミット → OrderAccepted へ遷移）を実装。
      - OrderRejectedError / OrderSentPendingError の扱いを定義（pending は broker_order_id を残す）。
      - sync_order による broker からの状態照合と部分約定のフィールド更新。
      - cancel_order におけるキャンセル不可能な状態チェック（終端状態の拒否）と broker へのキャンセル API 呼び出し。
    - ExecutionEngine（execution_engine.py）
      - Signal Queue Pull 型発注エンジンを実装。セッションスケジュール（8:50-9:10 シグナル処理、9:10-15:30 push ドレイン）を管理。
      - kill.flag 検査と KILL_FLAG_CLEAR_ON_START による起動時振る舞い制御（残留 flag の自動クリア可）。
      - PID ファイル書き出し、安全な削除処理。
      - シグナル処理フロー:
        - size_multiplier の適用（BUY のみ、100株刻み切り捨て）、数量 0 ならスキップ。
        - Gate 1（シグナルレベル）および Gate 2（エグゼキューションレベル、レート制限、リトライ）を統合したリスク検査。
        - DuplicateOrderError のハンドリング。
        - 発注成功/保留/失敗のロギングとリスクマネージャへの記録。
        - 発注後 position_entries への約定記録（BUY/pending の扱い差分、次営業日 fill_date を利用）。
        - 発注イベントの監視DBへの記録（監視DB があれば）。
      - push/drain の実装:
        - WebSocket push を受け取り _push_queue に入れ、sync_order を実行。
        - push 発生時も Gate 3（ドローダウン監視）を評価し、NG の場合は kill_switch を発動。
      - kill_switch 実装: 全 active 注文をキャンセルし、エンジン停止を誘導。
  - execution/kabu_client.py
    - kabu station REST API クライアントを追加（httpx 同期クライアント）。
    - トークン管理（遅延取得・再取得）を内部で完結する _get_token を実装。
    - 認証付きリクエストラッパ（401 のリトライ、自動トークン更新、429 の RateLimitError、5xx のサーバーエラー変換）。
    - レスポンス JSON パースに失敗した場合の BrokerAPIError 変換。
    - WebSocket push 処理のための stream_push サポート（broker 側に stream_push があれば ExecutionEngine が利用）。
    - kabu station の状態コード → 内部状態 ("open"/"partial"/"filled"/"cancelled"/"rejected") へのマッピングを提供。
  - DB / モニタリング
    - duckdb を利用したシグナル/portfolio 結合クエリを実装（ExecutionEngine の _read_signals）。
    - 監視用 SQLite 初期化を行う init_monitoring_db を呼び出す仕組みを追加（run scripts）。
  - ユーティリティ
    - プロセス優先度設定ユーティリティを使用して起動時に優先度を上げる処理を各 run_* スクリプトで実行。
    - ロギング初期化の共通セットアップを呼び出し（setup_logging）。

### Changed
- （初回リリースのため、既存挙動の変更点はなし）

### Fixed
- （初回リリースのため、既知の修正項目はなし）

### Security
- 機密値（トークン/パスワード）は Settings/ウィザードでシークレット取扱いとしてマスクや .env の Git コミット禁止注意を追加。

---

補足（コードから推測した運用上の注意）
- .env.example 相当のプレースホルダ値を残したままだと validate_config で警告が出るため、必須環境変数は実運用前に正しく設定すること。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定や KILL_FLAG_CLEAR_ON_START の扱いに注意すること（validate_config と run 時のガードあり）。
- ExecutionEngine は複数のコンポーネント（Broker, RiskManager, OrderRepository, Reconciler, MonitoringDB）に依存するため、実運用前に各種設定/テーブルの存在を確認すること。