KabuSys — README
================

概要
----
KabuSys は日本株向けの自動売買システムを想定した Python コードベースです。
主要機能（発注・リスク管理・監視・カレンダー管理・ニュース収集など）をモジュール化しており、
ローカル開発（development）、ペーパートレード（paper_trading）、本番（live）を環境切替して動作します。

特徴
----
- 設定管理（.env 自動読み込み、対話式ウィザード）
- 実行エンジン（ExecutionEngine）によるシグナル駆動の発注フロー
- ブローカー抽象化（MockBrokerClient / KabuStationClient）
- 注文状態管理（OrderRecord の状態遷移、SQLite 永続化）
- 再起動時のリコンシリエーション（Reconciler）
- 3段階のリスクガード（Gate1/2/3）
- 監視ループ（SystemMonitor をポーリング）
- マーケットカレンダー管理（DuckDBベース、J-Quants APIとの連携想定）
- ニュース収集（RSS、前処理、SSRF防止対策など）
- 起動前設定検証ツール（validate_config）

必要条件
--------
- Python 3.10+
- 推奨ライブラリ（少なくとも以下を入れておくことを推奨）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml のパース検証を有効化するため、任意）
  - （上記は pip でインストール可能）

インストール例
--------------
仮想環境を作成して依存をインストールする例:

- 仮想環境
  python -m venv .venv
  source .venv/bin/activate

- 必要パッケージ（プロジェクトの requirements.txt があればそれを使用）
  pip install duckdb httpx websocket-client defusedxml PyYAML

セットアップ手順
----------------
1. プロジェクトルートに .env を作成する（自動読み込みされます）
   - 対話式ウィザードで作成する:
     python -m kabusys.config_setup
   - ウィザードは既存 .env を読み込み、必要な項目を対話形式で補完します。

2. 設定を検証する:
   python -m kabusys.validate_config
   - 警告を FAILURE 扱いにしたい場合:
     python -m kabusys.validate_config --strict

3. DB の準備
   - 監視用 SQLite と DuckDB のデフォルトパス:
     - data/monitoring.db (SQLite)
     - data/kabusys.duckdb (DuckDB)
   - これらの親ディレクトリはスクリプトが自動作成する場合がありますが、不安な場合は事前に data/ ディレクトリを作成してください。
   - スキーマ作成用関数:
     - orders テーブル: kabusys.execution.order_repository.init_orders_db(conn)
     - monitoring テーブル: kabusys.monitoring.monitoring_db.init_monitoring_db(conn)
     実行時に自動作成するコードがある場合もありますが、手動で準備することも可能です。

主な環境変数
--------------
必須（少なくとも設定が必要）:
- JQUANTS_REFRESH_TOKEN  — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API パスワード

