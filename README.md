KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株の自動売買に必要な主要コンポーネントを備えたサンプル/実装基盤です。  
主に以下を提供します。

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカークライアント抽象化（kabu station 実装 + モック）
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- 起動時リコンシリエーション（Reconciler）
- 3段階リスクガード（RiskManager）
- 監視プロセス（SystemMonitor を回す run_monitoring）
- データ側ユーティリティ（マーケットカレンダー管理、ニュース収集など）
- 簡易な環境設定ウィザードおよび設定検証ツール

目的は「堅牢な発注フロー（クラッシュ安全／Reconciliation）とリスク統制」を示すことです。

主な機能
--------
- 環境変数管理と自動読み込み（.env/.env.local）
- 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
- 起動前設定検証ツール（python -m kabusys.validate_config）
- ExecutionEngine: シグナル読み込み → Gate1/2（発注前）→ 発注 → push ドレイン → Gate3（約定後監視）
- Order 状態管理（状態遷移検証、DB 永続化）
- Broker クライアント抽象化（MockBrokerClient と KabuStationClient）
- 起動時リコンシリエーション（OrderSent の突合せ + ポジション差分検出）
- 監視プロセス（monitoring 用ループ、SQLite + DuckDB を使用）
- データユーティリティ: JPX カレンダー管理、RSS ニュース収集（前処理 / SSRF対策等）

セットアップ手順
----------------

1. Python と依存ライブラリのインストール（推奨）
   - Python 3.9+ を想定（コードは typing/Path 機能を使用）
   - 必要ライブラリの例:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
     - PyYAML（validate_config の YAML パース用、任意）
   - 例:
     pip install duckdb httpx websocket-client defusedxml PyYAML

   （プロジェクトには requirements.txt がない想定なので、実行に必要なものを個別に入れてください）

2. リポジトリのルートに .env を用意
   - 対話式で作成する場合:
     python -m kabusys.config_setup
   - 既存の .env を使う場合はルートの .env/.env.local に必要な環境変数を設定してください。
   - 自動読み込みの挙動:
     - OS 環境変数 > .env.local > .env の優先順位で読み込まれます。
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

3. 必須環境変数（最低限設定が必要）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - 推奨・任意（validate_config 参照）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 時の別DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
     - KABU_API_BASE_URL（kabu station のベース URL）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番通知用）

   - 参考: python -m kabusys.validate_config で起動前に検証できます。

4. データディレクトリ作成
   - デフォルトでは data/ 以下に DB や PID/flag ファイルを作成します。必要に応じて作成権限を確認してください。

使い方
------

基本的な CLI スクリプト

- 環境設定ウィザード（.env の作成/更新）
  python -m kabusys.config_setup

- 設定検証（.env と config/*.yaml のチェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も FAIL 扱い

- ExecutionEngine（発注エンジン）起動
  python -m kabusys.run_execution

  注意:
  - KABUSYS_ENV=paper_trading または development の場合、MockBrokerClient が使われます（デフォルト）。
  - paper_trading のときは monitoring 本番 DB と分離された PAPER_TRADING_SQLITE_PATH が使用されます。
  - 実行中に data/stop_requested.flag を作成すると停止処理が走ります。
  - PID ファイルは data/execution.pid（設定で変更可）として書き込まれます。

- 監視プロセス起動
  python -m kabusys.run_monitoring

  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（デフォルト 60）。
  - 監視では sqlite_path（本番の監視 DB）と duckdb_path を使用します。

推奨起動順
1. .env を生成/確認（config_setup）
2. python -m kabusys.validate_config でチェック
3. python -m kabusys.run_monitoring を別プロセスで起動（監視）
4. python -m kabusys.run_execution でエンジン起動

主要設定 / デフォルトパス
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0（本番推奨。1 にすると起動時に kill.flag を自動クリアします）

ディレクトリ構成（主要ファイルの説明）
------------------------------------

src/kabusys/
- __init__.py
  - パッケージ定義・バージョン

- config.py
  - 環境変数の読み込みと Settings クラス。.env / .env.local の自動読み込みロジックを持ち、各種設定値（パス、トークン、閾値など）をプロパティとして提供します。

- config_setup.py
  - 対話式ウィザードで .env を生成/更新する CLI。

- validate_config.py
  - 起動前に .env と config/*.yaml の存在・値を検証する CLI。--strict モードあり。

- run_execution.py
  - ExecutionEngine の起動スクリプト。プロセス優先度設定や DB 接続、エンジンスレッド管理を行う。

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。監視用 DB に書き込む。

- execution/
  - __init__.py: エクスポートまとめ
  - broker_api.py: BrokerAPIProtocol、データモデル、例外、create_broker_api ファクトリ
  - kabu_client.py: kabu station REST API クライアント実装（httpx + websocket）
  - mock_client.py: テスト／開発用の MockBrokerClient
  - broker_factory.py: Settings に応じた Broker クライアント生成
  - order_record.py: Order の状態遷移モデル（純粋ロジック）
  - order_repository.py: SQLite を使った永続化層（init_orders_db 等）
  - order_manager.py: OrderRecord + OrderRepository + Broker を組み合わせる外向き API
  - reconciler.py: 起動時の注文突合せ・ポジション差分照合
  - execution_engine.py: ExecutionEngine（シグナル処理、push ドレイン、kill_switch 等）
  - risk_manager.py: Gate1/2/3 のリスク制御ロジック（トークンバケツ／サーキットブレーカー等）
  - その他: order_* 関連ファイル

- monitoring/
  - monitoring_db.py（参照される init_monitoring_db などがここにある想定）
  - system_monitor.py（SystemMonitor 実装）

- data/
  - calendar_management.py: JPX カレンダー管理（DuckDB ベース）
  - news_collector.py: RSS ニュース収集（正規化・SSRF 対策・前処理）

- utils/
  - logging_setup.py（ロガー初期化）
  - process_priority.py（プロセス優先度の設定）

注意事項 / 実運用に関する補足
----------------------------
- 本リポジトリは発注処理やブローカー API を扱うため、実環境での使用は慎重に行ってください。KABUSYS_ENV=live の場合は本番発注されます（現在 live 用のブローカークライアントは未実装箇所がありますので注意）。
- .env はセキュリティ上、決して Git にコミットしないでください (.gitignore に追加してください)。
- validate_config は起動前チェックに便利です。警告やエラーに従って設定を見直してください。
- DB 初期化: OrderRepository や monitoring の初期化関数（init_orders_db / init_monitoring_db）は起動時に呼ばれ、必要なテーブルを作成します（冪等）。
- KabuStationClient は実際に kabuステーション アプリが同じマシンで動作していることを前提とします。テスト時は MockBrokerClient を利用してください。

よく使うコマンドまとめ
--------------------
- .env 作成/更新:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- エンジン起動:
  python -m kabusys.run_execution

- 監視起動:
  python -m kabusys.run_monitoring

フィードバック / 貢献
--------------------
不具合報告や改善提案は issue を立ててください。Pull Request は歓迎します。

以上。必要なら README に追加したい具体例（.env テンプレート、起動例、ユースケース別手順など）を作成しますので教えてください。