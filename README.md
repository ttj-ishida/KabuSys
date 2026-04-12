README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を支援する Python ベースのプロジェクトです。本コードベースは以下の主要機能を提供します。

- Execution：発注エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- Monitoring：プロセス・資源・注文状況・リスク（ドローダウン等）を監視しログ・アラートを生成
- Research：DuckDB を用いたファクター計算・特徴量解析（モメンタム、バリュー、ボラティリティ等）
- Portfolio：銘柄選定・重み計算・ポジションサイズ決定（等配分・スコア加重・リスクベース）
- AI：OpenAI（gpt-4o-mini）を用いたニュース NLU によるセンチメントスコアリングや市場レジーム判定
- Tools：Paper Trading の検証レポート生成や Streamlit ダッシュボード等の補助スクリプト
- Utils：プロセス優先度設定や設定読込ユーティリティ等

特徴（機能一覧）
----------------
- 設定管理（kabusys.config.Settings）：.env / .env.local / OS 環境変数から安全に設定を取得
- ExecutionEngine は KABUSYS_ENV に応じて paper_trading 用のモックブローカーを切替（paper_trading は本番 DB と分離）
- 監視モジュール（SystemMonitor / TradeMonitor / RiskMonitor）による DB ログ（SQLite）への永続化とアラート送信（LINE）
- KillSwitch によるフラグファイル書き込みで ExecutionEngine 停止指示
- DuckDB を使ったファクター計算・リサーチ（prices_daily / raw_financials を前提）
- OpenAI を用いたニュースの銘柄別スコアリング（ai.news_nlp.score_news）およびレジーム判定（ai.regime_detector.score_regime）
- Streamlit ベースの監視ダッシュボード（読み取り専用で monitoring.db を可視化）
- Paper Trading 用検証レポート生成スクリプト（tools/paper_verification_report）

セットアップ手順
----------------

1. Python 環境
   - Python 3.9+ を推奨（コードは typing 機能などを使用）
   - 仮想環境を作成することを推奨:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージインストール（代表的なもの）
   - pip install duckdb psutil requests openai streamlit
   - 実際の環境では requirements.txt を用意している場合は pip install -r requirements.txt

3. データディレクトリ
   - デフォルトの DB / ファイルは data/ 以下を想定しています。必要に応じて作成してください。
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (SQLite: 監視ログ)
     - data/paper_trading.db (Paper Trading 用 SQLite)
     - data/execution.pid (ExecutionEngine が書き込む PID ファイル)
     - data/kill.flag (KillSwitch 用フラグファイル)

4. 環境変数設定
   - プロジェクトルートに .env / .env.local を配置して設定できます。自動ロードはデフォルトで有効です。
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject
     - MONITOR_POLL_INTERVAL=60  # run_monitoring でポーリング間隔を秒で上書き
     - LOG_LEVEL=INFO
   - .env 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 初期 DB 作成
   - run_monitoring.py / run_execution.py 実行時に monitoring DB のテーブルは自動で作成（init_monitoring_db）されます。

使い方（主要スクリプト）
-----------------------

- 実行（ExecutionEngine）
  - 本番/開発/ペーパー切替は KABUSYS_ENV による:
    - KABUSYS_ENV=paper_trading を設定すると、モックブローカーを使用し data/paper_trading.db を用います。
  - 起動コマンド:
    - python -m kabusys.run_execution
  - 起動処理:
    - プロセス優先度を "high" に設定（可能なら）
    - SQLite / DuckDB に接続し、ExecutionEngine を起動して run_session()

- 監視（SystemMonitor の単体起動スクリプト）
  - ポーリングループで定期監視を実行:
    - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定（デフォルト 60 秒）
  - 監視は本番 sqlite_path を使って記録（KABUSYS_ENV に依存しない）

- Streamlit ダッシュボード
  - 監視用ダッシュボードを起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で監視 DB を可視化（Positions / Orders / System / Overview）

- Paper Trading 検証レポート
  - tools/paper_verification_report を使用してレポートを生成:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - 引数 --db で SQLite のパスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI スコアリング（プログラムから呼び出し）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY か引数で指定）
  - ニューススコア（銘柄別 ai_scores への書き込み）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

設定（Settings）について
------------------------
- 設定は kabusys.config.Settings を介して参照します。主要プロパティ:
  - env: KABUSYS_ENV（development / paper_trading / live）
  - sqlite_path: 監視用 SQLite（デフォルト data/monitoring.db）
  - duckdb_path: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - paper_sqlite_path: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
  - pid_file_path / kill_flag_path: 実行管理用ファイルパス
  - paper_fill_mode: PAPER_FILL_MODE（instant/partial/never/reject）
  - CPU / メモリ / ディスクの閾値なども環境変数で指定可能

注意点 / 運用メモ
-----------------
- paper_trading 環境は本番 DB と分離されるため、安全に検証できます。
- Monitoring のログテーブルは init_monitoring_db() で冪等に作成されます。既存 DB に対して必要なマイグレーション（例: カラム追加）も自動的に行います。
- KillSwitch は data/kill.flag を作成して ExecutionEngine に停止指示を与える仕組みです。起動時に KILL_FLAG_CLEAR_ON_START を使って自動的に消去するオプションがあります。
- OpenAI API 呼び出しはリトライやバックオフ・レスポンスの厳密なバリデーションを行いますが、API キーの管理・利用料には注意してください。
- process priority / cpu affinity の設定は psutil に依存し、権限不足や非対応 OS の場合はログに警告が出てスキップされます。

ディレクトリ構成（主要ファイル）
--------------------------------
- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / .env 読込・Settings
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py                — ニュース NLU / OpenAI スコアリング
      - regime_detector.py         — 市場レジーム判定（LLM + MA200）
    - data/ (想定される外部 DB ファイル)
      - pipeline.py (参照されるユーティリティ)
      - stats.py (zscore など)
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - ... (broker_factory, execution_engine 等)
    - monitoring/
      - __init__.py
      - monitoring_db.py            — SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
      - streamlit_dashboard.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - process_priority.py

よく使うコマンド例
------------------
- 実行エンジンの起動:
  - python -m kabusys.run_execution
- 監視ループの起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
本リポジトリのライセンス情報や貢献ガイドはプロジェクトルートの LICENSE / CONTRIBUTING 等を参照してください（存在しない場合はリポジトリ管理者に相談してください）。

補足
----
- 本 README はコードベースから読み取れる設計意図・使い方をまとめたもので、実際の運用手順や追加の依存パッケージはプロジェクト固有の要件に合わせて調整してください。
- 実行前に必ず必要な API キーやパスワード（OPENAI_API_KEY / KABU_API_PASSWORD / JQUANTS_REFRESH_TOKEN 等）を適切に設定してください。