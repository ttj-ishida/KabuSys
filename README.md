# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。J-Quants API から市場データを取得して DuckDB に保存し、データ品質チェック、ニュース収集、監査ログ（発注～約定トレース）など ETL・運用に必要な共通処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を主に提供します。

- J-Quants API から株価（日足）、財務データ、JPX マーケットカレンダーを安全に取得するクライアント（レート制御・リトライ・トークン自動更新対応）。
- 取得データを DuckDB に冪等的に保存するスキーマ・ユーティリティ。
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）。
- RSS からのニュース収集・前処理・銘柄コード抽出および DuckDB への保存。
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化。
- 環境変数管理（.env 自動ロード・保護）と設定ラッパー。

設計方針は「冪等性」「Look-ahead バイアス防止（fetched_at の記録）」「ネットワーク安全（SSRF 対策等）」「ロバストなエラーハンドリング」です。

---

## 主な機能一覧

- jquants_client
  - get_id_token（リフレッシュトークンから idToken を取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - レート制限（120 req/min）、指数バックオフリトライ、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）

- data.schema
  - DuckDB 用テーブル定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) でスキーマを冪等的に初期化

- data.pipeline
  - 差分 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 日次 ETL の統合エントリ run_daily_etl（品質チェックを含む）
  - 差分・バックフィル・営業日調整等のロジックを内蔵

- data.news_collector
  - RSS 取得（fetch_rss）と前処理（URL除去・空白正規化）
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等保存
  - SSRF / gzip bomb / XML攻撃対策（defusedxml, サイズ制限, リダイレクト検査）
  - save_raw_news / save_news_symbols（DuckDB へ保存、INSERT RETURNING を使用）

- data.quality
  - 欠損データ・スパイク（急騰・急落）・重複・日付不整合の検出
  - run_all_checks でまとめて実行し QualityIssue リストを返す

- data.calendar_management / data.audit
  - カレンダー管理（営業日判定、next/prev_trading_day、夜間更新ジョブ）
  - 監査ログ向けスキーマ初期化（init_audit_schema / init_audit_db）

- config
  - .env（および .env.local）自動読み込み（プロジェクトルート検出）
  - 必須変数チェックヘルパー settings

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン／配置

2. Python 環境を用意（推奨: venv / pyenv）

3. 依存パッケージをインストール
   - 本コードで使われている主要パッケージ例:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   ※ requirements.txt がある場合はそれを利用してください。

4. 環境変数 / .env を用意
   - プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）に `.env` として配置すると自動読み込みされます。
   - 読み込み優先順位: OS 環境 > .env.local > .env
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必須環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN: Slack 通知用（必要な場合）
   - SLACK_CHANNEL_ID: Slack チャネル ID

   オプション:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（monitoring 用、デフォルト data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   KABU_API_PASSWORD=yyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベース初期化
   - Python REPL またはスクリプト内で:
     ```
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
   - メモリ DB を使う場合: init_schema(":memory:")

---

## 使い方（主要な使用例）

- DuckDB スキーマ初期化
  ```
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
  ```
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 個別 ETL（株価のみ）
  ```
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- J-Quants 直接呼び出し（テスト等）
  ```
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))
  ```

- ニュース収集ジョブ
  ```
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  # conn は init_schema で取得した DuckDB 接続
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)  # {source_name: saved_count}
  ```

- 監査ログ（オーディット）スキーマ初期化
  ```
  from kabusys.data.audit import init_audit_db, init_audit_schema
  # 既存 conn に追加する場合:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  # 専用 DB を作る場合:
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

---

## 主要設計・実装上の注意点

- 環境変数自動ロード
  - パッケージがインポートされると、.env / .env.local をプロジェクトルートから自動的に読み込みます。OS 環境変数は上書きされません（.env.local は .env を上書き）。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- J-Quants クライアント
  - レート制限は固定間隔スロットリング（120 req/min）で実施。
  - リトライは指数バックオフ（最大3回）。HTTP 408/429/5xx を対象。
  - 401 を受けた場合は refresh token で id_token を再取得して 1 回だけ再試行。

- ニュース収集の安全対策
  - defusedxml を使った XML パース、受信サイズ制限、リダイレクト先のスキームとプライベートIP検査（SSRF対策）を実装済み。
  - 記事 ID は正規化 URL の SHA-256 の先頭32文字で生成し、冪等性を担保。

- DuckDB スキーマ
  - Raw / Processed / Feature / Execution 層を分離。DDL は冪等（CREATE IF NOT EXISTS）。
  - 多数の CHECK 制約・インデックスを定義してデータ整合性と検索性能を確保。
  - ON CONFLICT ... DO UPDATE / DO NOTHING を利用し、ETL を安全に再実行可能。

- 品質チェック
  - fail-fast せず、複数の問題を収集して呼び出し元に返します。重大度（error/warning）に応じて呼び出し元で判断してください。

---

## ディレクトリ構成

（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得・保存）
    - news_collector.py      -- RSS ニュース収集・前処理・保存
    - schema.py              -- DuckDB スキーマ定義・初期化
    - pipeline.py            -- ETL パイプライン（差分取得・統合 run_daily_etl）
    - calendar_management.py -- 市場カレンダー運用ユーティリティ
    - audit.py               -- 監査ログスキーマ（発注～約定のトレーサビリティ）
    - quality.py             -- データ品質チェック
  - strategy/
    - __init__.py            -- 戦略層（拡張ポイント）
  - execution/
    - __init__.py            -- 発注 / ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py            -- 監視 / メトリクス（拡張ポイント）

---

## 拡張・運用のヒント

- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして環境読み込みを抑制し、明示的に設定を注入してください。
- ETL を定期実行するには run_daily_etl を cron / Airflow / Prefect 等から呼び出してください。run_daily_etl は個々のステップを独立してエラーハンドリングするため、部分的な失敗でも可能な限り処理を継続します。
- 監査ログ（audit）スキーマはトレーサビリティを目的としているため、削除や上書きは行わない運用が推奨されます。
- ニュースの銘柄紐付けには known_codes（有効銘柄リスト）を与えることで精度を向上できます。銘柄リストは別 ETL や証券会社提供のマスターから用意してください。

---

必要があれば README に「インストール済みパッケージの具体的バージョン」「より詳細なコード例」「運用手順（cron / systemd / docker）」などを追記します。どの情報を追加しますか？