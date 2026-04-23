# KabuSys — 日本株自動売買システム

概要
----
KabuSys は日本株の自動売買を目指した実験的なシステムです。  
主な目的はローカル環境・ペーパートレード環境での安全な発注ワークフローの検証と、実際のブローカー（kabuステーション）との接続を見据えたコンポーネント設計の検討です。

特徴
----
- .env 対話式ウィザード（config_setup）で環境変数ファイルを簡単に作成・更新可能
- validate_config による起動前チェック（必須環境変数、YAML 設定ファイル、パス等）
- ExecutionEngine: シグナルプル方式 + WebSocket プッシュドレインの発注エンジン
- OrderState マシン（OrderRecord）と SQLite 永続化（OrderRepository）による堅牢な注文管理
- Broker クライアント抽象化（MockBrokerClient / KabuStationClient）
  - 開発 / ペーパートレード時は MockBroker を利用（paper_trading）
  - live 用クライアントは未実装（作業対象）
- RiskManager（Gate1/2/3）による多段階リスクガード（余力・重複・ポジション上限、レート制限、ドローダウン等）
- Reconciler による再起動時の自動復旧（OrderSent の突合・ポジション差分検出）
- 監視コンポーネント（run_monitoring）でプロセス/メトリクス監視
- データ側に DuckDB を採用、マーケットカレンダー/ニュース収集等のユーティリティを含む

前提・依存関係
---------------
（代表的なもの）
- Python 3.10+（typing の Union 記法や型ヒントを想定）
- pip パッケージ:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config YAML のパースを有効にしたい場合）
- 標準ライブラリ: sqlite3 等

インストール例（仮）
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml pyyaml
```

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成して依存パッケージをインストールします（上記参照）。
2. data ディレクトリを作成（多くのファイルが data/ 下に書き込まれます）:
   ```
   mkdir -p data
   ```
3. .env の作成:
   - 対話式ウィザードで作成する:
     ```
     python -m kabusys.config_setup
     ```
     画面の案内に従って値を入力してください（Enter で既存値 / デフォルトを利用）。
   - 既存の .env を直接編集しても構いません（セキュリティ上 Git にコミットしないこと）。
4. 設定検証:
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
   validate_config は .env と config/*.yaml の存在・基本整合性をチェックします。PyYAML が未インストールだと YAML の中身チェックはスキップされます（ただし存在チェックは行います）。

主要な環境変数（主なもの）
------------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意 / デフォルト付き:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
  - paper_trading: MockBroker（ペーパートレード）を使用
  - live: 本番（注意: Live broker は未実装の部分があります）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABU_API_BASE_URL — kabu station API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番での通知に使用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- PAPER_FILL_MODE — paper_trading 用のモック約定挙動（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）

使い方（プロセス起動）
---------------------
- 設定ウィザード（.env の作成・編集）
  ```
  python -m kabusys.config_setup
  ```
- 設定チェック
  ```
  python -m kabusys.validate_config
  ```
- 実行プロセス（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV によって挙動が変わります（paper_trading は MockBroker、development も Mock）。
  - 起動時に data/kill.flag が存在する場合は、KILL_FLAG_CLEAR_ON_START=1 で自動的にクリアするか、存在する限り起動を拒否します。
  - プロセスは data/execution.pid（PID ファイル）を作成します。停止は data/stop_requested.flag を作成することで外部からリクエストできます（監視ループと実行ループ共通）。
- 監視プロセス（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します（監視 DB は一貫した保存先にするため）。
- プロセス終了方法:
  - 正常終了要求: プロジェクトルートの data/stop_requested.flag を作成すると、各ループが検知して終了します。
  - kill スイッチ: システム内で致命的条件が発生した場合 ExecutionEngine.kill_switch() が全 active 注文をキャンセルします（内部的に kill.flag に依存する挙動があります）。

データベース初期化
-----------------
- 監視 DB 初期化は run_monitoring / run_execution 内で init_monitoring_db を呼んで行います（冪等）。
- orders テーブル初期化関数: kabusys.execution.order_repository.init_orders_db(conn) — 必要なら起動前に SQLite 接続を作って呼び出せます。

注意事項 / 実装上のポイント
-------------------------
- Live broker（実際の kabuステーション クライアント）の利用は将来実装予定です。現時点では development / paper_trading では MockBrokerClient が使われます。
- validate_config は config/*.yaml（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）を確認します。YAML のパースには PyYAML が必要です。存在しない場合は警告を出します。
- .env は決してリポジトリにコミットしないでください（README や .env.example を参照）。
- WebSocket プッシュ受信は websocket-client を使用しています（KabuStationClient.stream_push）。Mock 環境では未使用または簡易実装です。
- セキュリティ: config_setup はシークレット項目（API トークン等）をマスク表示しますが、.env そのものは平文になります。運用時は適切に保護してください。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数読み込み・Settings クラス（自動 .env ロード機能含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前チェック CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

src/kabusys/execution/
- broker_api.py — Broker API の Protocol / データモデル / 例外 / create_broker_api ファクトリ
- kabu_client.py — kabuステーション REST API クライアント（httpx）
- mock_client.py — MockBrokerClient（テスト/ペーパー用）
- broker_factory.py — Settings に応じた Broker クライアント生成
- execution_engine.py — ExecutionEngine（シグナル処理 / WebSocket ドレイン / セッション管理）
- order_record.py — OrderState / OrderRecord（状態遷移ロジック）
- order_repository.py — SQLite による永続化層
- order_manager.py — OrderManager（OrderRecord + OrderRepository + Broker 呼び出し）
- reconciler.py — 再起動時のリコンシリエーション（OrderSent の同期等）
- risk_manager.py — RiskManager（Gate1/2/3）

src/kabusys/data/
- calendar_management.py — マーケットカレンダー管理（DuckDB）
- news_collector.py — RSS ニュース収集（defusedxml 使用）
- jquants_client.py — （参照されるがここでは詳細省略）J-Quants 関連ユーティリティ

src/kabusys/monitoring/
- monitoring_db.py — 監視 DB 初期化・記録（使用ファイル: data/monitoring.db）
- system_monitor.py — システム監視ロジック（使用者の要件に応じて拡張）

追加情報
--------
- 開発用・テスト用に MockBrokerClient は便利です。PAPER_FILL_MODE を切り替えることで約定挙動（即時/部分/未約定/拒否）をシミュレーションできます。
- config/*.yaml の生成スクリプト（generate_config.py）への参照がコード内にあります。プロジェクトに付属するスクリプトがある場合はそれで初期テンプレートを生成できます。
- 本 README はコードベースから抽出した情報をまとめたものです。実運用に移す際は追加の監査・テスト・セキュリティ対策を必須としてください。

この README を起点に、まずは仮想環境の構築、依存パッケージのインストール、.env の作成 → validate_config による検証 → run_execution / run_monitoring の順で動作確認してみてください。必要であれば README をプロジェクト固有の手順（DB 初期化スクリプト、外部サービス設定等）に合わせて追記してください。