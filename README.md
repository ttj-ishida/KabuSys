# KabuSys

日本株の自動売買プラットフォーム向け基盤ライブラリ群。データ取得（J-Quants）、ETL、ニュース収集、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定トレース）など、取引システムに必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の用途を想定したモジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する
- RSS からニュースを収集して正規化・DB保存し、銘柄コードと紐付ける
- ETL パイプライン（差分更新・バックフィル・品質チェック）を実行する
- 市場カレンダー（JPX）の夜間更新と営業日の判定を行う
- 監査ログ（signal → order_request → execution）を記録してトレーサビリティを確保する

設計上の特徴：
- API レート制御（J-Quants 120 req/min 固定間隔スロットリング）
- リトライ（指数バックオフ）・401 自動トークンリフレッシュ対応
- DuckDB への保存は冪等（ON CONFLICT）で重複・上書き制御
- ニュース収集では SSRF 防止・XML 攻撃対策・サイズ制限などを考慮

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート基準）および環境変数管理
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN 等）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - レート制御・リトライ・トークンリフレッシュ・fetched_at 記録

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) → 正規化した記事リスト
  - save_raw_news(conn, articles) → INSERT ... RETURNING で新規IDを返す
  - save_news_symbols / _save_news_symbols_bulk / extract_stock_codes
  - SSRF・XML・Gzip・サイズ制限などの安全対策を実装

- kabusys.data.schema
  - init_schema(db_path) → DuckDB にテーブル群・インデックスを作成
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl(...) → ETLResult を返す（品質チェック含む）

- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチでカレンダー差分更新）

- kabusys.data.audit
  - init_audit_schema(conn) / init_audit_db(db_path)（監査用テーブル初期化）

- kabusys.data.quality
  - 各種品質チェック（欠損、スパイク、重複、日付不整合）
  - run_all_checks(conn, ...) → QualityIssue のリスト

---

## システム要件

- Python 3.10+
- 依存パッケージ（主なもの）
  - duckdb
  - defusedxml

必要に応じて pyproject.toml / requirements.txt（プロジェクト側）を参照してください。

---

## セットアップ手順

1. リポジトリをクローン / パッケージをインストール

   開発環境であればソースツリー直下で:
   - pip install -e .

2. 必須環境変数を準備

   プロジェクトルートに `.env` ファイルを作り、以下を設定してください（例）:

   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack（通知用途）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # システム設定
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   注意:
   - 自動 .env 読み込みはデフォルトで有効。無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
   - 必須キー（未設定だとアクセス時に ValueError が発生します）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID

3. DuckDB スキーマ初期化

   Python REPL やスクリプトで初期化します:

   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   # またはメモリ DB
   # conn = schema.init_schema(":memory:")
   ```

4. 監査ログ用スキーマ（任意だが推奨）

   ```python
   from kabusys.data import audit
   # 既存の conn を使う
   audit.init_audit_schema(conn)
   # または専用 DB を初期化して取得
   # audit_conn = audit.init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主要な例）

- 日次 ETL を実行する（株価・財務・カレンダー・品質チェック）:

  ```python
  from kabusys.data import schema, pipeline
  conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema 済みを想定
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

  オプション:
  - target_date: ETL対象日（省略で今日）
  - run_quality_checks: True/False
  - spike_threshold, backfill_days, calendar_lookahead_days を調整可能

- ニュース収集ジョブの実行（RSS → raw_news 保存 + 銘柄紐付け）:

  ```python
  from kabusys.data import schema, news_collector
  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes は有効な銘柄コードのセット（例: DB の prices_daily から抽出）
  known_codes = {"7203", "6758", "1301"}
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- カレンダー夜間更新ジョブ:

  ```python
  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved:", saved)
  ```

- J-Quants クライアントを直接使う:

  ```python
  from kabusys.data import jquants_client as jq
  # トークンは settings.jquants_refresh_token から自動で取得
  quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  # DuckDB に保存
  conn = schema.get_connection("data/kabusys.duckdb")
  jq.save_daily_quotes(conn, quotes)
  ```

- 品質チェックの実行:

  ```python
  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i)
  ```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development|paper_trading|live, デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動読み込みを無効化)

---

## 開発者向けノート / 設計上の注意

- J-Quants API のレートは 120 req/min。モジュールは固定間隔スロットリングでこれに従います。
- HTTP リトライ: 408/429/5xx を対象に最大 3 回、指数バックオフ。401 は自動リフレッシュを行って1回だけ再試行します。
- DuckDB への保存は冪等化（ON CONFLICT DO UPDATE / DO NOTHING）されます。外部から直接データを挿入する場合は品質チェック（quality）を推奨します。
- ニュース収集は SSRF や XML 攻撃、巨大レスポンスを考慮した堅牢な実装になっています。fetch_rss/_urlopen はテスト時にモック可能です。
- calendar_management の営業日判定は market_calendar が未取得のときに曜日ベースでフォールバックしますが、DB にデータがある場合はそれを優先します。
- すべてのタイムスタンプは UTC を前提に扱う設計です（監査ログでは明示的に SET TimeZone='UTC' を実行）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - execution/ (発注・取引実行関連のエントリポイント用ディレクトリ)
    - __init__.py
  - strategy/ (戦略実装置き場)
    - __init__.py
  - monitoring/
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - calendar_management.py
    - audit.py
    - quality.py

---

必要に応じて README にサンプル .env.example、運用手順（cron/job runner での ETL スケジュール、Slack 通知の接続方法、kabuステーション接続設定）や API 使用上の制限・注意事項を追加してください。追加で詳しい使い方サンプルや運用チェックリストが必要であれば教えてください。