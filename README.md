# KabuSys

日本株向けの自動売買 / リサーチ / 監視ライブラリ群です。  
このリポジトリはポートフォリオ構築、ポジションサイジング、ファクター計算、ニュースNLP（OpenAI 経由）、実行エンジン、監視機構などをモジュール単位で提供します。

以下はコードベース（src/kabusys）を参照した README です。

## プロジェクト概要
- 目的: 日本株を対象としたアルゴリズムトレーディング基盤のコンポーネント群を提供する。
- 設計方針:
  - 各コンポーネントは可能な限り純粋関数／副作用を分離して実装（テスト容易性重視）。
  - DuckDB / SQLite をローカル DB として利用して時系列データやメタデータを管理。
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価やマクロ判定をオプションで提供。
  - run-time の設定は環境変数 / .env で制御。プロジェクトルートの .env(.local) を自動で読み込み。

## 主な機能一覧
- portfolio
  - 候補選定: スコア順で銘柄選定（select_candidates）
  - 重み計算: 等金額配分 / スコア加重（calc_equal_weights / calc_score_weights）
  - ポジションサイジング: リスクベース・等配分ロジック、単元丸め、aggregate cap（calc_position_sizes）
  - セクターキャップ適用・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- research
  - ファクター計算: Momentum / Volatility / Value（DuckDB の prices_daily / raw_financials を参照）
  - 将来リターン計算・IC（情報係数）・統計サマリー（calc_forward_returns, calc_ic, factor_summary 等）
- ai
  - ニュース NLU（news_nlp.score_news）: raw_news を集約して OpenAI でセンチメントを算出 → ai_scores へ書込
  - レジーム判定（regime_detector.score_regime）: ETF (1321) MA200 とマクロ記事センチメントを合成して market_regime テーブルへ書込
- execution
  - Order 管理: OrderManager（作成・送信・同期・キャンセル）、Reconciler（再起動時の自動復旧）
  - ExecutionEngine: シグナルの読み取り・発注ループ・WebSocket push ドレイン・kill switch 連携
  - Broker API 抽象: Protocol とデータモデル（OrderRequest/OrderStatus/Position 等）
- monitoring
  - MonitoringDB: SQLite ベースの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - System / Trade / Risk Monitor、KillSwitch、AlertManager（LINE push）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
- 設定管理
  - src/kabusys/config.py: .env/.env.local を自動で読み込み（プロジェクトルートは .git または pyproject.toml で検出）
  - Settings オブジェクト経由で各種パラメータにアクセス

## セットアップ手順（開発環境）
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール
   - パッケージ化されている場合:
     - python -m pip install -e .
   - 必要な依存を個別にインストールする例:
     - python -m pip install duckdb openai requests psutil streamlit

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

3. 環境変数 / .env の準備
   - プロジェクトルートに .env（および .env.local）を配置できます。自動ロードの優先度は:
     OS 環境変数 > .env.local > .env
   - 自動ロードを無効にするには環境変数を設定:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DB ファイルのパス（デフォルト）
   - DuckDB: data/kabusys.duckdb
   - Monitoring SQLite: data/monitoring.db
   - Paper trading SQLite: data/paper_trading.db

## 必要な / 推奨環境変数
（src/kabusys/config.py の Settings から抜粋）

必須（使用する機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / regime_detector で使用時に必須）

任意（デフォルト値あり）:
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE アラート用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — paper trading の fill モード（instant/partial/never/reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH — 実行時 PID ファイル / kill flag のパス
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（"1" で有効）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL"（デフォルト: INFO）

※ .env/.env.local のフォーマットは一般的な shell 形式を想定。config モジュールはクォートやコメントの扱いに柔軟に対応。

## 使い方（代表的な例）
- DuckDB 接続を用いたファクター計算
  - 例:
    from datetime import date
    import duckdb
    from kabusys.research import calc_momentum, calc_volatility, calc_value

    conn = duckdb.connect("data/kabusys.duckdb")
    results = calc_momentum(conn, date(2026, 3, 20))

- ニュースセンチメント（OpenAI）を使ったスコアリング
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")  # または OPENAI_API_KEY 環境変数

- レジーム判定（OpenAI + ETF MA）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, date(2026, 3, 20), api_key="sk-...")

- 監視 DB 初期化 & Streamlit ダッシュボード
  - SQLite 初期化:
    from sqlite3 import connect
    from kabusys.monitoring import init_monitoring_db

    conn = connect("data/monitoring.db")
    init_monitoring_db(conn)

  - Streamlit ダッシュボード起動:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Monitoring / Alert
  - AlertManager を作成して MonitoringEngine に渡すと、条件に応じて LINE へ通知します（クールダウン管理あり）。

- ExecutionEngine（本番的な使用）
  - ExecutionEngine は Broker API 実装、OrderRepository、RiskManager 等を組み合わせて利用します。  
    テストではモックの BrokerAPIProtocol を渡して run_session / run_once を呼び出して動作確認できます。
  - kill.flag（Settings.kill_flag_path）を使って外部から安全に停止できます。起動時は PID ファイルを生成し、終了時に削除します。

## 重要な実装ノート / 動作特性
- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を __file__ を起点に探索して検出します。CWD に依存しません。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
  - 読み込み順序: OS 環境 > .env.local（override=True）> .env（override=False）
- フェイルセーフ設計
  - OpenAI 呼び出し失敗時は適切にフォールバック（例: macro_sentiment=0.0）し、例外がプロセス全体を停止させないようにしています。
  - DB 書き込みはトランザクションで保護（必要に応じて BEGIN/COMMIT/ROLLBACK）。
- テストしやすさ
  - OpenAI 呼び出しや外部 API 呼び出し部分は内部の呼出関数を patch しやすいよう分離してあります（ユニットテストでモック可）。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/設定管理
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py
    - execution_engine.py
    - order_manager.py
    - reconciler.py
    - (その他: order_repository, order_record, risk_manager 等は同階層で存在想定)
  - research/（ファクター等）
  - data/（データパイプラインモジュールは別ファイルに存在）

※ 上記はコードベースの一部抜粋です。実際のリポジトリにはさらに補助モジュール（data.pipeline, data.stats, execution.order_repository など）が含まれる想定です。

## 開発 / テストのヒント
- OpenAI を使う箇所は外部 API 呼び出しのため、ユニットテストでは該当関数（内部の _call_openai_api 等）を patch して固定レスポンスを返すとテストが安定します。
- .env の自動読み込みはテストで邪魔になることがあるため、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化するか、テスト用の環境を用意してください。
- MonitoringDB の init_monitoring_db() は冪等。既存 DB に対するマイグレーション（例: peak_value カラム追加）も内包しています。

---

不明点や README に追加したい具体的な利用例（実行パイプライン、CI 用セットアップ、requirements ファイルの例など）があれば教えてください。必要に応じてサンプル .env.example や簡易デプロイ手順も作成します。