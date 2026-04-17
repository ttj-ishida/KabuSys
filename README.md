# KabuSys

KabuSys は日本株の自動売買および研究・監視ツール群を含む小規模なプロジェクトです。本リポジトリには、注文実行エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ（ファクター計算）、AI を使ったニュースセンチメント解析などのモジュールが含まれます。

以下はコードベースの概要、機能、セットアップ、使い方、主要ディレクトリ構成の README です。

---

目次
- プロジェクト概要
- 主な機能
- 前提・依存ライブラリ
- セットアップ手順
- 環境変数（主な設定）
- 実行例（監視 / 実行 / レポート / ダッシュボード / AI）
- ライブラリ利用例（主要モジュール）
- ディレクトリ構成

---

プロジェクト概要
- 日本株自動売買システムのプロトタイプ兼ユーティリティ集。
- 発注/注文管理、実行エンジン、監視エンジン、リスク管理、ポートフォリオ構築、ファクターリサーチ、ニュースの NLP スコアリング、Streamlit ダッシュボード等を含む。
- SQLite / DuckDB をデータストアに利用。OpenAI API をニュース解析やレジーム判定に利用する仕組みを備える。

主な機能
- ExecutionEngine（注文作成、発注、OrderManager、Reconciler による再同期機能）
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
  - プロセス死活、データ鮮度、滞留注文、約定価格の異常、ドローダウン・ポジション上限検出
  - kill.flag による ExecutionEngine 停止指示
  - LINE を使ったアラート（AlertManager）
  - Streamlit ダッシュボード（監視用）
- Portfolio（候補選定、等配分/スコア配分、ポジションサイズ計算、セクターキャップ、レジーム乗数）
- Research（ファクター計算: momentum, volatility, value、将来リターン、IC 計算、統計サマリー）
- AI（ニュース NLP による銘柄別センチメントスコア化、マクロニュースを使ったレジーム判定）
- ツール: Paper Trading の検証レポート生成スクリプト

前提・依存ライブラリ（主なもの）
- Python 3.9+
- duckdb
- requests
- psutil
- openai
- streamlit（ダッシュボード起動時）
- sqlite3（標準ライブラリ）
- その他：typing 等の標準ライブラリ

※ requirements.txt は本 README に含まれませんが、上記パッケージをインストールしてください。

セットアップ手順（例）
1. リポジトリをクローン / コピー
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb requests psutil openai streamlit
   - （必要に応じてその他パッケージを追加）
4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動でロードされます（自動ロードは OS 環境変数 > .env.local > .env の優先順）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
5. data ディレクトリを作成（実行・監視ファイル置き場）
   - mkdir -p data

主な環境変数（設定可能なキーとデフォルト）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live") — デフォルト: development
- SQLITE_PATH: 監視用 SQLite DB パス — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite DB — デフォルト: data/paper_trading.db
- DUCKDB_PATH: DuckDB パス — デフォルト: data/kabusys.duckdb
- PID_FILE_PATH: ExecutionEngine の PID ファイル — デフォルト: data/execution.pid
- KILL_FLAG_PATH: kill.flag のパス — デフォルト: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を消す（"1"で有効）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒） — デフォルト: 60（run_monitoring で上書き可能）
- PAPER_FILL_MODE: Paper Trading 時の fill モード ("instant" | "partial" | "never" | "reject") — デフォルト: "instant"
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必要）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など（実運用時に必須）

実行例

1) 監視ループを起動
- モジュール実行:
  - python -m kabusys.run_monitoring
- 補足:
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を設定できます（正の整数で、デフォルト 60 秒）。
  - run_monitoring は monitoring 用 DB に対して常に "本番" sqlite_path を使います（KABUSYS_ENV に依らず）。

2) ExecutionEngine（注文実行）を起動
- python -m kabusys.run_execution
- 補足:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用専用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。本番 DB と分離されます。
  - 起動時に data/execution.pid が生成され、data/stop_requested.flag や data/kill.flag によって停止を受け取ります。
  - プロセス優先度が "High" に設定されます（set_process_priority が呼ばれます。権限がなければ警告を出してスキップされます）。

3) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB は data/paper_trading.db。`--db PATH` で別ファイルを指定できます。
- 出力: システム稼働率、注文成功率、送信率、レイテンシ（P95）等を表示。PASS/FAIL 判定あり。

4) Streamlit ダッシュボード（監視）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードでは dashboard 集計、オープンポジション、最近の発注ログ、最新システム状態、最近のリスクイベントを閲覧できます。
- DB は読み取り専用で開かれます（URI に mode=ro を付与）。

5) AI モジュール（ニュース NLP / レジーム判定）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（ai モジュールは DuckDB を参照）と target_date を渡してニュースをスコア化し ai_scores テーブルへ書き込みます。
  - api_key を指定しない場合は環境変数 OPENAI_API_KEY を参照します。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime テーブルへ書き込みます。
- 注意: OpenAI API 呼び出しはリトライ・フェイルセーフ機構が組み込まれており、API キーが未設定の場合は例外を投げます。

ライブラリ利用例（簡単なコードスニペット）
- ポートフォリオ候補選定＋重み計算
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights
  - candidates = select_candidates(buy_signals, max_positions=10)
  - weights = calc_score_weights(candidates)
- ポジションサイズ計算
  - from kabusys.portfolio import calc_position_sizes
  - shares_map = calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices)
- ファクター計算（リサーチ）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - results = calc_momentum(duckdb_conn, target_date)

停止・フラグファイル
- data/stop_requested.flag: run_monitoring / run_execution のループがこのファイルの存在を検出すると終了します（運用側がプロセスをやさしく停止したいときに利用）。
- data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止シグナルを送ります（監視の重大トリガー発動時）。
- data/execution.pid: ExecutionEngine の PID を保存します。SystemMonitor はこの PID を使ってプロセス生存チェックを行います。

注意事項 / 運用上のヒント
- .env 読み込みは自動で行われます。OS 環境変数を保護するため .env.local を上書きとして読み込みます（優先度高）。
- monitoring 側は監視とアラートに特化しており、監視 DB は production 用 sqlite_path を参照します（run_monitoring では env に依らず production を使う仕様）。
- Paper Trading は本番 DB と分離されています。テストや検証は paper_trading 環境で行ってください。
- OpenAI API を使用する機能を利用する場合は OPENAI_API_KEY を必ず設定してください。
- Process priority（優先度）や CPU affinity の設定は psutil を使います。権限がないと警告が出てスキップされます。

主要ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py          —（エンジン本体は参照されています）
    - broker_factory.py
    - broker_api.py
    - order_record.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                           — 実行時に使用する DB・フラグファイル（リポジトリには含まれない想定）
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成

最後に
- 本 README はコードベースの主要な使い方と設計意図を簡潔にまとめたものです。実運用前には各モジュールのログ出力や DB スキーマ（monitoring_db.init_monitoring_db）を確認し、必要な初期データ（prices_daily / raw_financials / raw_news 等）を DuckDB にロードしてください。
- 追加の具体的な質問（例: 特定モジュールの振る舞い、API の呼び出し例、DB スキーマ詳細など）があれば教えてください。必要に応じて README を拡張します。