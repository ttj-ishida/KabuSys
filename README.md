README
======

概要
----
KabuSys は日本株自動売買のためのモジュール群です。本リポジトリには以下の機能が含まれており、取引実行エンジン、監視・アラート、ポートフォリオ構築、研究用ファクター計算、ニュースNLP（OpenAI）を用いたセンチメント評価などが実装されています。設計は本番 / ペーパートレードを環境変数で切り替えられるようになっており、SQLite / DuckDB を使ったローカル永続化を前提としています。

主な特徴
--------
- ExecutionEngine 起動スクリプト（run_execution）: ブローカークライアントを利用した発注・リスク管理・リコンシリエーション
- MonitoringEngine（run_monitoring）: システム状態・注文・リスク監視、LINE によるアラート、kill flag による停止シグナル
- Paper Trading 用分離 DB（data/paper_trading.db）を利用したペーパートレードモード
- ニュース NLU（OpenAI）による銘柄単位センチメントスコア生成（ai.news_nlp）
- 市場レジーム判定（ai.regime_detector）
- ポートフォリオ構築：候補選出、重み計算、ポジションサイズ計算、セクター制限、レジーム調整
- Research：ファクター計算（momentum/value/volatility）、将来リターン・IC・統計サマリー
- Streamlit ダッシュボード（監視用）
- Paper Trading 検証レポート生成スクリプト

前提条件 / 依存ライブラリ
-----------------------
以下を想定しています（pip でインストール）:
- python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit
（例）pip install duckdb psutil requests openai streamlit

セットアップ手順
---------------
1. リポジトリをクローン／展開し、作業ディレクトリをプロジェクトルートにする（pyproject.toml または .git があるディレクトリをプロジェクトルートとみなします）。
2. 依存パッケージをインストール:
   pip install -r requirements.txt
   （requirements.txt がない場合は上の依存を個別にインストール）
3. 環境変数を設定:
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（既存の OS 環境変数は保護されます）。
   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
4. data ディレクトリ（data/）を作成しておくことを推奨（DB・PID・フラグファイル格納）。
5. 必須環境変数を設定（詳細は下記「主な環境変数」参照）。

主な環境変数
------------
- KABUSYS_ENV: 起動環境 (development | paper_trading | live)。デフォルト: development
  - paper_trading の場合は MockBroker を使い、paper_sqlite_path（デフォルト data/paper_trading.db）を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector を利用する場合必須）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite パス（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視 DB のパス（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" でクリア）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒。デフォルト 60）

データ / フラグファイル
---------------------
- data/monitoring.db: 監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）
- data/paper_trading.db: ペーパートレード専用 SQLite（KABUSYS_ENV=paper_trading で使用）
- data/kabusys.duckdb: DuckDB（価格・財務データ等の分析用テーブル）
- data/execution.pid: ExecutionEngine が生成する PID ファイル
- data/kill.flag: KillSwitch が作成する停止フラグ（存在すると ExecutionEngine に停止シグナルを出す）
- data/stop_requested.flag: run_* スクリプトが参照する停止リクエスト用ファイル（存在するとループを抜ける）

使い方（主要エントリポイント）
---------------------------

1) ExecutionEngine を起動する（実行責務: 発注・リスク管理）
- コマンド:
  python -m kabusys.run_execution
- 動作:
  - Settings を読み、KABUSYS_ENV が paper_trading の場合は paper_sqlite_path を DB として使用
  - BrokerClientFactory によりブローカークライアントを生成（mock or real）
  - Reconciler による起動時リコンシリエーションを実行し、ExecutionEngine.run_session を別スレッドで開始
  - data/stop_requested.flag を監視して停止
- 注意:
  - PID ファイル path は Settings.pid_file_path（デフォルト data/execution.pid）
  - stop フラグが既に立っていれば起動しない

2) Monitoring（監視ループ）を起動する
- コマンド:
  python -m kabusys.run_monitoring
- 動作:
  - process priority を "high" に設定（可能な場合）
  - monitoring 用に sqlite_path（デフォルト data/monitoring.db）と duckdb を接続
  - SystemMonitor を起動して定期ポーリング（デフォルト 60 秒）
- ポーリング間隔の上書き:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 備考:
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視ログは環境に依存しない）

3) Streamlit ダッシュボード（監視 UI）
- コマンド例:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - read-only モードで monitoring DB を開きダッシュボードを表示
  - MonitoringEngine が先に起動していてデータが入っている必要あり

