# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量な Python コードベースです。DuckDB / SQLite を用いたオンプレミスのデータ処理、ポートフォリオ構築、発注エンジン、監視ダッシュボード、LLM を使ったニュースセンチメント評価などのモジュール群を含みます。

この README ではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語で説明します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API とコマンド例）
- 環境変数（主要設定）
- ディレクトリ構成

---

プロジェクト概要
- 目的：日本株の自動売買パイプラインを構成するためのライブラリ群（データ処理、ファクター計算、ポートフォリオ構築、発注管理、監視、LLM によるニュース解析など）。
- 設計方針：
  - 各モジュールは可能な限り純粋関数／副作用の少ない実装にする（テスト容易性の向上）。
  - DuckDB（時系列価格・財務データ）と SQLite（監視ログ／注文 DB）を利用。
  - OpenAI（gpt-4o-mini 等）を使った NLP 評価はフェイルセーフ（API 失敗時はフォールバック）で設計。
  - アプリ設定は環境変数／.env ファイルで管理。パッケージ内部で自動的に .env/.env.local をロードする機能あり（無効化可能）。

---

機能一覧
- 設定管理
  - 環境変数 / .env / .env.local の自動読み込み（優先度: OS 環境 > .env.local > .env）
  - settings オブジェクト経由で型付きアクセス
- ポートフォリオ構築
  - 候補選定（スコア順ソート）、等重・スコア加重の重み計算
  - セクター集中制限の適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - 株数決定（risk_based / equal / score ベース）、単元丸め、aggregate cap スケーリング
- リサーチ（factor / research）
  - Momentum / Volatility / Value のファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）やファクター統計サマリ
- AI（LLM）連携
  - ニュース記事の銘柄別センチメント評価（score_news）
  - マクロニュース＋ETF MA200 乖離による市場レジーム判定（score_regime）
  - OpenAI API 呼び出しに対するリトライ・レスポンス検証・クリッピング等の実装
- 実行（execution）
  - OrderManager / ExecutionEngine：注文の作成、送信、同期、キャンセル、再起動時のリコンシリエーション
  - Broker API 抽象化（Protocol）とエラー型
- 監視（monitoring）
  - MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard テーブル
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE への通知）
  - Streamlit ダッシュボード（監視データ表示）

---

セットアップ手順（開発・ローカル実行向け）
1. Python 環境
   - Python 3.10+ を推奨（typing の union 表記などを使用）
   - 仮想環境を作成して有効化：
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージ（例）
   - pip install duckdb openai requests psutil streamlit
   - プロジェクト固有の依存関係ファイルがある場合はそれを使ってください（requirements.txt / pyproject.toml）。

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml を基準）に .env（と任意で .env.local）を置くと、自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
   - 主要な環境変数は次節を参照。

4. データベース初期化（監視 DB の例）
   - SQLite file を生成して MonitoringDB スキーマを作成：
     - Python REPL 例:
       >>> import sqlite3
       >>> from kabusys.monitoring.monitoring_db import init_monitoring_db
       >>> conn = sqlite3.connect("data/monitoring.db")
       >>> init_monitoring_db(conn)
   - DuckDB 側のテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets 等）は、利用側で事前にロード／作成してください（本リポジトリは ETL スクリプトを含みません）。

---

使い方（主要な例）

- settings の利用
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path などでアクセス可能。
  - 自動 .env ロードの挙動: OS 環境 > .env.local > .env。ロードされる際、既存 OS 環境は保護されます。

- リサーチ関数（DuckDB 接続を渡す）
  - 例: momentum を計算する
    - import duckdb
      conn = duckdb.connect("data/prices.duckdb")
      from kabusys.research import calc_momentum
      from datetime import date
      res = calc_momentum(conn, date(2026, 3, 20))
  - 他にも calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary 等が利用可能。

- AI ニューススコアリング（OpenAI API 必須）
  - 必要: OPENAI_API_KEY を環境変数に設定するか、score_news に api_key を渡す。
  - 例:
    - from kabusys.ai.news_nlp import score_news
      import duckdb
      conn = duckdb.connect("data/research.duckdb")
      n_written = score_news(conn, date(2026,3,20))  # ai_scores テーブルへ書き込み
  - 内部では raw_news と news_symbols を参照し、ai_scores を更新します。
  - 大量 API 呼び出しはバッチ化（最大 _BATCH_SIZE=20）で行われ、429/タイムアウト等は指数バックオフでリトライします。

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/research.duckdb")
    score_regime(conn, date(2026,3,20))  # market_regime テーブルへ書き込み

- 監視ダッシュボード（Streamlit）
  - 起動方法（ローカル）:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite を開くため、DB は MonitoringEngine を稼働させて生成／更新しておく必要があります。

- 監視 DB の利用（MonitoringDB）
  - from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db
    conn = sqlite3.connect("data/monitoring.db")
    init_monitoring_db(conn)  # 初期スキーマ作成
    db = MonitoringDB(conn)
    db.log_system_status(...)

