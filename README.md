KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムを想定したモジュール群です。主な機能は次の通りです。

- 注文発行・状態管理（ExecutionEngine / OrderManager / Reconciler）
- リスク管理・監視（RiskMonitor / TradeMonitor / SystemMonitor / KillSwitch）
- 監視ログの永続化（SQLite: monitoring.db）と分析用 DuckDB（kabusys.duckdb）
- ポートフォリオ構築ロジック（候補選定、重み付け、ポジションサイズ算出）
- 研究用ファクター計算・特徴量解析（DuckDB 上の prices_daily/raw_financials を利用）
- ニュース NLP を用いた AI スコアリング（OpenAI を用いて ai_scores を生成）
- Streamlit による監視ダッシュボードと検証レポート生成ツール

設計方針（抜粋）
- DB/外部 API へのアクセス箇所を限定し、研究・検証コードは本番処理と分離。
- ルックアヘッドバイアスを避けるために date/time の直接参照を最小化。
- フェイルセーフ（API失敗時のフォールバックやログ出力）を重視。

主な機能一覧
--------------
- execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアント切替（本番 / paper_trading の切替）
  - OrderManager（発注・重複チェック・状態遷移）
  - Reconciler（再起動後の注文・ポジション突合）
- monitoring
  - run_monitoring.py: SystemMonitor のポーリングループ起動
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard 等
  - Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）
  - tools: Paper Trading 検証レポート生成スクリプト
- research
  - factor_research: モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC、統計サマリ
- ai
  - news_nlp: raw_news を集約して OpenAI API で銘柄別センチメントスコアを生成（ai_scores テーブルへ）
  - regime_detector: ETF ma200 乖離 + マクロニュースで市場レジーム判定し market_regime に保存
- portfolio
  - 候補選定、重み付け、リスク調整、ポジションサイズ算出（純粋関数群、DBに依存しない）

必須環境変数（主要）
-------------------
主に Settings クラス（kabusys.config）で参照します。実運用前に .env を用意してください（.env.example 相当を参照）。

必須（実行に必要な場合）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（research 等で必要）
- KABU_API_PASSWORD — kabuステーション API 用パスワード

重要な任意／設定系
- OPENAI_API_KEY — OpenAI 呼び出し（ai.news_nlp / ai.regime_detector）
- KABUSYS_ENV — 動作モード: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合は MockBrokerClient を使用し DB を分離（data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の成行執行挙動: instant | partial | never | reject（デフォルト: instant）
- SQLITE_PATH — 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- PID_FILE_PATH / KILL_FLAG_PATH 等も Settings で定義可能

.env 自動読み込み
- プロジェクトルートにある .env と .env.local が自動で読み込まれます（OS 環境変数を保護）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

セットアップ手順
----------------
推奨: Python >= 3.10

1. リポジトリを取得
   - git clone ...（プロジェクトルートが .git または pyproject.toml で特定されます）

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install pip --upgrade
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じて他のライブラリを追加してください）

   ※ requirements.txt がある場合は pip install -r requirements.txt を利用します。

4. .env を作成
   - プロジェクトルートに .env（または .env.local）を作成し、上記の環境変数を設定してください。
   - 例:
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

5. data ディレクトリの準備（任意）
   - data/ 以下は自動作成されますが、手動で mkdir -p data しておくとよいです。

基本的な使い方
--------------
起動／停止
- ExecutionEngine（取引エンジン）起動
  - 通常（本番）: KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行前に data/kill.flag をクリアしたい場合は KillSwitch.clear() を使うか手動で削除してください。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更したい場合:
    - export MONITOR_POLL_INTERVAL=30  # 秒（1 以上）
  - 監視は Settings.env に関わらず本番の sqlite_path を使用して監視テーブルを記録します（監視用は production DB を参照する設計）。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または指定 DB: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

停止フラグ / キルスイッチ
- 実行中の engine/monitor を外部から停止したい場合:
  - 停止要求フラグ: data/stop_requested.flag を作成すると run_execution/run_monitoring のループが優雅に終了します。
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。KillSwitch はリスク閾値（ドローダウン、ポジション上限など）に基づき自動的にフラグを書きます。
  - 起動時に KillFlag をクリアする設定 kill_flag_clear_on_start があります（Settings 参照）。

AI 機能の利用
- ai.news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡して銘柄別にニュースセンチメント（ai_scores）を作成します。api_key を省略すると環境変数 OPENAI_API_KEY を使用します。
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF (1321) の ma200 乖離 + マクロニュースでレジームを判定して market_regime テーブルへ書き込みます。

監視ログ DB 初期化
- init_monitoring_db(sqlite_conn) を呼ぶことで監視用のテーブル（system_status, trade_logs, positions, risk_logs, dashboard）を冪等に作成します。run_execution/run_monitoring は起動時に自動で呼び出します。

主要スクリプト一覧（実行例）
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py                     — パッケージ定義、バージョン
- config.py                       — 環境変数 / 設定管理（.env 自動読み込み含む）
- run_execution.py                — ExecutionEngine 起動スクリプト
- run_monitoring.py               — SystemMonitor ポーリング起動スクリプト

subpackages:
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - execution_engine.py (存在)
  - broker_factory.py / broker_api.py
  - ...（注文・ブローカー関連）
- monitoring/
  - monitoring_db.py               — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- ai/
  - news_nlp.py
  - regime_detector.py
- research/
  - factor_research.py
  - feature_exploration.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py
- data/                            — 実行時に生成されるファイル例:
  - monitoring.db (SQLite)
  - paper_trading.db (SQLite; paper_trading 環境用)
  - kabusys.duckdb (DuckDB)
  - execution.pid
  - kill.flag / stop_requested.flag

運用上の注意
-------------
- paper_trading モードは本番 DB と完全に分離して動作する設計です（PAPER_TRADING_SQLITE_PATH を利用）。
- OpenAI API 呼び出しはレート制御・リトライ実装がありますが、API キーやコストの管理は運用者側で行ってください。
- process priority や CPU affinity の設定はプラットフォーム依存（psutil）です。権限不足で設定できない場合はログに警告が出てスキップされます。
- monitoring/run scripts は停止フラグや PID ファイルを使ってプロセスの管理を行います。ファイルベースの信号を用いるため、ファイルのパーミッションや配置に注意してください。

テスト・開発
-------------
- 研究／解析機能は DuckDB 上の prices_daily / raw_financials / raw_news 等のテーブルを前提とします。サンプルデータや ETL パイプラインが必要です。
- OpenAI 呼び出し部はテスト容易性を考慮して呼び出し関数を分離しているため、unittest.mock で差し替えてテストしやすく設計されています。

ライセンス / 貢献
-----------------
（このリポジトリに含まれるライセンス／貢献ガイドラインに従ってください）

最後に
-------
この README はコードベースの主要コンポーネントと使い方の概略を示したものです。詳細は各モジュール（src/kabusys/...）の docstring と実装コメントを参照してください。不明点があればどの部分について知りたいかを教えてください。