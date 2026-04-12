KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株自動売買（KabuSys）のコアライブラリおよび運用用スクリプト群です。
戦略のファクター計算、ポートフォリオ構築、発注管理、監視（モニタリング）、AI を用いたニュース解析など
自動売買の運用に必要なコンポーネントを含みます。

主な特徴
--------
- ポートフォリオ構築（候補選定・重み付け・単元丸め・リスク調整）
- 注文管理（OrderManager / ExecutionEngine、ブローカーファクトリ経由で実際のブローカー連携）
- 再起動時のリコンシリエーション（Reconciler）による自動復旧
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE Push）
- Paper Trading モード（本番 DB と分離、MockBrokerClient を使用）
- AI（OpenAI）を使ったニュースセンチメント評価と市場レジーム判定
- DuckDB / SQLite を用いた履歴・分析・監視データの蓄積
- Streamlit ベースの監視ダッシュボード（読み取り専用）

必須・推奨依存パッケージ
-----------------------
（requirements.txt は含まれていないため、手動でインストールします）
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを使う場合)
- （標準ライブラリ）sqlite3, logging, argparse, datetime, etc.

例:
    python -m pip install duckdb psutil requests openai streamlit

設定（環境変数 / .env）
---------------------
config.Settings が .env または環境変数を読み込みます。自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われ、
OS 環境 > .env.local > .env の優先順位で適用されます。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API 用トークン
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール実行時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（未設定時は送信せずログのみ）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — Monitoring SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant / partial / never / reject）（デフォルト: instant）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用フラグ（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag をクリアする場合は 1
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視の閾値
- KABUSYS_ENV — 起動環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — SystemMonitor のポーリング間隔（秒、run_monitoring で利用）

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージをインストールします（上記参照）。
    python -m pip install --upgrade pip
    python -m pip install duckdb psutil requests openai streamlit

3. data ディレクトリを作成（必要に応じて）。
    mkdir -p data

4. 必須の環境変数を設定します（.env または .env.local を推奨）。
   - 最低限: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - AI を使う場合: OPENAI_API_KEY
   - Paper Trading を使う場合は KABUSYS_ENV=paper_trading を指定するか .env に設定

使用方法（エントリポイント）
----------------------------

- ExecutionEngine（トレード実行）
  - 本番 / 開発 / Paper Trading は KABUSYS_ENV により切替
  - 起動:
        python -m kabusys.run_execution
    Paper Trading にする場合:
        KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    特記事項:
    - Paper Trading 時は MockBrokerClient が使用され、デフォルトで data/paper_trading.db に記録されます（本番 DB と分離）
    - プロセス優先度を High に設定します（psutil による操作。権限により失敗する場合があります）
    - Execution 起動時に PID ファイル（デフォルト data/execution.pid）を作成します

- Monitoring（システム監視ループ）
  - 起動:
        python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）
  - 監視は常に production 用の sqlite_path（SQLITE_PATH）を使用してログを残します
  - LINE トークンを設定するとアラートを送信します

- Streamlit ダッシュボード（読み取り専用）
  - 起動:
        streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、ダッシュボードを表示します

- Paper Trading 検証レポート
  - 起動（期間指定可）:
        python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    --db PATH を指定して別 DB を参照可能。デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数 または data/paper_trading.db

- AI / 研究用 API（プログラムから呼び出す）
  - ニュースセンチメント:
        from kabusys.ai.news_nlp import score_news
        score_news(conn=duckdb_conn, target_date=date(2026,4,1), api_key="…")
  - レジーム判定:
        from kabusys.ai.regime_detector import score_regime
        score_regime(conn=duckdb_conn, target_date=date(2026,4,1), api_key="…")
  - 研究用ファクター計算:
        from kabusys.research import calc_momentum, calc_volatility, calc_value

注意事項・運用メモ
-----------------
- .env パースはシェル風のコメントやクォートに対応した独自実装です。.env.example を参考に作成してください。
- 自動 .env ロードはプロジェクトルートが見つからない場合はスキップされます。
- OpenAI 呼び出し部分は外部 API 呼び出しのため、ネットワークエラー・レート制限へ対応するリトライロジックを含みますが、API キーが必須です。
- run_execution/run_monitoring はプロセス優先度設定を試みます。権限不十分時は警告が出てスキップされます。
- Paper Trading は本番 DB と必ず分離される設計です（settings.is_paper による分岐）。
- Kill Switch (data/kill.flag) により ExecutionEngine の停止を外部から指示できます。kill.flag を作成するか、Monitoring が条件を満たした場合に書き込みます。
- MonitoringDB（SQLite）は冪等にテーブルを作成・マイグレーションを行います（列追加などの簡単なマイグレーション対応あり）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py                    パッケージ定義（__version__ 等）
- config.py                      環境変数 / 設定管理（Settings クラス）
- run_execution.py               ExecutionEngine 起動スクリプト（KABUSYS_ENV により paper_trading 切替）
- run_monitoring.py              SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py  Paper Trading 検証レポート生成スクリプト
- ai/
  - news_nlp.py                   ニュースセンチメント（OpenAI 呼び出し）
  - regime_detector.py            市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py              SQLite ベースの永続化レイヤ
  - system_monitor.py             CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py              注文滞留・約定異常監視
  - risk_monitor.py               ドローダウン・ポジション数監視
  - kill_switch.py                kill.flag の管理
  - alert_manager.py              LINE Push での通知（クールダウン制御あり）
  - monitoring_engine.py          各 Monitor を束ねる実行エンジン
  - streamlit_dashboard.py        Streamlit ダッシュボード（読み取り専用）
- execution/
  - order_manager.py              発注ロジック（OrderManager）
  - reconciler.py                 起動時のリコンシリエーション
  - ...                           （ブローカー API / execution engine 等の他モジュール）
- portfolio/
  - portfolio_builder.py          候補選定、重み計算
  - risk_adjustment.py            セクター制限、レジーム乗数
  - position_sizing.py            発注株数計算・単元丸め・aggregate cap
- research/
  - factor_research.py            Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py        将来リターン、IC、統計サマリー
- utils/
  - process_priority.py           プロセス優先度 / CPU affinity 設定ユーティリティ
- data/                           実行時に用いるデフォルトデータベース等（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）

開発用メモ
----------
- DuckDB の prices_daily / raw_financials / raw_news 等のテーブルが揃っている前提で研究機能（research）や AI 機能を実行します。
- Unit test や CI を導入する場合、環境変数の自動読み込みを KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化して .env に依存しないテストを実行できます。
- API キーやパスワードなどの機密情報は .env.local や CI シークレットで管理してください。

ライセンス・バージョン
----------------------
パッケージバージョンは kabusys.__version__（現状 "0.1.0"）。ライセンス情報はリポジトリルートに配置してください（本リポジトリには明示されていません）。

補足
----
README の内容は現時点のソースコードに基づく抜粋説明です。実運用時は必ず本番前に各モジュール（特にブローカー連携部・資金管理・Kill Switch 動作）を十分にテストしてください。質問や追記事項があれば教えてください。