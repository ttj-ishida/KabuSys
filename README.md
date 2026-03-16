# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。  
データ収集（J-Quants）、DuckDB スキーマ定義、監査ログ、データ品質チェックなど、トレーディングプラットフォームの基盤機能を提供します。

---

## 概要

KabuSys は以下を主目的とした内部ライブラリです。

- J-Quants API からの市場データ取得（株価日足、財務情報、マーケットカレンダー）
- DuckDB を用いた永続化とスキーマ管理（Raw / Processed / Feature / Execution 層）
- 発注〜約定に至る監査ログ（トレーサビリティ）
- データ品質チェック（欠損、スパイク、重複、日付不整合など）
- 環境変数 / .env の取り扱いと集中設定管理

設計上のポイント：
- API レート制限（120 req/min）を守るためのスロットリングとリトライ実装
- トークンの自動リフレッシュ（401 に対して 1 回のみリフレッシュして再試行）
- DuckDB への INSERT を冪等（ON CONFLICT DO UPDATE）にして重複を排除
- すべてのタイムスタンプは UTC を前提に保存・監査

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須環境変数チェック
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

- J-Quants クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レートリミット制御、リトライ、トークン管理
  - DuckDB への保存ユーティリティ（save_* 関数群）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層の DDL を定義
  - インデックス／外部キーを考慮した初期化 API（init_schema/get_connection）

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブルとインデックス定義
  - 監査スキーマの初期化（init_audit_schema / init_audit_db）

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合チェック
  - QualityIssue オブジェクトのリストで結果を返す（収集型）

---

## 要件

- Python 3.10 以上（PEP 604 の型記法（|）を使用）
- 主要依存: duckdb（その他は標準ライブラリで実装されています）
  - インストール例: pip install duckdb

（プロジェクトで使用するパッケージ群が別途ある場合は requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローンし、必要なパッケージをインストールします。

   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .  # 開発インストール（セットアップファイルがある場合）
   pip install duckdb
   ```

2. 環境変数を設定します。プロジェクトルートに `.env` として置くか、OS 環境変数で設定してください。自動読み込みは .git または pyproject.toml を起点にプロジェクトルートを探索します。

   重要な環境変数（最低限必要なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   任意 / 便利な設定
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化（テスト時に便利）

   .env のサンプル（例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   KABU_API_PASSWORD=pass
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（基本例）

以下は最低限の典型的な利用フロー例です。

- DuckDB スキーマを初期化して接続を得る

  ```python
  from kabusys.config import settings
  from kabusys.data import schema

  conn = schema.init_schema(settings.duckdb_path)
  ```

- J-Quants から日足を取得して DuckDB に保存する

  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
  saved = save_daily_quotes(conn, records)
  print(f"{saved} 件保存されました")
  ```

  仕様上のポイント：
  - fetch_* はページネーション対応
  - モジュールは内部でトークンキャッシュを保持し、必要時に get_id_token() で自動リフレッシュします
  - リクエストは秒間レートを満たすように待機し、リトライ（最大 3 回）を行います

- 財務データ・マーケットカレンダーの取得保存も同様

  ```python
  from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
  fin = fetch_financial_statements(code="7203")
  save_financial_statements(conn, fin)
  ```

  ```python
  from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar
  cal = fetch_market_calendar()
  save_market_calendar(conn, cal)
  ```

- 監査ログ（audit）をスキーマに追加する

  既存の DuckDB 接続に監査テーブルを追加する：

  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  ```

  または監査専用 DB を初期化する：

  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- データ品質チェックを実行する

  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

  - 各チェックは QualityIssue のリストで返るため、呼び出し元で重大度に応じた処理（ETL 停止、Slack 通知等）を行ってください。

---

## 主要 API と注意点

- 環境設定
  - settings はプロパティアクセスで各種設定を取得します（例: settings.jquants_refresh_token）。
  - 必須変数が未設定だと ValueError を投げます。

- jquants_client
  - _MIN_INTERVAL_SEC = 60.0 / 120 に基づく固定間隔のスロットリング実装
  - _MAX_RETRIES = 3、指数バックオフ（base=2.0）を採用
  - 401 発生時は get_id_token を使って一度だけトークンリフレッシュを行い再試行
  - save_* 関数は ON CONFLICT DO UPDATE によって冪等に保存します

- schema
  - init_schema(db_path) はテーブルとインデックスをすべて作成（冪等）
  - get_connection は既存 DB への単純接続（初回は init_schema を呼ぶこと）

- audit
  - init_audit_schema は接続に対して監査用テーブルを追加
  - すべての TIMESTAMP は UTC で扱います（init_audit_schema 内で SET TimeZone='UTC' を実行）

- quality
  - run_all_checks は fail-fast ではなく全チェック結果を返す設計
  - スパイク閾値や参照日を引数で変更可能

---

## ディレクトリ構成

（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（取得・保存）
      - schema.py              # DuckDB スキーマ定義・初期化
      - audit.py               # 監査ログ（トレーサビリティ）
      - quality.py             # データ品質チェック
      - (その他のデータ関連モジュール)
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主要テーブル（schema.py に定義）
- Raw: raw_prices, raw_financials, raw_news, raw_executions
- Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature: features, ai_scores
- Execution: signals, signal_queue, orders, trades, positions, portfolio_targets, portfolio_performance

監査テーブル（audit.py）
- signal_events, order_requests, executions

---

## 開発・運用上のメモ

- .env 自動読み込みはプロジェクトルートを .git / pyproject.toml で検出します。テストで自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のファイルパスの親ディレクトリがなければ自動作成されます。
- API のリトライ・レート制御はサーバー側のレート制限に依存するため、運用環境ではログとメトリクスを監視してください。
- 監査ログは基本的に削除しない前提です（ON DELETE RESTRICT）。誤ってデータを消さない運用を推奨します。

---

必要があれば、README に含める具体的なコマンド、CI 設定、テストの実行方法、または各関数のサンプル出力例などを追記します。どの項目を詳しく書きますか？