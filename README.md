README
=====

概要
----
KabuSys は日本株の自動売買を想定した小規模なフレームワークです。  
シグナルを読み込んで発注を行う ExecutionEngine、監視用の SystemMonitor、ブローカークライアントの抽象化、設定管理ツールなどが含まれます。テスト／開発用途に向けた Mock ブローカー実装（ペーパートレード）を備え、本番（live）環境にも対応できる設計になっています（ただし現状 Live ブローカークライアントは未実装の箇所があります）。

主な機能
--------
- 環境設定ウィザード（.env の対話式作成・更新）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml のチェック）: kabusys.validate_config
- ExecutionEngine（シグナル処理 → 発注 → WebSocket push ドレイン）: kabusys.run_execution
- SystemMonitor（定期ポーリングによりシステム状態を監視）: kabusys.run_monitoring
- ブローカー抽象 (BrokerAPIProtocol) と実装:
  - MockBrokerClient（テスト／paper_trading 用）
  - KabuStationClient（kabuステーション連携用、HTTP/WebSocket）
- 注文状態管理（OrderRecord）・永続化（SQLite）・リコンシリエーション（Reconciler）
- リスク管理（Gate1/2/3）: Rate limit / Circuit breaker / Drawdown など
- データ関連ユーティリティ:
  - マーケットカレンダー管理（DuckDB ベース）
  - ニュース収集モジュール（RSS パーサ、SSRF対策、正規化）

要件（推奨）
-------------
- Python 3.10+
- pip install で入れる主な依存:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml の内容検証を有効にする場合）
- SQLite（Python 標準ライブラリで利用）

セットアップ手順
--------------
1. リポジトリをクローンして作業ディレクトリに移動
   - 仮にプロジェクトルートに src/ がある想定です。

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml pyyaml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. .env ファイルを作成
   - 対話式ウィザードを使うのが推奨:
     - python -m kabusys.config_setup
     - オプション: --env-file を指定して別の場所に保存可能
   - 手動で作成する場合はプロジェクトルートに .env を配置
   - 自動ロード: 起動時に OS 環境変数 > .env.local > .env の順で読み込まれます。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 設定の検証（ウィザードで保存後は必ず実行推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict

重要な環境変数（抜粋）
---------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（よく使うもの）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KILL_FLAG_CLEAR_ON_START（0/1、本番での Kill Switch 自動クリア）

簡易 .env 例
-------------
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

使い方
-----
- 環境設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup
  - オプション: --env-file /path/to/.env を指定

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit(1) 扱いになります

- 実行エンジン（本番または paper_trading）
  - python -m kabusys.run_execution
  - ExecutionEngine は KABUSYS_ENV を参照して paper_trading なら MockBrokerClient を使用します。
  - 起動前に stop フラグや PID の扱いに注意してください（data/execution.pid, data/stop_requested.flag など）。

- 監視ループ（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）

- テスト／開発でのモックブローカー
  - KABUSYS_ENV=paper_trading または development の場合、MockBrokerClient が使われます。
  - MockBrokerClient の fill_mode は PAPER_FILL_MODE 環境変数で指定可能（instant/partial/never/reject）

運用に関する注意
----------------
- validate_config を最初に実行して設定の不備を検出してください（.env と config/*.yaml）。
- KABUSYS_ENV=live を設定する場合は LINE 通知等のアラート設定を必ず確認してください（validate_config が警告を出します）。
- kill flag（KILL_FLAG）:
  - 起動時に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START=1 であれば自動で削除して起動します。通常は 0 を推奨します（本番の安全措置）。
- DB パスの親ディレクトリが存在しない場合は自動生成されることがありますが、適切な権限を確認してください。
- YAML の内容検証は PyYAML が必要です。インストールされていない場合 validate_config は YAML 検証をスキップします。

ディレクトリ構成（要約）
----------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数の読み込み・Settings
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 起動前チェック CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor 起動スクリプト

src/kabusys/execution/
- broker_api.py              — BrokerAPIProtocol / データモデル / ファクトリ
- kabu_client.py             — KabuStationClient（kabuステーション用）
- mock_client.py             — MockBrokerClient（テスト用）
- broker_factory.py          — Settings を見てクライアントを生成
- execution_engine.py        — ExecutionEngine 本体（シグナル処理・push ドレイン）
- order_record.py            — 注文状態モデルと遷移検証
- order_repository.py        — SQLite 永続化層（orders テーブル）
- order_manager.py           — OrderManager（外向け API）
- reconciler.py              — リコンシリエーション（起動時の復旧）
- risk_manager.py            — Gate1/2/3 リスク管理

src/kabusys/data/
- calendar_management.py     — マーケットカレンダー（DuckDB ベース）
- news_collector.py          — RSS ニュース収集（SSRF 対策等）
- (その他データ関連モジュール)

src/kabusys/monitoring/
- monitoring_db.py           — 監視用 SQLite テーブル初期化 / ログ関数
- system_monitor.py          — 監視ロジック（ポーリング）

src/kabusys/utils/
- logging_setup.py           — ロギング設定ユーティリティ
- process_priority.py        — OS プロセス優先度設定ユーティリティ
- (その他ユーティリティ)

config/
- system_config.yaml
- data_config.yaml
- strategy_config.yaml
- risk_config.yaml
- execution_config.yaml
- monitoring_config.yaml
  （validate_config が存在確認を行います。テンプレート生成用スクリプト等がある場合はそれを利用してください）

data/
- データベース・PID・フラグファイルなどの格納先（例: data/kabusys.duckdb, data/monitoring.db, data/execution.pid, data/stop_requested.flag）

トラブルシューティング
--------------------
- validate_config が PyYAML がないと警告する:
  - pip install pyyaml で YAML 検証を有効化
- KabuStationClient の接続に失敗する:
  - kabuステーションアプリがローカルで稼働していること、KABU_API_PASSWORD や KABU_API_BASE_URL を確認
- ExecutionEngine が起動直後に終了する（kill.flag 関連）:
  - data/kill.flag の存在、KILL_FLAG_CLEAR_ON_START の設定を確認
- DB 関連のエラー:
  - 指定した DUCKDB_PATH / SQLITE_PATH の親ディレクトリとファイルへの書き込み権限を確認

ライセンス / 署名
-----------------
（プロジェクトのライセンスや著作権情報があればここに記載）

補足
----
- 本 README はコードベース内の各モジュールの実装内容に基づいて作成しています。細かな挙動や追加のユーティリティ等は実際のドキュメントやコードコメントを参照してください。