# KabuSys — README

注意: 本 README は提示されたコードベースの内容に基づいて作成しています。実行環境や補助モジュール（例: kabusys.data 等）の有無により一部コマンドや動作が変わる可能性があります。

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量なフレームワークです。  
主な機能は次のとおりです。

主な特徴 / 機能一覧
-----------------
- 環境設定管理
  - .env / .env.local / OS 環境変数から設定を読み込む自動ロード機構（プロジェクトルート検出あり）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- ポートフォリオ構築（純粋関数）
  - 候補選定 (select_candidates)
  - 等金額配分 / スコア加重配分 (calc_equal_weights / calc_score_weights)
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（ロット丸め、risk-based 等）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value ファクター計算（DuckDB の prices_daily / raw_financials を利用）
  - 将来リターン、IC（Spearman rank）、ファクター統計サマリ
- AI 支援（OpenAI）
  - ニュース NLP による銘柄ごとのセンチメントスコア算出（ai_scores への書き込み）
  - 市場レジーム判定（ETF + マクロニュースを LLM で評価）
  - OpenAI 呼び出しは冪等・リトライ等のハンドリングあり
- 実行エンジン / 発注
  - Signal Queue を読み取り、Gate チェックを経て発注（ExecutionEngine / OrderManager）
  - Broker API 用 Protocol / データモデル（OrderRequest, OrderStatus, Position 等）
  - 起動時リコンシリエーション（Reconciler）で OrderSent 状態を復旧
- 監視 / アラート
  - SQLite ベースの監視 DB（MonitoringDB）と各種 Monitor（System / Trade / Risk）
  - KillSwitch（フラグファイルによる安全停止）
  - LINE Push を使った AlertManager（クールダウン制御あり）
  - Streamlit ベースの監視ダッシュボード

セットアップ（開発環境）
---------------------
以下は一般的な開発環境構築手順の例です。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 依存はコードから推測すると次のパッケージが必要です:
     - duckdb
     - openai
     - requests
     - psutil
     - streamlit (ダッシュボードを使う場合)
   - 例:
     - pip install duckdb openai requests psutil streamlit

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートに .env/.env.local を作成（.env.example を参考に）。
   - 主に必要となる環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN（通知を使う場合）
     - LINE_USER_ID（通知を使う場合）
     - OPENAI_API_KEY（AI モジュールを使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE（paper trading の挙動: instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH（paper trading 用 DB）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development | paper_trading | live）
     - LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL）
   - 注意: .env, .env.local の読み込み順は OS 環境 > .env.local > .env。
     .env.local は .env を上書きします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（代表的な実行例）
---------------------

1) 設定値の参照
   - Python コード内で:
     - from kabusys.config import settings
     - token = settings.jquants_refresh_token

2) DuckDB / SQLite 接続例（AI モジュールや research モジュールから使用）
   - import duckdb, sqlite3
   - duck_conn = duckdb.connect("data/kabusys.duckdb")
   - sqlite_conn = sqlite3.connect("data/monitoring.db")

3) ニュース NLP によるスコア算出（ai.news_nlp.score_news）
   - from datetime import date
     from kabusys.ai.news_nlp import score_news
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
   - score_news は ai_scores テーブルに書き込みます。OPENAI_API_KEY が設定済みなら api_key 省略可。

4) 市場レジーム算出（ai.regime_detector.score_regime）
   - from kabusys.ai.regime_detector import score_regime
     score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

5) Streamlit 監視ダッシュボード起動
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - または適宜 db 引数を渡す（デフォルト: data/monitoring.db）

6) 監視 DB 初期化
   - import sqlite3
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)

7) ExecutionEngine の利用（簡易例）
   - ExecutionEngine は broker 実装、OrderRepository、RiskManager、OrderManager などを注入して使います。実運用ではこれらを実装・組み立てる必要があります。
   - 例（疑似コード）:
     - from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig
       engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duck_conn, EngineConfig(target_date=date.today()))
       engine.run_session()

ドキュメント・設計ノート（コード内コメントより）
-----------------------------------------
- ポートフォリオ構築やリスク計算は純粋関数（外部 DB を参照しない）で実装されており、単体テストが容易な設計です。
- AI 呼び出しは OpenAI SDK を利用。JSON Mode を使った厳密なレスポンス期待、リトライ/バックオフ、検証ロジックあり。
- 実行エンジンは複数の Gate（Gate1: シグナル検査、Gate2: 発注レート制限、Gate3: ドローダウン等）を経て発注します。
- リコンシリエーション（起動時復旧）機能により、クラッシュ後の状態回復を考慮した永続化設計が施されています。
- 監視は SQLite を採用し、ダッシュボードやアラート（LINE）と連携します。

主要なディレクトリ構成（src/kabusys）
-----------------------------------
以下は提示されたコードに基づく主要なパッケージ構成です（抜粋）。

- kabusys/
  - __init__.py
  - config.py                    — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（OpenAI 経由）
    - regime_detector.py         — 市場レジーム判定
  - portfolio/
    - __init__.py
    - portfolio_builder.py       — 候補選定・重み計算
    - risk_adjustment.py         — セクターキャップ・レジーム乗数
    - position_sizing.py         — 株数算出・丸め・aggregate cap
  - research/
    - __init__.py
    - factor_research.py         — Momentum/Volatility/Value 計算
    - feature_exploration.py     — 将来リターン、IC、統計サマリ
  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py              — Broker API 型定義 / Protocol / 例外
    - execution_engine.py        — 発注エンジン
    - order_manager.py
    - reconciler.py
    - (その他: order_repository, order_record, risk_manager 等は別ファイル想定)
  - (data/ 以下は code 内参照: kabusys.data.* が別途存在すると想定)

開発上の留意点
--------------
- 環境変数の自動読み込みはプロジェクトルート検出（.git または pyproject.toml）に依存します。配布後に動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して手動で環境を設定してください。
- OpenAI を使う処理は外部 API 呼び出しを行うため、テスト時はモック（_call_openai_api の差し替え等）を推奨します（コードにも差し替えポイントがコメントで示されています）。
- DuckDB / SQLite テーブルスキーマ（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, etc.）はコード側で参照されています。必要なテーブル・カラムを事前に作成してください。
- 実ブローカー連携時は BrokerAPIProtocol に準拠した実装（kabu station client 等）を用意してください。テストや paper_trading 用のモックを用意すると安全です。

サポート / 追加情報
-------------------
- この README はコード中のドキュメント文字列とコメントを要約したものです。詳細な挙動は各モジュールの docstring を参照してください。
- パッケージ化・CI・テストのセットアップはプロジェクト側で追加実装してください。

以上。必要に応じて README に追記（インストール工程の具体化、example .env、CLI の使い方、ユニットテスト例など）できますので、追加で欲しいセクションを教えてください。