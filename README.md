# KabuSys

日本株向けの自動売買基盤ライブラリ群（KabuSys）のリポジトリ内 README。  
以下はパッケージ src/kabusys の主要な機能、セットアップ、使い方、ディレクトリ構成の解説です。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なデータ取得（J-Quants 等）、ETL、データ品質チェック、ニュース収集、監査ログ（トレーサビリティ）、実行（発注）管理などを提供するモジュール群です。  
主要設計方針：

- J-Quants API のレート制限とリトライを自動処理（トークン自動リフレッシュ含む）
- DuckDB を用いた三層データモデル（Raw / Processed / Feature）と実行・監査テーブル
- ニュース収集でのセキュリティ対策（SSRF防止、XML攻撃対策、サイズ制限）
- ETL は差分更新・バックフィル・品質チェックを組み合わせて堅牢に実行

パッケージ名: kabusys、バージョンは src/kabusys/__init__.py の __version__ を参照。

---

## 主な機能一覧

- 設定管理（環境変数読み込み、自動 .env ロード）
  - 自動ロード順: OS 環境変数 > .env.local > .env
  - 自動ロード無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）/ 財務（四半期 BS/PL）/ マーケットカレンダーの取得
  - レートリミッタ、指数バックオフによるリトライ、401時のリフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS 取得、本文前処理（URL除去・空白正規化）、記事IDは正規化URLのSHA-256先頭32文字
  - SSRF対策（スキーム検証、プライベートアドレス検出）、defusedxml 使用、レスポンスサイズ制限
  - DuckDB への冪等バルク保存（INSERT ... RETURNING）と銘柄コード抽出
- スキーマ初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution / Audit 用のテーブル定義とインデックス
  - init_schema(), get_connection()
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新、バックフィル、品質チェックの実行（run_daily_etl, run_prices_etl 等）
  - quality モジュールと連携した欠損・スパイク・重複・日付不整合検出
- カレンダー管理（src/kabusys/data/calendar_management.py）
  - 営業日判定、前後営業日取得、カレンダー夜間更新ジョブ
- 監査ログ（src/kabusys/data/audit.py）
  - シグナル → 発注要求 → 約定のトレーサビリティテーブル、UUIDベースの冪等管理
  - init_audit_schema(), init_audit_db()
- データ品質チェック（src/kabusys/data/quality.py）
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks

注: strategy/ と execution/ 、monitoring/ のパッケージはエントリプレースホルダ（将来の拡張箇所）です。

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低依存:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに setup.cfg/pyproject.toml がある場合は pip install -e . が使えます）

3. 環境変数 (.env) を用意
   - プロジェクトルートに .env または .env.local を置くと自動ロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（settings で require されるもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN : Slack 通知用 Bot Token
     - SLACK_CHANNEL_ID : 通知先 Slack チャンネル ID
   - オプション（デフォルト値あり）:
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト "development"
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト "INFO"
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動 .env ロードを止められます
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）

   例 .env（参考）:
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

4. DuckDB スキーマの初期化
   - Python REPL やスクリプトで schema.init_schema() を呼ぶ（詳細は下記の使い方）

---

## 使い方（簡単なコード例）

以下は主要な利用例（Python スクリプト内）です。

- DuckDB スキーマ初期化（ファイル DB）
  ```python
  from kabusys.data.schema import init_schema, get_connection

  conn = init_schema("data/kabusys.duckdb")  # ファイルを作成してテーブルを作る
  # 既存DBに接続する場合は get_connection("data/kabusys.duckdb")
  ```

- 監査ログ DB 初期化（独立 DB を使う場合）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.db")
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行する
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 事前に銘柄一覧を用意しておく
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- J-Quants データを直接取得する（テストなど）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

  token = get_id_token()  # 環境変数の JQUANTS_REFRESH_TOKEN を使用
  recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 品質チェックを個別に実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

注意: 各関数は duckdb.DuckDBPyConnection（duckdb.connect() の戻り値）を受け取ります。インメモリ DB を使う場合は db_path として ":memory:" を使用できます。

---

## 主要 API（抜粋）

- 設定
  - kabusys.config.settings : 各種設定プロパティ（jquants_refresh_token, kabu_api_password, slack_bot_token, duckdb_path など）

- データ取得 / 保存（J-Quants）
  - jquants_client.get_id_token(refresh_token=None)
  - jquants_client.fetch_daily_quotes(...)
  - jquants_client.fetch_financial_statements(...)
  - jquants_client.fetch_market_calendar(...)
  - jquants_client.save_daily_quotes(conn, records)
  - jquants_client.save_financial_statements(conn, records)
  - jquants_client.save_market_calendar(conn, records)

- ニュース収集
  - news_collector.fetch_rss(url, source, timeout=30)
  - news_collector.save_raw_news(conn, articles)
  - news_collector.save_news_symbols(conn, news_id, codes)
  - news_collector.run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- スキーマ / ETL / カレンダー / 品質
  - data.schema.init_schema(db_path)
  - data.pipeline.run_daily_etl(...)
  - data.pipeline.run_prices_etl(...)
  - data.pipeline.run_financials_etl(...)
  - data.pipeline.run_calendar_etl(...)
  - data.calendar_management.calendar_update_job(conn, lookahead_days=90)
  - data.quality.run_all_checks(conn, target_date=None, reference_date=None)

- 監査ログ
  - data.audit.init_audit_schema(conn, transactional=False)
  - data.audit.init_audit_db(db_path)

---

## 環境変数一覧（主要）

- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
  - SLACK_BOT_TOKEN — Slack Bot Token（通知用）
  - SLACK_CHANNEL_ID — Slack チャンネル ID（通知先）

- 任意 / デフォルトあり:
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — ログレベル（デフォルト: INFO）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 を設定）

設定は .env / .env.local に記述しておくと自動で読み込まれます（ただし OS 環境変数が優先されます）。

---

## 注意事項 / 設計上のポイント

- J-Quants API
  - レート制限（120 req/min）に従うため内部で固定間隔スロットリングを行います。
  - HTTP 408/429/5xx 等は指数バックオフでリトライ、401 受信時はトークンを自動リフレッシュして 1 回リトライします。
  - 取得時点（fetched_at）を UTC で記録し、Look-ahead Bias を防ぐ設計です。

- ニュース収集のセキュリティ
  - defusedxml を使って XML 攻撃を防止
  - リダイレクト時と最終 URL に対してスキーム検証（http/https のみ）およびプライベートアドレス検査を実施（SSRF 対策）
  - レスポンスは最大 10MB に制限、gzip 解凍後も同上
  - URL から utm_* 等のトラッキングパラメータを除去して記事IDの一貫性を保つ

- DuckDB
  - スキーマ初期化関数は冪等であり、既存テーブルはスキップします。
  - audit.init_audit_schema はタイムゾーンを UTC に固定します（SET TimeZone='UTC'）。

- ETL と品質
  - ETL は差分更新・バックフィルを行い、品質チェックは Fail-Fast ではなく検出結果を返して呼び出し元で判断する設計です。

---

## ディレクトリ構成

リポジトリ内の主要ファイル / ディレクトリ（src 以下）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主要なモジュールは上記の data 以下に集中しており、strategy / execution / monitoring は今後の拡張ポイントです。

---

もし README に追加したい事項（例: 実行用 CLI、CI 設定、Docker サポート、より詳細な .env.example）や、特定のサンプルコードを補足してほしい箇所があれば教えてください。必要に応じて README のサンプルコードを実行可能な形に整備します。