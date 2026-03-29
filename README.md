KabuSys
=======

KabuSys は日本株向けのデータ基盤・リサーチ・簡易自動売買（監査・発注ログ設計含む）を目的とした Python モジュール群です。J-Quants API / kabuステーション / OpenAI（LLM）など外部サービスと連携し、ETL、データ品質チェック、ニュースセンチメント、ファクター計算、監査ログスキーマなどを提供します。

主な特色
--------
- DuckDB をデータレイク/分析用 DB として利用する ETL パイプライン（差分取得・保存・品質チェック）
- J-Quants API クライアント（株価・財務・市場カレンダー） — レート制御・リトライ・トークン自動更新対応
- ニュース収集（RSS）とニュースの NLP（OpenAI を用いた銘柄ごとのセンチメント）処理
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- ファクター計算（Momentum / Value / Volatility 等）および特徴量探索・IC 計算
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution）用の冪等スキーマと初期化ユーティリティ
- .env ファイル / 環境変数による設定管理（自動ロード機能あり）

機能一覧
--------
- data/jquants_client.py: J-Quants API からのデータ取得・DuckDB への保存（save_*, fetch_*）
- data/pipeline.py: 日次 ETL（run_daily_etl）・個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）と ETLResult
- data/quality.py: 品質チェック（check_missing_data, check_duplicates, check_spike, check_date_consistency, run_all_checks）
- data/calendar_management.py: 市場カレンダー管理と営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job）
- data/news_collector.py: RSS 取得と前処理（fetch_rss 等）、SSRF/圧縮/サイズ等の防御実装
- data/audit.py: 監査ログ用スキーマ作成 / 初期化（init_audit_schema, init_audit_db）
- ai/news_nlp.py: 銘柄ごとのニュースを集計して OpenAI でセンチメント（score_news）
- ai/regime_detector.py: ETF の MA とマクロニュース LLM を合成して市場レジーム判定（score_regime）
- research/*: ファクター算出・特徴量解析ユーティリティ（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary など）
- config.py: 環境変数/設定読み込みロジック（.env 自動読み込み・必須キーチェック・settings オブジェクト）

前提 / 必要条件
--------------
- Python 3.10+
- 推奨パッケージ（主な依存例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで実装されている部分が多いですが、実行する機能に応じて追加依存が必要です）
- J-Quants / OpenAI / Slack / kabuステーション の適切な資格情報（環境変数で指定）

セットアップ手順
----------------

1. Python のインストール（3.10+ 推奨）

2. リポジトリをクローンしてパッケージをインストール
   - 開発環境：
     - pip install -e . もしくは requirements.txt があれば pip install -r requirements.txt
   - 必要パッケージ例:
     - pip install duckdb openai defusedxml

3. 環境変数（.env）を準備
   - プロジェクトルート（.git または pyproject.toml がある位置）から自動で .env/.env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（config.Settings から）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack ボットトークン（通知用）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意（デフォルト値があるもの / 推奨）:
     - KABUSYS_ENV — one of: development, paper_trading, live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化
     - OPENAI_API_KEY — OpenAI を利用する機能で使う API キー（score_news / score_regime の呼び出し時に引数で指定可能）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - 例 (.env):
     - JQUANTS_REFRESH_TOKEN=YOUR_JQUANTS_REFRESH_TOKEN
     - OPENAI_API_KEY=sk-...
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - KABUSYS_ENV=development

4. DB 初期化（監査ログなど）
   - 監査 DB を初期化する例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - ETL 用 DuckDB 接続:
     - import duckdb
     - conn = duckdb.connect("data/kabusys.duckdb")

使い方（代表的な操作例）
-----------------------

- 日次 ETL を実行する（例: Python スクリプト）
  - from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- ニューススコアリング（OpenAI を使用）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    # api_key を渡さない場合は環境変数 OPENAI_API_KEY を参照
    written = score_news(conn, target_date=date(2026,3,20))
    print(f"書込み件数: {written}")

- 市場レジーム判定
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20))

- 監査スキーマの初期化（既存接続に追加）
  - from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)

- カレンダー操作（例: 翌営業日の取得）
  - from datetime import date
    import duckdb
    from kabusys.data.calendar_management import next_trading_day
    conn = duckdb.connect("data/kabusys.duckdb")
    next_day = next_trading_day(conn, date(2026,3,20))

設定値参照
----------
- アプリの設定は kabusys.config.settings から参照できます（プロパティで必須チェックあり）。
  - 例: from kabusys.config import settings; token = settings.jquants_refresh_token

自動 .env 読み込み
-----------------
- プロジェクトルート（.git または pyproject.toml を探索）にある .env, .env.local を自動で読み込みます。
- 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き）
- 無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを行いません（テスト等で利用）。

ロギング / 実行モード
--------------------
- KABUSYS_ENV (development / paper_trading / live) によって settings.is_dev / is_paper / is_live が切り替わります。ライブモードでは実際の発注や外部サービスへの接続時の安全制約を強める等の運用上の判断を行ってください（本コードは設定フラグを提供しますが、実際の発注ロジックは別実装です）。
- ログレベルは LOG_LEVEL で制御します（デフォルト INFO）。

ディレクトリ構成
----------------

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py (score_news を再エクスポート)
    - news_nlp.py (news の LLM スコアリング)
    - regime_detector.py (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント & DuckDB 保存)
    - pipeline.py (ETL パイプライン・ETLResult)
    - etl.py (ETLResult の公開エイリアス)
    - news_collector.py (RSS 収集)
    - calendar_management.py (市場カレンダー管理)
    - quality.py (データ品質チェック)
    - stats.py (共通統計ユーティリティ: zscore_normalize)
    - audit.py (監査ログスキーマ初期化)
  - research/
    - __init__.py
    - factor_research.py (calc_momentum, calc_value, calc_volatility)
    - feature_exploration.py (calc_forward_returns, calc_ic, factor_summary, rank)
  - research/* その他のユーティリティファイル

（上記はコードベースに含まれる主要モジュールの一覧です）

開発・テストに関する注意
------------------------
- OpenAI / J-Quants などの外部 API 呼び出し部分は、ユニットテスト時にモックすることが想定されています（モジュール内の _call_openai_api などを patch）。
- .env 自動読み込みはプロジェクトルート検出を行うため、テスト環境で意図しない .env を読み込まないように KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- DuckDB に対する executemany に空リストを渡すとエラーになるバージョン依存があるため、パラメータが空でないことを確認してから実行する実装になっています（pipeline/news_nlp 等で考慮済み）。

ライセンス / 貢献
-----------------
（この README ではリポジトリのライセンスや貢献方法は記載していません。必要に応じてプロジェクトルートに LICENSE / CONTRIBUTING.md を追加してください。）

付録: よく使うインポート例
--------------------------
- ETL 実行:
  - from kabusys.data.pipeline import run_daily_etl
- News スコア:
  - from kabusys.ai.news_nlp import score_news
- Regime 判定:
  - from kabusys.ai.regime_detector import score_regime
- Audit DB 初期化:
  - from kabusys.data.audit import init_audit_db

問題や改善提案があれば、ソース内のドキュメントとログメッセージを参照のうえ Issue/PR を作成してください。