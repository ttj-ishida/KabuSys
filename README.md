README
======

概要
----
KabuSys は日本株の自動売買システム向けのコンポーネント群です。本リポジトリには以下を含みます（抜粋）:
- 環境変数 / .env 管理（自動読み込み、対話式ウィザード）
- 設定検証 CLI（起動前に .env と config/*.yaml をチェック）
- ExecutionEngine：シグナルベースの発注エンジン（発注 / リスク管理 / リコンシリエーション）
- Broker クライアント抽象化（実際の kabu-station クライアントとテスト用 Mock）
- 監視（Monitoring）プロセスの起動スクリプト
- データユーティリティ（マーケットカレンダー、ニュース収集など）

目的は、本番／ペーパートレード／開発環境で安全に動作する発注フローを提供することです。設計は堅牢性（クラッシュ耐性、リコンシリエーション、サーキットブレーカー等）を重視しています。

主な機能
--------
- .env 自動読み込み（プロジェクトルートの .env / .env.local、OS 環境変数が優先）
- 対話式設定ウィザード（python -m kabusys.config_setup）で .env を生成・更新
- validate_config CLI（python -m kabusys.validate_config）で起動前チェック（--strict で警告も失敗扱い）
- Settings クラス経由の一元的設定取得（型安全なプロパティ）
- ExecutionEngine：シグナル取り込み、Gate1/2/3 のリスクガード、WebSocket push ドレイン、kill switch
- Order 管理層（OrderRecord：状態遷移の検証、OrderRepository：SQLite 永続化、OrderManager：API 送信フロー）
- BrokerAPI 抽象（Protocol）とファクトリ。mock=True で MockBrokerClient を利用可能
- Reconciler：再起動時に OrderSent の不確定注文をブローカーと突合して同期
- RiskManager：レート制限（トークンバケツ）、サーキットブレーカー、ドローダウン監視、ポジション上限チェック
- 監視プロセス（run_monitoring.py）：定期的にシステムメトリクスをチェックし monitoring DB に記録
- データ関連ユーティリティ（カレンダー管理、ニュース収集など）

セットアップ手順
----------------

前提
- Python 3.9+ を想定（dataclass/typing 機能を使用）
- システムに SQLite（標準）と duckdb がインストールされること

1) 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2) 依存パッケージのインストール
   下記は主要な依存想定です。プロジェクトに requirements.txt があればそちらを使用してください。

   pip install duckdb httpx websocket-client defusedxml

   オプション（YAML 検証用）:
   pip install PyYAML

   （必要に応じて他のライブラリを追加してください。）

3) 設定ファイルの準備
   プロジェクトルートに .env を作成します。対話式で作るには:

   python -m kabusys.config_setup

   このウィザードは .env（デフォルト）を生成・更新します。既存 .env があれば読み込んで Enter で再利用できます。

4) 設定の検証
   .env を作成したら、起動前に設定検証を実行します:

   python -m kabusys.validate_config
   # 警告も失敗扱いにする:
   python -m kabusys.validate_config --strict

   exit code:
   - 0: 問題なし（あるいは警告のみ）
   - 1: エラーあり（--strict 時に警告ありも 1）

主な必須環境変数
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）

任意（例）
- KABUSYS_ENV: execution 環境（development / paper_trading / live）
- DUCKDB_PATH / SQLITE_PATH: DB ファイルパス
- LOG_LEVEL
- KABU_API_BASE_URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート用）

使い方
------

1) 設定ウィザード
   python -m kabusys.config_setup
   --env-file オプションでパス指定可能:
   python -m kabusys.config_setup --env-file ./my.env

   ウィザード終了後、.env が生成されます。

2) 設定検証
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict

   出力に INFO/WARNING/ERROR が表示されます。
   config/*.yaml のパース検証には PyYAML が必要です（未インストールならスキップして警告）。

3) 実行エンジン（Execution）
   実稼働は KABUSYS_ENV の設定に依存します。開発／ペーパートレード環境では MockBrokerClient を使う構成です。

   実行（通常はサービス起動などで呼ぶ）:
   python -m kabusys.run_execution

   特記事項:
   - KABUSYS_ENV=paper_trading の場合、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に書き込まれ、本番 DB と分離されます。
   - 起動時に data/execution.pid に PID を書き込みます。data/kill.flag が存在すると起動拒否（KILL_FLAG_CLEAR_ON_START=1 ならクリアして起動）。
   - stop フラグ: プロジェクトルートの data/stop_requested.flag を作成すると実行中に検知して安全停止します。

4) 監視プロセス
   python -m kabusys.run_monitoring

   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を調整（デフォルト 60 秒）。
   - 監視は sqlite_path（settings.sqlite_path）を使用して監視 DB に記録します。監視は本番・ペーパーを問わず同じ sqlite_path を参照します（必要なら別 DB を設定してください）。

5) 開発／テスト時の Mock Broker 利用
   Settings（.env の KABUSYS_ENV）で development / paper_trading を選ぶと、BrokerClientFactory が mock=True のクライアント（MockBrokerClient）を生成します。PAPER_FILL_MODE で挙動（instant/partial/never/reject）を指定可能です。

動作上のポイント
- 発注フローの耐久性: OrderCreated → OrderSent → (broker_order_id 保存) → OrderAccepted という二相永続化を採用し、クラッシュ後の復旧を容易にしています。
- Reconciler により OrderSent の不確定注文をブローカー照合で回復し、ポジション差分を検出します。
- RiskManager は 3 段階のガード（Signal / Execution / Metrics）で安全性を担保します。
- WebSocket push（kabu station）の受信は ExecutionEngine の別スレッドで行い、受信した通知は内部キューに入れて処理します。

ディレクトリ構成（抜粋）
--------------------
以下は本リポジトリの主要なファイル/ディレクトリ（提供コードに基づく抜粋）です。

- pyproject.toml / setup.cfg / …（パッケージ設定: 存在する前提）
- .env, .env.local （環境変数ファイル）
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/
  - monitoring.db (SQLite、監視用)
  - kabusys.duckdb (DuckDB)
  - execution.pid, stop_requested.flag, kill.flag など
- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数読み込みと Settings
    - config_setup.py              — .env ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — Monitoring 起動スクリプト
    - execution/
      - __init__.py
      - broker_api.py              — Protocol・データモデル・例外・ファクトリ
      - broker_factory.py
      - kabu_client.py             — 実 API クライアント（httpx）
      - mock_client.py             — テスト用モック
      - order_record.py
      - order_repository.py
      - order_manager.py
      - execution_engine.py
      - reconciler.py
      - risk_manager.py
    - data/
      - calendar_management.py
      - news_collector.py
      - jquants_client.py (想定)
    - monitoring/
      - monitoring_db.py (想定)
    - utils/
      - logging_setup.py (想定)
      - process_priority.py (想定)
    - strategy/ (想定)
    - monitoring/ (想定)
- scripts/
  - generate_config.py (validate_config から参照される可能性あり)

（上記はコードから推定した構成です。実際のリポジトリでは若干の差分があるかもしれません。）

補足 / トラブルシューティング
------------------------------
- PyYAML が未インストールの場合、validate_config は config/*.yaml の内容検証をスキップして警告を出します。YAML 内容検証を行う場合は PyYAML をインストールしてください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行います。自動読み込みを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- モニタリング／実行のログ出力は LOG_LEVEL で制御できます。デフォルトは INFO。
- 本番環境（KABUSYS_ENV=live）では LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の設定を慎重に確認してください。validate_config は live 環境に関する追加の警告を出します。

貢献・拡張
-----------
- live 環境向けの KabuStationClient（kabu station 実クライアント）や運用用デプロイ設定を追加することで実際の取引接続が可能になります（現状は Mock を推奨）。
- strategy モジュール（シグナル生成ロジック）や config/*.yaml のテンプレート生成スクリプトを整備すると導入が容易になります。

ライセンス・作者
----------------
プロジェクトルートに LICENSE ファイルを置いてください（この README はライセンス情報を含みません）。README を元に運用ドキュメントやデプロイ手順を追加することを推奨します。

以上。必要であれば README に含めるサンプル .env やコマンド実行例、API の更に詳細な仕様（OrderRequest/OrderResponse フィールド説明など）を追記します。どの情報を追加しますか？