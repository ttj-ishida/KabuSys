KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株自動売買のための軽量フレームワークです。  
シグナルを読み取り発注を行う ExecutionEngine、起動時のリコンシリエーション、監視用の SystemMonitor、データ管理（DuckDB / SQLite）、および設定管理用の CLI を含みます。  
本リポジトリは実運用（live）／ペーパートレード（paper_trading）／開発（development）を想定した設計になっています。なお、kabuステーションの本番クライアントは現時点で未実装で、paper_trading / development では MockBrokerClient を使用します。

主な機能
--------
- 環境設定ウィザード（.env 作成 / 更新）: kabusys.config_setup
- 起動前設定検証 CLI: kabusys.validate_config（必須環境変数や config/*.yaml をチェック）
- ExecutionEngine: シグナル読み取り → Gate1/2 を経て発注、WebSocket push ドレイン
- Order 管理: OrderRecord（状態機械）、OrderRepository（SQLite 永続化）、OrderManager（送信 / 同期 / 取消）
- Reconciler: 起動時の OrderSent 注文の突合・ポジション差分検出
- RiskManager: 3段階のリスクガード（シグナルレベル / エグゼキューションレベル / メトリクスレベル）
- ブローカークライアント: MockBrokerClient（テスト用）と将来の KabuStationClient 実装
- データモジュール: マーケットカレンダー管理（DuckDB）、ニュース収集など
- 監視ループ: SystemMonitor ポーリング（SQLite を使用）

要件
----
- Python 3.9+
- 主な依存パッケージ（プロジェクトの pyproject.toml / requirements.txt を参照してくださいが、少なくとも）:
  - duckdb
  - httpx
  - websocket-client
  - pyyaml（config YAML 検証を行う場合）
  - defusedxml（RSS パース）
  - その他: sqlite3（標準ライブラリ）、typing、dataclasses など

セットアップ手順
--------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone <repo> && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または個別に: pip install duckdb httpx websocket-client pyyaml defusedxml

4. .env の作成（推奨） — 対話式ウィザード
   - python -m kabusys.config_setup
     - ウィザードに従って J-Quants トークンや kabu API パスワード、DB パスなどを入力します。
   - 生成された .env は絶対に Git にコミットしないでください（config_setup.py 内にも警告があります）。

5. 設定検証（起動前に実行）
   - python -m kabusys.validate_config
   - 厳格モード（警告を FAIL と扱う）: python -m kabusys.validate_config --strict

環境変数（重要）
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意／上書き可能（主なもの）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - 注意: live 設定時はいくつかの警告が出ます。本番運用は慎重に。
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL（kabu station API のベース URL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用・任意）
- KILL_FLAG_CLEAR_ON_START（本番で kill.flag を自動クリアするか: 0/1）

自動 .env ロード:
- プロジェクトルートにある .env / .env.local が起動時に自動で読み込まれます（OS 環境変数が優先）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用）。

使い方（主要コマンド）
---------------------
- 環境ウィザード（.env 作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- Execution（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV に応じて paper_trading は MockBrokerClient、live は未実装で起動不可
    - PID ファイル: data/execution.pid（デフォルト）
    - 停止フラグ: data/stop_requested.flag を作成するとエンジンが停止します
    - kill.flag による Kill Switch があり、設定により起動時動作が変わります

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト: 60）
  - 監視は sqlite_path を使用（KABUSYS_ENV に関係なく本番 sqlite を使用）

注意点・運用メモ
---------------
- paper_trading（PAPER_FILL_MODE）はモックの約定挙動を制御します: instant / partial / never / reject
- live 環境は現時点で本番ブローカークライアントが未実装です（BrokerClientFactory が明示的に NotImplementedError を出します）
- stop フラグ / kill.flag:
  - data/stop_requested.flag: 外部からループを安全に停止するために使用
  - KILL_FLAG_CLEAR_ON_START 環境変数で起動時に kill.flag を自動クリアするか制御
- DB 初期化:
  - orders テーブル等は init_orders_db(sqlite_conn) を使って冪等に初期化できます（コード内に init 実装あり）
  - monitoring 用 DB 初期化も init_monitoring_db を使用

ディレクトリ構成（主なファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理（自動 .env ロード含む）
- config_setup.py          — .env 作成ウィザード CLI
- validate_config.py       — 起動前設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

src/kabusys/execution/
- __init__.py
- broker_api.py            — Broker API のデータモデル / Protocol / ファクトリ
- broker_factory.py        — Settings に基づくブローカーファクトリ
- kabu_client.py           — KabuStationClient（REST + WebSocket 実装）
- mock_client.py           — テスト用 MockBrokerClient
- order_record.py          — OrderState / OrderRecord（状態遷移ロジック）
- order_repository.py      — SQLite 永続化層（orders テーブル定義含む）
- order_manager.py         — OrderManager（作成・送信・同期・キャンセル）
- execution_engine.py      — ExecutionEngine（シグナル処理 / push ドレイン）
- reconciler.py            — リコンシリエーション（OrderSent 照合、ポジション差分）
- risk_manager.py          — RiskManager（Gate1/2/3）

src/kabusys/data/
- calendar_management.py   — マーケットカレンダー管理（DuckDB）
- news_collector.py        — RSS ニュース収集（defusedxml 等で堅牢に実装）
- jquants_client.py        — （参照あり、J-Quants API 連携用クライアント想定）

src/kabusys/monitoring/
- monitoring_db.py         — 監視用 SQLite テーブル初期化 / ログ格納（参照される）

src/kabusys/utils/
- logging_setup.py         — ロギング設定ユーティリティ（参照される）
- process_priority.py      — プロセス優先度設定ユーティリティ（参照される）

開発・拡張メモ
---------------
- 本番ブローカークライアント（KabuStationClient）実装は既に存在しますが、BrokerClientFactory は live を未対応としているため注意してください（設計上 live 対応は将来的に有効化することが想定されています）。
- YAML 設定ファイル（config/*.yaml）が存在する場合、validate_config は PyYAML がインストールされていればパース検証を行います。未インストール時は検証をスキップして警告を出します。
- テストで環境変数の自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- logging や監視 DB への書き込みは障害に強い設計（例: 監視失敗時も発注フローは継続）になっていますが、実運用ではログ収集とアラート設定を整備してください。

サンプルコマンドまとめ
--------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring

最後に
-----
この README はリポジトリ内の主要なモジュールと起動フローに基づいて作成しています。実際の運用・デプロイ時は pyproject.toml / requirements.txt、及び config/*.yaml（存在する場合）を参照し、必要な外部サービス（kabuステーション、J-Quants API 等）へのアクセス設定を行ってください。何か不明点があれば具体的な状況（エラーメッセージ / 実行コマンド）を添えて質問してください。