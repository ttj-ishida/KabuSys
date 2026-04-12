KabuSys — 日本株自動売買システム
=================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした小規模なPythonパッケージです。  
主な目的は以下です。

- 自動売買の実行エンジン（ExecutionEngine）
- 発注・約定のリコンシリエーションとリスク管理
- 監視（System / Trade / Risk）と通知（LINE）
- Paper Trading（モックブローカー）による検証ワークフロー
- 研究用ファクター計算・特徴量探索（DuckDBを使用）
- ニュースのLLM（OpenAI）によるセンチメントスコアリングとレジーム判定
- Streamlit を使った監視ダッシュボード、検証レポート生成ツール

主な特徴
--------
- ExecutionEngine は本番 / paper_trading を切り替えて動作（DBは分離）
- 監視用プロセス（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
  - kill.flag による外部停止指示、LINEによるアラート機能を備える
- DuckDB を用いたファクター計算・研究モジュール（prices_daily / raw_financials 想定）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai.score_news）および市場レジーム判定（ai.score_regime）
- Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）
- Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）
- 設定は .env ファイルまたは環境変数で管理（kabusys.config.Settings）

前提（推奨）
------------
- Python 3.10+
- DuckDB（Pythonパッケージ duckdb）
- psutil
- requests
- openai（OpenAI Python SDK）
- streamlit（ダッシュボード利用時）
- SQLite（Python 標準ライブラリ sqlite3 を使用）

必要なパッケージ例（インストール例）
- pip install duckdb psutil requests openai streamlit

セットアップ手順
--------------
1. リポジトリをクローン / ソースを配置（パッケージは src/ 配下に配置済みを想定）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

4. 環境変数の設定
   - プロジェクトルートに .env/.env.local を置くことができます（kabusys.config が自動ロード）
   - 重要な環境変数（一部）:
     - KABUSYS_ENV = development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY （AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知）
     - SQLITE_PATH（監視DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH 等（デフォルトを使用可）

   - サンプル .env（最小）
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=your_jquants_token
     - KABU_API_PASSWORD=your_kabu_password
     - OPENAI_API_KEY=sk-xxxxx
     - LINE_CHANNEL_ACCESS_TOKEN=xxxxx
     - LINE_USER_ID=Uxxxxxxxxxxxx

5. データディレクトリ作成
   - デフォルトの DB / PID / フラグ用ディレクトリを作成:
     - mkdir -p data

起動方法 / 使い方
----------------

- 監視プロセス（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト 60）
    - 監視は settings.sqlite_path（data/monitoring.db など）にログを保存します。
    - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使います（監視ログは本番 DB を想定）

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にデータを保存します（本番DBと分離）
    - Engine は Settings を参照して duckdb / sqlite を接続します
    - ExecutionEngine は PID ファイルを作成して自己監視が行えます

- Paper Trading 検証レポート（CSV ではなく標準出力）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH を上書き）

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - データベースを読み取り専用で開きます（存在しない場合はエラー表示）

- AI（ニュースセンチメント / レジーム判定）
  - ai.score_news(conn, target_date, api_key=None) — ai/news_nlp.py を参照
  - ai.score_regime(conn, target_date, api_key=None) — ai/regime_detector.py を参照
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください

挙動の重要な注意点
------------------
- Settings は .env を自動でロードしますが、テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- run_monitoring は監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）用のテーブルがなければ自動作成します（init_monitoring_db）。
- Paper Trading を使うときは KABUSYS_ENV=paper_trading を設定してください。paper_trading 用 DB は production DB と物理的に分離されます。
- process priority / CPU affinity の設定には psutil を使用します。権限不足の場合はログにワーニングが出ますが、動作は続行します。
- OpenAI 呼び出しはリトライやフェイルセーフを複数箇所で実装していますが、APIキー未設定時は ValueError が発生します。

主なファイル / ディレクトリ構成
------------------------------
（src/kabusys 配下） — 主要モジュールを抜粋

- src/kabusys/
  - __init__.py
  - config.py                —— 環境変数 / Settings 管理
  - run_monitoring.py        —— SystemMonitor のポーリング起動スクリプト
  - run_execution.py         —— ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py —— Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py            —— ニュースセンチメント（OpenAI）処理
    - regime_detector.py     —— 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       —— monitoring DB 初期化 / MonitoringDB クラス
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - ...（OrderRepository / BrokerFactory 等、実行関連の実装を含む）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                     —— パイプライン / DuckDB 関連（prices_daily 参照コードが期待）
  - utils/
    - process_priority.py     —— psutil を使った優先度設定ユーティリティ

主要テーブル（監視 DB: monitoring.db）
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (single row id=1 に集計ダッシュボード情報)

開発 / テスト
-------------
- DuckDB を利用したファクター計算・研究モジュールは、prices_daily / raw_financials 等のテーブルを想定しています。ローカルでテストデータを用意して DuckDB ファイルを作成してください。
- OpenAI 呼び出し部は直接 API を叩くため、テスト時は該当関数（_call_openai_api）をパッチするか、APIキーを与えないことでエラーを防げます（関数は例外処理内でフェイルセーフを取っていますが、明示的なテスト用モックがおすすめです）。
- run_monitoring / run_execution はそれぞれ main() があるため、python -m kabusys.run_monitoring のようにモジュールとして起動できます。

ライセンス / その他
-------------------
- このリポジトリにライセンスファイルがある場合はそちらを参照してください（本READMEはライセンス情報を含みません）。
- 本README はソースコードのコメントと実装に基づく要約です。実運用前に .env の機密情報やAPIキー、アクセス権限周りは慎重に取り扱ってください。

問題が発生したら
----------------
- 実行時に DB のスキーマが不足する場合は、run_monitoring/run_execution 起動で init_monitoring_db が実行されてテーブルが作成されます。
- OpenAI 呼び出しや LINE 通知の失敗はログに記録されます。ログ出力を確認してください。
- さらに詳細が必要であれば、どの機能（例: 実行エンジンの起動手順、AI モジュールのテスト方法、DB スキーマ説明など）にフォーカスして欲しいか教えてください。