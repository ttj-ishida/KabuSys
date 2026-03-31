KabuSys — 日本株自動売買プラットフォーム
====================================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・AI 支援・監査ログ機能を備えた自動売買プラットフォームのコアライブラリです。  
主に以下の機能群を提供します。

- J-Quants API を利用したデータ ETL（株価・財務・市場カレンダー）
- ニュース収集・NLP（OpenAI を利用した銘柄別センチメント算出）
- 市場レジーム判定（ETF の MA とマクロニュースを統合）
- 研究用ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order → execution のトレーサビリティ）
- DuckDB を用いた永続化と冪等保存ロジック

主な機能一覧
--------------
- data.jquants_client
  - J-Quants API からのデータ取得（daily_quotes / financial_statements / market_calendar / listed info）
  - DuckDB への冪等保存（save_* 関数）
  - レートリミット・リトライ・トークン自動リフレッシュ対応
- data.pipeline
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェックの一括 ETL
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別実行
  - ETLResult による実行結果まとめ
- data.news_collector
  - RSS フィード収集、URL 正規化、SSRF 対策、raw_news への冪等保存想定
- data.quality
  - 欠損 / スパイク / 重複 / 日付不整合の検出（QualityIssue を返す）
- data.calendar_management
  - market_calendar を参照した営業日判定・next/prev_trading_day・get_trading_days 等
- data.audit
  - 監査ログ用テーブル定義と初期化（init_audit_schema / init_audit_db）
- ai.news_nlp
  - raw_news + news_symbols をまとめて OpenAI（gpt-4o-mini）でスコアリングし ai_scores に書き込む（score_news）
- ai.regime_detector
  - ETF 1321 の 200 日 MA 乖離とマクロニュースセンチメントを組み合わせて市場レジームを判定・保存（score_regime）
- research
  - calc_momentum / calc_value / calc_volatility や特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - .env 自動読み込み（プロジェクトルートを基準に .env / .env.local を読み込み、OS 環境変数を保護）
  - Settings オブジェクト経由で設定値を安全に取得

セットアップ手順
----------------

1. リポジトリをクローン

   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境を作成（例: venv）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell / CMD)

3. 依存関係のインストール
   - プロジェクトが Poetry/pyproject.toml を使っている想定なら:

     poetry install

   - もしくはパッケージを editable インストール:

     pip install -e .

   - 必要な外部ライブラリ（例）
     - duckdb
     - openai
     - defusedxml
     - など（プロジェクトの pyproject.toml / requirements.txt を参照）

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある階層）に .env または .env.local を作成できます。
   - 自動ロードの挙動:
     - OS 環境変数 > .env.local > .env の順で優先されます。
     - テストや特殊用途で自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
     - KABU_API_PASSWORD     : kabu ステーション API 用パスワード（必要な場合）
     - SLACK_BOT_TOKEN       : Slack 通知に使用（必要な場合）
     - SLACK_CHANNEL_ID      : Slack チャンネル ID
     - OPENAI_API_KEY        : OpenAI を直接使うとき（score_news / score_regime の引数でも渡せます）
   - 任意 / デフォルト
     - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite（デフォルト data/monitoring.db）

   - 例 .env（テンプレート）
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

5. データベース初期化（監査ログなど）
   - 監査ログ専用 DB を作る例:

     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

使い方（簡易例）
----------------

- DuckDB 接続の作成（多くの関数は DuckDB 接続を受け取ります）:

  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行:

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）:

  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")

- 市場レジーム判定:

  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))

- 研究用関数の利用例:

  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from kabusys.data.stats import zscore_normalize

  momentum = calc_momentum(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))

  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

- 監査スキーマを既存 DuckDB に追加:

  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

注意と開発者向けヒント
--------------------
- OpenAI 呼び出しは各モジュールで独立実装されています。ユニットテストでは内部の _call_openai_api を patch してモックしてください（例: unittest.mock.patch）。
- config モジュールはプロジェクトルートを .git または pyproject.toml から自動検出して .env を読み込みます（CWD に依存しません）。
- ETL/品質チェック/ニュース収集などは Look-ahead Bias を避けるため datetime.today()/date.today() に依存しない実装を心掛けています。テスト時は target_date を明示的に渡してください。
- DuckDB の executemany はバージョンによって空リストを許容しないため、コード内で空チェックを行っています。バージョンアップ時は注意してください。

ディレクトリ構成（主要ファイル）
-----------------------------
以下はソースツリーの主要モジュール（src/kabusys）を抜粋した構成です。

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
    - pipeline.py (ETLResult エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - data/__init__.py

ライセンス / 貢献
-----------------
（このセクションはリポジトリの LICENSE ファイルやコントリビューション方針に従って追記してください）

お問い合わせ
------------
バグ報告や機能要望は issue を作成してください。開発者向けの詳細な設計ドキュメント（DataPlatform.md / StrategyModel.md 等）がリポジトリに同梱されていることを想定しています。README を読んで動作しない点や不明点があれば issue を立ててください。

以上。必要であれば README にサンプルの .env.example や実行スクリプト（CLI）利用方法、CI / テスト実行方法を追記します。どの情報を追加しますか？