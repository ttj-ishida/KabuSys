# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買支援ライブラリ群です。  
ETL、ニュース収集・NLP（LLM）によるセンチメント評価、市場レジーム判定、ファクター計算、監査ログ（トレーサビリティ）などの機能を提供します。DuckDB を主要な永続化層として利用する設計です。

---

## 主な機能

- データ取得・ETL
  - J-Quants API から株価(日足)、財務データ、上場銘柄情報、マーケットカレンダーを差分取得・保存（pagination, retry, rate limit 対応）
  - ETL パイプライン（run_daily_etl）でカレンダー→株価→財務→品質チェックを一括実行
- データ品質チェック
  - 欠損、スパイク（急変）、重複、日付不整合検出（QualityIssue 型で集約）
- ニュース収集
  - RSS フィード収集（SSRF / Gzip / XML 攻撃対策、トラッキングパラメータ除去、記事IDは正規化 URL の SHA256）
- NLP / AI
  - ニュースごとの銘柄センチメント算出（score_news）
  - マクロニュース + ETF（1321）の MA200乖離で市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini）を JSON Mode で利用、リトライ / フォールバックの実装あり
- 研究・ファクター
  - Momentum / Value / Volatility 等のファクター計算、将来リターン、IC（Spearman）計算、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（init_audit_db / init_audit_schema）
- 設定管理
  - .env / .env.local / 環境変数からの自動読み込み（プロジェクトルート検出: .git または pyproject.toml）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone ... （プロジェクトルートが .git を持つことが自動 .env ロードの前提）

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - Linux/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - 必要なライブラリ（代表例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （パッケージ化された requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数設定
   - プロジェクトルートに `.env`（と必要に応じて `.env.local`）を作成します。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN = <J-Quants の refresh token>
     - SLACK_BOT_TOKEN = <Slack Bot Token>（Slack通知を使う場合）
     - SLACK_CHANNEL_ID = <Slack Channel ID>
     - KABU_API_PASSWORD = <kabuステーション API パスワード>（発注等を行う場合）
     - OPENAI_API_KEY = <OpenAI API Key>（AI 機能を使う場合）
   - 任意・設定例:
     - KABUSYS_ENV = development | paper_trading | live (デフォルト: development)
     - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL
     - DUCKDB_PATH = data/kabusys.duckdb (デフォルト)
     - SQLITE_PATH = data/monitoring.db
   - 自動読み込み:
     - パッケージ起動時にプロジェクトルート（.git または pyproject.toml）を基準に `.env` → `.env.local` を自動で読み込みます。
     - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB 用ディレクトリ作成
   - デフォルトの DB パス `data/kabusys.duckdb` の親ディレクトリを作成しておく（多くの初期化ユーティリティが自動作成しますが念のため）。
   - mkdir -p data

---

## 使い方（代表的な利用例）

下記は Python REPL／スクリプトでの利用例です。DuckDB 接続は duckdb.connect() で取得します。

- ETL 実行（デイリー）
  - 例: 日次 ETL を実行して結果を取得する
    - from datetime import date
      import duckdb
      from kabusys.data.pipeline import run_daily_etl
      conn = duckdb.connect("data/kabusys.duckdb")
      result = run_daily_etl(conn, target_date=date(2026,3,20))
      print(result.to_dict())

- ニュースセンチメント（AI）
  - ai/news_nlp.score_news を使ってニュースの銘柄別スコアを生成して ai_scores テーブルへ書き込む
    - from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
      print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定（AI + MA200）
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査ログ DB 初期化
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # テーブルが作成された DuckDB 接続が返る

- ファクター計算（研究）
  - from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    conn = duckdb.connect("data/kabusys.duckdb")
    mom = calc_momentum(conn, target_date=date(2026,3,20))
    vol = calc_volatility(conn, target_date=date(2026,3,20))
    val = calc_value(conn, target_date=date(2026,3,20))

- ニュース収集（RSS）
  - from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
    # 返り値は NewsArticle のリスト（id, datetime, source, title, content, url）

