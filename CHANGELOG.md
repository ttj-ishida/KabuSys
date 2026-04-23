# Changelog

すべての重要な変更を記録します。セマンティック バージョニング (SemVer) に準拠します。  
（参考: https://keepachangelog.com/ja/）

## [0.1.0] - 2026-04-23

Added
- 初回リリース。
- 環境/設定管理
  - .env ファイルおよび環境変数の自動読み込み機能を実装（os 環境変数 > .env.local > .env の優先順）。
  - .env のパースはシングル/ダブルクォート、エスケープ、コメント、`export KEY=...` 形式に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加（テスト用途）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能（例: jquants_refresh_token, kabu_api_password, duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, 各種閾値）。
  - Settings による値検証を実装（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE などの許容値チェック）。

- 設定ウィザード CLI
  - kabusys.config_setup: 対話式ウィザードで .env を初期作成・更新する機能を追加。
  - シークレット値は表示時にマスク表示、既存値の再利用、入力キャンセルのサポートを実装。
  - `.env` ファイルのテンプレート書き出しを実装（Git へのコミット注意を明記）。

- 設定検証 CLI
  - kabusys.validate_config: 起動前に .env と config/*.yaml の不備を検出する CLI を追加。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）。
  - プレースホルダ値の検出（末尾が `_here`、"your_value" 等）で警告提示。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック、KABUSYS_ENV=live の場合は本番用注意を警告。
  - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック。
  - PyYAML が利用可能な場合は config/*.yaml をパースして内容を検証。PyYAML 未インストール時はスキップ警告。
  - --strict オプションで警告を FAIL（exit code 1）として扱う機能。

- 実行スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db 等）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を上げ、PID ファイルの書き出し・停止フラグ検出を実装。
  - run_monitoring: SystemMonitor ポーリングループの起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0以下はデフォルトへフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。

- 発注エンジン / 注文管理
  - OrderRecord: 注文状態遷移を保持する純粋ロジックのデータモデルを実装（状態遷移の検証、updated_at 自動更新、オプションフィールドの更新）。
    - Enum による状態定義と許可された遷移マップを実装。InvalidStateTransitionError を定義。
  - OrderRepository / OrderManager による DB 統合（SQLite）と外向け API を実装。
    - create_order: signal_id の重複チェック（部分ユニークインデックス考慮）。UUID ベースの client_order_id 採番。
    - send_order: 2相永続化（OrderSent を先に永続化 → broker 呼出し → broker_order_id 永続化 → OrderAccepted へ遷移）によりクラッシュ時の回復性を向上。
    - send_order は OrderRejectedError, OrderSentPendingError を適切に扱う（pending は broker_order_id を保存して再照合対象に）。
    - sync_order: broker の状態を照合してローカル状態を更新。部分約定の進捗は差分更新で対応。
    - cancel_order: キャンセル不可能な状態を判定して例外を投げる。broker_order_id があれば API 呼び出しでキャンセル。
    - DuplicateOrderError を定義し、重複シグナルの保護を提供。

  - ExecutionEngine: シグナルプル型発注エンジンを実装。
    - シグナル処理（デフォルト 8:50-9:10）と WebSocket push ドレイン（9:10-15:30）の実行フロー。
    - Gate 構成によるリスク検査:
      - Gate1: シグナルレベル検査（check_signal）
      - Gate2: エグゼキューションレベル検査（レート制限、最大3回リトライ、サーキットブレーカー検知でシグナルループ停止）
      - Gate3: ドローダウン監視で閾値超過時に kill_switch 発動
    - kill_switch: 全ループ停止と active 注文のキャンセルを行う（外部停止 API として stop() を公開）。
    - WebSocket による push 処理は broker が stream_push をサポートしている場合に専用スレッドで受信し、_push_queue 経由で同期処理。
    - 発注成功時に position_entries テーブルへの記録（fill_date は翌営業日を使用）と、監視 DB へのトレードイベント記録（MonitoringDB が存在する場合）を行う。

- ブローカークライアント（kabu station）
  - KabuStationClient の実装（httpx を用いた同期 REST クライアント）。
    - トークン取得の遅延初期化と 401 時の再取得・リトライを実装。
    - HTTP エラー（タイムアウト / ネットワーク / 5xx / 429 等）を専用例外（BrokerAPIError / RateLimitError 等）に変換。
    - kabu ステーションの状態コード→内部ステータス変換マップを提供。
    - websocket 経由の push/stream 受信と統合可能（stream_push がある broker のみ）。

- モニタリング
  - monitoring_db 初期化ユーティリティと SystemMonitor を統合し、run_monitoring/run_execution からの初期化を実装。
  - 監視データ（発注イベントやレイテンシ等）を監視 DB に記録するフックを実装。

- パッケージ情報
  - パッケージバージョン __version__ = "0.1.0" を設定。

Changed
- n/a（初回リリース）

Fixed
- n/a（初回リリース）

Notes / 注意事項
- .env は絶対にリポジトリにコミットしないこと（config_setup にも注意喚起を記載）。
- 本番環境（KABUSYS_ENV=live）の設定は慎重に行ってください。validate_config の --strict モードを利用すると警告も失敗扱いにできます。
- ExecutionEngine / run_execution は kill.flag / PID 管理、及びプロセス優先度設定を行います。運用時の権限やファイルパスに注意してください。