4) Paper Trading 検証レポート生成
- コマンド:
  python -m kabusys.tools.paper_verification_report
  または
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション:
  --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH（デフォルト data/paper_trading.db）
- 出力:
  - 稼働率、注文成功率、送信率、レイテンシ（P95）などの指標と PASS/FAIL 判定

5) AI 系機能（プログラム的に呼び出し）
- ニューススコアリング:
  from kabusys.ai.news_nlp import score_news
  score_news(duckdb_conn, target_date, api_key="...")

- レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(duckdb_conn, target_date, api_key="...")

- これらは OPENAI_API_KEY を環境変数で提供しても動作します。

停止フラグ・停止の仕組み
---------------------
- run_execution / run_monitoring はプロジェクト内 data/stop_requested.flag を監視します（存在すると安全に終了します）。
- KillSwitch（監視側）はリスク閾値を超えると data/kill.flag を書き込みます。ExecutionEngine は起動時にこの kill.flag を検査し、存在する場合は起動を中止できます（Settings.kill_flag_clear_on_start によって自動クリアの挙動が制御されます）。

ディレクトリ構成（主なファイル）
------------------------------
- src/kabusys/
  - __init__.py: パッケージ定義
  - config.py: 環境変数/.env の読み込みと Settings クラス
  - run_execution.py: ExecutionEngine 起動スクリプト
  - run_monitoring.py: Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py: Paper Trading 検証レポート生成CLI
  - ai/
    - news_nlp.py: ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py: 市場レジーム判定（ma200 + マクロセンチメント）
  - portfolio/
    - portfolio_builder.py: 候補選出・重み計算
    - position_sizing.py: 株数・投資額算出
    - risk_adjustment.py: セクターキャップ・レジーム乗数
  - research/
    - factor_research.py: momentum/value/volatility 等のファクター計算
    - feature_exploration.py: 将来リターン、IC、統計サマリー等
  - monitoring/
    - monitoring_db.py: SQLite テーブル初期化・読み書きラッパー
    - system_monitor.py: システム状態・データ鮮度監視
    - trade_monitor.py: 注文滞留・約定異常監視
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: kill.flag の生成/削除ユーティリティ
    - alert_manager.py: LINE Push 送信ユーティリティ
    - monitoring_engine.py: 各モニタを束ねる実行ループ
    - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py: 発注の外向き API、状態遷移管理
    - reconciler.py: 起動時の同期・リコンシリエーション
    - order_repository.py: Orders DB 操作（SQLite）
    - order_record.py: OrderRecord と状態定義
    - broker_factory.py, broker_api.py: ブローカー抽象とファクトリ
  - utils/
    - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/（実行時に使用されるディレクトリ、リポジトリ外に置くことも可能）
    - monitoring.db (default SQLITE_PATH)
    - paper_trading.db (default PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (default DUCKDB_PATH)
    - execution.pid
    - kill.flag / stop_requested.flag

実運用上の注意
--------------
- 環境変数の必須チェックは Settings クラスで行われます（JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD 等）。
- OpenAI を利用する機能は API エラー耐性（リトライ、フェイルセーフ値）を備えていますが、キーやリクエスト上限には注意してください。
- Monitoring は監視DB（SQLite）に継続的に書き込みます。定期的なバックアップ・ログローテーションを検討してください。
- process priority / cpu affinity の設定は実行環境の権限に依存します。権限不足時は警告ログが出てスキップされます。
- データ鮮度チェックは DuckDB の prices_daily を参照します。データロードパイプライン（kabusys.data.pipeline）を別途用意してください。

トラブルシュート / 開発メモ
--------------------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基に行われます。テスト時などで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MonitoringDB.init_monitoring_db は冪等でマイグレーション（列追加）を行います。既存 DB との互換性に配慮しています。
- run_monitoring は MONITOR_POLL_INTERVAL が不正（0以下や非整数）の場合デフォルト 60 秒にフォールバックします。
- run_execution は KABUSYS_ENV=paper_trading のとき DB を分離します（実口座と完全分離）。

ライセンス
----------
（リポジトリに合わせて記載してください）

以上。必要があれば、README に追加したいサンプル .env のテンプレートやデプロイ手順（systemd / supervisor 用 unit 例）、開発用の Dockerfile / docker-compose 例も作成できます。どの項目が必要か教えてください。