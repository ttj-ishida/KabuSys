# KabuSys

日本株自動売買システム（プロジェクト初期版）

バージョン: 0.1.0

概要
- KabuSys は日本株の自動売買を想定したモジュール群と起動スクリプト群を提供します。
- 発注ロジック、リスクガード、発注状態管理、リコンシリエーション、監視（Monitoring）やデータ処理ユーティリティ（カレンダー管理、ニュース収集など）を含む設計です。
- 実運用（live）・ペーパートレード（paper_trading）・開発（development）のモードを切り替えて動作します。現状、paper_trading / development はモッククライアントを用いた動作が実装されています。

主な機能一覧
- 環境設定ウィザード（.env の対話的生成）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml のチェック）: kabusys.validate_config
- 発注エンジン（ExecutionEngine）: シグナルに従った発注、WebSocket push ドレイン、kill switch 等
- ブローカークライアント抽象化: 実ブローカー（kabu station）と MockBrokerClient を切り替え可能
- OrderState 管理（OrderRecord）と永続化（SQLite: OrderRepository）
- リスク管理（RiskManager）: Gate1~3（重複・余力・ポジション上限・レート制限・サーキットブレーカー・ドローダウン）
- リコンシリエーション（Reconciler）: 再起動時に OrderSent を照合して状態回復
- 監視ループ（SystemMonitor 起動）: 監視用 DB への書き込み、ポーリングループ
- データユーティリティ: 市場カレンダー管理（DuckDB）、ニュース収集（RSS）など

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンしてプロジェクトルートへ移動
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
     ※ requirements.txt が無い場合は最低限以下が必要になる可能性があります: httpx, websocket-client, duckdb, PyYAML, defusedxml
4. 環境変数ファイルを生成（対話ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成/更新します（デフォルト: プロジェクトルート/.env）
5. 設定を検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict
6. DB 関連・データディレクトリ
   - デフォルトの DB パスは .env の DUCKDB_PATH / SQLITE_PATH（defaults: data/kabusys.duckdb, data/monitoring.db）
   - 必要に応じて data/ ディレクトリを作成（起動時自動作成の処理も一部ありますが手動作成を推奨）

主要な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意（便利な上書き/設定）:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading モード用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - KABU_API_BASE_URL: kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番通知用（任意）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60、run_monitoring に適用）

使い方（起動例）
- 環境設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup
- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit(1) として扱う
- ExecutionEngine を起動（本番/テスト共通の起動スクリプト）
  - python -m kabusys.run_execution
  - paper_trading / development では MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH に記録されます
  - run_execution は data/execution.pid を書き、 data/stop_requested.flag の検出で停止します
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）
  - 監視は settings.sqlite_path（本番 DB）を使用します

停止・Kill スイッチ
- kill.flag（デフォルト: data/kill.flag）を置くことで発注ループが kill_switch を発動し、全 active 注文をキャンセルして停止します。
- 起動時に kill.flag が存在している場合、KILL_FLAG_CLEAR_ON_START=1 で自動クリアして起動する挙動が設定可能（本番は 0 推奨）。
- 外部停止フラグ: data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検出して優雅に終了します。

開発・テスト向けのポイント
- 環境自動ロード:
  - プロジェクトルートに .env/.env.local があれば自動でロードされます（OS 環境変数が優先、.env.local は上書き可）。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで便利）。
- MockBrokerClient:
  - settings.paper_fill_mode の設定によって挙動を変えられます（instant / partial / never / reject）。
  - テスト時は MockBrokerClient を使用し、外部サービスに依存せず単体テストが可能です。
- DB の初期化:
  - OrderRepository, monitoring などは起動時に必要テーブルを初期化する関数（例: init_orders_db, init_monitoring_db）を呼んでいます。明示的に初期化が必要な場合はこれらを呼んでください。

ディレクトリ構成（主なファイル / モジュール）
- src/kabusys/
  - __init__.py: パッケージ定義（__version__ = "0.1.0"）
  - config.py: 環境変数読み込み・Settings クラス（.env 自動ロード、必須チェック等）
  - config_setup.py: .env の対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py: 起動前チェック CLI（python -m kabusys.validate_config）
  - run_execution.py: 発注エンジン起動スクリプト（ExecutionEngine）
  - run_monitoring.py: 監視ループ起動スクリプト（SystemMonitor）
  - execution/
    - broker_api.py: BrokerAPIProtocol、データモデル、例外、ファクトリ
    - broker_factory.py: Settings によるクライアント生成
    - kabu_client.py: kabu station REST API 実装（httpx）
    - mock_client.py: MockBrokerClient（テスト/開発用）
    - order_record.py: 注文状態のデータモデルと遷移ロジック
    - order_repository.py: SQLite 永続化レイヤ（orders テーブル初期化含む）
    - order_manager.py: 発注フロー（create/send/sync/cancel）
    - execution_engine.py: ExecutionEngine（シグナル処理／WebSocket ドレイン等）
    - reconciler.py: リコンシリエーション（再起動時の状態復旧）
    - risk_manager.py: リスクガード（Gate1~3）
  - monitoring/
    - monitoring_db.py: 監視用 SQLite 初期化・ログ記録（init 関数が呼ばれる想定）
    - system_monitor.py: システム監視ロジック（使用される想定）
  - data/
    - calendar_management.py: マーケットカレンダー管理（DuckDB ベース）
    - news_collector.py: RSS ニュース収集・整形・保存
  - utils/
    - logging_setup.py: ロギング初期化（起動スクリプトで使用）
    - process_priority.py: プロセス優先度設定ユーティリティ

補足
- 本リポジトリは設計と主要ロジックを示す実装が中心です。live 環境向けブローカークライアント（kabu station の完全実装）や運用用のデプロイ設定は部分的に未実装・未検証箇所があります。live 運用は十分なテストとレビューを行ってください。
- config/*.yaml の雛形が必要な場合は scripts/generate_config.py（コメントで参照されている）等で生成する想定です。PyYAML がない場合、validate_config は YAML 検証をスキップします。
- セキュリティ: .env は絶対に Git にコミットしないでください（config_setup でもコメントで注意喚起あり）。

問い合わせ・開発
- バグ報告や機能追加は Issue を立ててください。
- 主要な変更はテストとリコンシリエーションの影響を必ず確認してください（OrderState/永続化の互換性に注意）。

以上。必要があれば README にさらに使用例、サンプル .env、デプロイ手順（systemd / Docker Compose 等）を追加します。どの情報を優先して追記しますか？