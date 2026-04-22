README
======

概要
----
KabuSys は日本株向けの自動売買システム向けライブラリ／実行フレームワークです。
主に以下を含みます。

- シグナル駆動の発注エンジン (ExecutionEngine)
- 注文管理（OrderManager / OrderRepository / OrderRecord）
- ブローカークライアントの抽象化（実ネット用の KabuStationClient とテスト用の MockBrokerClient）
- リスクガード（3段階の Gate）
- 起動時リコンシリエーション（Reconciler）
- 監視プロセス（SystemMonitor を定期実行する run_monitoring）
- 環境設定ウィザード（.env 生成）と設定検証 CLI

機能一覧
--------
- 環境変数・.env 自動読み込み（.env / .env.local、OS 環境変数優先）
- 対話式 .env ウィザード（python -m kabusys.config_setup）
- 起動前設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数の確認、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在確認
  - --strict オプションで警告も FAIL 扱い
- ExecutionEngine によるシグナル処理（シグナルプル型）と WebSocket プッシュドレイン
- Order の状態遷移管理と永続化（SQLite）
- ブローカー API 抽象化（Protocol）と Mock 実装（テスト用）
- サーキットブレーカー、レート制限、ポジション上限などのリスク管理
- 起動時のリコンシリエーション（OrderSent 状態の同期、ポジション差分検出）
- DuckDB を用いたデータアクセス（シグナルやカレンダー等）
- ニュース収集（RSS 取得・正規化・保存） — defusedxml 等を利用した安全化処理

セットアップ手順
----------------
1. Python (3.10+) を用意してください。

2. 依存パッケージをインストールします（プロジェクトで requirements.txt が無ければ以下を参考に）。
   - 必須（開発 / 実行に便利）:
     - duckdb
     - httpx
     - websocket-client
     - defusedxml
   - 設定検証で YAML パースを行いたい場合:
     - PyYAML
   - 例:
     pip install duckdb httpx websocket-client defusedxml PyYAML

   注意: MockBrokerClient を使う開発（paper_trading / development）では httpx/websocket は不要な場合がありますが、
   実ブローカー接続 (KabuStationClient) を利用するには必要です。

3. プロジェクトルートに data ディレクトリなど必要な親ディレクトリを作成しておくと警告が減ります。
   例:
     mkdir -p data

4. .env の作成
   - 対話式ウィザードで作成するのが簡単です:
       python -m kabusys.config_setup
   - もしくは手動で .env を作成してください（後述のサンプル参照）。

5. 設定検証
   - 作成・編集後は必ず検証してください:
       python -m kabusys.validate_config
     - 警告も許容しない場合:
       python -m kabusys.validate_config --strict

使い方（主なコマンド）
--------------------

- 環境設定ウィザード（.env を生成／更新）
    python -m kabusys.config_setup
  - 対話形式で主要な環境変数を入力し .env を保存します。

- 設定検証
    python -m kabusys.validate_config
  - --strict を付けると警告も exit(1)（失敗）になります。

- 実行エンジン起動（本番相当 / ペーパートレードのセッション実行）
    python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading や development の場合は MockBrokerClient が使われます。
  - paper_trading の場合、専用の SQLite（デフォルト: data/paper_trading.db）に分離されます。
  - 実行中に data/stop_requested.flag を作成すると安全に停止を促すことができます。
  - PID ファイルは data/execution.pid（デフォルト）に書き込まれます。

- 監視ループ起動（SystemMonitor のポーリング）
    python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を秒単位で調整（デフォルト 60）。
  - 監視は sqlite_path（通常: data/monitoring.db）を使用します（KABUSYS_ENV にかかわらず本番 sqlite を使用）。

主要な環境変数
----------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 任意（よく使われるもの）:
  - KABUSYS_ENV  — 実行環境 ("development", "paper_trading", "live")
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"
  - KABU_API_BASE_URL — kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — アラート通知（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアするか（0/1）

- テスト用:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化