- ExecutionEngine / OrderManager（発注）
  - ExecutionEngine は BrokerAPIProtocol 実装（kabu station client 等）、OrderRepository、RiskManager、OrderManager、DuckDB 接続と設定を渡して使用します。
  - 実稼働前に kill.flag の扱い、PID ファイルの場所、リコンシリエーションの設定等を確認してください。
  - 重要: 実際の発注を行うモジュールは BrokerAPI の具象実装を必要とし、誤発注を防ぐためテスト環境でモックすることを強く推奨します。

---

主要な環境変数（settings による参照、デフォルト値/意味）
- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API のリフレッシュトークン。settings.jquants_refresh_token で必須取得。
- KABU_API_PASSWORD (必須)
  - kabu ステーション API のパスワード。
- KABU_API_BASE_URL (任意)
  - kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY (必須 for AI 機能)
  - OpenAI API キー。score_news / score_regime 等の呼び出し時に使われる。
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
  - AlertManager（LINE push）で使用。未設定なら送信はスキップされログのみ出力。
- DUCKDB_PATH (任意)
  - DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)
  - 監視データ用 SQLite。デフォルト: data/monitoring.db
- PAPER_FILL_MODE (任意)
  - Paper Trading のモック約定モード（instant|partial|never|reject）。デフォルト: instant
- PAPER_TRADING_SQLITE_PATH (任意)
  - Paper Trading 用 SQLite DB パス。デフォルト: data/paper_trading.db
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
  - 実行中の PID ファイル / kill.flag のパス・起動時のクリア挙動制御。
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
  - リスク監視用閾値（パーセント）。

.env の自動ロードの挙動
- プロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を起点に .env と .env.local を探し、順に読み込みます。
- 読み込み優先順位（最終的な環境変数値）: OS 環境変数 > .env.local > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化します（テスト用）。

.env のパース
- export KEY=val、コメント行（#）、引用符内のエスケープ、インラインコメント処理などに対応した柔軟なパーサが組み込まれています。

---

開発／運用上の注意
- OpenAI キーやブローカー API の資格情報は厳重に管理してください。開発時はモックを利用し実口座に誤って送信しないよう注意してください。
- DuckDB / SQLite のスキーマ（特に価格・財務・ニューステーブル）は期待する列が存在することを確認してください。リサーチ関数は prices_daily や raw_financials 等の列構成に依存します。
- 実システム運用時は KillSwitch（kill.flag）、PID ファイルのみならず、アラート運用（LINE など）・ログ収集を整備してください。
- ExecutionEngine／OrderManager の挙動は注文状態遷移や再起動時の整合性を重視していますが、ブローカー実装に依存する部分は事前にステージングで十分検証してください。

---

ディレクトリ構成（主要ファイル抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py               -- 環境変数 / settings
    - ai/
      - __init__.py
      - news_nlp.py           -- ニュース NLP（OpenAI）スコアリング
      - regime_detector.py    -- 市場レジーム判定（ETF + マクロニュース）
    - research/
      - __init__.py
      - factor_research.py    -- Momentum / Volatility / Value 等
      - feature_exploration.py-- IC / forward returns / summary
    - portfolio/
      - __init__.py
      - portfolio_builder.py  -- 候補選定・重み計算
      - position_sizing.py    -- 株数計算・スケーリング・単元丸め
      - risk_adjustment.py    -- セクターキャップ / レジーム乗数
    - execution/
      - broker_api.py         -- Broker API Protocol / データモデル / 例外
      - order_manager.py      -- OrderManager（作成・送信・同期・キャンセル）
      - order_repository.py   -- （DB 層: orders）※実装ファイルがプロジェクトに存在する前提
      - order_record.py       -- OrderRecord, 状態遷移
      - reconciler.py         -- 再起動時リコンシリエーション
      - execution_engine.py   -- ExecutionEngine（signal pull + websocket drain）
      - risk_manager.py       -- （リスク判定ロジック）※実装ファイルがプロジェクトに存在する前提
    - monitoring/
      - __init__.py
      - monitoring_db.py      -- SQLite スキーマと MonitoringDB
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py -- Streamlit ダッシュボード
    - portfolio/ (上記)
    - research/ (上記)
    - data/                    -- データパイプライン周り（get_last_price_date など）
    - (その他ユーティリティ・モジュール)

（注）上記はコードベースからの抜粋。実際のリポジトリにはさらに追加モジュールや ETL スクリプト、DB 初期化スクリプトや Broker 実装が含まれる場合があります。

---

貢献・テスト
- ユニットテストや CI の設定はプロジェクトに応じて整備してください。各モジュールは依存を明確に分離しているため、モックを用いた単体テストが容易です（例: OpenAI 呼出し関数をパッチする等）。

---

補足／問い合わせ
- 特定のモジュール（例: ExecutionEngine の使い方、OrderRepository の具体的な DB スキーマ、または AI スコアリングの挙動）について詳細な説明やサンプルコードが必要であれば、対象箇所を指定して質問してください。必要に応じて README に追記するサンプルや実行例を追加します。