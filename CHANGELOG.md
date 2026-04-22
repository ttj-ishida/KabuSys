# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
セマンティック バージョニング: https://semver.org/

## [0.1.0] - 2026-04-22

初回リリース。KabuSys の設定管理・検証、監視・実行ランナー、発注エンジンとブローカークライアント、注文状態管理などのコア機能を実装しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 環境設定管理
  - Settings クラスを実装し、環境変数からの各種設定値をプロパティで提供（src/kabusys/config.py）。
    - 必須値の取得時に未設定なら ValueError を送出する _require() を用意。
    - PAPER_FILL_MODE や KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装。
    - DB パスや PID / kill flag パスなどを Path として取得するユーティリティプロパティを提供。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env の上書き時に OS 環境変数を保護する機能を実装。

- .env パーサと読み込み
  - .env ファイルのパースを強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、行内コメント処理など）を実装（src/kabusys/config.py）。
  - .env ファイルを読み書きするヘルパーを実装。

- 対話式設定ウィザード
  - .env の初期作成/更新を行う CLI ウィザードを実装（src/kabusys/config_setup.py）。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE 関連など）を含む。
    - シークレット値はマスク表示、選択肢・デフォルト値の提示、既存 .env の取り込み、確認プロンプト、ファイル保存機能を提供。
    - 書き込みフォーマットはコメント付きで .env を出力。

- 設定検証 CLI
  - 起動前に .env と config/*.yaml の不備を検出する検証ツールを実装（src/kabusys/validate_config.py）。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）、プレースホルダ検出。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェックと live 用ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - DUCKDB / SQLITE パスの親ディレクトリ存在チェック。
    - config/*.yaml の存在確認および PyYAML がインストールされている場合は YAML パース検証。
    - --strict オプションで警告を失敗扱いにできる CLI インターフェース。

- 実行ランナー
  - Execution (発注エンジン) 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - PID 管理、停止フラグ検出、プロセス優先度設定（utils 経由）を組み込む。

  - Monitoring (監視) 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。

- 発注システムコア
  - OrderRecord: 注文状態を表すデータモデルと状態遷移ロジックを実装（src/kabusys/execution/order_record.py）。
    - 状態列挙 OrderState と許可遷移テーブル、遷移検証で InvalidStateTransitionError を送出。
    - transition_to() により更新時刻やオプションフィールドを更新。

  - OrderRepository（SQLite）と組み合わせる OrderManager を実装（src/kabusys/execution/order_manager.py）。
    - create_order: signal_id に対する重複注文検出 (DuplicateOrderError) と DB 永続化。
    - send_order: クラッシュ耐性を考慮した 2 段階永続化フローを実装（OrderSent の事前保存 → ブローカー送信 → broker_order_id 永続化 → OrderAccepted 遷移）。
      - OrderRejectedError, OrderSentPendingError の扱いを実装。
    - sync_order: ブローカー状態照合と部分約定情報の更新、必要に応じた状態遷移（OrderSent→OrderAccepted 経由など）。
    - cancel_order: 終端状態チェックとキャンセル呼び出し、状態更新の実装。

  - ExecutionEngine: シグナル取得→Gate1/2 リスク検査→発注、push ドレインループ、Gate3（ドローダウン）検査、kill_switch の実装（src/kabusys/execution/execution_engine.py）。
    - シグナルの数量調整（size_multiplier、BUY のみ）、発注のレート制限リトライ（最大3回）、Circuit Breaker 時の挙動。
    - 発注成功/保留/失敗時のリスク管理記録、position_entries へ約定予定の記録（DuckDB への書き込み。発注 pending の扱い差異含む）。
    - WebSocket push の取り込み（_push_queue）と sync_order の呼び出し、push によるポートフォリオ再評価を行う Gate3。
    - セッション開始時のリコンシリエーション呼び出し（Reconciler が設定されている場合）、kill.flag の扱い（KILL_FLAG_CLEAR_ON_START による自動クリア可）。
    - PID ファイルの書き込み/削除、WS ワーカーのデーモンスレッド管理。

  - Broker クライアント
    - KabuStationClient を実装（src/kabusys/execution/kabu_client.py）。
      - httpx による同期 REST クライアント、トークン取得の遅延初期化と 401 時の自動再取得＋1回リトライ。
      - レスポンス JSON パース例外を BrokerAPIError に変換、タイムアウト・ネットワーク例外を適切に変換。
      - 429 を RateLimitError として扱うマッピング、kabu ステータスコード → 内部ステータス文字列マップを実装。
      - 将来の WebSocket/非同期対応を意識した設計（stream_push の有無で push スレッドを起動可否判定）。

- 監視用 DB 初期化ユーティリティ、プロセス優先度・ログセットアップ使用箇所
  - run_monitoring / run_execution で init_monitoring_db, setup_logging, set_process_priority を利用して起動整備を行う（モジュール参照を含む）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env の注意書きを出力するテンプレート（config_setup）があり、.env を誤ってコミットしないよう促すメッセージを含む。

---

注:
- YAML コンテンツの厳密検証は PyYAML のインストール有無に依存します（validate_config は PyYAML 未インストール時にパース検証をスキップして警告を出します）。
- 実際のブローカー API のエラー型（BrokerAPIError / RateLimitError / OrderRejectedError 等）は実装済みの契約に依存します。クライアント/工場から適切な例外が投げられることが前提です。