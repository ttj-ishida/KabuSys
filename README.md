README
======

概要
----
KabuSys は日本株の自動売買エンジン（プロトタイプ）を想定した Python パッケージです。  
主に以下の責務を持つコンポーネントで構成されています。

- 環境設定読み込み／ウィザード（.env）
- 設定検証 CLI（起動前チェック）
- 実際の発注を行う ExecutionEngine（ペーパートレード対応）
- 監視用の SystemMonitor（監視ループ）
- Broker クライアント層（kabu station 実装 & モック）
- 注文状態管理・永続化（SQLite）
- データ周り（DuckDB を使ったカレンダー/シグナル等）
- ニュース収集等の補助モジュール

機能一覧
--------
主な機能は次のとおりです。

- .env ウィザード（config_setup.py）
  - 初期 .env を対話形式で作成・更新
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の存在／基本整合性を検証
  - --strict オプションで警告も失敗扱いにできる
- 実行エンジン（run_execution.py）
  - Signal Queue ベースの発注フロー（発注前後の 3 段階リスクガード等）
  - paper_trading モードでは MockBrokerClient を使用して本番 DB と分離
- 監視ループ（run_monitoring.py）
  - SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で調整）
- ブローカークライアント
  - KabuStationClient（kabu station の REST / WebSocket）
  - MockBrokerClient（テスト / 開発用、fill_mode 制御）
  - create_broker_api / BrokerClientFactory による切り替え
- 注文永続化
  - OrderRepository（SQLite）
  - OrderRecord（状態遷移検証）
  - Reconciler（クラッシュ後の OrderSent レコード照合）
- データユーティリティ
  - カレンダー管理（next_trading_day 等）
  - ニュース収集（RSS 正規化・SSRF対策等）

セットアップ手順
--------------
1. リポジトリをクローンして Python 環境を作成します（任意の仮想環境）:
   - python -m venv venv
   - source venv/bin/activate  (Windows: venv\Scripts\activate)

2. 依存パッケージをインストールします（project に requirements.txt がある想定）:
   - pip install -r requirements.txt

   主要なランタイム依存（最低限）:
   - duckdb
   - httpx
   - websocket-client
   - defusedxml
   - PyYAML（config 検証を行う場合）
   - （標準ライブラリ）sqlite3, logging, argparse 等

   ※ requirements.txt がない場合は上のパッケージを個別にインストールしてください。

3. .env を作成します（ウィザードを推奨）:
   - python -m kabusys.config_setup
   対話に従って必須の値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を入力してください。

4. 設定を検証します:
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict

5. データディレクトリ等の権限を確認:
   - デフォルトの DB パスは data/kabusys.duckdb（DuckDB）および data/monitoring.db（SQLite）
   - 必要に応じて .env で DUCKDB_PATH / SQLITE_PATH を変更できます

使い方
------
基本的な実行方法（開発用 / ペーパートレード想定）:

- .env の初期化（対話式）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動（バックグラウンドで常駐する想定）
  - python -m kabusys.run_monitoring
  - ポーリング間隔をオーバーライド: export MONITOR_POLL_INTERVAL=30

- 実行エンジン起動（当日のセッションを実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に結果を保存します。

主要な環境変数（一部）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / デフォルトあり:
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
  - LOG_LEVEL — default: INFO
  - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用
  - PAPER_FILL_MODE — instant | partial | never | reject（paper_trading の動作制御）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 実行制御・安全機構

例: 最小 .env（ウィザードで作成する想定）
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO

重要な挙動・注意点
- Settings モジュールはプロジェクトルート（.git または pyproject.toml を基準）から .env を自動ロードします。OS 環境変数が優先され、.env.local が .env を上書きします。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用）。
- run_execution は起動時に kill.flag を検査し、KILL_FLAG_CLEAR_ON_START の値により自動クリアするか起動拒否するかを決定します。運用時は kill.flag の運用に注意してください。
- paper_trading モードは本番 DB と分離するよう設計されています（PAPER_TRADING_SQLITE_PATH）。
- run_monitoring は常に "本番 sqlite_path" を参照する設計です（監視データは本番 DB に保管されます）。

ディレクトリ構成
----------------
以下はパッケージ配下の主要ファイルと役割です（src/kabusys 配下）:

- __init__.py
  - パッケージ定義（__version__ 等）

- config.py
  - 環境変数読み込み / Settings クラス（アプリケーション設定）

- config_setup.py
  - .env 対話式ウィザード（python -m kabusys.config_setup）

- validate_config.py
  - 起動前の設定検証 CLI（python -m kabusys.validate_config）

- run_execution.py
  - ExecutionEngine を起動するエントリスクリプト

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- execution/
  - broker_api.py — BrokerAPIProtocol、データモデル、ファクトリ
  - kabu_client.py — kabu station REST/WebSocket 実装（KabuStationClient）
  - mock_client.py — MockBrokerClient（テスト用）
  - broker_factory.py — Settings に応じてクライアント生成
  - order_record.py — 注文状態（OrderRecord）と遷移検証
  - order_repository.py — SQLite ベースの永続化
  - order_manager.py — 外向きの注文管理（create/send/sync/cancel）
  - execution_engine.py — シグナル取得→発注→push ドレインのメインロジック
  - reconciler.py — 起動時リコンシリエーション（OrderSent の同期）
  - risk_manager.py — Gate1/2/3 によるリスク統制

- data/
  - calendar_management.py — マーケットカレンダーと営業日ロジック
  - news_collector.py — RSS 収集・前処理

- monitoring/
  - （監視 DB 初期化や SystemMonitor 実装はこの下に存在する想定）

- utils/
  - logging_setup.py, process_priority.py などユーティリティ（ロガー設定やプロセス優先度）

運用／開発メモ
--------------
- ログレベルは LOG_LEVEL 環境変数で制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- 設定検証では PyYAML がインストールされていると config/*.yaml をパースしてチェックします。未導入時は YAML 検証はスキップされます。
- KabuStationClient は HTTP (httpx) と websocket-client を利用します。実機運用時には kabuステーション® のローカルアプリが必要です。
- MockBrokerClient は fill_mode により発注挙動を制御でき、単体テストやローカル検証に便利です。

ライセンス・貢献
----------------
本ドキュメントはコードベースの概要説明です。ライセンスや貢献ルールはリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください。

備考
----
この README はコード内コメントと設計意図に基づいて作成しています。実行環境や運用ポリシーに応じて .env の設定や DB パス、ログの取り扱いを適切に調整してください。問題や改善提案があれば Issue を立ててください。