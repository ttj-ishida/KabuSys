CHANGELOG
=========

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------

なし

0.1.0 - 2026-04-22
------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の主要コンポーネントを追加。
  - 実行スクリプト
    - python -m kabusys.run_execution: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度設定、PID ファイル管理、停止フラグ検出、スレッドでのセッション実行を実装。
    - python -m kabusys.run_monitoring: SystemMonitor のポーリングループを起動する監視用スクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境に関わらず本番用 sqlite_path を使用。
  - 設定管理とウィザード
    - kabusys.config: 環境変数読み込みと Settings クラスを追加。
      - 自動 .env ロード機能（プロジェクトルート判定: .git または pyproject.toml を基準）。優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env ファイルの読み込み挙動: override / protected（OS 環境の保護）をサポート。
      - rich な値検証: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE などの検証と適切なエラーを提供。
      - パス系設定は Path オブジェクトで提供（duckdb/sqlite 等）。
    - kabusys.config_setup: 対話式ウィザードで .env を作成/更新する CLI を追加。シークレットのマスク表示や選択肢、デフォルト値をサポート。
      - .env の読み書きフォーマットとテンプレートを提供。生成後に validate_config の実行を推奨するメッセージを表示。
  - 設定検証ツール
    - kabusys.validate_config: .env と config/*.yaml の事前検証 CLI を追加。
      - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML がある場合）を行う。
      - --strict オプションで警告を FAIL として扱い exit(1) を返す。
  - Execution サブシステム
    - ExecutionEngine: シグナル処理（8:50–9:10）と push ドレイン（9:10–15:30）を備えたセッション実行エンジンを実装。
      - run_session によるリコンシリエーション呼び出し（Reconciler がある場合）、kill.flag の扱い（KILL_FLAG_CLEAR_ON_START に依存）および PID ファイル管理を実装。
      - _process_signals: Gate 1/2 によるリスク検査、重複注文検出、発注（create/send）フロー、OrderSentPendingError の扱い、position_entries への書き込み（次営業日を計算）を実装。
      - push ドレイン: broker の get_positions に基づく Gate 3（ドローダウン）チェックと kill_switch 発動。
      - WebSocket ワーカースレッド（broker が stream_push を持つ場合のみ起動）による push ペイロード受信と同期処理。
    - run_execution: paper_trading モード時は paper_trading 用 SQLite を使用し、本番 DB と分離する挙動を追加。
  - 発注/注文管理
    - order_record: 注文状態マシン（OrderState）と OrderRecord データモデルを実装。許可された状態遷移を定義し、不正遷移時に InvalidStateTransitionError を投げる。
    - order_manager: OrderRecord と OrderRepository を組み合わせた外向き API を追加。
      - create_order: signal_id 単位の重複検出（DB 部分ユニーク制約にも対応）と client_order_id の UUID 発番。
      - send_order: クラッシュ耐性を考慮した 2 相永続化パターンを採用（OrderSent を先に永続化してから broker 呼び出し、broker_order_id を先にコミット、その後 OrderAccepted に遷移）。OrderRejectedError / OrderSentPendingError を適切に処理。
      - sync_order: broker 側の状態取得に基づく同期を実装。部分約定の進展は差分更新。
      - cancel_order: 終端状態チェックと broker 呼び出しによるキャンセル、ステート遷移を実装。
    - DuplicateOrderError を導入（同一 signal_id の active 注文が既に存在する場合）。
    - 状態変換と永続化により Reconciliation（再照合）で復元可能な設計を採用（Issue #32 に対応する設計方針）。
  - broker クライアント
    - kabu_client: KabuStation REST API クライアントを追加（httpx 同期クライアントを使用）。
      - Token 取得の遅延初期化と 401 時の再取得・リトライ処理を実装。
      - HTTP エラーの種類ごとに例外を変換（タイムアウト・ネットワーク・429 レート制限→RateLimitError・5xx→ BrokerAPIError 等）。
      - kabu の状態コードを内部ステータス ("open"/"partial"/"filled"/"cancelled"/"rejected") にマッピング。
      - WebSocket 経路（websocket ライブラリ）を用いた push 受信のための stream_push 呼び出し設計を想定。
  - データベース / 監視
    - monitoring_db の初期化ユーティリティ（init_monitoring_db）を使用して監視 DB の整合性を保証するフローを追加。
    - 発注イベントを監視 DB にログするためのフック（monitoring_db.log_trade_event の呼び出し）を ExecutionEngine に組み込んだ（監視 DB が渡された場合）。
  - その他ユーティリティ
    - .env パーサーの強化: export プレフィックス対応、クォート値内のバックスラッシュエスケープ処理、インラインコメントの扱いを改善。
    - パスの親ディレクトリ存在チェックと自動作成可能である旨の警告表示（validate_config）。
    - プロセス優先度設定ユーティリティ呼び出し場所の明確化（起動直後に High に設定）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 本番環境向けの注意点を複数追加:
  - validate_config にて KABUSYS_ENV=live の場合に LINE 設定や KILL_FLAG_CLEAR_ON_START の注意喚起を表示。
  - config_setup にて .env を絶対に Git にコミットしない旨を明記。

Notes / Usage examples
- 環境検証:
  - python -m kabusys.validate_config
  - 警告も fail としたい場合: python -m kabusys.validate_config --strict
- 設定ウィザード:
  - python -m kabusys.config_setup
- 実行スクリプト:
  - 監視: python -m kabusys.run_monitoring
  - 発注エンジン: python -m kabusys.run_execution
- 環境変数の自動ロードはプロジェクトルートを基準に行われ、テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

開発/既知の制約
- YAML ファイルの内容検証は PyYAML インストール時のみ行われます（未インストール時は警告を出してスキップ）。
- KabuStationClient は同期 httpx.Client を使用。将来的に非同期化する場合は httpx.AsyncClient への移行で対応可能。
- 一部外部コンポーネント（BrokerClientFactory、Reconciler、MonitoringDB 等）は外部実装に依存します（実装が揃っている前提で動作）。

もし追加で日付やリリースノートの粒度調整（たとえば細かいファイル単位の変更点やテストケースの追加等）を望まれる場合は、どのレベルの詳細を反映するか教えてください。