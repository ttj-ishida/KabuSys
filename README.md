KabuSys — 日本株自動売買システム (README)
=================================

概要
----
KabuSys は日本株向けの自動売買／監視用ライブラリ兼実行スクリプト群です。  
主要コンポーネントとして、発注を担う ExecutionEngine、起動時のリコンシリエーション機能、SystemMonitor による監視、設定ウィザード／検証ツールなどを備えています。  
本リポジトリはライブラリとしても実行スクリプトとしても利用でき、開発（development） / ペーパートレード（paper_trading） / 本番（live）に対応する設計です。

特徴（機能一覧）
----------------
- 環境設定ウィザード（対話式）: .env を生成・更新する kabusys.config_setup
- 設定検証 CLI: .env と config/*.yaml の検査（PyYAML があると YAML パース検証を行う）
- ExecutionEngine: シグナル処理 → 発注 → WebSocket ドレインのセッション実行
- Broker クライアント抽象化:
  - MockBrokerClient（テスト／ペーパートレード用）
  - KabuStationClient（kabuステーション API 実装、HTTP/WebSocket）
- Order 管理:
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite による永続化）
  - OrderManager（DB と Broker API を繋ぐ外向き API）
- RiskManager（3 段階ガード: Gate1/2/3）
- Reconciler（起動時の OrderSent 照合とポジション差分検出）
- Data 周辺: DuckDB を用いたカレンダー管理・シグナル/ポートフォリオ参照・ニュース収集モジュール
- 監視プロセス: run_monitoring によるポーリング監視（監視用 SQLite を使用）

必要な環境
----------
- Python 3.10+
- 推奨パッケージ（最低限）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（任意だが validate_config の YAML 検査に便利）
- 標準で利用する DB: SQLite（組み込み）／DuckDB（パッケージ必要）

インストール例（venv 推奨）
-------------------------
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb httpx websocket-client defusedxml pyyaml

セットアップ手順
----------------
1. プロジェクトルートに移動（README のあるルート）
2. .env を作成する（対話式ウィザードを推奨）
   - python -m kabusys.config_setup
     - 各項目を対話形式で入力して .env を生成／更新します。
     - 既存 .env があれば読み込んで Enter で再利用できます。
3. 設定を検証する
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict
4. 実行前に依存 DB（data ディレクトリ）へ書き込み権限があるか確認してください。
   - run_execution / run_monitoring は起動時に必要なテーブルを初期化します（init_monitoring_db / init_orders_db 等）。

重要な環境変数
----------------
（.env に設定する想定の主なキー）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意（デフォルトあり／運用に応じて設定）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station API ベース URL（例: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定（本番で推奨）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1、デフォルト 0）

自動 .env ロード
- 実行時、OS 環境変数 > .env.local > .env の順で自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能）。

使い方（主要コマンド）
--------------------
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict  （警告も exit(1) とする）

- 実行エンジン（発注）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）へ記録します。
    - 実行中は data/execution.pid（デフォルト）に PID を書きます。
    - 停止は data/stop_requested.flag を作成することで安全に停止できます（または Ctrl-C）。

- 監視ループ（SystemMonitor）
  - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path を使用します（KABUSYS_ENV に依存しない）。

運用上のフラグ / ファイル
------------------------
- data/stop_requested.flag — このファイルが存在するとループを終了して安全に停止します。
- data/execution.pid（または Settings().pid_file_path） — PID を書き出すファイル
- data/kill.flag（Settings().kill_flag_path） — Kill スイッチ: 存在すると起動拒否や即時停止ロジックが働きます（KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に自動で削除されますが、本番では 0 推奨）。

データベース初期化
-----------------
- Execution/Monitoring の起動時に必要なテーブルは自動で作成されます（init_orders_db / init_monitoring_db 等）。
- DuckDB のファイルパスは DUCKDB_PATH で指定（デフォルト data/kabusys.duckdb）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールの一覧です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト

  - execution/
    - __init__.py
    - broker_api.py          — BrokerAPI の Protocol / データモデル / ファクトリ
    - broker_factory.py      — Settings に基づく Broker クライアント生成
    - kabu_client.py         — kabu station REST/WebSocket クライアント
    - mock_client.py         — モックブローカ（paper_trading / テスト用）
    - order_record.py        — Order の状態遷移ロジック（純粋モデル）
    - order_repository.py    — SQLite 永続化層（orders テーブル）
    - order_manager.py       — 発注 / 同期 / キャンセルの外向 API
    - execution_engine.py    — セッション管理 / シグナル処理 / WebSocket ドレイン
    - reconciler.py          — 起動時リコンシリエーション
    - risk_manager.py        — Gate1/2/3 リスクガード

  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集（defusedxml 等を使用）

  - monitoring/
    - monitoring_db.py       — 監視 DB 初期化・操作（run_monitoring で使用）
    - system_monitor.py      — 監視ロジック（run_monitoring 実行）

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ

設計上の注意点 / 運用上のヒント
--------------------------------
- KABUSYS_ENV:
  - development: 開発用（MockBrokerClient, 発注なし想定）
  - paper_trading: ペーパートレード（MockBrokerClient を使用し別 DB に記録）
  - live: 本番（KabuStationClient の想定、設定を慎重に）
- 本番運用では LINE 通知などのアラート設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。validate_config は live モードで警告を出します。
- 発注フローの耐障害性:
  - OrderManager はクラッシュ耐性を考慮して OrderSent の永続化→broker 呼び出し→broker_order_id 永続化→OrderAccepted 更新の順に処理します。
  - Reconciler が起動時に OrderSent を照合して状態を回復する設計です。
- セキュリティ:
  - .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きがあります）。
- テスト:
  - paper_trading / development では MockBrokerClient により実行可能。fill_mode の挙動（instant/partial/never/reject）で挙動を変えられます。

よく使うコマンドまとめ
---------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行（発注エンジン）: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring

ライセンス / 貢献
-----------------
この README ではライセンス情報は含めていません。実際の配布時は LICENSE ファイルを追加してください。バグ報告やプルリクエストはリポジトリの Issue / PR を通じてお願いします。

付録: 例 .env の最小例
--------------------
（開発・動作確認用の最小例。実運用では各値を適切に設定してください）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

以上。必要があれば README にサンプル .env フォーマット、より詳しい運用手順、Dockerfile や systemd ユニットの例を追記します。どの情報を追加しますか？