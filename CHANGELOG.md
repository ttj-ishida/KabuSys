# Changelog

すべての破壊的変更はここに記録します。  
フォーマットは Keep a Changelog に準拠します。  

## [0.1.0] - 初期リリース
最初の公開リリース。KabuSys のコア設定管理、起動スクリプト、実行エンジン、注文状態管理、kabu station クライアントなどの基本機能を実装しました。

### Added
- パッケージのバージョンと公開情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 設定読み込み・管理
  - 環境変数および .env ファイル自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートの検出は .git または pyproject.toml に基づく（CWD 非依存）。
    - .env / .env.local の読み込み順序: OS 環境 > .env.local（override）> .env（未設定時セット）。
    - OS 環境変数の保護（既存キーは protected として上書き不可）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
    - .env のパース強化:
      - export KEY=val 形式に対応
      - シングル／ダブルクォート内でのバックスラッシュエスケープを考慮した値抽出
      - 非クォート値でのコメント処理（'#' の前に空白がある場合をコメントとみなす） 
  - Settings クラス（src/kabusys/config.py）を導入し、アプリケーション設定をプロパティ経由で取得可能に。
    - 必須キー取得時は未設定だと ValueError を送出する _require を提供。
    - env/log_level などのバリデーションと is_live/is_paper/is_dev ユーティリティを提供。
    - paper_trading 向けに paper_sqlite_path / paper_fill_mode の設定を追加。
    - 各種監視閾値（CPU/MEM/DISK）や PID / kill flag のパス設定を追加。

- 対話式設定ウィザード
  - python -m kabusys.config_setup により .env の作成・更新を対話式で行えるウィザードを実装（src/kabusys/config_setup.py）。
    - 入力項目: KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LINE_* 等
    - シークレット（マスク表示）、選択肢、デフォルト、説明のサポート。
    - 既存 .env の読み込み／再利用、保存前の確認、.env ファイルのフォーマット出力を実装。
    - 保存後に validate_config 実行を推奨するメッセージを出力。

- 構成検証 CLI
  - python -m kabusys.validate_config により起動前に設定不備（.env / config/*.yaml / 必須環境変数等）を検出するツールを実装（src/kabusys/validate_config.py）。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV / LOG_LEVEL の値検証と live 環境時の警告。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック。
    - config/*.yaml の存在確認と PyYAML がインストールされていればパース検証（PyYAML が無ければ警告）。
    - 本番環境（KABUSYS_ENV=live）向け追加ガード（LINE 設定未設定・KILL_FLAG_CLEAR_ON_START の警告等）。
    - --strict オプションで警告を FAIL（exit 1）扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト: python -m kabusys.run_execution（src/kabusys/run_execution.py）
    - Process 優先度を high に設定（utils/process_priority）。
    - paper_trading 環境では paper_trading 用 SQLite を使用して本番 DB と分離。
    - 停止フラグ / PID ファイル管理。
  - 監視ループ起動スクリプト: python -m kabusys.run_monitoring（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視は常に本番 sqlite_path を使用（環境にかかわらず）。
    - 停止フラグ検出でループを終了。

- 実行エンジンと注文フロー
  - ExecutionEngine（src/kabusys/execution/execution_engine.py）を実装:
    - シグナル読み取り（DuckDB）→ Gate1/2 を経て発注、WebSocket push をドレインして同期（Gate3）。
    - push_queue の実装と WebSocket ワーカースレッド（broker.stream_push がある場合に有効）。
    - kill_switch による全注文キャンセル（stop の公開エイリアス）。
    - 起動時に Reconciler によるリコンシリエーション実行（任意）。
    - セッションタイミング管理（signal_send_start/end, market_close）と PID ファイル管理。
    - 発注成功時の position_entries 登録（次営業日を fill_date として記録）。
    - 発注時の監視 DB ログ記録機能（MonitoringDB が渡された場合）。
    - size_multiplier 適用、注文単位切り下げなどのロジック。
  - OrderManager（src/kabusys/execution/order_manager.py）を実装:
    - create_order / send_order / sync_order / cancel_order の API を提供。
    - DuplicateOrderError の判定（同一 signal_id の active 注文重複防止）。
    - send_order はクラッシュ安全性を考慮した二相永続化:
      - OrderCreated → OrderSent を先に永続化してから broker 呼び出し
      - broker_order_id は最初に保存してから OrderAccepted への遷移を行う
      - OrderSentPendingError（注文番号発行済だが約定しないケース）を上位へ伝播
      - OrderRejectedError 発生時は Rejected に遷移して保存
    - sync_order は broker の状態を照合して適切に遷移／更新（部分約定の進行はフィールド更新のみ）。
    - cancel_order は終端状態チェックを行い不可能な場合は InvalidStateTransitionError を送出。

- 注文状態モデル
  - OrderRecord と OrderState（src/kabusys/execution/order_record.py）を実装:
    - 明示的な状態列挙（created, sent, accepted, partial, filled, closed, cancelled, rejected）。
    - 許容される遷移テーブルと遷移検証。InvalidStateTransitionError を導入。
    - transition_to により updated_at を自動更新し、broker_order_id / filled_qty / avg_fill_price / error_message をキーワード引数で更新可能。

- ブローカー API 抽象と kabu station 実装
  - Broker クライアント実装例として KabuStationClient（src/kabusys/execution/kabu_client.py）を提供:
    - httpx.Client を使用した同期 REST クライアント（将来 async 対応可能）。
    - トークン取得の遅延初期化と自動再取得（401 時に再取得してリトライ）。
    - レスポンス JSON パース失敗時やネットワークエラーを BrokerAPIError / RateLimitError 等に変換。
    - kabu ステータスコード → 内部ステータスへのマッピング実装。

- 監視・DB 初期化ユーティリティ
  - monitoring_db 初期化呼び出し（init_monitoring_db）を使用して監視テーブルの存在を保証（run_execution / run_monitoring）。

- ロギング・プロセス優先度ユーティリティ
  - setup_logging と set_process_priority を利用して起動時にログ初期化とプロセス優先度設定を行う（呼び出しポイントを全起動スクリプトで統一）。

### Changed
- （初版につき該当なし）

### Fixed
- （初版につき該当なし）

---

注:
- YAML のパース検証は PyYAML インストール時のみ実行され、未インストール時は警告してスキップします。
- paper_trading モードでは監視用 SQLite の使用先が切り替わります（data/paper_trading.db など）。
- データベースファイルや PID ファイルの親ディレクトリが存在しない場合、警告を出しつつ起動時に自動作成される想定です。