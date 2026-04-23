# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
- 環境設定関連
  - Settings クラス（kabusys.config）を実装し、環境変数から各種設定を取得する仕組みを提供。
    - 必須値取得時の _require() による未設定時のエラー通知。
    - env 値（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証。
    - paper_trading 用 DB パス、PID ファイル、kill フラグ、閾値（CPU/Memory/Disk）などのプロパティを実装。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）。
  - 自動 .env ロード機能
    - プロジェクトルートを .git または pyproject.toml で検出し、.env / .env.local を自動読み込み（OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサ実装（_parse_env_line）
    - export 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理をサポート。
- 環境設定ウィザード CLI
  - kabusys.config_setup: 対話式ウィザードにより .env の初期作成／更新を支援。
    - 各種設定項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE 設定など）。
    - 既存 .env 読み込み、シークレット表示マスク、選択肢の検証、保存確認、.env ファイル書き込みを実装。
- 設定検証 CLI
  - kabusys.validate_config: 起動前に .env と config/*.yaml の問題を検出する CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）とプレースホルダ検出（末尾が "_here" または "your_value"）。
    - KABUSYS_ENV / LOG_LEVEL の検証（有効値リスト）。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック（存在しない場合は警告）。
    - config/*.yaml の存在確認と（PyYAML が利用できる場合の）パース検証。PyYAML 未インストール時はスキップして警告。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定の確認、KILL_FLAG_CLEAR_ON_START の危険値検出）。
    - --strict オプションにより警告も失敗扱いで exit(1) を返すモードをサポート。
    - 情報 / 警告 / エラーを集約してコンソール出力。
- 実行エントリ・監視
  - run_execution: ExecutionEngine を起動する CLI 実装。
    - paper_trading 環境では専用の paper_trading SQLite DB を使用し、本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ (stop_requested.flag) 検出ロジック。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバックかつ警告）。
    - Monitoring は実行環境にかかわらず本番 sqlite_path を使用する仕様。
    - DB 接続（SQLite / DuckDB）の初期化処理を行い、ポーリング中の例外をログ出力して継続する設計。
- 発注エンジン
  - ExecutionEngine（kabusys.execution.execution_engine）を実装。
    - セッション制御（signal_send_start/ signal_send_end / market_close）。
    - run_session による一連の処理（リコンシリエーション起動、kill.flag 検査、PID 書き込み、WebSocket スレッド、シグナル処理、push ドレイン）。
    - _process_signals によるシグナル読み込み（DuckDB）→ Gate1/Gate2 のリスクチェック→発注の流れ。
    - Gate2 のレート制限リトライ（最大 3 回）、Circuit Breaker 検知時のシグナルループ停止。
    - 発注後の position_entries 更新（BUY / SELL の分岐、pending 処理の考慮）。
    - _drain_push_queue / _handle_push による push 処理（sync_order + Gate3 チェック）。
    - Gate3 が NG の場合は kill_switch を発動し全 active 注文をキャンセル。
    - kill_switch は全アクティブ注文の cancel を実行し、stop イベントを設定する。
    - WebSocket（push）に対応し、broker が stream_push を提供しない場合はスキップする安全設計。
- 注文管理
  - OrderRecord（kabusys.execution.order_record）
    - 注文状態列挙（OrderState）と状態遷移テーブルを実装。
    - transition_to による遷移検証と updated_at 自動更新、関連情報（broker_order_id, filled_qty, avg_fill_price, error_message）の任意更新。
    - 不正遷移時は InvalidStateTransitionError を送出。
  - OrderManager（kabusys.execution.order_manager）
    - create_order: signal_id の重複チェック（DB とメモリ）・client_order_id に uuid4 を採番して保存。SQLite の一部ユニーク制約違反を DuplicateOrderError に変換。
    - send_order: 二相永続化戦略を採用（OrderCreated→OrderSent を先に永続化 → broker 呼び出し → broker_order_id を先に永続化 → OrderAccepted へ遷移）。OrderRejected / OrderSentPending の取り扱いを実装。
    - sync_order: broker から最新ステータスを取得しローカル状態へ反映（同一状態で filled_qty/avg_fill_price のみ更新する最適化、OrderSent→Filled の際に OrderAccepted を経由）。
    - cancel_order: 終端状態のキャンセル不許可判定と broker cancel 呼び出し、Cancelled への遷移。
    - OrderSentPendingError の伝播や、エラー発生時のリスク/監視記録も考慮。
- ブローカー API クライアント
  - KabuStationClient（kabusys.execution.kabu_client）
    - httpx.Client を用いた同期 REST 実装。
    - トークン取得（/token）、X-API-KEY ヘッダ付与、401 時のトークン再取得・1回リトライ機構。
    - HTTP エラー・タイムアウト・ネットワークエラーを BrokerAPIError 等に変換。
    - 429 を RateLimitError として扱う。
    - kabu station の注文状態コードを内部ステータス（open/partial/filled/cancelled/rejected）にマッピング。
- 監視 DB 連携
  - monitoring DB 初期化（init_monitoring_db）呼び出しを run_execution / run_monitoring で実施し、監視テーブルの存在を保証。
  - ExecutionEngine 内で監視イベント（発注 latency 等）を監視 DB に記録する処理を追加（監視書き込み失敗時は警告で発注フローを継続）。

### 変更 (Changed)
- 本リリースは初回のため該当なし。

### 修正 (Fixed)
- 強化・堅牢化
  - ExecutionEngine の起動前に kill.flag を検査し、KILL_FLAG_CLEAR_ON_START に応じてクリア or 起動拒否する仕組みを確立。
  - send_order の二相永続化により、クラッシュ発生時でも broker_order_id が DB に残り、Reconciliation により状態回復可能（Issue 想定ケース対応）。
  - MONITOR_POLL_INTERVAL の不正値を検出してデフォルトにフォールバックする処理を追加。
  - .env 読み込みでファイルオープン失敗時に警告を出すようにして、プロセスを停止させない（堅牢化）。

### セキュリティ (Security)
- .env は Git にコミットしないよう生成ヘッダに注意喚起を追加（config_setup の .env 書き込み）。
- シークレット表示は UI 上でマスク（config_setup の対話表示）。

### 既知の制限 / 注意点
- YAML の内容検証は PyYAML がインストールされていないとスキップされます。パース検証を行う場合は PyYAML をインストールしてください。
- KabuStationClient は同期実装（httpx.Client）であり、将来の非同期対応は httpx.AsyncClient への移行で対応予定です。
- 一部のエラー（例: BrokerAPIError 等）は呼び出し元でそのまま伝播されます。適切なハンドリングが必要です。

---

今後の予定（例）
- 非同期クライアント対応（async/await）や詳細な監視ダッシュボード統合。
- より詳細なユニットテストと e2e テストの拡充。
- Reconciler 周りの拡張と自動修復ロジックの強化。