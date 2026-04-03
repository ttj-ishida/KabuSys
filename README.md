KabuSys
======

KabuSys は日本株の自動売買・データプラットフォーム用のライブラリ群です。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュースの NLP によるセンチメントスコアリング、マーケットレジーム判定、監査ログ（発注→約定のトレーサビリティ）などの機能を提供します。

主な特徴
--------
- データ ETL
  - J-Quants API から株価日足、財務データ、JPX マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分更新 / バックフィル機能、取得トークン自動リフレッシュ、レート制御、リトライ
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などを検出するチェック群
- ニュース収集・NLP
  - RSS からニュースを安全に収集して raw_news に保存
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（ai_scores）算出
- レジーム判定
  - ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して日次の市場レジーム（bull/neutral/bear）を算出
- 監査ログ（Audit）
  - signal → order_request → execution を追跡する冪等性の高い監査テーブル用 DDL / 初期化ユーティリティ
- 研究用ユーティリティ
  - ファクター計算（モメンタム、バリュー、ボラティリティ）、将来リターン、IC 計算、Z-score 正規化 など

セットアップ
----------
前提
- Python 3.10 以上（型ヒントで | を使用しているため）
- 必要なシステムライブラリは環境による（DuckDB をバイナリで pip が入る想定）

手順（開発環境）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール
   - pip install -U pip
   - pip install -e .    （プロジェクトが pyproject.toml / setup.cfg 等を持つ想定）
   - あるいは最低限の依存:
     - pip install duckdb openai defusedxml

3. 環境変数設定
   - プロジェクトルートの .env / .env.local を読み込みます（KabuSys は起動時に自動で .env を探索して読み込みます。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要な環境変数（後述）を .env に設定してください。

必須環境変数（代表）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注系がある場合）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定に必要）

推奨・任意の環境変数
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用 DB, デフォルト: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

.env の例 (.env.example を参考にする想定)
- .env
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=sk-...
  KABU_API_PASSWORD=your_kabu_password
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

使い方（基本的な呼び出し例）
--------------------------

DuckDB 接続の作成例:
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")  # ":memory:" も可能

ETL（デイリー）
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    res = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(res.to_dict())

ニューススコアリング（OpenAI 必須）
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    # OPENAI_API_KEY が環境変数にあれば api_key 引数は不要
    n = score_news(conn, target_date=date(2026, 3, 20))
    print(f"書き込んだ銘柄数: {n}")

市場レジーム判定（OpenAI 必須）
    from datetime import date
    from kabusys.ai.regime_detector import score_regime
    r = score_regime(conn, target_date=date(2026, 3, 20))
    print("OK" if r == 1 else "Failed")

監査ログ DB 初期化
    from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")
    # audit_conn は監査用の DuckDB 接続

RSS 取得（ニュース収集の一部）
    from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
    for a in articles:
        print(a["id"], a["datetime"], a["title"])

設定管理
--------
- kabusys.config.Settings はアプリ設定をラップしています。settings = Settings() を経由して読み出します。
- 自動で .env をプロジェクトルート（.git または pyproject.toml があるディレクトリ）から読み込みます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

テスト時のヒント
- AI や外部 API 呼び出しは外部モック可能な設計になっています（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- 自動 .env 読み込みを無効にするとテストが安定します（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

ディレクトリ構成（主要ファイル）
-------------------------------
プロジェクトの主要なファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 - 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             - ニュースセンチメント算出（OpenAI）
    - regime_detector.py      - マーケットレジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - pipeline.py             - ETL パイプライン（run_daily_etl 等）
    - etl.py                  - ETL ユーティリティ再エクスポート
    - jquants_client.py       - J-Quants API クライアント（fetch / save）
    - news_collector.py       - RSS 収集と保存
    - calendar_management.py  - 市場カレンダー管理（is_trading_day 等）
    - quality.py              - データ品質チェック
    - stats.py                - 汎用統計関数（zscore_normalize）
    - audit.py                - 監査ログ（DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py      - ファクター計算（momentum/value/volatility）
    - feature_exploration.py  - 将来リターン、IC、統計サマリー等

設計上の注意（重要）
------------------
- ルックアヘッドバイアス回避: 内部処理は date や target_date を明示的に渡す設計で、datetime.today() を直接参照しないよう配慮しています。バックテストや履歴再現性を確保するため、この設計に従ってください。
- 冪等性: ETL の保存関数は ON CONFLICT DO UPDATE を使用して冪等に保存します。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）の一時エラーはリトライやフォールバックで処理し、可能な限り処理を継続します（ただし重大なエラーはログ化して上位へ通知します）。
- セキュリティ: news_collector では SSRF 対策、XML ハンドリングに defusedxml を使用、RSS のサイズ制限等を実装しています。

開発・貢献
----------
- バグ報告・機能提案は Issue でお願いします。
- 大きな変更は PR を通してください。コード規約・テストを追加してください。

最後に
-------
この README はコードベースに基づく概要ドキュメントです。各モジュールの詳細な仕様・パラメータはソース内の docstring（各関数の説明）を参照してください。必要であればサンプルスクリプトや追加の運用ドキュメント（デプロイ手順、監視手順）を作成できます。