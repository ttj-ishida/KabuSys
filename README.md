# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。J-Quants API から市場データ（株価・財務・カレンダー）や RSS ニュースを取得して DuckDB に保存し、ETL・品質検査・監査ログ・カレンダー管理などの基盤機能を提供します。

---

## 概要

KabuSys は以下を目的とした Python パッケージです：

- J-Quants API を使った株価・財務・市場カレンダーの差分取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- RSS フィードからのニュース収集（SSRF 対策・XML 安全処理・トラッキングパラメータ除去）
- DuckDB を用いた三層データスキーマ（Raw / Processed / Feature）および実行／監査テーブルの管理
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- 市場カレンダー判定ユーティリティ（営業日判定・前後営業日検索）
- 監査ログ（シグナル→発注→約定のトレース）

設計上のポイント：
- API レート制限（120 req/min）を順守する RateLimiter
- ネットワーク/HTTP のリトライ（指数バックオフ、401 時はトークン自動リフレッシュ）
- DuckDB への保存は冪等（ON CONFLICT）で重複を排除
- ニュース収集は SSRF や XML BOM 対策を実装

---

## 機能一覧

主要機能（抜粋）:

- データ取得（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンから idToken を取得）
  - レート制御 / リトライ / トークン自動リフレッシュ

- データ保存（DuckDB）
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - スキーマ初期化: init_schema, init_audit_schema, init_audit_db

- ETL パイプライン（kabusys.data.pipeline）
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl（オールインワン日次 ETL + 品質チェック）

- ニュース収集（kabusys.data.news_collector）
  - fetch_rss / save_raw_news / save_news_symbols / run_news_collection
  - URL 正規化・トラッキングパラメータ除去・SSRF 対策・gzip サイズチェック

- データ品質チェック（kabusys.data.quality）
  - 欠損 / 重複 / スパイク / 日付不整合の検出
  - run_all_checks（QualityIssue のリストを返す）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチでカレンダー更新）

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルと初期化ユーティリティ

- 設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクト経由で必要な環境変数を取得

---

## 要求・依存

推奨 Python バージョン: 3.10+

主な依存パッケージ（実行に必要なもの）:
- duckdb
- defusedxml

（プロジェクトでは urllib, json, datetime, logging など標準ライブラリも使用）

pip インストール用の requirements.txt がプロジェクトにある場合はそれを利用してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-directory>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   例:
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトに requirements があれば `pip install -r requirements.txt`）

4. 環境変数の設定
   プロジェクトルートに `.env` または `.env.local` を配置すると自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動読込を無効化可能）。

   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabu API（kabuステーション等）のパスワード
   - SLACK_BOT_TOKEN       : Slack 通知用トークン
   - SLACK_CHANNEL_ID      : Slack チャネル ID

   任意/デフォルト:
   - KABUS_API_BASE_URL    : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite（monitoring）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV           : development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL             : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

5. スキーマ初期化（DuckDB）
   Python REPL もしくはスクリプトで実行：

   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ディレクトリは自動作成されます
   ```

   監査ログ用スキーマを追加する場合：

   ```python
   from kabusys.data import audit
   # 既に init_schema() で得た conn を渡す
   audit.init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（簡単な例）

- 日次 ETL を実行してデータを取得・保存・品質チェックする例：

  ```python
  from kabusys.data import pipeline, schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
  result = pipeline.run_daily_etl(conn)  # target_date 等は省略可
  print(result.to_dict())
  ```

- ニュース収集の実行：

  ```python
  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  # 既知の銘柄コードセットを渡すと自動的に紐付けを行う
  known_codes = {"7203", "6758", "9984"}  # 例
  stats = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: saved_count, ...}
  ```

- J-Quants API から株価を直接取得する（id_token は settings から自動取得される）：

  ```python
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2024, 1, 1), date_to=date(2024, 1, 31))
  ```

- カレンダー更新ジョブ（夜間バッチ）：

  ```python
  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- 品質チェックを手動で実行：

  ```python
  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i)
  ```

---

## 設計上の注意点 / ヒント

- settings は環境変数を参照します。必須変数が不足していると ValueError が送出されます。
- J-Quants の API はページネーションとレート制御が必要です。jquants_client はこれらに対応しています。
- save_* 関数は冪等（ON CONFLICT DO UPDATE / DO NOTHING）なので、再実行による二重登録を避けられます。
- ニュース収集では SSRF 対策（リダイレクト先検査、プライベート IP 拒否）、XML の安全パース、受信サイズ上限などを実装しています。
- DuckDB をファイルとして使用する場合、parent ディレクトリは自動作成されます。
- audit.init_audit_schema は接続の TimeZone を UTC に設定します（監査ログは UTC 推奨）。

---

## ディレクトリ構成

プロジェクト内の主要ファイルと簡単な説明:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定オブジェクト (settings)
    - .env 自動読み込みロジック
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得/保存/認証/リトライ/レート制御）
    - news_collector.py
      - RSS フィード取得、記事正規化、DuckDB へ保存、銘柄抽出
    - schema.py
      - DuckDB スキーマ定義（Raw / Processed / Feature / Execution）
      - init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py
      - マーケットカレンダー管理（営業日判定・夜間更新ジョブ）
    - audit.py
      - 監査ログ（signal / order_request / executions）定義と初期化
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - strategy/
    - __init__.py
    - （戦略関連モジュールを追加する場所）
  - execution/
    - __init__.py
    - （発注・ブローカー連携関連モジュールを追加する場所）
  - monitoring/
    - __init__.py
    - （監視・メトリクス関連を追加する場所）

---

## 付録：主な公開 API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path, settings.env, settings.log_level, settings.is_live, ...

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続
  - get_connection(db_path)

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, ...)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

必要であれば README に含めるサンプルスクリプト（cron / systemd 用の簡易 runner）や、CI / テスト実行方法、より詳細な環境変数の説明（.env.example のテンプレート）を追記します。追加希望があれば教えてください。