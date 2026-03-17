# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（ミニマム実装）。  
J-Quants / kabuステーション 等の外部サービスからデータを取得し、DuckDB に保存・管理するための ETL、ニュース収集、カレンダー管理、品質チェック、監査ログ用スキーマなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を主目的とした内部ライブラリ群です。

- J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーを取得するクライアント
- DuckDB に対するスキーマ定義と初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と銘柄抽出（SSRF/サイズ制限など安全対策あり）
- マーケットカレンダー管理（営業日判定・前後営業日取得）
- 監査ログ（シグナル→発注→約定のトレース）用スキーマ
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

設計上の特徴:
- API レート制御（J-Quants: 120 req/min）
- リトライ（指数バックオフ、401 時はトークン自動リフレッシュ）
- DB 操作は冪等（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING を使用）
- セキュリティ対策（XML の defusedxml 利用、RSS の SSRF 防止、レスポンスサイズ制限）
- DuckDB を利用した軽量なデータプラットフォーム設計

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - トークン管理・レートリミット・リトライロジック組込み
- data.schema
  - DuckDB の全テーブル定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) で初期化
- data.pipeline
  - run_daily_etl: 日次 ETL（カレンダー→価格→財務→品質チェック）
  - 差分更新・バックフィル対応
- data.news_collector
  - fetch_rss / save_raw_news / save_news_symbols / run_news_collection
  - URL 正規化・記事ID生成（SHA-256）・銘柄抽出（4 桁）など
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチで JPX カレンダーを差分更新）
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks でまとめ実行
- data.audit
  - 監査ログ用スキーマ（signal_events, order_requests, executions）
  - init_audit_db(db_path) で専用 DB を初期化

---

## セットアップ手順

前提:
- Python 3.9+（typing 機能、型ヒントで Path | None 等を使用）
- pip が利用可能

1. リポジトリをクローン／配置し、パッケージをインストール（開発環境向け例）:

   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

   もしくは最低限の依存のみインストール:

   ```bash
   pip install duckdb defusedxml
   ```

2. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（Settings を参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID — Slack チャネル ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

   例 `.env`（簡易）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマ初期化（Python REPL やスクリプトで）:

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

4. 監査ログ用 DB 初期化（必要に応じて）:

   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主要な呼び出し例）

- 日次 ETL 実行（カレンダー・株価・財務・品質チェック）:

  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- ニュース収集ジョブの実行（RSS ソースから収集して raw_news に保存）:

  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema(settings.duckdb_path)
  known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(stats)
  ```

- カレンダー夜間更新ジョブ:

  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print("saved calendar records:", saved)
  ```

- J-Quants の単発データ取得（テストやデバッグ）:

  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  from kabusys.config import settings

  token = get_id_token()  # settings.jquants_refresh_token を使用
  recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  print(len(recs))
  ```

- 品質チェックの実行:

  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注意点:
- run_daily_etl 等は例外を捕捉・ログ化しつつ続行する設計ですが、戻り値の ETLResult に errors と quality_issues が入ります。運用側で判断してください。
- J-Quants API はレート制限とエラーハンドリング（401→自動リフレッシュ、408/429/5xx のリトライ）を実装しています。

---

## ディレクトリ構成

（省略されているファイルはパッケージ管理・メタ情報等）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理 / Settings（自動 .env ロード機能、必須変数チェック）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（フェッチ／保存／認証／レート制御）
    - news_collector.py
      - RSS 取得・記事正規化・DB 保存・銘柄抽出
    - schema.py
      - DuckDB の全 DDL 定義と init_schema / get_connection
    - pipeline.py
      - ETL（差分取得・バックフィル・品質チェック等）
    - calendar_management.py
      - マーケットカレンダー管理（判定・前後営業日・バッチ更新）
    - audit.py
      - 監査ログ（signal / order_request / executions）の DDL と初期化
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - strategy/
    - __init__.py (戦略層のエクスポート場所、実装はここに追加)
  - execution/
    - __init__.py (発注・約定周りの実装場所)
  - monitoring/
    - __init__.py (監視・メトリクス等の実装場所)

---

## 運用上の注意・設計メモ

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。CI/テスト環境で自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants のレート制限（120 req/min）を厳守するためモジュール内でスロットリングを実装しています。複数プロセスで同時に API コールを行う場合は追加で調整が必要です。
- RSS 取得では SSRF、XML Bomb、巨大レスポンスなどに対する防御を実装していますが、公開環境ではプロキシ・ネットワーク制限等の追加対策を推奨します。
- DuckDB を用いることでローカルファイルベースで高速に分析・ETL を実行できます。運用で高可用性や並列書き込みを求める場合は別途 DB 設計が必要です。
- 監査ログ（audit）スキーマはトレーサビリティを目的とし、削除を想定していません（ON DELETE RESTRICT 等）。

---

## 貢献・拡張ポイント

- strategy / execution 層に具体的なアルゴリズム（ポジション管理・リスク管理・注文送信ロジック）を実装してください。
- Slack 通知やモニタリング（Prometheus 等）、ジョブスケジューラ（Airflow / cron）との連携を追加可能です。
- テスト用の fixtures（モックされた J-Quants レスポンス、RSS フィード）を整備すると信頼性が向上します。

---

以上が KabuSys の概要と使い方です。必要であれば README にサンプル .env.example や CLI ラッパー（管理スクリプト）例も追加できます。追加したい情報があれば教えてください。