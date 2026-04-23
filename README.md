KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリです。  
主な責務はシグナルを受け取って発注を行う ExecutionEngine、システム監視ループ、環境設定ウィザード／検証ツール、ブローカークライアントやリスク管理などです。設計はテストしやすく、paper_trading（モックブローカー）と本番（live）を切り替えられるようになっています。

主な機能
--------
- 環境設定ウィザード（.env の対話式生成 / 更新）: kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の事前チェック）: kabusys.validate_config
- ExecutionEngine: シグナル読み込み → Gate（リスク判定） → 発注、WebSocket プッシュ処理、kill switch
- ブローカークライアント:
  - MockBrokerClient（テスト / paper_trading 用）
  - KabuStationClient（kabuステーション REST API 実装、将来的に本番対応）
- 注文状態管理（OrderRecord）と永続化（SQLite を用いた OrderRepository）
- リコンシリエーション（再起動時の OrderSent 照合とポジション差分検査）
- RiskManager（Gate1/2/3: シグナル検査、レート制限・サーキットブレーカー、ドローダウン監視）
- System monitoring（監視ループ、監視用 DB へのログ）
- Data モジュール（マーケットカレンダー管理、ニュース収集など）

前提（推奨）
-----------
- Python 3.10 以上（型ヒントに | 演算子等を使用）
- 推奨パッケージ（実行する機能に応じて必要）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - pyyaml（config 検証で YAML パースを行いたい場合）
- 標準ライブラリ: sqlite3 等

セットアップ手順
---------------
1. リポジトリを取得してプロジェクトルートへ移動
   - 例: git clone ... && cd kabusys

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要な依存をインストール（最低限の例）
   - pip install duckdb httpx websocket-client defusedxml pyyaml

   ※ 実際は requirements.txt を用意している場合はそれを使ってください。

4. 環境変数ファイルの作成
   - 対話式ウィザードを実行して .env を生成:
     - python -m kabusys.config_setup
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - その他の主な環境変数（任意 / デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - LOG_LEVEL — デフォルト: INFO
     - KABU_API_BASE_URL — kabu station のベース URL
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

使い方
-----
- 環境ウィザード（.env を作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- 実行エンジン（注文処理）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading or development では MockBrokerClient を使用
    - paper_trading は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に分離して記録
    - PID 管理、kill.flag に基づく起動制御あり

- 監視ループ（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒、デフォルト 60）

- DB 初期化（orders テーブル等）
  - 監視用 DB は run_monitoring/run_execution の起動フローで監視テーブルが初期化されます。
  - orders テーブルを手動で初期化したい場合（例）:
    - python -c "import sqlite3; from kabusys.execution.order_repository import init_orders_db; conn=sqlite3.connect('data/monitoring.db'); init_orders_db(conn); conn.close()"

運用上の注意
-------------
- KABUSYS_ENV=live に設定すると本番稼働モードになります。LINE 通知設定などを必ず確認してください。
- kill.flag（デフォルト: data/kill.flag）により起動制御・kill switch 制御が働きます。KILL_FLAG_CLEAR_ON_START 環境変数で起動時に自動クリアするか制御できます（本番では 0 を推奨）。
- PID ファイル（デフォルト: data/execution.pid）や停止フラグ stop_requested.flag がプロセス制御に使われます。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py
  - .env 自動ロードロジック、Settings クラス（環境変数アクセスの集中管理）
- config_setup.py
  - .env の対話式ウィザード
- validate_config.py
  - 起動前に環境変数や config/*.yaml の検査を行う CLI
- run_execution.py
  - ExecutionEngine の起動スクリプト（セッション管理、PID/stop フラグ）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- execution/
  - broker_api.py — ブローカー API の Protocol / データモデル / ファクトリ
  - broker_factory.py — Settings に応じたブローカー生成ファクトリ
  - kabu_client.py — kabuステーション REST API 実装
  - mock_client.py — テスト用モックブローカー
  - execution_engine.py — ExecutionEngine（シグナル処理、push drain、kill switch）
  - order_record.py — OrderState / OrderRecord（状態遷移ロジック）
  - order_repository.py — SQLite を用いた永続化層（orders テーブル）
  - order_manager.py — 発注ワークフロー（create/send/sync/cancel）
  - reconciler.py — 再起動時のリコンシリエーションロジック
  - risk_manager.py — Gate1/2/3 のリスク検査
- monitoring/
  - monitoring_db.py — 監視 DB 初期化・書き込み（run_monitoring で使用）
  - system_monitor.py — システムメトリクス監視（CPU/MEM/DISK 閾値等）
- data/
  - calendar_management.py — マーケットカレンダー管理（DuckDB を利用）
  - news_collector.py — RSS ニュース収集モジュール
- utils/
  - logging_setup.py — ロギング設定
  - process_priority.py — プロセス優先度設定（起動時に High へ切替）
- その他: config/*.yaml （system_config.yaml 等 — YAML の存在を validate_config が確認）

サンプル .env（抜粋）
-------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

付記
----
- YAML の内容検証には PyYAML が必要です（validate_config が自動検出）。
- 実際に本番ブローカー（kabuステーション）を使う場合は KabuStationClient の接続先設定や API パスワードを適切に設定してください。Broker の本番実装はプロジェクト内の注記（NotImplementedError）を参照してください。
- 各モジュールの詳細な使い方や API（OrderRequest / OrderStatus / RiskConfig など）はソース内の docstring を参照してください。

問題・貢献
---------
バグ報告や機能提案は Issue を作成してください。プルリクエストは歓迎します（テストとドキュメントを添えてください）。