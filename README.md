KabuSys — README
=================

このドキュメントは、提供されたコードベース（src/kabusys）向けの簡易 README です。日本株の自動売買・リサーチ・監視・AI スコアリングを行う内部ライブラリ群を含みます。

プロジェクト概要
--------------
KabuSys は日本株向けの自動売買／リサーチ／監視プラットフォームのライブラリ群です。主に以下を目的とします。

- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究用ユーティリティ
- ポートフォリオ構築（候補選定、重み計算、銘柄ごとの株数算出）
- 市場レジーム判定・ニュース NLP による LLM ベースのセンチメント集約
- 発注エンジン（ExecutionEngine）・注文管理（OrderManager）・リコンシリエーション
- 監視（System / Trade / Risk）と通知（LINE）・ダッシュボード（Streamlit）
- 小さな永続層：DuckDB（価格・ファイナンス等）と SQLite（監視ログ等）

主な機能一覧
--------------
- 環境変数管理（自動 .env/.env.local 読み込み、settings オブジェクト）
- Portfolio construction
  - 候補選定（select_candidates）
  - 等配・スコア加重配分（calc_equal_weights / calc_score_weights）
  - ポジションサイズ算出（calc_position_sizes） — risk/equal/score モード対応
  - セクターキャップ適用、レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- Research（duckdb ベース）
  - モメンタム / ボラティリティ / バリュー ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン・IC・統計要約（calc_forward_returns, calc_ic, factor_summary）
- AI
  - ニュース記事を LLM（OpenAI）でセンチメント化し ai_scores に書き込む（score_news）
  - マクロニュース + ETF MA による市場レジーム判定（score_regime）
- Execution / Broker
  - Broker API 抽象（Protocol, データモデル、例外）
  - OrderManager（作成・送信・同期・キャンセル）
  - ExecutionEngine（signal 取込み → 発注ループ、WebSocket プッシュ処理、Kill Switch）
  - 起動時リコンシリエーション（Reconciler）
- Monitoring
  - MonitoringDB（SQLite）初期化 / CRUD
  - System / Trade / Risk モニタ、KillSwitch、AlertManager（LINE Push）
  - Streamlit ダッシュボード

必要条件（依存パッケージの例）
-----------------------------
主なランタイム依存（実行する機能により必要なものが変わります）：
- Python 3.10+
- duckdb
- openai (OpenAI SDK)
- requests
- psutil
- streamlit（ダッシュボードを使用する場合）
- sqlite3（標準ライブラリ）
必要に応じて pip / Poetry 等でインストールしてください（requirements.txt は別途作成してください）。

セットアップ手順
----------------
1. リポジトリをクローン / 展開
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai requests psutil streamlit
   - （必要に応じて他パッケージを追加）
4. 環境変数の設定
   - プロジェクトルートに .env/.env.local を置くと、自動で読み込まれます（settings モジュールが自動ロード）。
   - .env.example を参考に作成してください（リポジトリに含める想定）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
5. DuckDB / SQLite の用意
   - DuckDB に price/financial/news 等のテーブルが必要です（データ投入は別途）。
   - 監視用 DB: デフォルト data/monitoring.db。MonitoringDB 初期化は init_monitoring_db(conn) を呼ぶことでテーブル作成します。

主要な環境変数（settings から参照）
-----------------------------------
- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API 用
- KABU_API_PASSWORD（必須） — Kabu ステーション API 用
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — アラート送信用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB パス（デフォルト data/monitoring.db）
- PAPER_FILL_MODE — paper trading 設定（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — paper trading 用 SQLite path（デフォルト data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / 各種閾値（CPU/MEM/DISK）
- KABUSYS_ENV — development|paper_trading|live
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL

使い方（コード例）
------------------

- settings の利用（環境変数読み取り）
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path など

- ファクター計算（DuckDB 接続がある前提）
  - import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    from datetime import date
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    recs = calc_momentum(conn, date(2026, 3, 20))