ミニマム .env（例）
------------------
以下は最小限の設定例（実運用では secret 値を実際に設定してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KABU_API_BASE_URL=http://localhost:18080/kabusapi
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
KILL_FLAG_CLEAR_ON_START=0

ディレクトリ構成
----------------
（省略表現：プロジェクトルート直下に src/kabusys 以下が配置される想定）

- src/
  - kabusys/
    - __init__.py                — パッケージ定義（バージョン等）
    - config.py                  — 環境変数読み込みと Settings クラス
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 起動前設定検証 CLI
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — Monitoring 起動スクリプト
    - execution/                 — 発注エンジン関連
      - __init__.py
      - broker_api.py            — BrokerAPI Protocol、データモデル、ファクトリ
      - broker_factory.py        — Settings に応じたクライアント生成
      - kabu_client.py           — KabuStation REST / WebSocket 実装
      - mock_client.py           — テスト用 MockBrokerClient
      - execution_engine.py      — ExecutionEngine（セッション／ループ制御）
      - order_manager.py         — 注文作成・送信・同期・キャンセルの外向き API
      - order_record.py          — Order 状態遷移ロジック（ビジネスロジック）
      - order_repository.py      — SQLite 永続化層
      - reconciler.py            — 起動時リコンシリエーション
      - risk_manager.py          — 3段階リスクガード（Gate1/2/3）
      - ...（その他補助モジュール）
    - data/                      — データ関連（DuckDBクエリ・カレンダー・ニュース等）
      - calendar_management.py   — マーケットカレンダー管理
      - news_collector.py        — RSS ニュース収集
      - jquants_client.py        — J-Quants API クライアント（参照される想定）
      - ...
    - monitoring/                — 監視用 DB / SystemMonitor 実装（別ファイル群）
      - monitoring_db.py
      - system_monitor.py
    - utils/                     — ロギング設定・プロセス優先度変更などユーティリティ
      - logging_setup.py
      - process_priority.py
    - config/                    — 設定用 YAML（system_config.yaml 等）

主要モジュールの役割（要約）
---------------------------
- config.py
  - .env 自動読み込みと Settings クラスを提供。Settings はプロパティ経由で型変換・妥当性チェックを行う。

- config_setup.py
  - 対話式に .env を作成／更新するウィザード。

- validate_config.py
  - 起動前に環境変数・config/*.yaml の有無・DB パス親ディレクトリなどを検査する CLI。

- execution/*
  - 発注ロジック、Order の状態管理、SQLite 永続化、ブローカー API 抽象化。MockBrokerClient によりローカル開発での動作確認が可能。

- data/*
  - DuckDB を用いたマーケットカレンダー等の時系列データ管理、ニュース収集等。

- monitoring/*
  - 実行中の監視（リソース閾値、注文イベントログ）を SQLite に記録する機能。

運用上の注意
------------
- KABUSYS_ENV=live に設定する場合は特に注意してください。validate_config では live 設定時に複数の警告を出します（LINE 通知設定や Kill Switch の扱い等）。
- .env は機密情報を含むため絶対に Git 等へコミットしないでください（config_setup.py のヘッダにも注意書きあり）。
- ExecutionEngine は kill.flag（デフォルト: data/kill.flag）・stop_requested.flag（data/stop_requested.flag）・PID ファイルを使用してプロセス制御を行います。運用手順を定めてください。
- DuckDB / SQLite のファイルパスは環境変数で上書きできます。バックアップ・アクセス権に注意してください。

その他
-----
- YAML のパース検査を有効にするには PyYAML をインストールしてください。インストールされていない場合、validate_config は YAML 内容検証をスキップし警告を出します。
- 実ブローカ接続（KabuStationClient）を行うには cabuステーション® アプリがローカルで動作している必要があります（API ベース URL の確認を行ってください）。
- テスト／ローカル開発のために MockBrokerClient を活用すると、実際の発注を行わずに発注フローのテストができます。

ライセンスや貢献方法、詳細な設計ドキュメント（DataPlatform.md 等）がある場合はプロジェクトルートに追記してください。必要であれば README にサンプルのユースケース（簡単なテストスクリプト等）を追加します。