任意 / 推奨:
- KABUSYS_ENV            — 実行環境 (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 用）
- LOG_LEVEL              — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- KABU_API_BASE_URL      — kabu station のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番での通知用 LINE 設定
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL  — run_monitoring のポーリング間隔（秒、デフォルト 60）

自動 .env ロード動作
--------------------
- 起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env / .env.local を自動読み込みします。
- OS の環境変数が優先されます（.env の値は既存の OS 環境変数を上書きしません）。
- 自動読み込みを無効化するには:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（主要スクリプト）
------------------------
- 環境設定ウィザード（.env の作成/更新）
  python -m kabusys.config_setup

- 設定検証（.env と config/*.yaml の整合性チェック）
  python -m kabusys.validate_config
  - --strict を付けると警告をエラー扱いして exit code 1 を返します。

- 実行エンジン起動（発注エンジン）
  python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使って paper_trading 用 DB に記録します。
  - 実行中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag を作るか kill.flag 等で制御。

- 監視ループ起動（SystemMonitor ポーリング）
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（デフォルト 60）。
  - 監視は環境にかかわらず本番 sqlite_path を使用します（監視 DB は常に本番想定）。

動作例（本番起動フロー）
-----------------------
1. .env を用意（config_setup で作成）
2. python -m kabusys.validate_config --strict でチェック
3. python -m kabusys.run_monitoring を別プロセスで起動
4. python -m kabusys.run_execution を起動して当日のセッションを処理

重要な実行制御・ファイル
-----------------------
- kill.flag / stop_requested.flag:
  - settings.kill_flag_path（デフォルト: data/kill.flag）を置くと ExecutionEngine 内で kill_switch が発動します。
  - data/stop_requested.flag を作成すると run_monitoring/run_execution のループが終了します（スクリプト内で監視）。
- PID ファイル:
  - 実行時に data/execution.pid などに PID を書きます（config の pid_file_path で変更可能）。

主要ディレクトリ構成
--------------------
（プロジェクトルートの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py                 — パッケージ定義（__version__ など）
  - config.py                   — 環境変数読み込み・Settings クラス（自動 .env ロード含む）
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 起動前設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor 起動スクリプト
  - data/
    - calendar_management.py    — マーケットカレンダー管理（DuckDB + J-Quants）
    - news_collector.py         — RSS ニュース収集モジュール
    - (jquants_client.py など想定)
  - execution/
    - broker_api.py             — BrokerAPI の Protocol / データモデル / ファクトリ
    - mock_client.py            — テスト用モックブローカ
    - kabu_client.py            — kabu station 実装（httpx, websocket）
    - broker_factory.py         — 設定に応じたクライアント生成
    - order_record.py           — 注文状態と状態遷移ロジック
    - order_repository.py       — SQLite 永続化層
    - order_manager.py          — 発注フローの外向き API
    - execution_engine.py       — シグナル駆動の発注エンジン
    - reconciler.py             — 再起動時の自動復旧
    - risk_manager.py           — Gate1/2/3 のリスク管理
    - (その他: order_* や工場的モジュール)
  - monitoring/
    - monitoring_db.py          — 監視用 DB 初期化 / ログ記録（init_monitoring_db など）
    - system_monitor.py         — システム監視ロジック（ポーリング処理）
  - strategy/                    — 戦略関連モジュール（存在が想定されるディレクトリ）
  - utils/
    - logging_setup.py          — ロギング初期化
    - process_priority.py       — プロセス優先度設定等ユーティリティ

開発メモ / 注意点
-----------------
- ExecutionEngine はセッション時間（デフォルト: 8:50〜15:30）に合わせた処理を行います。テストでは run_session を呼ぶ代わりに内部メソッドを直接操作できます。
- MockBrokerClient を利用することで kabuステーション無しでローカルテストが可能です（paper_trading / development）。
- 設定検証ツール (validate_config) は PyYAML があれば config/*.yaml をパースして検証します。PyYAML 未インストール時は YAML 内容検証をスキップします。
- .env ファイルは機密情報を含むため絶対にコミットしないでください（config_setup はヘッダに注意喚起を出力します）。

よくあるトラブルと確認ポイント
-----------------------------
- .env を作ったのに設定が反映されない:
  - OS 環境変数が優先されます。自動ロードはプロジェクトルートを正しく検出できる必要があります（.git または pyproject.toml を参照）。
  - 自動ロードを無効化している場合（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）やルートが見つからない場合は手動で export してください。
- 実行時に orders テーブルがないエラー:
  - init_orders_db を呼んでテーブルを作成してください。または実行フローで初期化処理が呼ばれるかを確認してください。
- 本番環境の注意:
  - KABUSYS_ENV=live を指定すると警告が強く出る設計です（LINE 通知設定の未設定や KILL_FLAG_CLEAR_ON_START の誤設定に注意）。

付録: よく使うコマンドまとめ
-----------------------------
- .env 作成ウィザード:
  python -m kabusys.config_setup

- 起動前チェック:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 発注エンジン:
  python -m kabusys.run_execution

- 監視ループ:
  python -m kabusys.run_monitoring

以上がプロジェクトの概要・セットアップ・使い方・構成のまとめです。必要ならば、各モジュールの API 使用例や DB スキーマの詳細、運用手順（デプロイ、サービス化、ログ/監視設計）についての追補ドキュメントも作成します。どの項目を詳細化しますか？