- 将来リターン / IC / 統計
  - from kabusys.research import calc_forward_returns, calc_ic, factor_summary
    fwd = calc_forward_returns(conn, date(2026,3,20))
    ic = calc_ic(factor_records, fwd, "mom_1m", "fwd_1d")
    summary = factor_summary(factor_records, ["mom_1m","mom_3m","per"])

- AI ニューススコアリング（score_news）
  - from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,3,20), api_key="sk-...")

  - 注意：OPENAI_API_KEY を ENV で渡すことも可能。score_news は ai_scores テーブルに書き込みます。

- レジーム判定（score_regime）
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監視 DB 初期化（SQLite）
  - import sqlite3
    from kabusys.monitoring.monitoring_db import init_monitoring_db
    conn = sqlite3.connect("data/monitoring.db")
    init_monitoring_db(conn)

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ExecutionEngine（簡易）
  - 実際には Broker 実装・OrderRepository 等を用意する必要があります。概念例:
    from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig
    engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duckdb_conn, EngineConfig(target_date=date.today()))
    engine.run_session()

  - ExecutionEngine は起動時に kill.flag の存在をチェックし、既存フラグの挙動は settings.kill_flag_clear_on_start で制御されます。

ディレクトリ構成（主要ファイルと説明）
------------------------------------
src/kabusys/
- __init__.py — パッケージ宣言・バージョン
- config.py — 環境変数・設定管理（.env/.env.local 自動読み込み、settings オブジェクト）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）
  - risk_adjustment.py — セクターキャップ、レジーム乗数（apply_sector_cap, calc_regime_multiplier）
  - position_sizing.py — 株数算出 / aggregate cap / lot_size の考慮（calc_position_sizes）
  - __init__.py — エクスポート
- research/
  - factor_research.py — calc_momentum, calc_volatility, calc_value（DuckDB ベース）
  - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
  - __init__.py — エクスポート
- ai/
  - news_nlp.py — raw_news を LLM でスコアリングし ai_scores に書き込む（score_news）
  - regime_detector.py — ETF MA + マクロ NLP 結合で market_regime 判定（score_regime）
  - __init__.py
- monitoring/
  - monitoring_db.py — SQLite 層（init_monitoring_db, MonitoringDB）
  - system_monitor.py — システム・データ鮮度チェック（SystemMonitor）
  - trade_monitor.py — 注文滞留・約定異常監視（TradeMonitor）
  - risk_monitor.py — ドローダウン / position limit の監視（RiskMonitor）
  - alert_manager.py — LINE 押し出し通知（AlertManager）
  - kill_switch.py — kill.flag 管理（KillSwitch）
  - monitoring_engine.py — 各 Monitor を束ねる（Polling）
  - streamlit_dashboard.py — Streamlit ダッシュボード
  - __init__.py
- execution/
  - broker_api.py — Broker 抽象モデル、例外、データクラス
  - order_manager.py — 注文作成/送信/同期/キャンセルの外向け API（OrderManager）
  - execution_engine.py — Signal-driven 発注エンジン
  - reconciler.py — 起動時リコンシリエーション
  - （※ その他、OrderRepository / OrderRecord / RiskManager 等の実装が想定されるが省略）
- monitoring/（上に記載の通り）

テスト・開発向けメモ
-------------------
- settings モジュールはプロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を読み込みます。テストで自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し関数は内部で分離されており、ユニットテストではパッチして差し替えられるよう設計されています（_call_openai_api をモック）。
- DuckDB / SQLite のスキーマ期待（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets 等）はコード内 SQL から読み取れます。実運用では適切な ETL でテーブルを準備してください。

最後に
------
この README はコードベースから抽出した主要点をまとめた簡易ドキュメントです。実運用や詳細設計・環境構築手順はプロジェクト固有の README / infra ドキュメントと合わせて整備してください。必要であれば、各モジュールの API 使用例やデプロイ手順（systemd / cron / container 化等）を追加で作成します。