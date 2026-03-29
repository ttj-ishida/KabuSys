KabuSys
=======

概要
----
KabuSys は日本株のデータパイプライン、リサーチ、ニュースNLP、マーケットレジーム判定、監査ログおよび ETL 処理を含む日本株自動売買（アルゴリズム取引）プラットフォームのコアライブラリです。本リポジトリは以下の要素をモジュール化して提供します。

- データ取得・ETL（J-Quants 経由の株価・財務・カレンダー）
- ニュース収集（RSS）とニュースの NLP スコアリング（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの LLM 評価の合成）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）
- 環境変数 / 設定管理

主な機能
--------
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- J-Quants API クライアント（認証リフレッシュ、ページネーション、保存用ユーティリティ）
- ニュース収集（fetch_rss）および前処理（preprocess_text）
- ニュース NLP（score_news）：OpenAI（gpt-4o-mini）を使った銘柄別センチメント集約・バッチ評価
- 市場レジーム判定（score_regime）：ETF 1321 の 200 日 MA とマクロニュース LLM スコアを合成
- 監査テーブル初期化（init_audit_schema / init_audit_db）
- データ品質チェック（quality.run_all_checks）
- 研究用ユーティリティ（research パッケージ内のファクター計算・IC 計算・正規化等）
- 環境設定管理（kabusys.config: .env 自動ロード・必須変数チェック）

セットアップ手順
----------------

1. 前提
   - Python 3.10 以上を推奨（PEP 604 の型記法などを利用）
   - DuckDB、OpenAI SDK、defusedxml 等のライブラリが必要

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   実運用では logging、requests 等の追加パッケージや CI 用の依存を加えることがあります。

4. 環境変数の準備
   プロジェクトルートに .env または .env.local を置くと自動でロードされます（kabusys.config により .git や pyproject.toml をルート判定）。

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_station_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   自動ロードを無効にする場合:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース用ディレクトリ作成（必要なら）
   - mkdir -p data

使い方（代表的なユースケース）
----------------------------

以下はライブラリを Python から直接呼ぶ例です。

- DuckDB 接続を作って ETL を回す（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 株価差分 ETL（個別）
  ```python
  from kabusys.data.pipeline import run_prices_etl
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
  ```

- ニュースのセンチメント評価（OpenAI API キーが必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key: None の場合は環境変数 OPENAI_API_KEY を参照
  count = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print("scored:", count)
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- RSS フェッチ（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの duckdb 接続
  ```

設定（kabusys.config）について
------------------------------
- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を探索して .env/.env.local を自動読み込みします。
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効にできます（テスト時に有用）。
  - 読み込む順序: OS 環境変数 > .env.local (override=True) > .env

- 必須環境変数（Settings にて _require() で取得）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - その他: KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL（DEBUG/INFO/...）等

主な公開 API / 関数一覧（抜粋）
------------------------------
- kabusys.config.settings: アプリ設定オブジェクト
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - ETLResult クラス
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.news_collector
  - fetch_rss, preprocess_text
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency

注意点 / 設計上のポイント
------------------------
- Look-ahead バイアス回避
  - 各モジュール（news_nlp / regime_detector / pipeline 等）は date.today() を直接使わない設計（外部から target_date を渡す）。
- OpenAI 呼び出し
  - gpt-4o-mini を用いた JSON mode を使用。API 呼び出しはリトライやエラー時のフォールバック（0.0）等の安全策あり。
  - テストのために _call_openai_api をモック可能。
- J-Quants API
  - トークンリフレッシュ、固定間隔レート制限、リトライ、ページネーションに対応。
- DuckDB について
  - 永続化ファイル（例: data/kabusys.duckdb）を想定。init_audit_db は必要な監査テーブルを初期化します。
- ニュース収集の安全対策
  - SSRF 対策、受信サイズ上限、gzip 解凍の検査、defusedxml による XML パース等を実装。

ディレクトリ構成（src/kabusys 以下）
-----------------------------------
概要的なツリー（主要ファイルのみ抜粋）:

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
    - news_collector.py
    - calendar_management.py
    - stats.py
    - quality.py
    - audit.py
    - (その他: schema 初期化等のユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/, strategy/, execution/ など（パッケージ公開に含まれるが本サンプルでは実装の一部のみ）

貢献 / テスト
--------------
- OpenAI 呼び出し箇所はモック可能（内部の _call_openai_api を patch して返り値を固定化）。
- J-Quants クライアントもネットワーク呼び出しを行うため、ネットワーク依存テストはモック推奨。
- DuckDB を :memory: で接続してユニットテストを行うことができます（init_audit_db(":memory:") 等）。

ライセンス / 免責
-----------------
（ここではライセンス情報は含めていません。実際のプロジェクトでは LICENSE ファイルを追加してください。）

補足
----
- ここに記載したコードは核となるロジックの抜粋です。実運用には更なるエラーハンドリング、監視、運用ドキュメント（バックテスト手順・CI/CD・デプロイ方法）、そして適切な秘密情報管理が必要です。
- 本 README はリポジトリのコードベースに基づいた導入ガイドです。詳細な API ドキュメントや実装細部は各モジュールの docstring を参照してください。