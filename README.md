# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。J-Quants や RSS を取り込み、DuckDB に格納・整備し、戦略層・発注層のためのデータ基盤／ユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

- J-Quants API から株価（日足 OHLCV）、財務（四半期 BS/PL）、JPX のマーケットカレンダーを取得・保存。
- RSS フィードからニュースを収集して記事・銘柄紐付けを行うニュースコレクタ。
- DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）を定義し初期化するユーティリティ。
- ETL パイプライン（差分取得、バックフィル、品質チェック）を実行するモジュール群。
- カレンダー管理、品質チェック、監査ログ（トレーサビリティ）等の補助機能を提供。

設計上のポイント:
- J-Quants のレート制限（120 req/min）に準拠する RateLimiter、リトライ／指数バックオフ、401 時の自動トークンリフレッシュ対応。
- NewsCollector は SSRF 対策、XML の安全パース（defusedxml）、最大受信サイズ制限、トラッキングパラメータ除去による冪等性確保。
- DuckDB への保存は冪等（ON CONFLICT ..）で安全に更新。

---

## 主な機能一覧

- 環境設定管理（.env 自動読み込み、必須 env チェック）
  - 自動ロード順: OS 環境 > .env.local > .env
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- J-Quants API クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - トークン管理（get_id_token）、ページネーション対応、保存用 save_* 関数（DuckDB）
- ニュース収集
  - fetch_rss（RSS 取得・前処理）、save_raw_news / save_news_symbols
  - URL 正規化・ID 生成、銘柄コード抽出（4桁コード）
- DuckDB スキーマ管理
  - init_schema(db_path)：全テーブル・インデックスを作成
  - get_connection(db_path)
- ETL パイプライン
  - run_daily_etl：カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別実行
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（夜間バッチ用）
- 監査ログ（Audit）
  - init_audit_schema / init_audit_db：監査用テーブル（signal_events, order_requests, executions 等）
- 品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks

（戦略・発注モジュールのエントリパッケージは存在しますが、具体的な戦略／取引実装は本コードには含まれていません。）

---

## 必要条件

- Python 3.10 以上（型ヒントに `X | None` などを使用しているため）
- 必要な Python パッケージ（例）
  - duckdb
  - defusedxml

プロジェクトに追加する依存は用途に応じて増えます（HTTP クライアント、Slack SDK 等）。ここに挙げたのは本リポジトリで明示的に使用されている最低限の依存です。

---

## セットアップ手順（例）

1. リポジトリをクローン／取得

   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境の作成（例: venv）

   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール

   pip install --upgrade pip
   pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

4. 環境変数の用意

   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（デフォルト）。
   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN      （J-Quants リフレッシュトークン）
   - KABU_API_PASSWORD         （kabuステーション API パスワード）
   - SLACK_BOT_TOKEN           （Slack 通知用 Bot トークン）
   - SLACK_CHANNEL_ID          （Slack 通知対象チャネル ID）

   任意／デフォルト値:
   - KABUSYS_ENV               （development / paper_trading / live、default=development）
   - LOG_LEVEL                 （DEBUG / INFO / WARNING / ERROR / CRITICAL、default=INFO）
   - KABU_API_BASE_URL         （kabuAPI のベース URL、default=http://localhost:18080/kabusapi）
   - DUCKDB_PATH               （DuckDB ファイルパス、default=data/kabusys.duckdb）
   - SQLITE_PATH               （監視用 SQLite パス、default=data/monitoring.db）

   自動ロードを無効にする場合:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマの初期化（例）

   Python REPL やスクリプトから:

   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")  # ファイルを作成してテーブルを初期化

   監査ログ専用 DB 初期化:
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主要ユースケース）

- 日次 ETL を実行する（プログラム内から）

  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- J-Quants から株価を取得して保存する（個別）

  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f"saved={saved}")

- RSS からニュースを収集して保存する

  from kabusys.data.news_collector import run_news_collection
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット（例）
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- カレンダー関連ユーティリティ

  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  from datetime import date
  print(is_trading_day(conn, date(2024,1,1)))
  print(next_trading_day(conn, date(2024,1,1)))

- 品質チェックを実行する

  from kabusys.data.quality import run_all_checks
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルトあり:
- KABUSYS_ENV (development | paper_trading | live) — default "development"
- LOG_LEVEL — default "INFO"
- KABU_API_BASE_URL — default "http://localhost:18080/kabusapi"
- DUCKDB_PATH — default "data/kabusys.duckdb"
- SQLITE_PATH — default "data/monitoring.db"

自動 .env ロード制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化

---

## ディレクトリ構成

（プロジェクト内で提供されている主な Python モジュールを示します）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理（.env 自動ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント + DuckDB 保存関数
    - news_collector.py        — RSS 取得・前処理・保存・銘柄抽出
    - pipeline.py              — ETL パイプライン（差分取得、バックフィル、品質チェック）
    - schema.py                — DuckDB スキーマ定義・初期化
    - calendar_management.py   — 市場カレンダーのロジック・夜間更新ジョブ
    - audit.py                 — 監査ログ（signal_events, order_requests, executions）
    - quality.py               — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py              — 戦略関連パッケージ（拡張ポイント）
  - execution/
    - __init__.py              — 発注・ブローカー連携パッケージ（拡張ポイント）
  - monitoring/
    - __init__.py              — 監視・メトリクス用のエントリ（拡張ポイント）

---

## 注意点 / 運用上のヒント

- J-Quants API の利用にはトークン管理が必須です。get_id_token() がリフレッシュを行うため、リフレッシュトークンを安全に管理してください。
- DB 初期化は idempotent（既存テーブルがあればスキップ）ですが、スキーマ変更時はマイグレーションの検討をしてください。
- NewsCollector は外部 URL を扱うため SSRF／巨大レスポンス等の対策を含んでいますが、運用環境でのプロキシ／認証設定に注意してください。
- ETL は各ステップを独立してエラーハンドリングします。品質チェックで重大な問題が検出された場合は運用側でどう扱うか（アラート / ロールバック / 停止）を決めてください。
- DuckDB のファイル保管場所（DUCKDB_PATH）はバックアップと永続化を考慮して設定してください。

---

## 今後の拡張案（参考）

- ブローカ連携（kabuステーション / 証券会社 API）を実装して execution 層を具現化。
- Slack 通知、メトリクス（Prometheus）連携を monitoring に追加。
- 戦略モジュールのサンプル実装と戦略バージョン管理（strategy_id）を整備。
- デプロイ用の CLI / サービス化（cron / Airflow / Prefect など）。

---

もし README の形式（より詳細なセットアップ、CI、開発者向けのコントリビュート手順、サンプル .env.example 等）を追加したい場合は、必要な項目を教えてください。