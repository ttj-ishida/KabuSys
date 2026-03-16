# KabuSys

日本株の自動売買プラットフォーム向けユーティリティ群（ライブラリ）。  
データ取得・保存（J-Quants / DuckDB）、スキーマ初期化、データ品質チェック、監査ログなど、取引システムの基盤機能を提供します。

バージョン: 0.1.0

## 概要

KabuSys は以下の機能を提供する Python モジュール群です。

- J-Quants API クライアント（OHLCV / 財務 / マーケットカレンダーの取得）
  - レート制限（120 req/min）を守る RateLimiter
  - リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（UTC）を記録し look-ahead bias を防止
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 環境変数／.env の自動読み込みと設定管理

設計上、ETLや戦略レイヤーへ組み込めるように、関数ベースで接続やレコードを受け渡す形になっています。

## 主な機能一覧

- data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - レート制限、リトライ、トークンキャッシュ
- data.schema
  - init_schema(db_path)
  - get_connection(db_path)
  - DuckDB 上のテーブル（raw_prices, raw_financials, market_calendar, features, signals, orders, trades, positions など）を定義・生成
- data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)
  - 監査用テーブル（signal_events, order_requests, executions）を定義・生成
- data.quality
  - check_missing_data(conn, target_date=None)
  - check_spike(conn, target_date=None, threshold=0.5)
  - check_duplicates(conn, target_date=None)
  - check_date_consistency(conn, reference_date=None)
  - run_all_checks(conn, ...)
- config
  - Settings: 環境変数から設定を取得（必須値は _require により例外を発生）
  - 自動 .env ロード（プロジェクトルート：.git または pyproject.toml を探索）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

## 動作要件

- Python 3.10+（Union 型表記 (X | None) を使用）
- 依存パッケージ（最低限）
  - duckdb
- 標準ライブラリ: urllib, json, logging, time, datetime, pathlib など

（プロジェクト管理に Poetry / pip-tools 等を使う場合は pyproject.toml / requirements.txt を参照してください）

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb
   - （プロジェクトを editable インストールする場合）
     - pip install -e .

4. 環境変数設定 (.env)
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション:
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN="eyJ...your_refresh_token..."
   KABU_API_PASSWORD="your_kabu_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C0123456789"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ初期化
   - Python スクリプトや REPL で schema.init_schema を呼び出して DB を作成します（:memory: 可）。
   - 例:
     ```
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```

6. 監査ログの初期化（必要に応じて）
   - 既存接続に追加:
     ```
     from kabusys.data import audit
     audit.init_audit_schema(conn)
     ```
   - 監査専用 DB を作る:
     ```
     audit_conn = audit.init_audit_db("data/audit.duckdb")
     ```

## 使い方（簡単な例）

- J-Quants から日足を取得して DuckDB に保存する例:

  ```
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data import schema
  from datetime import date

  conn = schema.init_schema("data/kabusys.duckdb")

  # 全銘柄・特定期間の取得例
  records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
  inserted = save_daily_quotes(conn, records)
  print(f"保存件数: {inserted}")
  ```

- 財務データを取得して保存する例:

  ```
  from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
  records = fetch_financial_statements(date_from=date(2023,1,1), date_to=date(2023,12,31))
  save_financial_statements(conn, records)
  ```

- マーケットカレンダー取得例:

  ```
  from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar
  cal = fetch_market_calendar()
  save_market_calendar(conn, cal)
  ```

- データ品質チェックの実行:

  ```
  from kabusys.data import quality
  issues = quality.run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- 設定の参照方法:

  ```
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

## 注意事項 / 実装上のポイント

- J-Quants API に対するリクエストはモジュール内でレート制御・リトライ・トークンリフレッシュが行われます。ただしアプリ全体での並列化（マルチプロセス／複数ホスト）を行う場合は別途レート制御が必要です。
- save_* 関数群は冪等（ON CONFLICT DO UPDATE）なので、再実行しても重複登録を防げます。
- DuckDB スキーマは外部キーやチェック制約で整合性を担保しています。既存 DB に対しては init_schema を実行しても既存テーブルは上書きされません（IF NOT EXISTS）。
- 環境変数自動読み込みはプロジェクトルートを基準に `.env` / `.env.local` を読み込みます。テスト等で無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 全ての TIMESTAMP は設計上 UTC で扱う想定です（監査スキーマ初期化時に SET TimeZone='UTC' を実行します）。

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py         # J-Quants API クライアント（取得・保存）
      - schema.py                 # DuckDB スキーマ定義・初期化
      - audit.py                  # 監査ログ（signal → order → execution）
      - quality.py                # データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

## 開発・貢献

- バグ修正や機能追加は pull request を歓迎します。
- テスト実行や CI の設定はリポジトリの慣習に従ってください（KABUSYS_DISABLE_AUTO_ENV_LOAD をテストで利用することを推奨します）。

---

この README はリポジトリ内の実装（config, data.jquants_client, data.schema, data.audit, data.quality）をもとに作成しています。実運用前に .env の設定、API トークンの管理、DB バックアップ戦略、実行ログの保守・モニタリング等を整備してください。