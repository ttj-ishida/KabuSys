# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

全般
- バージョン管理: パッケージ版の初期リリースとして記録します。
- バージョン: 0.1.0

## [0.1.0] - 初期リリース
リリース日: 未指定

### Added
- 環境・設定まわり
  - Settings クラスを導入し、環境変数からアプリケーション設定を取得する一元化された API を提供。
  - .env 自動ロード機能を実装（優先順位: OS 環境変数 > .env.local > .env）。プロジェクトルート探索は .git または pyproject.toml を基準に行うため、CWD に依存しない動作を実現。
  - 自動 .env ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env ファイル読み込みロジック（_parse_env_line）を実装。以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォート内のエスケープ処理
    - クォートなし値内のインラインコメント（前の文字がスペース/タブの場合のみ）
  - .env ファイルの書き込み/ウィザードを実装する CLI（kabusys.config_setup）。対話式ウィザードで主要な設定項目を作成・更新可能。
  - .env ファイル書き込み時に OS 環境変数を保護する機構（protected set）を導入。

- 設定検証
  - validate_config CLI を追加。起動前に.env と config/*.yaml（存在確認・パース）および主要な環境変数を検証。
  - 必須/任意の環境変数チェック、プレースホルダ値（末尾が "_here" や "your_value"）の検出と警告出力。
  - KABUSYS_ENV 値検証（development/paper_trading/live のみ有効）。live の場合は注意喚起の警告。
  - LOG_LEVEL の妥当性チェックと既定値処理。
  - DUCKDB_PATH/SQLITE_PATH の親ディレクトリ存在チェック（存在しない場合は警告）。
  - PyYAML の有無に応じて YAML パース検証をスキップする仕組み。
  - --strict オプションにより警告を FAIL（exit 1）扱いにできる。

- 実行スクリプト / サービス
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - paper_trading 環境では paper_trading 用の SQLite DB を使用して本番 DB と分離。
    - プロセス優先度設定、PID ファイル管理、停止フラグ（stop_requested.flag）、kill.flag の挙動（KILL_FLAG_CLEAR_ON_START を尊重）を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
    - stop フラグ検知による安全停止、例外発生時のログ出力とループ継続を実装。

- 発注系コア
  - OrderRecord: 注文状態を表す状態機械（state machine）と遷移ロジックを実装。許可された遷移テーブルと InvalidStateTransitionError を提供。状態遷移時に broker_order_id / filled_qty / avg_fill_price / error_message の更新をサポート。
  - OrderManager: OrderRecord（純粋ロジック）と OrderRepository（SQLite）を組み合わせた外向き API を実装。以下の主要機能を実装:
    - create_order: signal_id の重複チェック（部分ユニークインデックスの DB エラーを DuplicateOrderError に変換）
    - send_order: クラッシュ耐性を考慮した 2 相永続化（OrderSent 状態の永続化→broker 呼び出し→broker_order_id の永続化→OrderAccepted へ遷移）。OrderRejectedError / OrderSentPendingError の扱いを実装。
    - sync_order: broker の get_order_status を元に状態同期。部分約定の進行検出と更新。OrderSent→Filled/PartialFill の場合に OrderAccepted を経由して遷移させる補正ロジックを実装。
    - cancel_order: キャンセル不可状態のチェックおよび broker cancel 呼び出し、Cancelled への遷移。
  - execution_engine: Signal Queue Pull 型の ExecutionEngine を実装。主な機能:
    - セッション定義（signal_send_start / signal_send_end / market_close）と run_session の実装
    - シグナル処理ループ（_process_signals）と WebSocket push ドレイン（_drain_push_queue）
    - Gate 1/2/3 によるリスク判定統合（RiskManager を利用）
    - size_multiplier による買数量調整（100株単位切捨）、重複注文回避、発注遅延メトリクスの監視 DB ログ化（監視 DB が設定されている場合）
    - kill_switch の実装（全 active 注文をキャンセルしてループ停止）
    - WebSocket スレッド（broker が stream_push を持つ場合）との連携

- broker / API クライアント
  - KabuStationClient を追加（kabu station REST API 実装、同期 httpx クライアント）。
    - トークン取得（遅延初期化）と 401 の際の再取得＋リトライを自動処理。
    - HTTP エラー（401/429/5xx など）を専用例外（BrokerAPIError / RateLimitError）に変換。
    - websocket 等の push 処理（stream_push）と連携可能な設計。
    - kabu station の内部状態コードを内部ステータス ('open','partial','filled','cancelled','rejected') にマッピング。

- 監視 / DB 初期化
  - monitoring_db.init_monitoring_db を利用して起動時に監視テーブルの存在を保証。

- その他ユーティリティ
  - process_priority の設定（High）呼び出しを実行スクリプト起動時に行う。
  - logging_setup を行うユーティリティを利用してアプリケーションログ設定を標準化。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Notes / Implementation details
- .env のパースは限定的ルール（コメントの扱い、クォートとエスケープの解釈）で実装されています。既存の .env ファイルや特殊な値を使用する場合は validate_config や config_setup を使って検証・生成することを推奨します。
- ExecutionEngine / OrderManager 周りはクラッシュ・再起動時の整合性（OrderSent の残存、broker_order_id の先行永続化等）を考慮して実装されています。リコンシリエーション機構（Reconciler）との連携により、クラッシュ後の注文状態復元を図っています。
- run_monitoring と run_execution は stop flag / pid file / kill flag の存在を前提とした運用設計になっています。運用前に validate_config による検証を推奨します。

--- 

今後のリリースではテストカバレッジ、ドキュメント（運用手順・デプロイ手順）、より詳細なモニタリング指標、非同期対応（httpx.AsyncClient）などを追加予定です。