注意:
- AI 機能（score_news / score_regime）は OpenAI API キー（OPENAI_API_KEY）または api_key 引数が必須です。未設定の場合は ValueError が発生します。
- run_daily_etl 等は内部で date.today() を使用する箇所がありますが、関数に target_date を渡すことでルックアヘッドバイアスを避けられます。AI モジュールも target_date を基準にウィンドウを算出します。

---

## 設定（Environment / .env の詳細）

主な環境変数（settings にマッピングされる項目）:

- JQUANTS_REFRESH_TOKEN
  - J-Quants の refresh token。jquants_client.get_id_token で使用。
- KABU_API_PASSWORD
  - kabuステーション API のパスワード（発注系を利用する場合）。
- KABU_API_BASE_URL
  - kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY
  - OpenAI の API キー（AI モジュールで使用）
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- DUCKDB_PATH
  - デフォルト DB パス（Path オブジェクトで扱う）
- SQLITE_PATH
  - 監視用 SQLite パス
- KABUSYS_ENV
  - 実行環境: development / paper_trading / live（validation あり）
- LOG_LEVEL
  - ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

.env の読み込み挙動:
- パッケージインポート時に自動でプロジェクトルート（.git または pyproject.toml）を探索し、`.env`、続いて `.env.local` を読み込みます（.env.local が優先して上書き）。
- OS 環境変数は保護され、.env の値で上書きされないよう保護されます（ただし .env.local は override=True のため上書き可能）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

.env のパースは Bash ライクな形式をサポートし、シングル/ダブルクォートや export プレフィックス、コメント行等に対応します。

---

## 主要なモジュール / ディレクトリ構成（src/kabusys）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py (score_news をエクスポート)
    - news_nlp.py (ニュースセンチメント: score_news)
    - regime_detector.py (市場レジーム判定: score_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、fetch/save 系)
    - pipeline.py (ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl...)
    - etl.py (ETLResult の再エクスポート)
    - news_collector.py (RSS 収集)
    - calendar_management.py (マーケットカレンダー管理)
    - quality.py (品質チェック)
    - stats.py (zscore_normalize など)
    - audit.py (監査ログスキーマ初期化: init_audit_schema / init_audit_db)
  - research/
    - __init__.py (各研究用ユーティリティのエクスポート)
    - factor_research.py (calc_momentum, calc_value, calc_volatility)
    - feature_exploration.py (calc_forward_returns, calc_ic, factor_summary, rank)
  - researchパッケージは data.stats の zscore_normalize と連携してファクター研究を行う設計

---

## 開発上の注意・設計方針（抜粋）

- Look-ahead bias の防止:
  - AI モジュール・ETL・研究モジュールは target_date を明示して過去データのみを参照する設計。
- 冪等性:
  - J-Quants からの保存は ON CONFLICT DO UPDATE を使い冪等化。
  - audit の order_request_id や broker_execution_id は冪等キーとして扱う。
- フォールバック＆フェイルセーフ:
  - AI API の失敗時は基本的に例外を上げずにフォールバック値を使用（例: macro_sentiment=0.0）して処理を継続する設計が多く採用されています。
- リトライ＆レート制御:
  - J-Quants クライアントは固定間隔の RateLimiter と指数バックオフリトライ、401 時の自動トークンリフレッシュ等を実装。

---

## よくある利用例 / トラブルシューティング

- OpenAI のレスポンスが得られない / JSON パースに失敗する
  - レスポンスの形式が想定外の場合、該当チャンクはスキップして空のスコアが返る設計です。ログを確認し、API キー・モデルの利用制限をチェックしてください。
- .env が読み込まれない
  - パッケージは __file__ を基準にプロジェクトルート（.git または pyproject.toml）を探索します。`.env` を配置する場所を確認してください。自動ロードを無効化している可能性もあります（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- DuckDB のファイルパス
  - settings.duckdb_path で指定できます（デフォルト data/kabusys.duckdb）。パスは expanduser() されます。

---

必要であれば「具体的な .env.example のテンプレート」「requirements.txt」「実行スクリプト（cron / CI 用）」のサンプルや、各モジュールの API リファレンス（関数一覧と引数説明）を README に追記します。どちらを優先しますか？