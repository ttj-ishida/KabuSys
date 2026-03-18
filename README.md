KabuSys
=======

日本株向けの自動売買 / データプラットフォーム用ライブラリ群（モジュール群）です。
このリポジトリには、J-Quants API からのデータ取得、DuckDB スキーマ定義・初期化、ETL パイプライン、
RSS ニュース収集、データ品質チェック、マーケットカレンダー管理、監査ログ用スキーマなど
運用に必要な基盤機能が実装されています。

概要
----
KabuSys は以下を目的とした Python ライブラリ群です。

- J-Quants API から株価（日足）、財務情報（四半期 BS/PL）、マーケットカレンダーを取得するクライアント
- DuckDB を用いたデータスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS からのニュース収集と銘柄紐付け（SSRF、XML Bomb 等への防御を考慮）
- マーケットカレンダー管理（営業日判定・前後営業日検索）
- 監査ログ用スキーマ（シグナル→発注→約定のトレースを保証）

主な設計方針（抜粋）
- API のレート制限とリトライ（指数バックオフ、401 の自動トークンリフレッシュなど）を考慮
- DuckDB に対する保存は冪等（ON CONFLICT）を基本
- RSS 収集時は SS R F 対策、受信サイズ上限、defusedxml を使った安全な XML パース
- 品質チェックは Fail-Fast とせず、検出結果を収集して呼び出し元で評価可能にする

主な機能一覧
--------------
- jquants_client
  - get_id_token、fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar
  - DuckDB への保存 save_daily_quotes, save_financial_statements, save_market_calendar
  - レートリミッタ、リトライ、トークンキャッシュ（自動リフレッシュ）

- data.schema
  - DuckDB の全スキーマ定義（raw_prices, raw_financials, raw_news, market_calendar, features, signals, orders, trades, positions, audit テーブル など）
  - init_schema(db_path) → DuckDB 接続を初期化して返す
  - get_connection(db_path)

- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - 差分更新、バックフィル、品質チェックの統合的な日次 ETL 実行

- data.news_collector
  - fetch_rss(url, source) → RSS 取得と記事整形
  - save_raw_news, save_news_symbols, run_news_collection（複数ソース一括収集）
  - URL 正規化、トラッキングパラメータ除去、記事ID（SHA-256 ベース）生成、銘柄コード抽出

- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks（品質問題をまとめて返す）

- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（夜間バッチでのカレンダー更新）

- data.audit
  - 監査ログ用テーブルの初期化 init_audit_schema / init_audit_db（UTC 固定、トレーサビリティ確保）

必要条件（推奨）
---------------
- Python 3.10 以上（型注釈で | を使用）
- 必要なライブラリ（少なくとも）:
  - duckdb
  - defusedxml

インストール例（最低限）
- 仮想環境を作成してから:
  - pip install duckdb defusedxml

環境変数（設定）
----------------
kabusys.config.Settings が参照する主要な環境変数（必須は _require により未設定時に例外）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン（使用する場合）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID（使用する場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（monitoring 用。デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

自動 .env ロード
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動で読み込みます。
- 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順
----------------

1. リポジトリをクローンして仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を実行）

3. .env を用意
   プロジェクトルートに .env ファイルを作り、必要な環境変数を設定します（例）:

   .env（例）
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

4. DuckDB スキーマの初期化
   - Python REPL またはスクリプトで以下を実行:

     from kabusys.config import settings
     from kabusys.data import schema
     conn = schema.init_schema(settings.duckdb_path)  # ファイルがなければ作成し全テーブルを構築

   - 監査ログ用 DB を分ける場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

使い方（例）
------------

- 日次 ETL 実行（市場カレンダー、株価、財務の差分取得 + 品質チェック）:

  from kabusys.config import settings
  from kabusys.data import schema, pipeline
  conn = schema.init_schema(settings.duckdb_path)
  result = pipeline.run_daily_etl(conn)  # ETLResult を返す
  print(result.to_dict())

- ニュース収集ジョブを実行して DuckDB に保存する:

  from kabusys.data import schema, news_collector
  conn = schema.init_schema("data/kabusys.duckdb")
  # 既知銘柄コードのセット (extract_stock_codes に渡す)
  known_codes = {"7203", "6758", "9984"}  # 例
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}

- J-Quants から日足を直接取得して保存する（テストやデバッグ用）:

  from kabusys.data import jquants_client as jq
  from kabusys.data import schema
  from kabusys.config import settings
  conn = schema.init_schema(settings.duckdb_path)
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f"fetched={len(records)} saved={saved}")

- マーケットカレンダーの営業日判定:

  from kabusys.data import calendar_management as cm
  conn = schema.init_schema("data/kabusys.duckdb")
  cm.is_trading_day(conn, date(2025,1,1))

注意点・運用上のポイント
-----------------------
- J-Quants API はレート制限（120 req/min）があるため、jquants_client モジュールは内部でスロットリングとリトライを実装しています。
- fetch_* 系はページネーション対応で、取得時に fetched_at を UTC で付与します（Look‑ahead bias を防ぐため）。
- RSS 収集は外部 URL を扱うため SSRF 対策（スキーム検証、プライベート IP 拒否、リダイレクト検査）やレスポンスサイズ上限を実装しています。
- DuckDB スキーマは冪等に作成されるため、init_schema を何度呼んでも安全です。
- 監査ログ（audit）機能はタイムゾーンを UTC に固定します。init_audit_db / init_audit_schema を使用して初期化してください。
- 品質チェックは run_all_checks でまとめて実行できます。重大度（error / warning）ごとに扱いを変えて運用してください。
- 自動 .env 読み込みはプロジェクトルートを基準に行います。テスト等で無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成
-----------------
（主要なファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定管理、自動 .env ロード
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント & DuckDB 保存
    - news_collector.py      # RSS ニュース収集・保存・銘柄抽出
    - schema.py              # DuckDB スキーマ定義・初期化
    - pipeline.py            # ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py # マーケットカレンダー管理
    - audit.py               # 監査ログスキーマの初期化
    - quality.py             # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

サンプルファイル
- デフォルト DuckDB パス: data/kabusys.duckdb
- RSS デフォルトソース: news_collector.DEFAULT_RSS_SOURCES に定義（例: Yahoo Finance ビジネスカテゴリ）

ライセンス / 貢献
----------------
本 README にはライセンス情報が含まれていません。実際のリポジトリでは LICENSE ファイルや CONTRIBUTING ガイドを参照してください。

補足（開発者向けメモ）
---------------------
- 型注釈・設計文書（DataPlatform.md 等）に基づく実装が多く含まれます。既存の API を拡張する際は各モジュールの設計方針コメントを参照してください。
- 外部サービス（J-Quants / kabuステーション / Slack 等）との連携部は設定値・認証トークンに依存します。ローカル開発時はテスト用のモックや KABUSYS_DISABLE_AUTO_ENV_LOAD を活用してください。

以上がこのコードベースの概要と基本的な使い方です。必要であれば README に含めるサンプルコマンドや .env.example のテンプレート、CI/デプロイ手順なども追加できます。どの部分を詳しく追加しますか？