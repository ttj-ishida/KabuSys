README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量なライブラリ群です。  
主に以下の機能をモジュール単位で提供します。

- ファクター計算・リサーチ（DuckDB を用いたオフライン分析）
- ポートフォリオ構築（候補選定、配分、リスク調整、株数決定）
- ニュース NLP / LLM ベースのセンチメントスコアリング（OpenAI API 経由）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 発注エンジン用ユーティリティ（Order 管理、Reconciliation、ExecutionEngine）
- 監視（システム / 注文 / リスク監視）と LINE 通知、Streamlit ダッシュボード
- 設定（.env / 環境変数読み込み・管理）

主な設計方針は「DB やブローカーに直接アクセスする本番コードと分離された純粋関数群を提供し、テスト可能でフェイルセーフな挙動を保つ」ことです。

機能一覧
-------
主要機能と公開 API の一部（抜粋）：

- 設定
  - kabusys.config.settings — .env / 環境変数を読み込み、アプリ設定を提供
- ポートフォリオ構築
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（等金額 / スコア / リスクベースの株数算出）
  - apply_sector_cap（セクター集中制限）
  - calc_regime_multiplier（レジームに応じた投下資金乗数）
- リサーチ
  - calc_momentum, calc_volatility, calc_value（DuckDB を使ったファクター計算）
  - calc_forward_returns, calc_ic, factor_summary（特徴量探索・IC 計算）
- AI (LLM)
  - kabusys.ai.score_news — raw_news から銘柄別センチメントを算出して ai_scores に保存
  - kabusys.ai.regime_detector.score_regime — マクロ記事 + ETF MA でレジーム判定
- 発注・実行
  - BrokerAPIProtocol（クライアントインターフェース）
  - OrderManager（作成・送信・同期・キャンセル）
  - Reconciler（起動時の自動同期）
  - ExecutionEngine（Signal Pull 型発注エンジン）
- 監視
  - MonitoringDB / init_monitoring_db（SQLite を用いた永続化）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - streamlit_dashboard（Streamlit による監視ダッシュボード）

セットアップ手順
--------------
以下は開発・実行のための基本手順例です。

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai psutil requests streamlit
   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使ってください）

4. 環境変数 / .env を用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env または .env.local を置くと自動で読み込まれます。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants 用トークン（必須）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, KABUSYS_ENV, LOG_LEVEL など（コード中にデフォルト値・妥当性チェックあり）

例 .env（抜粋）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

データベース初期化（監視 DB）
- Python から:
  from sqlite3 import connect
  from kabusys.monitoring.monitoring_db import init_monitoring_db
  conn = connect("data/monitoring.db")
  init_monitoring_db(conn)

使い方
------
以下は代表的なユースケースの使用例と呼び出し方です。

設定取得
- 環境変数は自動ロードされ、settings オブジェクトから参照できます。
  from kabusys.config import settings
  token = settings.jquants_refresh_token

DuckDB を用いたファクター計算（例）
- DuckDB 接続を作成して呼び出す:
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  results = calc_momentum(conn, date(2026, 3, 20))

AI ベースのニューススコアリング
- OpenAI API キーを環境変数または引数で渡して実行:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, date(2026, 3, 20), api_key="sk-...")

市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026,3,20), api_key="sk-...")

ポートフォリオ構築の例
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)
  sizes = calc_position_sizes(weights, candidates, portfolio_value=100_000_000, available_cash=70_000_000, current_positions={}, open_prices=price_map)

監視ダッシュボード（Streamlit）
- 起動コマンド:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ExecutionEngine（発注の実行）
- ExecutionEngine は具体的な Broker 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続などを組み合わせて動作します。簡易的な流れ:

  from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig
  # broker: BrokerAPIProtocol 実装
  # repo: OrderRepository (SQLite 実装)
  # risk_manager: RiskManager 実装
  # order_manager: OrderManager(broker, repo)
  # duckdb_conn: duckdb.connect(...)
  config = EngineConfig(target_date=date(2026,3,20))
  engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duckdb_conn, config)
  engine.run_session()  # 本番的なセッション実行

監視 / Alert
- AlertManager を使って LINE に通知できます（token と user_id が必要）。
- MonitoringEngine を構成して定期ポーリングを行い、KillSwitch による自動停止・アラート送信が可能です。

注意点 / 運用メモ
- .env の自動ロード: プロジェクトルート (.git または pyproject.toml を基準) にある .env / .env.local を自動読み込みします。テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- OpenAI 呼び出しは外部 API に依存します。API 失敗時はフェイルセーフ的に処理を続行する実装箇所が多いですが、API キーは確実に設定してください。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news / ai_scores / market_regime 等）はリサーチ・AI モジュールが参照します。事前に必要スキーマを用意してください。
- ExecutionEngine / OrderManager を実運用する場合は broker 実装の堅牢性とリコンシリエーション（Reconciler）を必ず組み合わせてください。
- Paper Trading 用の設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）が用意されています。

ディレクトリ構成
----------------
主要なファイル / モジュール構成（src/kabusys 配下の抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      # .env/環境変数管理
  - ai/
    - __init__.py
    - news_nlp.py                  # ニュース NLP / OpenAI 呼び出し
    - regime_detector.py           # 市場レジーム判定（MA + マクロセンチメント）
  - portfolio/
    - __init__.py
    - portfolio_builder.py         # 候補選定・重み計算
    - position_sizing.py           # 株数決定・資金管理
    - risk_adjustment.py           # セクター制限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py           # Momentum/Value/Volatility 等の計算
    - feature_exploration.py       # IC/forward returns/統計
  - monitoring/
    - __init__.py
    - monitoring_db.py             # SQLite スキーマ + MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py                # Broker API のデータモデル / Protocol / 例外
    - order_manager.py             # Order 作成・送信・同期・キャンセル
    - reconciler.py                # 起動時リコンシリエーション
    - execution_engine.py          # 実行エンジン（Signal Pull + Push drain）
    - ...（OrderRepository / OrderRecord 等は別ファイル）
  - monitoring/ (上記)
  - その他: data/ 以下に DuckDB / SQLite 用 DB を配置する想定

貢献・テスト
------------
- ユニットテストを書く際は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して .env 自動読込を抑制できます。
- OpenAI 呼び出しは _call_openai_api をモックすることでネットワーク依存を切り離せます（ニュース/レジーム両モジュールで注釈あり）。
- DuckDB を用いた関数は副作用を持たない純粋関数的実装が多いため、テスト用の小さな DuckDB を用意して検証できます。

ライセンス
----------
- 当リポジトリにライセンスファイルがある場合はそれに従ってください（README 内では明示していません）。

以上が README の概要です。必要であれば、実行例や API の更に詳しい使用例（OrderRepository の初期化、Broker 実装の雛形、DuckDB のスキーマ定義など）を追加で作成します。どの部分の詳細が欲しいか教えてください。