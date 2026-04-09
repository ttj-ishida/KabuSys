KabuSys — 日本株自動売買・リサーチ基盤
==================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を想定した軽量なPythonライブラリ群です。
主な役割は次の通りです。

- ファクター計算・特徴量探索（DuckDBベース、prices_daily / raw_financials を参照）
- ポートフォリオ構築（候補選定・重み算出・リスク調整・株数決定）
- AI（LLM）を用いたニュースセンチメント評価・市場レジーム判定（OpenAI API）
- 発注エンジン周りの状態管理（OrderManager / ExecutionEngine / Reconciler）
- 監視・アラート機能（LINE Push / SQLiteによる永続化 / Streamlit ダッシュボード）

このリポジトリは「計算ロジック」「DBアクセス層」「監視」「実行エンジン」「AI連携」などが
責務ごとに分離されて実装されています。

主な機能一覧
-------------
- 環境設定管理（.env 自動読み込み、Settings クラス）
- リサーチ
  - momentum / volatility / value ファクター計算（kabusys.research）
  - 将来リターン・IC計算・統計サマリー
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定（select_candidates）
  - 等配分 / スコア配分、リスクベースのポジションサイズ計算
  - セクターキャップ制御、レジーム乗数
- AI（kabusys.ai）
  - ニュースのセンチメントスコア化（score_news）
  - マクロニュース＋ETF MA による市場レジーム判定（score_regime）
- 発注・実行（kabusys.execution）
  - Broker API プロトコル定義、OrderManager、ExecutionEngine、Reconciler
  - 発注状態遷移とクラッシュ耐性のある処理フロー
- 監視（kabusys.monitoring）
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE送信）
  - Streamlit ベースの監視ダッシュボード（read-only 表示）

動作要件（概略）
----------------
- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - requests
  - psutil
  - streamlit (ダッシュボードを利用する場合)
- SQLite（標準ライブラリの sqlite3 を使用）
- ネットワークアクセス（OpenAI / LINE 連携を行う場合）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai requests psutil streamlit

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を利用）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml を基準）に .env / .env.local を置くと自動で読み込みます。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須・主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI機能を使う場合、score_news / score_regime）
- LINE_CHANNEL_ACCESS_TOKEN — LINE Push 用トークン（アラート送信）
- LINE_USER_ID — LINE Push 送信先ユーザーID
- KABUSYS_ENV — 実行環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG" / "INFO" / ...)

設定ファイルの自動読み込み挙動
- プロジェクトルートの .env をまず読み込み（既存 OS 環境変数を上書きしない）
- .env.local を次に読み込み（override=True。OS環境変数は保護）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化

使い方（代表例）
----------------

1) DuckDB を使ったファクター計算（リサーチ）
- Python から DuckDB 接続を渡して呼び出します。

  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))

  各関数は prices_daily / raw_financials などのテーブルを参照します。

2) ニュースのAIスコアリング（OpenAI 必須）
- ai.score_news を呼ぶと raw_news / news_symbols を集約して OpenAI に問い合わせ、ai_scores テーブルへ書き込みます。

  from datetime import date
  import duckdb
  from kabusys.ai import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, date(2026, 3, 20), api_key="sk-...")

  api_key を None にすると環境変数 OPENAI_API_KEY を参照します。
  score_news は失敗を許容するフェイルセーフ設計で、部分失敗時も他銘柄の既存スコアを保護します。

3) 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026, 3, 20), api_key="sk-...")

  成果は market_regime テーブルに冪等的に書き込まれます。

4) 監視データベース初期化
  import sqlite3
  from kabusys.monitoring import init_monitoring_db

  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)

5) Streamlit ダッシュボード
- 監視DB を read-only で開き、簡易ダッシュボードを表示します。

  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

6) ExecutionEngine（発注エンジン）
- 実行には BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続等が必要です。
- 単純な実行フロー（概念）:

  from datetime import date, time
  import duckdb
  from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig
  # broker, repo, risk_manager, order_manager, reconciler は呼び出し側で実装/注入
  engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duckdb_conn, EngineConfig(target_date=date.today()))
  engine.run_session()

注意点・設計上のポイント
-----------------------
- ルックアヘッドバイアス対策: AI・リサーチ・レジーム判定等は内部で date を明示的に渡し、datetime.today()/date.today() を直接参照しない実装を心掛けています。
- DB 書き込みは冪等性を考慮（DELETE→INSERT や BEGIN/COMMIT を明示的に使う箇所あり）。
- OpenAI 呼び出しは 429・ネットワーク断・5xx に対して指数バックオフでリトライする箇所があります。失敗時は安全にフォールバックする設計（例: macro_sentiment=0）。
- .env のパースはシェル風のクォート・コメントをある程度サポートします。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py                パッケージメタ情報
- config.py                  環境変数/設定管理（自動 .env ロード・Settings）
- portfolio/
  - __init__.py
  - portfolio_builder.py     候補選定・配分（select_candidates, calc_equal_weights, calc_score_weights）
  - risk_adjustment.py       セクターキャップ・レジーム乗数
  - position_sizing.py       株数算出・資金割当
- research/
  - __init__.py
  - factor_research.py       momentum/vol/ value のファクター計算
  - feature_exploration.py   将来リターン、IC、統計サマリ
- ai/
  - __init__.py
  - news_nlp.py              ニュース→LLM→ai_scores 書込
  - regime_detector.py       マクロ+ETFで市場レジーム判定
- monitoring/
  - __init__.py
  - monitoring_db.py         SQLite テーブル定義・ MonitoringDB クラス
  - system_monitor.py        システム・データ鮮度監視
  - trade_monitor.py         注文滞留・約定異常監視
  - risk_monitor.py          ドローダウン・ポジション上限監視
  - kill_switch.py           フラグファイルによる停止シグナル
  - alert_manager.py         LINE 通知ラッパー
  - monitoring_engine.py     監視の実行ループ
  - streamlit_dashboard.py   Streamlit ダッシュボード
- execution/
  - broker_api.py            ブローカーClientのプロトコル・データモデル・例外
  - order_manager.py         注文状態遷移・送出ロジック
  - execution_engine.py      Signal Queue を読む発注エンジン
  - reconciler.py            起動時リコンシリエーション
  - ...                      （OrderRepository 等、他ファイル群）
- monitoring/、ai/、research/、portfolio/ の各モジュールは用途別に分離されています。

追加情報
---------
- デフォルト DB / ファイルパス:
  - DuckDB: data/kabusys.duckdb
  - 監視用 SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID ファイル: data/execution.pid
  - kill flag: data/kill.flag

- 環境に応じた設定例:
  - KABUSYS_ENV=paper_trading に設定すると paper 用のパスや挙動が有効化される箇所があります。
  - PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のいずれかで Paper Trading の約定挙動を設定できます。

フィードバック / 貢献
--------------------
バグ報告や改善提案は Issue を通じてお願いします。各モジュールは単体でテストしやすいよう純粋関数・副作用を分離する設計を心がけています。PR は歓迎します。

以上です。README の内容や利用例で補足が必要な箇所があれば、どの部分を詳しく記載するか教えてください。