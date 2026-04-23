Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従います。

0.1.0 - 2026-04-23
------------------

初回リリース。以下の主要機能と実装を含みます。

Added
- CLI / ユーティリティ
  - config_setup ウィザード（python -m kabusys.config_setup）
    - .env の対話的作成・更新を支援するウィザードを追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連など）を含む。
    - 秘密値は表示をマスク、選択肢・デフォルトのサポート、保存の確認ダイアログあり。
    - .env の書式整形と注意書き（Git にコミットしない旨）を出力。
    - --env-file オプションで .env の保存先を指定可能。
  - validate_config 検証ツール（python -m kabusys.validate_config）
    - .env および config/*.yaml の設定不備（必須環境変数未設定、不正値、ファイル未存在や YAML パースエラー等）を起動前に検出。
    - --strict オプションで警告も FAIL として exit(1) を返す。
    - PyYAML 未インストール時は YAML 内容検証をスキップして警告を出力。
    - 環境変数がプレースホルダ（末尾が "_here" や "your_value"）の場合は警告。
    - KABUSYS_ENV が "live" の場合は本番向けの警告（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START 等）。
- 設定管理
  - kabusys.config
    - プロジェクトルートを .git / pyproject.toml で探索し、.env/.env.local を自動ロード（OS 環境変数の保護と上書きルールを尊重）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途向け）。
    - .env パーサーは export プレフィックス、シングル/ダブルクォートのエスケープ、インラインコメントを考慮した堅牢な実装。
    - Settings クラスを導入（settings = Settings() で使用可能）。
      - 必須取得用の _require()、各種プロパティ（jquants_refresh_token, kabu_api_password, duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/MEM/DISK 閾値など）。
      - env, log_level, paper_fill_mode などの値検証（不正値は ValueError を raise）。
      - is_live / is_paper / is_dev 補助プロパティ。
- 実行スクリプト
  - run_execution（python -m kabusys.run_execution）
    - ExecutionEngine の起動スクリプト。プロセス優先度設定、PID ファイル管理、停止フラグ（data/stop_requested.flag）検出、DB 接続（paper_trading は専用 DB を使用）を実装。
  - run_monitoring（python -m kabusys.run_monitoring）
    - SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
- 発注 / 実行基盤（execution パッケージ）
  - OrderRecord（Order State Machine）
    - 状態列挙 OrderState を定義（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許可遷移テーブルと transition_to() 実装。無効遷移は InvalidStateTransitionError を raise。
    - メタデータ（broker_order_id, filled_qty, avg_fill_price, error_message, created_at, updated_at）を保持・更新。
  - OrderManager
    - DB（OrderRepository）と純粋ロジック（OrderRecord）を組み合わせた外向き API（create_order, send_order, sync_order, cancel_order）。
    - create_order: signal_id に対する active 注文の重複検出（DuplicateOrderError）。
    - send_order: クラッシュ安全性を考慮した二相的永続化戦略（OrderSent を先に永続化→broker 呼び出し→broker_order_id を永続化→OrderAccepted へ遷移）。
      - OrderRejectedError は Rejected に遷移して保存。
      - OrderSentPendingError（注文番号は発行されたが未約定等）は broker_order_id を永続化したまま OrderSent の状態で再スロー（Reconciliation 対象）。
    - sync_order: broker 側の状態を照合し DB を更新。部分約定の進行はフィールド直接更新で対応。
    - cancel_order: 終端状態ではキャンセル不可（InvalidStateTransitionError）、それ以外は broker.cancel_order を呼び Cancelled に遷移。
  - ExecutionEngine
    - Signal Queue Pull 型の発注エンジン実装（EngineConfig で target_date と時間帯を指定）。
    - 発注フローにおける Gate チェック（Gate 1: signal-level、Gate 2: execution-level（レート制限・サーキットブレーカー）、Gate 3: セッション中ドローダウン監視）。
    - size_multiplier 適用（BUY のみ）、注文生成と send の経過計測・監視 DB へのログ記録（監視 DB は optional）。
    - WebSocket push（broker.stream_push がある場合）を別スレッドで受け取り _push_queue に投入、drain で sync_order を呼び Gate 3 チェック。
    - kill_switch() 実装: 全 active 注文をキャンセルしループ停止、stop() はエイリアス。
    - セッションの起動時に Reconciliation を実行（reconciler が与えられた場合）。
- ブローカークライアント（kabu station）
  - KabuStationClient（kabu_client.py）
    - httpx を用いた同期 REST クライアント実装。
    - トークン管理（遅延初期化、401 時の再取得と再試行）を内蔵。
    - レスポンスの JSON パース失敗やネットワーク/タイムアウトを BrokerAPIError に変換。
    - 429 応答は RateLimitError を発生させる。
    - websocket を利用した push の受け取り（stream_push）を想定した設計。
- 監視
  - monitoring モジュールとの統合
    - init_monitoring_db による監視 DB テーブルの初期化（冪等）。
    - run_monitoring と run_execution の両方から監視 DB にログを書けるようにするフックを用意。

Changed
- プロジェクト構成
  - 初回公開にあたり、実行用スクリプト群、設定管理、発注エンジン/状態管理、ブローカークライアント、監視ループなどのコアコンポーネントを整備。

Fixed
- 該当なし（初回リリース）。

Security
- .env は絶対に Git にコミットしない旨を README/.env ヘッダに明記。
- .env 自動ロード時に OS 環境変数を protected として上書きを避ける設計を採用。

Notes / Implementation details
- デフォルトパス
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視 DB): data/monitoring.db
  - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
- Paper trading
  - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（既定: data/paper_trading.db）を使用し、本番 DB と完全分離。
  - PAPER_FILL_MODE によりペーパートレードの約定挙動を制御（instant, partial, never, reject）。不正値は例外を投げる。
- 環境検証ツール（validate_config）は PyYAML 不在でも実行可能だが、YAML パース検証はスキップする。
- MONITOR_POLL_INTERVAL が 0 以下・不正な値の場合はデフォルト 60 秒にフォールバックする（run_monitoring）。
- ExecutionEngine は 8:50 にシグナル処理、9:10 以降は push ドレインを行い、15:30 にセッション終了する既定のタイミングで動作する（EngineConfig でカスタマイズ可能）。
- Order 管理はクラッシュ時の不整合を考慮して設計（OrderSent の永続化順序、broker_order_id 永続化、Reconciliation による回復）。

このリリースには多くのコア機能が含まれます。既知の問題・改善予定は次回以降のバージョンで追記します。