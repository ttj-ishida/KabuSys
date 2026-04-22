KabuSys — 日本株自動売買システム
======================

概要
----
KabuSys は日本株向けの自動売買システムのコア部分を実装した Python パッケージです。
主に次を提供します。

- シグナルを元にした発注エンジン（ExecutionEngine）
- 注文状態遷移の管理（OrderRecord / OrderManager / OrderRepository）
- ブローカー API 抽象化（kabu station 実装 + Mock 実装）
- リスクガード（Gate1/2/3）
- 起動時のリコンシリエーション（Reconciler）
- 監視プロセス（SystemMonitor 起動スクリプト）
- 環境設定ウィザード (.env) と設定検証 CLI

特徴
----
- 明示的な状態遷移を持つ注文ステートマシン（不正遷移は例外）
- 発注フローのクラッシュ安全性（OrderSent の永続化・2相的手順）
- Paper trading（モック）と本番の切り替えを想定した設計
- 3段階のリスクガード（注文前・送信前・約定後）
- 起動時に未確定注文をブローカーと突合するリコンシリエーション機能
- .env ウィザードと validate_config による設定検証

前提条件 / 必要なライブラリ
--------------------------
（プロジェクトで想定されている主要ライブラリの例）
- Python 3.9+
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（config/*.yaml をパースして検証したい場合）
- その他（プロジェクトで追加のユーティリティがあれば requirements.txt を参照）

セットアップ手順
----------------

1. リポジトリをチェックアウトし、仮想環境を作成して有効化します。
   (例)
   python -m venv .venv
   source .venv/bin/activate

2. 必要なパッケージをインストールします（プロジェクトに requirements.txt がある想定）。
   pip install -r requirements.txt

   ※ もし requirements.txt が無い場合は少なくとも次を入れてください:
   pip install duckdb httpx websocket-client defusedxml PyYAML

3. .env を作成します（対話型ウィザード推奨）
   python -m kabusys.config_setup
   ウィザードが .env を作成・更新します。既存の .env を読み込んで Enter で再利用できます。

4. 作成した .env を検証します
   python -m kabusys.validate_config
   警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict

主要な環境変数
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（デフォルトあり / 推奨設定あり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — データ分析用 DuckDB のパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- KABU_API_BASE_URL — kabu station の base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番での通知用

その他:
- PAPER_FILL_MODE（paper_trading 時の fill 挙動: instant | partial | never | reject）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔、秒。デフォルト 60）

自動 .env 読み込み
-------------------
- 起動時に .env（プロジェクトルート）と .env.local（存在すれば上書き）を自動ロードします。
- OS 環境変数が優先され、.env.local は override=True（ただし既存の OS 環境変数は保護）で読み込まれます。
- 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

設定ファイル（config/*.yaml）
----------------------------
プロジェクトは複数の YAML 設定ファイル（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）を期待します。validate_config はそれらの存在をチェックし、PyYAML が利用可能であればパースも行います。
config ファイルのテンプレートはスクリプト（scripts/generate_config.py 等）で生成できる旨のメッセージが出ます。

使い方（主要スクリプト）
-----------------------

1. 環境ウィザード（.env 作成）
   python -m kabusys.config_setup

2. 設定検証
   python -m kabusys.validate_config
   --strict を付けると警告も exit(1) 扱いになります。

3. Execution エンジン（発注プロセス）を起動
   python -m kabusys.run_execution
   挙動:
   - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）を使用します。
   - 起動時に stop flag（data/stop_requested.flag）や kill.flag を確認します。
   - 実行中は pid ファイル（data/execution.pid 等）を書きます。停止時は削除されます。

4. Monitoring（監視プロセス）を起動
   python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
   - 監視は常に本番用 sqlite_path を使用します（環境にかかわらず）。

主要な設計上の注意点
--------------------
- Paper trading と本番 DB は分離されています。paper_trading 環境では paper_trading 用 SQLite に書き込まれます。
- KabuStationClient（本番向け REST/WebSocket 実装）は実装されていますが、BrokerClientFactory は live 環境での直接利用を明示的に未実装にしている箇所があります（将来的な実装に備えた設計）。
- OrderManager は「OrderCreated → OrderSent → OrderAccepted → ...」という明確な遷移を期待します。Invalid な遷移は InvalidStateTransitionError を投げます。
- 発注フローではクラッシュ耐性を考慮した永続化順序（OrderSent を先に永続化する等）を採用しています。
- Reconciler は起動時に OrderSent 状態の注文をブローカーに照合して同期します。
- kill.flag / stop_requested.flag により外部から安全にプロセスを停止できます。KILL_FLAG_CLEAR_ON_START により起動時に kill.flag を自動でクリアするオプションがあります（本番では慎重に扱ってください）。

ディレクトリ構成（src/kabusys の主要ファイル）
----------------------------------------
以下はリポジトリ内の主要モジュール（抜粋）と役割です。

- kabusys/
  - __init__.py                — パッケージ初期化、__version__
  - config.py                  — 環境変数/.env ロードと Settings クラス
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前の設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト（発注プロセス）
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - execution/
    - broker_api.py            — Broker API Protocol / データモデル / ファクトリ
    - kabu_client.py           — kabu station REST/WebSocket クライアント
    - mock_client.py           — MockBrokerClient（テスト・paper_trading 用）
    - broker_factory.py        — Settings に基づくクライアント生成
    - execution_engine.py      — ExecutionEngine 実装（発注ループ、WebSocket ドレイン等）
    - order_record.py          — OrderRecord（状態遷移ロジック）
    - order_repository.py      — SQLite 永続化
    - order_manager.py         — OrderManager（外向け API）
    - reconciler.py            — 起動時のリコンシリエーション処理
    - risk_manager.py          — Gate1/2/3 を実装するリスク管理
  - data/
    - calendar_management.py   — マーケットカレンダー管理（JPX / J-Quants 連携想定）
    - news_collector.py        — RSS ニュース収集（前処理 / 保存ロジック）
  - monitoring/
    - monitoring_db.py         — 監視用 DB 初期化・ログ関数（参照）
    - system_monitor.py        — 監視ロジック（参照）
  - utils/
    - logging_setup.py         — ロギング初期化ユーティリティ
    - process_priority.py      — プロセス優先度設定ユーティリティ
  - scripts/
    - generate_config.py       — config/*.yaml のテンプレート生成（参照される想定）

（注）実際のファイル構成はリポジトリの tree を参照してください。上記は主要モジュールの抜粋です。

トラブルシューティング / 補足
----------------------------
- validate_config は PyYAML 非インストール時に YAML の内容検証をスキップしますが、存在チェックは行います。PyYAML を入れると詳細な構文検査を行います。
- run_execution / run_monitoring は起動時に pid ファイルや flag ファイルを扱います。これらのパスは Settings で上書き可能です。
- 本番環境（KABUSYS_ENV=live）に設定する際は validate_config の警告や注意を必ず確認してください（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）。
- 新しい環境変数を追加した場合は .env と .env.local の読み込み順（OS > .env.local > .env）に注意してください。

開発・貢献
---------
コードの設計意図や既知の TODO は各モジュールの docstring / コメントに記載されています。Pull Request や Issue を送る際は、設計コメントを参照して整合性を保つようにしてください。

以上。README のサンプルはこのリポジトリの実際の requirements.txt、scripts、config テンプレートに合わせて適宜調整してください。