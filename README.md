README.md

プロジェクト名
KabuSys — 日本株自動売買システム（プロトタイプ）

プロジェクト概要
- KabuSys は日本株の自動売買を想定したシステムの実装サンプルです。
- 発注エンジン、リスクガード、リコンシリエーション、監視（Monitoring）、
  データ処理（カレンダー・ニュース収集等）、kabu-station クライアント（モック含む）
  を含み、開発／ペーパートレード／本番を想定した設定切替が可能です。
- 開発／テスト環境では MockBrokerClient を用いて kabu station を不要に動作確認できます。

主な機能
- 環境設定ウィザード（.env の対話式作成 / 更新）
- 設定検証ツール（.env と config/*.yaml の事前チェック）
- 実行エンジン（ExecutionEngine）:
  - シグナルに基づく発注ループ（Pull 型）と WebSocket Push のドレイン
  - Order State Machine と永続化（SQLite）
  - 3 階層のリスクガード（Gate1/2/3）
  - リコンシリエーション（再起動後の復旧）
- 監視ループ（SystemMonitor）: ポーリングでシステム健全性を記録
- broker クライアント層:
  - MockBrokerClient（テスト用）
  - KabuStationClient（kabu-station REST/WebSocket クライアント）
- データ関連:
  - DuckDB を使ったシグナル／ポートフォリオ処理、マーケットカレンダー管理
  - ニュース収集（RSS パース、SSRF 対策、整形）

前提条件
- Python 3.9+（typing、Path 等を使用）
- SQLite（標準ライブラリ）
- 推奨（機能に応じて）:
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config/*.yaml のパース検証に使用）
  - defusedxml（RSS パースの安全化）
- 必要パッケージはプロジェクト配布に requirements.txt があればそれを使用してください。
  例: pip install -r requirements.txt
  （無ければ上のライブラリを個別に pip install してください）

環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / 推奨:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL — kabu station の base URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート用（任意）
  - その他: PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等

設定の自動読み込み
- Settings モジュールはプロジェクトルート（.git または pyproject.toml を探索）を基準に .env を自動読み込みします。
- 優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順（簡易）
1. リポジトリをクローン
   - git clone <repo>
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もし requirements.txt が無い場合:
     - pip install duckdb httpx websocket-client PyYAML defusedxml
4. .env 作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードの完了後、.env が生成されます。
5. 設定検証
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict

使い方（実行）
- 実行エンジン（Execution）
  - 開発 / ペーパートレード環境（MockBrokerClient 使用）:
    - KABUSYS_ENV=paper_trading または development を .env に設定
    - python -m kabusys.run_execution
  - 実行時の挙動:
    - paper_trading の場合、orders/監視は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。
    - stop フラグ: プロジェクト下 data/stop_requested.flag を作成すると起動中ループが検出して停止します。
    - PID 管理: data/execution.pid 等に PID を書き込みます。
    - kill.flag: settings.kill_flag_path（デフォルト data/kill.flag）により起動拒否やキルスイッチが働きます。
- 監視（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を調整できます（デフォルト 60 秒）。
  - 監視は常に「本番 sqlite_path」を使用する点に注意（KABUSYS_ENV に依存しない設計）。
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]

開発・テストのヒント
- paper_trading / development では MockBrokerClient を使うため、kabu-station を立てる必要はありません。
- MockBrokerClient の fill_mode（instant / partial / never / reject）は Settings.paper_fill_mode で制御できます。
- 自動ロードを無効にして静的に環境変数を注入したいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- 発注の堅牢性:
  - OrderManager はクラッシュ耐性を考慮して OrderSent の永続化タイミングを工夫しています。
  - Reconciler は起動時に OrderSent の注文をブローカーに照合し、ポジション差分を検出します。

重要ファイル・挙動のまとめ
- .env / .env.local: 環境設定ファイル
- data/: データ格納ディレクトリ（DuckDB / SQLite / PID / stop/kill フラグ 等）
- config/*.yaml: 各種設定ファイル（存在確認と YAML パース検証あり。PyYAML があれば検査）

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py
    - 環境変数読み込みと Settings クラス（自動 .env 読込、必須チェック等）
  - config_setup.py
    - .env を対話式に作るウィザード
  - validate_config.py
    - .env と config/*.yaml を起動前に検査する CLI
  - run_execution.py
    - ExecutionEngine を初期化してセッションを実行するスクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト
  - execution/  (発注関連)
    - broker_api.py        — BrokerAPI のデータモデル・Protocol・ファクトリ
    - mock_client.py       — MockBrokerClient（テスト用）
    - kabu_client.py       — KabuStationClient（kabu-station REST + WS 実装）
    - broker_factory.py    — Settings に基づいてブローカークライアントを生成
    - order_record.py      — 注文状態モデルと遷移ロジック（純粋ロジック）
    - order_repository.py  — SQLite による永続化レイヤ
    - order_manager.py     — 注文作成／送信／同期／キャンセルの外向き API
    - execution_engine.py  — 発注エンジン（シグナル処理・WebSocket drain・kill switch）
    - reconciler.py        — 起動時のリコンシリエーション（OrderSent の照合、ポジション差分）
    - risk_manager.py      — Gate1/2/3 の実装（余力・レート制限・ドローダウン等）
  - data/  (データ関連)
    - calendar_management.py — マーケットカレンダー管理（DuckDB + J-Quants 連携）
    - news_collector.py      — RSS ニュース収集（SSRF 対策、正規化、保存）
  - monitoring/ (監視関連)
    - monitoring_db.py (参照されるが実装ファイルはここで管理)
    - system_monitor.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - strategy/ (戦略層: 実装場所)
  - その他: config/*.yaml（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml） — 必要に応じて生成・編集

注意事項
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- 実運用（KABUSYS_ENV=live）では、LINE などの通知設定や KILL フラグの取り扱いを慎重に設定してください（validate_config は live 設定時に警告を出します）。
- KabuStationClient を本番で使う場合は kabuステーションアプリのセットアップが必要です（ローカル REST / WebSocket を提供するソフトウェア）。
- 本リポジトリは実運用を保証するものではなく、設計／実装例として提供されています。実運用の前に十分なレビューとテストを行ってください。

問い合わせ・貢献
- バグ報告・機能要望は Issue を作成してください。
- コントリビュートの際はテストと文書の追加をお願いします。

以上。README に含めたい追加情報（例: 実際の requirements.txt、実行ログの例、データベーススキーマ、CI 設定など）があれば教えてください。