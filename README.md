KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリです。  
主に以下を提供します。

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカークライアント抽象（kabu station 実装と Mock 実装）
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- リスクガード（3段階の Gate）
- リコンシリエーション（起動時の自動復旧）
- 監視プロセス（SystemMonitor のポーリング）
- データ周りのユーティリティ（マーケットカレンダー、ニュース収集等）
- .env ベースの設定管理 / 対話式ウィザード / 設定検証 CLI

主な設計方針は「DB と API 呼び出しを明確に分離」「クラッシュに強い永続化（2相永続化など）」「安全なリスクガード」です。

主な機能
--------
- 環境設定管理
  - 自動でプロジェクトルートの .env を読み込み（.env, .env.local）
  - 対話式ウィザードで .env を作成・更新（python -m kabusys.config_setup）
  - 起動前に設定を検証（python -m kabusys.validate_config）
- 発注（Execution）
  - ExecutionEngine によるシグナル処理／WebSocket ドレインループ
  - OrderManager／OrderRepository による注文ライフサイクル管理
  - Broker API 抽象（実運用用 KabuStationClient とテスト用 MockBrokerClient）
  - リスクガード（Gate1: シグナルレベル、Gate2: 実行レベル、Gate3: メトリクス）
  - Reconciler による OrderSent の突合せとポジション差分検出
- 監視
  - run_monitoring.py による定期ポーリング（MONITOR_POLL_INTERVAL 環境変数）
  - 監視用 SQLite / DuckDB 連携
- データ
  - DuckDB を用いたシグナル / ポートフォリオ処理
  - market_calendar の管理（J-Quants 連携想定）
  - ニュース収集（RSS）用モジュール（SSRF 対策、正規化、前処理）

必要条件
--------
- Python 3.10+
- 推奨 / 使用ライブラリ（最低限）:
  - duckdb
  - httpx
  - websocket-client
  - pyyaml (設定 YAML 検証に任意)
  - defusedxml (ニュース収集)
  - その他: sqlite3 は標準ライブラリ

セットアップ手順
----------------
1. リポジトリをクローン:
   - git clone <repo-url>

2. Python 仮想環境の作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール:
   - （プロジェクトに requirements.txt があれば）
     - pip install -r requirements.txt
   - 明示的にインストールする場合:
     - pip install duckdb httpx websocket-client defusedxml pyyaml

4. データディレクトリ作成:
   - プロジェクトルートに data/ を作成（デフォルトの DB パスに合わせるため）
     - mkdir -p data

5. .env の作成:
   - 対話式ウィザードで作成（推奨）:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成。必須環境変数:
     - JQUANTS_REFRESH_TOKEN=
     - KABU_API_PASSWORD=
   - 例（テンプレート）:
     - JQUANTS_REFRESH_TOKEN=your_value
     - KABU_API_PASSWORD=your_value
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO

6. 設定検証:
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

使い方（実行）
--------------
起動前の確認
- まず .env を用意し、validate_config で問題がないか確認してください。

監視プロセスの起動
- python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
  - 監視は常に本番用の sqlite_path を使用します（設定に依らず）

実行エンジンの起動（発注）
- python -m kabusys.run_execution
  - KABUSYS_ENV に応じて Mock クライアントを使用:
    - development / paper_trading → MockBrokerClient（デフォルト）
    - live →（現在未実装の旨 NotImplementedError を投げます）
  - paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます

設定の対話式編集
- python -m kabusys.config_setup
  - .env を対話的に作成／更新します。作成後は validate_config を推奨します。

主要な挙動（運用上のポイント）
- kill.flag（デフォルト: data/kill.flag）を検知するとセッション停止・注文キャンセルが走ります。
- 起動時に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START=1 で自動クリアできます（本番では推奨しません）。
- ExecutionEngine はシグナル処理と WebSocket push ドレインの二相構成です（スケジュールはコード内の EngineConfig を参照）。
- Order の永続化は SQLite（orders テーブル）で行います。init_orders_db() による初期化が想定されています。
- リスクガードにより余力不足やポジション上限、レート制限、サーキットブレーカー、ドローダウンで発注がブロックされます。

重要な環境変数
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意／上書き可能:
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABU_API_BASE_URL (kabu station の base URL)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番通知設定）
- KILL_FLAG_CLEAR_ON_START（起動時の kill.flag 自動クリア）
- MONITOR_POLL_INTERVAL（run_monitoring 用ポーリング間隔）

ディレクトリ構成（主なファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数読み込みと Settings クラス
- config_setup.py              — 対話式 .env ウィザード
- validate_config.py           — .env / config/*.yaml の起動前チェック CLI
- run_execution.py             — ExecutionEngine を起動するスクリプト
- run_monitoring.py            — SystemMonitor のポーリング起動スクリプト

パッケージ: src/kabusys/execution/
- broker_api.py                — BrokerAPIProtocol / データモデル / ファクトリ
- kabu_client.py               — kabu station REST API 実装（httpx + websocket）
- mock_client.py               — MockBrokerClient（テスト用）
- broker_factory.py            — Settings に応じたクライアント生成
- order_record.py              — Order の状態マシン（純粋ロジック）
- order_repository.py          — SQLite を用いた永続化層
- order_manager.py             — 外向きの注文 API（作成・送信・同期・取消）
- execution_engine.py          — ExecutionEngine 本体（シグナル処理・push 処理）
- reconciler.py                — 起動時の自動復旧・リコンシリエーション
- risk_manager.py              — 3 段階リスクガード

パッケージ: src/kabusys/data/
- calendar_management.py       — マーケットカレンダー管理（DuckDB, J-Quants 連携想定）
- news_collector.py            — RSS ニュース収集（SSRF 対策・前処理）

パッケージ: src/kabusys/monitoring/
- monitoring_db.py             — 監視用 DB 初期化 / ログ関数 等
- system_monitor.py            — 実際の監視ロジック（run_monitoring から参照）

ユーティリティ: src/kabusys/utils/
- logging_setup.py             — ロギング初期化
- process_priority.py          — プロセス優先度設定（プラットフォーム依存）

設定ファイル:
- config/ (期待される YAML ファイル)
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

備考 / 運用上の注意
-------------------
- .env は機密情報を含むため決して Git にコミットしないでください（config_setup.py のヘッダにも同様の注意書きがあります）。
- KABUSYS_ENV=live の場合は特に注意が必要です。validate_config は live 時に追加の警告（LINE 未設定など）を出します。
- KabuStationClient は kabu ステーションがローカルで起動していることを前提とします（API のベース URL は設定で変更可能）。
- paper_trading / development では MockBrokerClient を使用するため本番の売買を行いません。CI やローカル開発での検証は Mock を使って行ってください。
- 本リポジトリには運用スクリプト・ジョブ管理（systemd / cron 等）は含まれません。プロセス管理やログローテーションは別途ご用意ください。

ライセンス・貢献
----------------
- 本 README にはライセンス情報が含まれていません。実際のリポジトリの LICENSE ファイルを参照してください。  
- 貢献やバグ報告は Pull Request / Issue を通じて行ってください。

以上。プロジェクトの詳細実装や各モジュールの使い方はソースコード内の docstring を参照してください。必要であれば各機能（例: ExecutionEngine の動作フロー、OrderManager のトランザクションモデル等）に関する追加ドキュメントを作成します。