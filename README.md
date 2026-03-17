# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。J-Quants API からの市場データ取得、ニュース収集、DuckDB によるデータ格納とスキーマ管理、日次 ETL パイプライン、マーケットカレンダー管理、データ品質チェック、監査ログ用スキーマなどを提供します。

バージョン: 0.1.0

---

## 特徴（概要）

- J-Quants API 連携
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）の遵守、指数バックオフによるリトライ、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）の記録により Look-ahead Bias を防止

- データ格納（DuckDB）
  - Raw / Processed / Feature / Execution 層のスキーマ定義
  - 冪等な保存（ON CONFLICT ... DO UPDATE / DO NOTHING）
  - 監査用スキーマ（signal → order_request → execution のトレース可能）

- ニュース収集
  - RSS フィード取得、コンテンツ前処理、記事IDは正規化 URL の SHA-256（先頭32文字）
  - defusedxml による XML 攻撃対策、SSRF 対策、レスポンスサイズ制限による DoS 対策
  - 銘柄コード抽出と raw_news / news_symbols 保存

- ETL / パイプライン
  - 差分更新（最終取得日に基づく差分取得 + バックフィル）
  - 日次 ETL エントリ（run_daily_etl）でカレンダー・株価・財務・品質チェックを一括実行

- マーケットカレンダー管理
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - 夜間バッチ（calendar_update_job）で先読み更新

- データ品質チェック
  - 欠損・スパイク（前日比）・重複・日付不整合の検出
  - QualityIssue オブジェクトで問題を一覧として返却

---

## 主要機能一覧

- kabusys.config
  - 環境変数管理（.env / .env.local の自動読み込み、プロジェクトルート検出）
  - 必須設定の検査・ラッパー（Settings）

- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar

- kabusys.data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, extract_stock_codes, run_news_collection

- kabusys.data.schema
  - init_schema, get_connection（DuckDB スキーマの初期化・接続取得）

- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl（ETL パイプライン）

- kabusys.data.calendar_management
  - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job

- kabusys.data.audit
  - 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）

- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントに `X | Y` を使用しているため）
- Git のあるプロジェクトルートまたは `pyproject.toml` が存在する構成を想定

1. リポジトリをクローン（あるいはソースをプロジェクト内に配置）

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 必須依存（例）
     ```
     pip install duckdb defusedxml
     ```
   - プロジェクト化されている場合は pyproject.toml / requirements.txt に従ってください。
   - 開発時は editable install:
     ```
     pip install -e .
     ```

4. 環境変数 (.env) の準備
   - プロジェクトルート（.git または pyproject.toml のある親階層）を自動検出して `.env` / `.env.local` を読み込みます。
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）

   - サンプル .env:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=./data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（簡単な例）

以下はライブラリを使った最小限の実行例です。詳細は各モジュールの関数を参照してください。

- DuckDB スキーマ初期化
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリを自動作成
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)  # 既存DBへ接続（初回は init_schema を推奨）
  result = run_daily_etl(conn)  # デフォルトで今日分を処理
  print(result.to_dict())
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は銘柄コードセット（例: {'7203','6758',...}）
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: 新規保存件数}
  ```

- カレンダー更新（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved calendar rows: {saved}")
  ```

- 監査ログスキーマ初期化（別 DB にしたい場合）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- 品質チェックの実行
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for issue in issues:
      print(issue)
  ```

ログ出力や Slack 通知など外部連携はプロジェクト側で設定して利用してください（SLACK_* 環境変数等を参照）。

---

## 環境変数 / 設定（まとめ）

必須（実行する機能により必要）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（fetch 系を使う場合）
- KABU_API_PASSWORD — kabuステーション API パスワード（execution 層を使う場合）
- SLACK_BOT_TOKEN — Slack 通知（ある場合）
- SLACK_CHANNEL_ID — Slack 通知先

オプション
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（任意）

自動 .env 読み込み
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` を読み込みます。
- 読み込み順序: OS 環境変数（最優先） > .env.local（上書き） > .env（未上書き）
- OS 環境変数は保護され、.env.local の override からも除外されます。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 配下に実装されています。主なファイル:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント / 保存ユーティリティ
    - news_collector.py      — RSS ニュース収集と保存ロジック
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理
    - audit.py               — 監査ログ（signal / order_request / executions）
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py
    - (戦略ロジックを配置する場所)
  - execution/
    - __init__.py
    - (ブローカー発注・約定管理を配置する場所)
  - monitoring/
    - __init__.py
    - (監視・メトリクス周り)

---

## 開発・拡張のヒント

- テストしやすさのため、jquants_client の id_token 等は引数注入可能（ユニットテストではモックを注入）。
- news_collector._urlopen をテストでモックすると外部ネットワーク呼び出しを置き換えられます。
- DuckDB の初期化は init_schema を使い、スキーマ変更は DDL を追加して冪等に保つ。
- ETL 実行は run_daily_etl が主要なエントリポイント。品質チェックは ETL の一部として任意で実行可能。
- ローカル実行では .env と DUCKDB_PATH を使って素早く試せます。運用環境では KABUSYS_ENV を適切に設定してください。

---

もし README に追加したい内容（CI 設定、デプロイ手順、テスト実行方法、より詳細な API 使用例など）があれば教えてください。必要に応じて追記します。