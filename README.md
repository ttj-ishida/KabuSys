# KabuSys

日本株向けの自動売買・リサーチ・監視ライブラリ群。ポートフォリオ構築、ポジションサイジング、ファクター計算、ニュースNLP（OpenAI 活用）によるセンチメント評価、実行エンジン、監視（アラート・Kill Switch）等のコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は、以下の目的で設計された Python モジュール群です。

- バックテスト／リサーチ用のファクター計算（DuckDB を用いる）
- ポートフォリオ構築（銘柄選定・重み付け・リスク調整・株数決定）
- ニュースの LLM（OpenAI）によるセンチメントスコア化（ai モジュール）
- 実際の発注処理を担う Execution Engine（OrderManager / Broker API を抽象化）
- 運用監視（システム状態、注文滞留、ドローダウン監視、LINE 通知、ストリームリット監視ダッシュボード）
- 起動時のリコンシリエーション（Reconciler）

設計方針としては「外向き副作用を最小にした純粋関数群」「DuckDB / SQLite を使ったデータ永続化」「OpenAI 呼び出しは明示的に行う（APIキーは引数 or 環境変数）」などを採用しています。

---

## 主な機能一覧

- config
  - 環境変数/.env 自動読み込み（.env, .env.local、OS 環境変数優先）
  - Settings オブジェクト経由で設定値を取得
- portfolio
  - 銘柄選定（select_candidates）
  - 等金額/スコア加重の重み算出（calc_equal_weights / calc_score_weights）
  - セクター上限適用（apply_sector_cap）
  - レジームに基づく資金乗数（calc_regime_multiplier）
  - 株数決定（calc_position_sizes）
- research
  - momentum / volatility / value ファクター計算（DuckDB を参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- ai
  - ニュースセンチメント評価（news_nlp.score_news）
    - OpenAI（gpt-4o-mini）を用いたバッチ評価、レスポンス検証、クリップ、DuckDB へ書込
  - 市場レジーム判定（ai.regime_detector.score_regime）
    - ETF（1321）の MA200 とマクロニュース LLM センチメントを合成して判定
- execution
  - Broker API 抽象化（Protocol/データモデル/例外）
  - OrderManager / OrderRepository / ExecutionEngine（シグナル処理・push ドレイン・Kill Switch）
  - Reconciler（起動時自動復旧・注文/ポジション突合）
- monitoring
  - SQLite ベースの永続層（MonitoringDB, init_monitoring_db）
  - System / Trade / Risk モニタと MonitoringEngine
  - LINE プッシュ通知（AlertManager）
  - streamlit による監視ダッシュボード（streamlit_dashboard.py）

---

## セットアップ手順

推奨 Python バージョン: 3.10+

1. リポジトリをチェックアウト
   - git clone ...（お使いのリポジトリに合わせて）

2. 必要パッケージのインストール（代表的なもの）
   - pip install duckdb openai psutil requests streamlit
   - 追加で unittest や sqlite3 は標準ライブラリに含まれます。

   ※ 実際の requirements.txt があればそちらを使ってください。

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml がある位置）に `.env` として必要なキーを配置できます。`.env.local` は .env をオーバーライドします。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。

   主な環境変数（コードから拾えるもの）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_FILL_MODE (instant/partial/never/reject、デフォルト instant)
   - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
   - PID_FILE_PATH (デフォルト: data/execution.pid)
   - KILL_FLAG_PATH (デフォルト: data/kill.flag)
   - KILL_FLAG_CLEAR_ON_START (1 で起動時に kill.flag をクリア)
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
   - KABUSYS_ENV (development/paper_trading/live)
   - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
   - OPENAI_API_KEY（ai モジュールを環境変数で使う場合）

4. 監視 DB の初期化（Monitoring）
   - Python から:
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     import sqlite3
     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)

---

## 使い方（主要例）

- Settings（設定値取得）
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token
  - settings は .env / .env.local / OS 環境変数から値を取得します。

- ニューススコア生成（AI）
  - DuckDB コネクションと target_date を用意して実行:
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")  # api_key を引数で渡せます
  - api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。
  - 処理は対象ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）のニュースを対象にします。

- レジーム判定（AI）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key="...")

- 監視ダッシュボード（Streamlit）
  - 起動:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開きます（監視エンジンがデータを書き込みます）。

- 監視 DB クラス
  - from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db
  - db = MonitoringDB(sqlite3_conn)
  - db.log_system_status(...), db.upsert_dashboard(...), db.log_risk_event(...)

- ExecutionEngine（運用用）
  - ExecutionEngine は BrokerAPIProtocol 実装（ブローカークライアント）, OrderRepository（SQLite）, RiskManager, OrderManager, DuckDB コネクション と EngineConfig を受け取ります。
  - 簡易起動イメージ（実際には各依存を実装/注入する必要があります）:
    from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig
    engine = ExecutionEngine(broker, order_repo, risk_manager, order_manager, duckdb_conn, EngineConfig(target_date=date.today()))
    engine.run_session()
  - 起動時リコンシリエーション、kill.flag チェック、PID 書き出し、WebSocket push ドレイン等を行います。

- Kill Switch / flag
  - KillSwitch はファイル（defaults: data/kill.flag）を作成して ExecutionEngine を停止させます。
  - 起動時に kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START=1 により自動クリア可能（設定で制御）。

---

## 注意点 / ヒント

- OpenAI 呼び出しは外部 API であり失敗する可能性があります。ai モジュール側は失敗時にフェイルセーフなフォールバック/スキップを行う設計です。
- DuckDB / SQLite のテーブルスキーマ（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime など）を準備してから実行してください（リポジトリにスキーマ定義がある場合はそちらを参照）。
- settings._load_env_file の自動読み込みはプロジェクトルートの検出に .git または pyproject.toml を使います。配布後でも正しく動作するよう設計されています。
- テストや CI で自動的に .env を読みたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- paper trading 用のパラメータ（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）を用意しておくと模擬環境での動作確認が容易です。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- portfolio/
  - __init__.py
  - portfolio_builder.py
  - risk_adjustment.py
  - position_sizing.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/
  - __init__.py
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - broker_api.py
  - execution_engine.py
  - order_manager.py
  - reconciler.py
  - (その他: order_repository.py, order_record.py 等が存在する想定)
- research, data, etc.（データパイプラインや統計ユーティリティは別モジュール）

（※ 上は主要ファイルの抜粋です。実プロジェクトでは追加のモジュールやテストが存在します。）

---

必要に応じて README に実行例（docker-compose, systemd ユニット、CI 設定など）を追加できます。特定の操作（例: ExecutionEngine の具象的な起動方法や Broker クライアント実装例）について詳しく書く必要があれば、その用途に合わせて追記します。どの部分を重点的に説明しましょうか？