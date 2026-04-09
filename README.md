# KabuSys — 日本株自動売買プラットフォーム（README）

概要
- KabuSys は日本株向けのデータプラットフォーム・研究・AI スコアリング・監査ログ・ETL を含むライブラリ群です。
- 主に以下の目的を持ちます：
  - J-Quants からのデータ取得（株価、財務、マーケットカレンダー）
  - DuckDB を用いたデータ格納・品質チェック・ETL パイプライン
  - ニュースの収集と LLM を使った銘柄別センチメント（ai_score）算出
  - 市場レジーム判定（MA とマクロニュースの合成）
  - 監査ログ（signal → order → execution のトレーサビリティ）
  - 研究用ファクター計算・IC/統計ユーティリティ

主な機能一覧
- data
  - ETL（差分更新・バックフィル・品質チェック）: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants API クライアント（認証・ページネーション・リトライ・保存関数）
  - 市場カレンダー管理（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS 取得・前処理、SSRF 対策、正規化）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（監査用テーブル・インデックス作成）
  - 統計ユーティリティ（zscore_normalize など）
- ai
  - ニュース NLP（gpt-4o-mini を用いた銘柄ごとのセンチメント → ai_scores テーブルへ書き込み）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM を合成）
- research
  - ファクター計算（モメンタム、バリュ―、ボラティリティ）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- 設定管理（kabusys.config）
  - .env / .env.local を自動で読み込む仕組み（プロジェクトルート検出）
  - 必須/任意の環境変数を型変換して提供

動作要件（推奨）
- Python >= 3.10（typing の | 表記等を使用）
- 必要な主要パッケージ（例）
  - duckdb
  - openai (または OpenAI の Python SDK)
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS ソース へアクセスする場合）

環境変数（主なもの）
- 認証 / API
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - OPENAI_API_KEY: OpenAI の API キー（AI 機能を使う場合）
  - KABU_API_PASSWORD: kabu ステーション API パスワード
  - KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- 通知
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DB / ファイルパス
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（Paper Trading 用 SQLite、デフォルト data/paper_trading.db）
- Paper Trading 等
  - PAPER_FILL_MODE（instant | partial | never | reject）
- 実行 / 監視
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- 環境/ログ
  - KABUSYS_ENV（development | paper_trading | live、デフォルト development）
  - LOG_LEVEL（DEBUG, INFO, ...）
- 自動 .env ロード無効化
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化

セットアップ手順（ローカル開発向け）
1. ソースを取得
   - git clone <repo>
   - cd <repo>

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存インストール（必要に応じて）
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）
   - 開発中は pip install -e . を使うと便利（パッケージとしてインストール可能な場合）

4. 環境変数設定
   - プロジェクトルートに .env を作成（.env.example を参考に必要項目を設定）
   - 例（.env）
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - OPENAI_API_KEY=sk-xxxx
     - DUCKDB_PATH=data/kabusys.duckdb
   - 自動ロードは kabusys.config がプロジェクトルート（.git または pyproject.toml）を検出すると行います。
   - テスト等で自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB 初期化（監査DB等）
   - 監査スキーマを作る例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - ETL の実行は既存の DuckDB 接続を渡して行います。

使い方（代表的な利用例）

- 設定の参照
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env など

- ETL（日次パイプライン）の実行
  - from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- J-Quants API を直接使って取得／保存
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
    # fetch
    records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
    # save
    saved = save_daily_quotes(conn, records)

- ニュース収集（RSS）
  - from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
    # fetch_rss は NewsArticle のリストを返すので、自分の raw_news テーブルへ永続化してください。
    # （raw_news/news_symbols に保存する処理は実装例が別にある想定です）

- AI スコアリング（ニュース）
  - from kabusys.ai.news_nlp import score_news
    # conn は DuckDB 接続、target_date は date オブジェクト
    score_news(conn, target_date=date(2026,3,20), api_key="sk-xxxx")

- 市場レジームスコア算出
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20), api_key="sk-xxxx")

- 監査スキーマ初期化（既存接続へ）
  - from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)

- 研究用ユーティリティ（ファクター計算）
  - from kabusys.research import calc_momentum, calc_value, calc_volatility
    momentum = calc_momentum(conn, target_date=date(2026,3,20))

注意点 / 実装上の設計方針（要点）
- ルックアヘッドバイアス防止のため、内部処理は datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
- J-Quants クライアントはレート制御とリトライ、401 の自動トークンリフレッシュを実装。
- NewsCollector は SSRF 対策、XML の安全パース、受信バイト数制限、URL 正規化（utm 等除去）を行う。
- AI 呼び出しは JSON mode（gpt-4o-mini）で厳密な JSON を期待し、失敗時はフェイルセーフ（0.0 等）で継続する設計。
- ETL は差分取得 + バックフィル（デフォルト 3 日）で API 後出し修正を吸収する方針。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py
    - (その他 data 内ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*.py （factor/feature 用）
  - research/__init__.py
  - (他: strategy/, execution/, monitoring/ 等のパッケージを想定)

開発・テスト
- 環境ごとに .env / .env.local を用意して秘密情報を管理してください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行いますが、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- OpenAI API 呼び出し部分はテスト時にモック可能（モジュール内の _call_openai_api を patch）。

よくある質問（FAQ）
- Q: .env の読み込み順は？
  - A: OS 環境変数 > .env.local > .env の順で上書きされます。既存 OS 環境は保護されます。
- Q: DuckDB のパスはどこで設定する？
  - A: 環境変数 DUCKDB_PATH を設定してください（デフォルト data/kabusys.duckdb）。
- Q: OpenAI のレスポンスが JSON でない場合は？
  - A: モジュール側でパース失敗時にログを出しフェイルセーフ値（例: 0.0）で継続します。テストでは API 呼び出しをモックしてください。

最後に
- 本 README はコードベースの主要な設計方針と使い方をまとめた簡易ドキュメントです。各モジュールには詳細な docstring（日本語コメント）を含んでいるため、API を直接確認することを推奨します。必要ならば個別モジュールの使い方や例を追記しますので、知りたい箇所を教えてください。