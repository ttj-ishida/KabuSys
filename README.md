README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコードベースです。  
主な目的はシグナルを元に発注を行う ExecutionEngine、システム監視、設定管理・検証、およびテスト用のモックブローカーを提供することです。  
設計上、実際の発注周りは抽象化されており、開発/ペーパートレード環境ではモッククライアント、将来的に本番（kabuステーション）クライアントを選択できます。

主な特徴
--------
- 環境設定管理
  - .env の自動読み込み（プロジェクトルートにある .env / .env.local）
  - 対話式設定ウィザード (python -m kabusys.config_setup)
  - 設定検証 CLI (python -m kabusys.validate_config)（警告を厳密扱いする --strict オプションあり）
- 発注エンジン
  - Signal Queue Pull 型の ExecutionEngine（シグナル読込 → 発注 → WebSocket push ドレイン）
  - 発注の状態管理（OrderRecord の状態遷移、OrderRepository による永続化）
  - 再起動時の自動リコンシリエーション（Reconciler）
  - 3段階リスクガード（Gate1/2/3）を備えた RiskManager
- ブローカーインターフェース
  - BrokerAPIProtocol に基づく抽象化
  - テスト用 MockBrokerClient（fill_mode: instant/partial/never/reject）
  - kabuステーション用同期クライアント（KabuStationClient）
- 監視（Monitoring）
  - run_monitoring スクリプトで SystemMonitor のポーリングを実行（監視 DB は SQLite）
- データ処理
  - マーケットカレンダー管理（DuckDB 利用）
  - ニュース収集・正規化（RSS パーシング、SSRF 対策、トラッキング除去）

前提・依存
----------
最低限の環境:
- Python 3.9+（型注釈・Path などを利用）
- duckdb (pip)
- httpx (kabu client)
- websocket-client (kabu websocket)
- PyYAML（config/*.yaml のパース検証で使用、無くても動作するが警告が出る）
- defusedxml（ニュース収集で安全に XML を扱うため）

例: pip で導入する主要パッケージ
pip install duckdb httpx websocket-client PyYAML defusedxml

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone .../kabusys.git

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb httpx websocket-client PyYAML defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

4. .env を作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - 対話で J-Quants トークン、kabu API パスワード、DB パス、環境（development/paper_trading/live）等を入力して .env を生成します。

5. 設定検証
   - python -m kabusys.validate_config
   - 必要に応じて厳密モード:
     - python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
--------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（よく使うもの）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KILL_FLAG_CLEAR_ON_START: 0/1（起動時に kill.flag を自動クリアするか）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番でのアラート用（任意）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

実行方法
-------
- 環境設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗にする）: python -m kabusys.validate_config --strict

- 実行エンジン（発注）
  - python -m kabusys.run_execution
    - KABUSYS_ENV が paper_trading / development の場合は MockBrokerClient を使用（本番の発注を行いません）
    - paper_trading は paper_trading 用の SQLite DB（PAPER_TRADING_SQLITE_PATH）に記録される

- 監視プロセス
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔を制御可能（デフォルト 60 秒）
    - 監視 DB は settings.sqlite_path を使用（環境に依らず本番 sqlite を参照）

停止 / フラグ制御
- 停止シグナル: プロジェクトルートの data/stop_requested.flag を作成するとループが検知して終了します。
- Kill Switch: settings.kill_flag_path（デフォルト data/kill.flag）を用いて起動中の処理を強制停止・注文取消する仕組みがあります。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に既存の kill.flag を自動クリアします（危険なので本番は 0 推奨）。

主なファイル・ディレクトリ構成
----------------------------
（プロジェクトルートは src/kabusys 以下を想定しています。主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py                — パッケージ定義（__version__ 等）
    - config.py                  — 環境変数読み込み / Settings クラス（自動 .env ロード含む）
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 起動前設定検証 CLI
    - run_execution.py           — ExecutionEngine 起動ラッパー（PID/stop フラグ/DB 初期化含む）
    - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py            — BrokerAPIProtocol / データモデル / ファクトリ
      - broker_factory.py        — Settings に基づくブローカークライアント生成
      - kabu_client.py           — kabu station REST/WebSocket 実装
      - mock_client.py           — テスト用 MockBrokerClient
      - order_record.py          — Order の状態遷移ロジック（DB に触れない純粋ロジック）
      - order_repository.py      — SQLite による永続化（orders テーブル管理）
      - order_manager.py         — OrderRecord + OrderRepository + Broker を組み合わせた外側 API
      - execution_engine.py      — セッション/発注ループ実装（Signal 処理 + push ドレイン）
      - reconciler.py            — 再起動時の自動リコンシリエーション
      - risk_manager.py          — Gate1/2/3 のリスクガード
    - data/
      - calendar_management.py   — マーケットカレンダー管理（DuckDB）
      - news_collector.py        — RSS ニュース収集/正規化
      - jquants_client.py        — J-Quants API への接続（参照あり）
    - monitoring/
      - monitoring_db.py        — 監視 DB 初期化とログ周り（参照あり）
      - system_monitor.py       — システム監視ロジック（参照あり）
    - utils/
      - logging_setup.py        — ロギング設定ユーティリティ（参照あり）
      - process_priority.py     — プロセス優先度設定ユーティリティ（参照あり）

補足・設計ノート
----------------
- Settings クラスは環境変数をラップしており、バリデーションを行います。KABUSYS_ENV は development / paper_trading / live のいずれかである必要があります。
- ExecutionEngine は signal の読み取り（DuckDB）→ 発注 → push ドレイン → セッション終了というライフサイクルを持ちます。発注は OrderManager 経由で行われ、OrderSent 前に DB 保存を行うなどクラッシュ耐性が考慮されています（2相永続化や Reconciler による補正）。
- MockBrokerClient により本番 API が不要な単体テストやローカル実行が可能です（PAPER_FILL_MODE で挙動を制御）。
- config/*.yaml（system_config.yaml 等）は存在すれば内容検証されますが、PyYAML が無い場合は検証をスキップして警告が出ます。
- セキュリティ上の注意: .env は絶対にリポジトリにコミットしないでください。config_setup は README 内でも同様に警告を出します。

よくある操作のまとめ
-------------------
- 新規セットアップ: 仮想環境作成 → 必要パッケージインストール → python -m kabusys.config_setup → python -m kabusys.validate_config
- ローカルテスト実行: KABUSYS_ENV=development (デフォルト) のまま python -m kabusys.run_execution
- ペーパートレード: KABUSYS_ENV=paper_trading を .env に設定 → python -m kabusys.run_execution
- 監視プロセス起動: python -m kabusys.run_monitoring

ライセンス・貢献
----------------
（この README にはライセンス情報が含まれていません。実際のプロジェクトでは LICENSE ファイルを配置してください。）

問い合わせ・開発メモ
-------------------
- 本 README はコードベース（src/kabusys 以下）から抽出した概要です。内部の詳細実装（例: monitoring/system_monitor、data/jquants_client など）はソースコードのドキュメントを参照してください。
- 追加のユーティリティや CI 設定、リリース文書はプロジェクトルート（pyproject.toml / .github workflows 等）に格納することを推奨します。

以上。必要ならこの README を README.md 形式で出力するか、各コマンドの具体的な例（環境変数のテンプレートや .env.example の自動生成）を追記します。どの程度詳しく書き足しますか？