README
======

概要
----
KabuSys は日本株向けの自動売買システムの骨格を実装した Python パッケージです。
主要な役割は以下の通りです。

- シグナルに基づく発注（ExecutionEngine）
- 注文状態管理と永続化（OrderManager / OrderRepository）
- ブローカー API 抽象化（実ネット用 KabuStationClient とテスト用 MockBrokerClient）
- リスクガード（RiskManager：Gate1/2/3）
- 起動時のリコンシリエーション（Reconciler）
- マーケットカレンダー管理・ニュース収集などのデータ処理ユーティリティ
- 監視プロセス（SystemMonitor）および監視用 DB 操作
- 開発支援ツール：.env ウィザード（config_setup）と設定検証 CLI（validate_config）

本 README はコードベース（src/kabusys 以下）に基づく簡易ドキュメントです。

主な機能一覧
-------------
- .env 対話式ウィザード（python -m kabusys.config_setup）
- 起動前設定検証（python -m kabusys.validate_config）:
  - 必須環境変数チェック、YAML 設定ファイルのパース確認、パスの存在確認、KABUSYS_ENV の妥当性など
  - --strict オプションで警告も失敗扱いにできる
- ExecutionEngine:
  - シグナルプル型の発注ループと WebSocket push ドレイン
  - OrderRecord を用いる状態遷移、DB 永続化、リスクチェック、PID / kill.flag 管理
- Broker API 層:
  - BrokerAPIProtocol に基づく実装（KabuStationClient）と MockBrokerClient（ペーパートレード / テスト用）
- リスク管理:
  - Gate1（余力/重複/ポジション上限）、Gate2（レート制限/サーキットブレーカー）、Gate3（ドローダウン監視）
- Reconciler:
  - 再起動時の OrderSent 注文突合せとポジション差分検出
- データユーティリティ:
  - カレンダー管理（is_trading_day / next_trading_day 等）
  - ニュース収集・前処理（RSS から raw_news へ）など
- 監視プロセス起動スクリプト（run_monitoring）:
  - 監視ループ、監視 DB 初期化、MONITOR_POLL_INTERVAL による間隔調整

セットアップ手順
----------------
1. リポジトリをクローン（例）
   - git clone <repo-url>
   - cd <repo-root>

2. Python 環境を準備（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 主要な依存例（本リポジトリの機能によって必要）:
     - duckdb
     - httpx
     - websocket-client
     - PyYAML (validate_config で YAML 検証を行う場合)
     - defusedxml
   - SQLite は標準ライブラリの sqlite3 を使用します。

4. 環境変数（.env）の作成
   - 対話式ウィザードを使う（.env を生成／更新）:
     - python -m kabusys.config_setup
   - 既存 .env がある場合は上書きや既存値の利用が可能。

5. 設定検証（必須項目・警告の確認）
   - python -m kabusys.validate_config
   - 警告を失敗扱いにしたいときは --strict を付ける:
     - python -m kabusys.validate_config --strict

使い方（起動 / 開発）
--------------------
- .env ウィザード
  - python -m kabusys.config_setup
  - 対話で JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等を入力して .env を作成する。

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告も exit code 1 として扱う。

- 実行エンジン（発注処理）
  - python -m kabusys.run_execution
  - Settings に従って DB 接続、ブローカークライアント生成、ExecutionEngine の run_session 開始。
  - KABUSYS_ENV が paper_trading または development のときは MockBrokerClient が使われる（本番クライアントは未実装箇所あり）。
  - 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが検知して停止する。kill.flag（KILL_FLAG）による安全停止機構あり。

- 監視プロセス
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は settings.sqlite_path を使用。

- 環境変数の自動読み込み
  - 起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env を自動ロードします。
  - ロード順序: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。

主要な環境変数（例）
--------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / 推奨:
  - KABUSYS_ENV (development / paper_trading / live) — デフォルト development
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)
  - KABU_API_BASE_URL (kabu station API のベース URL)
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番アラート用）
  - KILL_FLAG_CLEAR_ON_START (0/1) — 本番で 1 は危険

注意事項 / 運用上のポイント
---------------------------
- KABUSYS_ENV=live のときは設定に注意（validate_config は live を警告扱い）。
- kill.flag と stop_requested.flag の振る舞い:
  - ExecutionEngine は起動前に kill.flag が存在すると起動を拒否（KILL_FLAG_CLEAR_ON_START=1 の場合は解除して起動可能）。
  - run_execution/run_monitoring は同梱の stop_requested.flag を監視して安全停止する。
- DB パスはデフォルトで data/ 配下を使用。親ディレクトリが存在しない場合は起動時に自動作成されることがあるが、validate_config は警告を出す。
- Reconciler は再起動時の OrderSent 注文の整合性回復を担う。OrderSent 状態の永続化は二相持続化（id 保存 → 状態更新）を考慮している。

ディレクトリ構成（主なファイル）
-----------------------------
src/kabusys/
- __init__.py
- __version__ = "0.1.0"

トップレベルモジュール
- config.py               — 環境変数読み込み / Settings クラス（.env 自動ロード）
- config_setup.py         — .env 対話式ウィザード CLI
- validate_config.py      — 起動前設定検証 CLI
- run_execution.py        — ExecutionEngine 起動スクリプト
- run_monitoring.py       — SystemMonitor 起動スクリプト

execution/（発注関連）
- broker_api.py           — Broker API の Protocol / データモデル / ファクトリ
- kabu_client.py          — kabu station 実装（HTTP + WebSocket）
- mock_client.py          — テスト用 MockBrokerClient
- broker_factory.py       — Settings に応じたクライアント生成
- order_record.py         — OrderRecord（状態遷移ロジック）
- order_repository.py     — SQLite 永続化
- order_manager.py        — 発注ワークフロー（create/send/sync/cancel）
- execution_engine.py     — ExecutionEngine（シグナル処理 + push ドレイン）
- reconciler.py           — リコンシリエーション（再起動復旧）
- risk_manager.py         — RiskManager（Gate1/2/3）

data/（データ処理）
- calendar_management.py  — マーケットカレンダー管理（next_trading_day 等）
- news_collector.py       — RSS ニュース収集と前処理
- jquants_client.py       — （参照あり、コードベースで J-Quants API 呼び出しを扱う想定）

monitoring/
- monitoring_db.py        — 監視用 SQLite 初期化 / ログ関係
- system_monitor.py       — システム監視ロジック（run_monitoring が使用）

utils/
- logging_setup.py        — ロギング初期化ユーティリティ
- process_priority.py     — プロセス優先度設定ユーティリティ

スクリプト・補助
- scripts/generate_config.py （validate_config が参照：config/*.yaml を生成するスクリプトが存在すると想定）

付録：よく使うコマンド例
-----------------------
- .env の作成:
  - python -m kabusys.config_setup
- 設定検証（警告も失敗扱い）:
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動（ポーリング間隔を 30 秒に変更）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

最後に
------
この README はコードベースの主要機能と実行手順の概要を示すものです。実運用や詳細な実装理解のためには、各モジュールの docstring と実装を参照してください。修正・補足したい点があれば知らせてください。