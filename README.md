KabuSys
======

日本株自動売買システム（ミニマル実装）。  
このリポジトリは、シグナルに基づく発注エンジン、ブローカークライアント（mock / kabu station）、リスクガード、リコンシリエーション、監視ループ、データ処理ユーティリティ等を含むモジュール群で構成されています。

概要
---
KabuSys は次の目的を持ったコンポーネント群を提供します。

- シグナルを取得して発注する ExecutionEngine（Signal Queue Pull 型）
- 発注の永続化（SQLite）と状態遷移管理（OrderRecord / OrderRepository）
- ブローカークライアント抽象（BrokerAPIProtocol）と Mock / KabuStation 実装
- 三段階のリスクガード（Gate1/2/3）を備えた RiskManager
- 起動時のリコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor）と監視用 SQLite DB
- データモジュール（マーケットカレンダー管理、RSS ニュース収集など）
- .env 対応の設定管理と対話式ウィザード / 設定検証 CLI

主な機能一覧
---
- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話生成
- 設定検証 CLI（python -m kabusys.validate_config）で必須環境変数や config/*.yaml の存在・構文検査
- ExecutionEngine による発注フロー（OrderManager / OrderRepository / ExecutionEngine）
- MockBrokerClient を使ったペーパートレード検証（KABUSYS_ENV=paper_trading / development）
- KabuStation REST API クライアント（KabuStationClient）を用意（実運用は未実装部分あり）
- Reconciler によるクラッシュ後の自動復旧（OrderSent の突合）
- 監視用ポーリングループ（run_monitoring）と監視 DB 初期化
- マーケットカレンダー管理（J-Quants を想定）と営業日ユーティリティ
- RSS ニュース収集と前処理（SSRF を考慮した安全な取得ロジック）

セットアップ手順
---
1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb httpx websocket-client defusedxml
   - PyYAML は config/*.yaml のパース検証で使用（任意）:
     - pip install pyyaml

   （プロジェクトに requirements.txt がある場合はそれを使用してください。）

3. プロジェクトルートに .env を配置
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成
     - 例（最低限必須）:
       JQUANTS_REFRESH_TOKEN=your_token_here
       KABU_API_PASSWORD=your_password_here
       KABUSYS_ENV=development
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       LOG_LEVEL=INFO

4. 設定検証（任意、起動前推奨）
   - python -m kabusys.validate_config
   - 警告を FAIL とするには --strict を付ける:
     - python -m kabusys.validate_config --strict

5. データベース初期化等は各モジュールが起動時に行う（例: init_orders_db / init_monitoring_db を呼ぶ）。

使い方
---
- 環境ウィザード（.env 作成/更新）
  - python -m kabusys.config_setup
  - 実行すると対話形式で主要な環境変数を設定できます。保存後は validate_config を実行して確認してください。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit code 1）になります。
  - PyYAML がない場合、YAML 内容の検証はスキップされます（警告が出ます）。

- 実行エンジン（本番相当のセッション実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading または development の場合は MockBrokerClient を使用します。
  - KABUSYS_ENV=live は現在未実装（BrokerClientFactory で NotImplementedError を送出）。

- 監視ループ
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は環境にかかわらず本番 sqlite_path を使用します（監視専用 DB を適宜設定してください）。

主要な環境変数（抜粋）
---
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 主要オプション:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（live 時は未設定だと警告）
  - KILL_FLAG_CLEAR_ON_START: 0/1（起動時に kill.flag を自動クリアするか）

運用上の注意
---
- KABUSYS_ENV=live を設定すると本番モードとして挙動が変わるため、すべての設定を慎重にチェックしてください（validate_config は live での追加チェックを行います）。
- 実際の注文を行う場合は必ず十分なテストとリスク設定（RiskConfig）を実施してください。
- kill.flag / PID ファイルの扱いに注意してください。起動時に kill.flag が存在すると通常は起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合はクリアして起動）。
- Reconciler により再起動後の OrderSent 状態の回復を試みますが、手動確認が必要なケースもあります。

ディレクトリ構成（要約）
---
src/kabusys/
- __init__.py
- config.py                       — 環境変数読み込み / Settings
- config_setup.py                 — 対話式 .env ウィザード
- validate_config.py              — 起動前設定検証 CLI
- run_execution.py                — ExecutionEngine 起動スクリプト
- run_monitoring.py               — SystemMonitor ポーリング起動スクリプト

src/kabusys/execution/
- broker_api.py                   — BrokerAPIProtocol / データモデル / ファクトリ
- kabu_client.py                  — KabuStationClient（HTTP + WebSocket 実装）
- mock_client.py                  — MockBrokerClient（テスト用）
- broker_factory.py               — Settings に基づくクライアント生成
- order_record.py                 — OrderRecord と状態遷移ロジック
- order_repository.py             — SQLite 永続化層（orders テーブル）
- order_manager.py                — 発注フロー（create/send/sync/cancel）
- execution_engine.py             — ExecutionEngine（シグナル処理 / push ドレイン）
- reconciler.py                   — リコンシリエーション（起動時の復旧）
- risk_manager.py                 — Gate1/2/3 リスクガード

src/kabusys/data/
- calendar_management.py          — マーケットカレンダー管理 / 営業日ユーティリティ
- news_collector.py               — RSS ニュース収集・前処理
- jquants_client.py (参照あり)    — J-Quants 関連クライアント（データ取得用、実装がある場合）

src/kabusys/monitoring/
- monitoring_db.py                — 監視用 DB 初期化 / ロギング用 API
- system_monitor.py               — 監視ループ本体（run_monitoring から使用）

src/kabusys/utils/
- logging_setup.py                — ログ設定ユーティリティ
- process_priority.py             — プロセス優先度設定ユーティリティ

補足
---
- PyYAML がインストールされていると validate_config は config/*.yaml をパースして内容検証を行います。未インストール時は YAML 検証がスキップされます（warning）。
- MockBrokerClient は複数の fill_mode（instant / partial / never / reject）を持ち、テストでの振る舞い制御に便利です。
- KabuStationClient は HTTP（httpx）と WebSocket（websocket-client）で通信します。ローカルで kabuステーションアプリが起動していることが前提です。

ライセンス / バージョン
---
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

以上。必要であれば、README に含めるサンプル .env.example や requirements.txt、起動フローチャート、監視 / ログ出力の具体例などを追加で作成します。どの情報を詳しく追記しますか？