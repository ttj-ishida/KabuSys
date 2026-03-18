# KabuSys

日本株自動売買プラットフォーム向けのコアライブラリ群 (KabuSys)。  
データ収集（J-Quants / RSS）、ETLパイプライン、データ品質チェック、マーケットカレンダー管理、DuckDB スキーマ／監査ログ等を提供します。

---

## 概要

KabuSys は日本株の自動売買システムで利用するための「データ基盤」と「基礎ユーティリティ」を提供する Python モジュール群です。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー取得（レート制限・リトライ・トークン自動更新対応）
- RSS からのニュース収集と銘柄紐付け（SSRF対策・入力正規化・冪等保存）
- DuckDB によるスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー（営業日判定、前後営業日の検索）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上の特徴：
- API レート制御、指数バックオフ、トークンの自動リフレッシュなど実運用を意識した堅牢な実装
- DuckDB へ冪等に保存するための ON CONFLICT / INSERT RETURNING の活用
- セキュリティ考慮（XMLパーサの hardening、SSRF/プライベートIPブロック、応答サイズ制限）

---

## 主な機能一覧

- jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存関数 (save_daily_quotes, save_financial_statements, save_market_calendar)
  - レートリミッタ、リトライ、401 発生時のリフレッシュ処理
- data.pipeline
  - run_daily_etl: 市場カレンダー→株価→財務 → 品質チェックの一括処理
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL ジョブ
- data.schema
  - init_schema / get_connection: DuckDB のスキーマ初期化と接続取得
  - テーブルは Raw / Processed / Feature / Execution 層を網羅
- data.news_collector
  - fetch_rss / save_raw_news / save_news_symbols / run_news_collection
  - RSS の取得・正規化・トラッキングパラメータ除去・記事ID生成・銘柄抽出
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job: 夜間バッチでカレンダーを更新
- data.quality
  - 各種データ品質チェック（欠損・スパイク・重複・日付不整合）
  - run_all_checks でまとめて実行
- data.audit
  - 監査ログ（signal_events / order_requests / executions）の DDL と初期化ユーティリティ

---

## 要求環境 / 依存パッケージ

- Python 3.10 以上（型注釈で | を使用しているため）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

プロジェクトで必要なパッケージはプロジェクト側で管理してください（requirements.txt 等）。

例:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをチェックアウト
2. Python 仮想環境を作成して依存パッケージをインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -r requirements.txt
3. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を配置すると、`kabusys.config` が自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードは無効化できます）。
   - 必須項目（アプリ動作に必要）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
     - SLACK_CHANNEL_ID — Slack の通知先チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) - デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) - デフォルト: INFO
     - KABU_API_BASE_URL - デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH - デフォルト: data/kabusys.duckdb
     - SQLITE_PATH - デフォルト: data/monitoring.db

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトから init_schema を呼ぶ:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用に初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn_audit = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（代表的な例）

- ETL（日次パイプライン）を実行する例:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から株価を直接取得して保存:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  token = get_id_token()  # settings から refresh token を利用
  records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  print("saved:", saved)
  ```

- RSS ニュース収集を実行して銘柄紐付けまで行う例:
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は有効な銘柄コードの集合（例: ファイルや別テーブルから取得）
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # ソースごとの新規保存件数
  ```

- カレンダー夜間更新ジョブ:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)
  print("calendar saved:", saved)
  ```

- 品質チェックを手動で実行:
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema
  import datetime

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=datetime.date.today())
  for i in issues:
      print(i)
  ```

---

## 重要な実装上の注意点

- 自動環境変数ロード:
  - `kabusys.config` は .git または pyproject.toml を探してプロジェクトルートを特定し、そこにある `.env` / `.env.local` を自動で読み込みます（既存 OS 環境変数は保護されます）。
  - テストなどで自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB 初期化:
  - init_schema は冪等（既存テーブルはスキップ）です。初回のみ実行すれば良いです。
- J-Quants API:
  - レート制限（120 req/min）を守るために内部でスロットリングを行います。
  - 401 が返った場合はリフレッシュトークンから id_token を再取得して一度だけリトライします。
- ニュース収集:
  - RSS の XML パースには defusedxml を使用し、SSRF 対策や gzip 展開後のサイズ制限などの防御を実装しています。
- トランザクション:
  - ニュースやシンボル紐付け等はトランザクションでまとめて保存されます。失敗時はロールバックします。

---

## ディレクトリ構成

（プロジェクトルートに `src/` を置く場合の主要ファイル一覧）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得/保存）
    - news_collector.py     — RSS ニュース収集・前処理・保存
    - schema.py             — DuckDB スキーマ定義 / init_schema
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py— カレンダー管理（営業日判定・更新ジョブ）
    - quality.py            — データ品質チェック
    - audit.py              — 監査ログ（signal/order/execution）DDL と初期化
  - strategy/
    - __init__.py           — 戦略層（拡張ポイント）
  - execution/
    - __init__.py           — 発注・ブローカー連携用（拡張ポイント）
  - monitoring/
    - __init__.py           — 監視 / メトリクス（拡張ポイント）

---

## 開発・拡張のヒント

- strategy / execution / monitoring パッケージはプレースホルダとして用意されています。戦略ロジックやブローカー接続はここに実装して統合してください。
- DuckDB のスキーマは DataPlatform.md に合わせて詳細設計済みなので、feature 層や execution 層の上書きや拡張の際は既存 DDL と整合性を保ってください。
- 単体テストを行う際は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使い、必要な環境変数はテスト内で注入してください。また、DuckDB は ":memory:" を指定してインメモリでテスト可能です。

---

必要であれば README にサンプル .env.example、CI 実行手順、さらに詳細な API ドキュメント（各関数のパラメータと戻り値）を追加できます。どの情報を優先して追加しますか？