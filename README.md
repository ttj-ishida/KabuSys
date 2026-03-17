# KabuSys

日本株向け自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、DuckDB スキーマ管理、監査ログなどのユーティリティを提供します。

---

## 概要

KabuSys は日本株の自動売買システムを構築するための内部ライブラリ群です。主な役割は以下の通りです。

- J-Quants API からの市場データ（株価日足・財務・マーケットカレンダー）取得と DuckDB への保存
- RSS フィードからのニュース収集と銘柄紐付け
- DuckDB のスキーマ（Raw / Processed / Feature / Execution / Audit）の初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日の取得）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order → execution のトレース構造）

設計上の特徴として、API レート制限・リトライ、冪等保存（ON CONFLICT）、SSRF対策、XML安全パーサ（defusedxml）などを考慮しています。

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（トークンリフレッシュ、ページネーション、リトライ、レートリミッティング）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）

- data/news_collector.py
  - RSS 取得（SSRF対策、gzip・サイズ制限、defusedxml）
  - 記事正規化・ID生成（URL正規化 → SHA-256先頭32文字）
  - raw_news へ一括保存（INSERT ... RETURNING）
  - 銘柄コード抽出・news_symbols 保存

- data/schema.py
  - DuckDB 用 DDL（Raw / Processed / Feature / Execution テーブル）と初期化関数 init_schema()
  - インデックス作成

- data/pipeline.py
  - 日次 ETL run_daily_etl(): カレンダー → 株価 → 財務 → 品質チェック（差分・バックフィル対応）
  - run_prices_etl / run_financials_etl / run_calendar_etl

- data/calendar_management.py
  - market_calendar の更新ジョブ calendar_update_job
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day

- data/quality.py
  - 各種品質チェック（欠損、スパイク、重複、日付不整合）
  - run_all_checks()

- data/audit.py
  - 監査ログ用テーブル定義（signal_events / order_requests / executions）と初期化関数

- config.py
  - .env ファイルまたは環境変数からの設定読み込み（自動読み込み機能あり）
  - 必須環境変数チェック・ユーティリティ（settings オブジェクト）

---

## 前提 / 必要条件

- Python 3.10+
- 依存ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS ソース等）

実際のプロジェクトでは pyproject.toml / requirements.txt に依存関係を明記してください。

---

## 環境変数 (主なもの)

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注機能を使う場合）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（通知実装を利用する場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" に設定すると .env の自動ロードを無効化

注意: config.Settings は必須環境変数が未設定の場合に ValueError を送出します。

---

## セットアップ手順

1. Python と依存ライブラリをインストール
   - 例（pip）:
     pip install duckdb defusedxml

   - 開発時は editable install:
     pip install -e .

2. プロジェクトルートに .env を配置（あるいは環境変数を設定）
   - 必要なキー（上記参照）を設定してください。
   - 自動ロードの仕組み:
     - プロジェクトルートは .git または pyproject.toml を基準に検出されます。
     - OS 環境変数 > .env.local > .env の順で読み込まれます。
     - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット。

3. DuckDB スキーマ初期化
   - Python REPL やスクリプトで:
     from kabusys.config import settings
     from kabusys.data import schema
     conn = schema.init_schema(settings.duckdb_path)

4. 監査DB（必要なら）
   - audit.init_audit_db() を使って監査専用 DB を初期化できます:
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/audit.duckdb")

---

## 使い方（簡易例）

- 日次 ETL（市場カレンダー・株価・財務の差分取得 + 品質チェック）:

  from datetime import date
  from kabusys.config import settings
  from kabusys.data import schema, pipeline

  # DB 初期化（既に初期化済みなら接続のみ）
  conn = schema.init_schema(settings.duckdb_path)

  # ETL を実行（引数で日付やバックフィル日数を調整可能）
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- RSS ニュース収集と銘柄紐付け:

  from kabusys.config import settings
  from kabusys.data import schema, news_collector
  import duckdb

  conn = schema.get_connection(settings.duckdb_path)  # schema.init_schema() を事前に実行しておく
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット

  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)

- J-Quants の ID トークン取得（必要に応じて）:

  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用

- DuckDB の接続取得:
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")

---

## 実装上の注意 / 設計メモ

- API レート制限: J-Quants は 120 req/min を想定。jquants_client は内部でスロットリングを実装しています。
- リトライ: ネットワークエラーや 408/429/5xx に対する指数バックオフとリトライを実装。
- トークン管理: 401 受信時には設定の refresh token で自動リフレッシュを試みます（1 回のみ）。
- 冪等性: DuckDB への保存は ON CONFLICT（DO UPDATE / DO NOTHING）で冪等。
- セキュリティ: RSS 取得は defusedxml を使用、SSRF 対策としてリダイレクト先やホストのプライベート IP 判定を行います。
- 日付の扱い: すべての監査 TIMESTAMP は UTC を前提に管理されます（audit.init_audit_schema は TimeZone='UTC' を設定）。

---

## ディレクトリ構成

（主なファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント（取得・保存）
    - news_collector.py         # RSS 取得・記事整形・保存・銘柄抽出
    - schema.py                 # DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py               # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    # マーケットカレンダー管理・夜間更新ジョブ
    - audit.py                  # 監査ログスキーマ（signal/events/order/execution）
    - quality.py                # データ品質チェック
  - strategy/
    - __init__.py               # 戦略関連（拡張用）
  - execution/
    - __init__.py               # 発注周り（拡張用）
  - monitoring/
    - __init__.py               # 監視関連（拡張用）

---

## 例: よくあるコマンド／ワークフロー

- 初期セットアップ
  1. .env を作成して必要な環境変数を設定
  2. python スクリプトで schema.init_schema() を呼ぶ
  3. （必要なら）audit.init_audit_db() を呼ぶ

- 毎朝のジョブ（または cron）
  - calendar_update_job（カレンダー更新）
  - run_daily_etl（データ差分取得 + 品質チェック）
  - news_collector.run_news_collection（ニュース収集）

---

## ライセンス / 貢献

この README はコードベースに基づく説明書きです。実際のライセンスや貢献方法はプロジェクトのルートにある LICENSE / CONTRIBUTING ファイルを参照してください（なければリポジトリ管理者に確認してください）。

---

追加説明や、特定機能（例: 発注連携、Slack 通知、運用監視）の README 追記を希望する場合は、使い方や期待する運用フローを教えてください。