# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータパイプラインと研究・自動売買基盤を構成するためのモジュールセットです。主な役割は以下の通りです。

- J-Quants API からの株価・財務・カレンダー取得（rate limiting / retry / token refresh 対応）
- DuckDB を用いた差分 ETL（保存は冪等性を考慮）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集・前処理（RSS、SSRF 対策、トラッキング除去）
- OpenAI を用いたニュースセンチメント（銘柄毎）およびマクロセンチメント評価（市場レジーム判定）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー など）と統計ユーティリティ
- 監査ログ用スキーマ（signal → order_request → executions のトレーサビリティ）

---

## 機能一覧

- config: 環境変数の自動読み込み（.env / .env.local）、必須キーの検証、設定アクセス（settings）
- data:
  - jquants_client: J-Quants API 呼び出し、保存（raw_prices, raw_financials, market_calendar 等）、rate limiter、token refresh
  - pipeline: 日次 ETL 実行（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）、ETL 結果クラス（ETLResult）
  - quality: データ品質チェック（欠損、スパイク、重複、将来日付等）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - news_collector: RSS 取得・テキスト前処理（SSRF・XML 防御・トラッキング除去）
  - audit: 監査ログ（監査スキーマ初期化、専用 DB 初期化）
  - stats: 汎用統計ユーティリティ（Zスコア正規化等）
- ai:
  - news_nlp.score_news: 指定日のニュースを銘柄毎に集約して OpenAI でセンチメント評価し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に書込
- research:
  - factor_research: calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提・依存

主な外部依存（必須）:
- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

プロジェクト固有の環境変数も利用します（下記参照）。

インストール（開発用・ローカル）例:
- ソースを配置したディレクトリで:
  - python -m venv .venv
  - source .venv/bin/activate
  - python -m pip install -U pip
  - python -m pip install duckdb openai defusedxml

（パッケージ化されている場合は `pip install -e .` 等を利用してください）

---

## 環境変数

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（優先度: OS環境 > .env.local > .env）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な設定キー（例・説明）:

- J-Quants / Data
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OpenAI / AI
  - OPENAI_API_KEY — OpenAI を利用する関数で使用（関数呼び出し時に引数で指定可能）
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- 実行・監視
  - PID_FILE_PATH — default: data/execution.pid
  - KILL_FLAG_PATH — default: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START — "1" で起動時に kill flag をクリア
- 動作モード / ログ
  - KABUSYS_ENV — development | paper_trading | live （default: development）
  - LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL （default: INFO）
- Paper trading の挙動
  - PAPER_FILL_MODE — instant | partial | never | reject （default: instant）

.env 例（.env.example を作る際の参考）:
JQUANTS_REFRESH_TOKEN="your_refresh_token_here"
KABU_API_PASSWORD="your_kabu_password"
OPENAI_API_KEY="sk-xxxx..."
DUCKDB_PATH="data/kabusys.duckdb"
LOG_LEVEL="INFO"
KABUSYS_ENV="development"

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   - git clone <repository>
2. 仮想環境作成と依存インストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （必要に応じて他のライブラリを追加）
3. 環境変数準備
   - プロジェクトルートに .env または .env.local を作成し必要なキーを設定
   - 自動ロードをテストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
4. データベースディレクトリ等を作成
   - mkdir -p data
5. 初期化（監査用 DB 等）
   - Python から init_audit_db を実行（例は下記）

---

## 使い方（主要な例）

以下はライブラリを利用する基本的な例です。すべての関数は duckdb 接続オブジェクトや必要な引数を受け取ります。

- DuckDB 接続を開く:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行する:
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメントを生成（OpenAI APIキーを環境変数に設定しておくか api_key 引数を渡す）:
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n_written = score_news(conn, date(2026, 3, 20), api_key=None)
  - print("書込み件数:", n_written)

- 市場レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, date(2026, 3, 20), api_key=None)

- 研究用ファクター計算:
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - records = calc_momentum(conn, date(2026, 3, 20))
  - normalized = from kabusys.data.stats import zscore_normalize
  - zrecords = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])

- 監査 DB 初期化:
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db("data/monitoring.db")
  - # conn_audit を監査ログ書き込みに利用

- ニュース RSS 取得（収集）:
  - from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  - articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
  - for a in articles: print(a["id"], a["title"], a["datetime"])

注意:
- OpenAI の呼び出しはレスポンスフォーマットを厳密な JSON に期待します。APIキーが未設定だと ValueError が発生します。
- ETL / API 呼び出しはネットワーク・APIエラーに対して内部でリトライやフォールバックを実装していますが、ログを確認してください。

---

## ディレクトリ構成

主要ファイルとモジュール（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (パッケージ参照用宣言あり)
  - strategy/, execution/ 等（パッケージ API に含める予定）

上記はこの README を作成したコードベースに含まれる主なモジュールです。各モジュールはドメイン毎に責務を分離して実装されています（ETL / 資料取得 / AI スコアリング / 研究用分析 / 監査ログなど）。

---

## ロギング・運用に関する補足

- ログレベルは LOG_LEVEL で制御します（デフォルト INFO）。
- KABUSYS_ENV により挙動（paper_trading / live）を切替可能です。特に live 時は取引系コードの安全チェック（実売買の抑止等）を必ず確認してください。
- Paper Trading 挙動は PAPER_FILL_MODE（instant/partial/never/reject）で制御されます。
- ETL は品質チェック（quality.run_all_checks）を呼ぶことが可能で、問題の有無は ETLResult で確認できます。
- 自動 .env 読込はプロジェクトルートに .git または pyproject.toml を探して行います。CI やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うことで抑止できます。

---

## 貢献・拡張

- 新しいデータソースを追加する場合は data/jquants_client.py に倣った fetch/save の設計を推奨します（冪等保存・fetched_at の記録）。
- AI プロンプトやモデルを変更する場合は ai/news_nlp.py 及び ai/regime_detector.py の SYSTEM_PROMPT とモデル名を更新してください。レスポンスの検証ロジックは厳格に保つことをおすすめします。
- 監査テーブル定義は data/audit.py に集約されています。監査拡張はここに追加してください。

---

必要に応じて README を拡張します。特定の機能（例: ETL の運用スケジュール例、監査ログのクエリ例、.env の完全な例、OpenAI のレスポンス例）を追加したい場合は教えてください。