# KabuSys

日本株向けの自動売買プラットフォーム基盤ライブラリ（KabuSys）。  
データ取得・ETL、データ品質チェック、DuckDB スキーマ定義、監査ログなど、自動売買システムの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株のマーケットデータや財務データを外部 API（現状：J-Quants）から取得し、DuckDB に保存・整形するための基盤モジュール群を提供します。主な目的は以下です。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB を用いたスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新、バックフィル、先読みカレンダー）
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- 発注・監査ログ（order_request / executions 等の監査テーブル）

設計上のポイント: レート制限厳守（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ、取得時刻（fetched_at）の記録による Look-ahead Bias 管理、DuckDB への冪等保存（ON CONFLICT DO UPDATE）。

---

## 主な機能一覧

- データ取得 (kabusys.data.jquants_client)
  - fetch_daily_quotes（株価日足）
  - fetch_financial_statements（四半期財務）
  - fetch_market_calendar（JPX カレンダー）
  - トークン取得・自動リフレッシュ（get_id_token）
  - レートリミッタ / リトライロジック / ページネーション対応

- DuckDB スキーマ管理 (kabusys.data.schema)
  - init_schema / get_connection
  - Raw / Processed / Feature / Execution 層のテーブルとインデックス定義

- ETL パイプライン (kabusys.data.pipeline)
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の一括実行
  - 個別ジョブ: run_calendar_etl, run_prices_etl, run_financials_etl
  - 差分更新・バックフィル・品質チェック統合

- 品質チェック (kabusys.data.quality)
  - 欠損データ検出、スパイク検出、重複チェック、日付不整合チェック
  - QualityIssue オブジェクトで問題を集約

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - signal_events / order_requests / executions 等の監査テーブル
  - init_audit_schema / init_audit_db

- 設定管理 (kabusys.config)
  - 環境変数の自動ロード（.env / .env.local）
  - 必須環境変数の取得ラッパー（settings オブジェクト）
  - KABUSYS_ENV / LOG_LEVEL 判定とヘルパー

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 `X | Y` 型注釈を使用）
- pip が利用可能

1. リポジトリをクローン（例）:
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 開発インストール（任意）:
   ```
   pip install -e .
   ```

3. 必要な依存パッケージをインストール（最低限）:
   ```
   pip install duckdb
   ```
   ※ 実運用ではロギング、Slack 通知などの依存が追加される場合があります。requirements.txt がある場合はそれを使用してください。

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` および `.env.local` を置くと自動で読み込まれます（.env.local は .env を上書き）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu API（kabuステーション）用パスワード
     - SLACK_BOT_TOKEN: Slack ボットトークン
     - SLACK_CHANNEL_ID: 通知先チャネル ID
   - 任意/デフォルト:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

   サンプル `.env`（例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡易ガイド）

以下は Python REPL またはスクリプトから使う例です。

- DuckDB スキーマの初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  # settings.duckdb_path は環境変数 DUCKDB_PATH の値（またはデフォルト）
  conn = init_schema(settings.duckdb_path)
  ```

  - インメモリ DB を使う場合:
    ```python
    conn = init_schema(":memory:")
    ```

- 監査ログ（audit）テーブルを既存接続に追加
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  ```

- 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 個別ジョブ実行（例: 株価のみ）
  ```python
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched}, saved={saved}")
  ```

- 直接 API を使ってデータ取得（テスト用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes

  records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  print(len(records))
  ```

- 設定・ログレベル確認
  ```python
  from kabusys.config import settings
  print(settings.env, settings.log_level, settings.is_live)
  ```

注意:
- J-Quants の API レート制限（120 req/min）に合わせて内部でスロットリングが働きます。
- 401 受信時は自動で get_id_token によりトークンを更新して 1 回リトライします。
- ETL 結果は ETLResult オブジェクトで返り、品質チェック結果を含みます。

---

## よくある操作 / トラブルシューティング

- 自動で .env が読み込まれない
  - プロジェクトのルート判定は .git または pyproject.toml を基準に行います。開発環境の構成に応じて .env をプロジェクトルートに置いてください。
  - テスト等で自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Token 関連のエラー（401）
  - settings.jquants_refresh_token が正しく設定されているか確認してください。
  - get_id_token は refresh token を使って idToken を取得します。環境変数を更新したらプロセスを再起動してください（モジュール内で id token をキャッシュしています）。

- DuckDB の初期化でディレクトリエラー
  - init_schema は db_path の親ディレクトリが存在しない場合、自動で作成しますが、ファイルシステムの権限などで失敗することがあります。適切な権限を確認してください。

---

## ディレクトリ構成

リポジトリ内の主なファイル（抜粋）:

- src/kabusys/
  - __init__.py (パッケージ定義、version=0.1.0)
  - config.py (環境変数・設定管理)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント／保存ロジック)
    - schema.py (DuckDB スキーマ定義・初期化)
    - pipeline.py (ETL パイプライン)
    - quality.py (データ品質チェック)
    - audit.py (監査ログテーブルの初期化)
    - pipeline.py, audit.py, quality.py など
  - strategy/
    - __init__.py (戦略関連モジュールのためのパッケージ)
  - execution/
    - __init__.py (発注実行関連のためのパッケージ)
  - monitoring/
    - __init__.py (監視／メトリクス関連のためのパッケージ)

主要モジュールの役割:
- kabusys.config: 環境変数読み込み、自動 .env ロード、settings オブジェクト
- kabusys.data.jquants_client: API リクエスト、トークン管理、DuckDB への保存関数
- kabusys.data.schema: DB スキーマの DDL と初期化
- kabusys.data.pipeline: 差分 ETL と品質チェックの統合ロジック
- kabusys.data.quality: 各種データ品質チェック
- kabusys.data.audit: 監査ログ（発注 → 約定のトレーサビリティ）

---

## 開発上のメモ（設計上の注意）

- すべての TIMESTAMP は UTC を前提に扱う設計です（監査ログ初期化時に SET TimeZone='UTC' を実行）。
- DuckDB の INSERT は ON CONFLICT DO UPDATE による冪等性を目指しています。
- ETL は Fail-Fast とせず、各ステップの問題を収集して呼び出し元が判断できる形（ETLResult）で返します。
- J-Quants の API レート制限（120 req/min）を超えないよう固定間隔スロットリングを採用しています。

---

必要であれば、README に含めるサンプルの .env.example、requirements.txt、CI/実行例（cron / Airflow）や、戦略・発注フローのサンプルスクリプトも作成できます。どの内容を追加しますか？