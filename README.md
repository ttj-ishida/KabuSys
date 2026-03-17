# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム（ライブラリ）です。J-Quants API からの市場データ取得、DuckDB によるデータ保管、ETL パイプライン、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ（発注 → 約定トレース）などを提供します。

## 主な目的
- J-Quants などの外部データソースから市場データを安定的かつ冪等に取得・保存する
- ETL パイプラインで差分取得・バックフィル・品質チェックを行う
- ニュース（RSS）を安全に収集して銘柄と紐付ける
- 発注／約定の監査ログを取り、トレーサビリティを保証する

---

## 機能一覧
- data/jquants_client
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）管理、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存（ON CONFLICT を利用）
- data/news_collector
  - RSS 取得・パース（defusedxml 使用）・前処理（URL 除去、空白正規化）
  - SSRF リダイレクト防止、受信サイズ制限、トラッキングパラメータ除去、記事IDは正規化 URL の SHA-256 の先頭 32 文字
  - raw_news / news_symbols への冪等保存（チャンク挿入・INSERT ... RETURNING）
- data/schema, data/audit
  - DuckDB スキーマ定義（Raw, Processed, Feature, Execution, Audit）
  - 監査ログ（signal_events / order_requests / executions）を UTC タイムゾーンで管理
- data/pipeline
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
- data/calendar_management
  - 営業日判定、前後営業日の算出、カレンダー夜間更新ジョブ
- config
  - 環境変数ベースの設定管理（.env, .env.local 自動ロード、プロジェクトルート探索）

---

## 要求環境 / 依存
- Python 3.10+
- 主なパッケージ
  - duckdb
  - defusedxml
- （プロジェクトを pip パッケージとして扱う場合は setup/pyproject に従ってください）

例（仮）:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを配置
2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存インストール
   - pip install duckdb defusedxml
   - 追加で必要なパッケージがあれば pyproject.toml / requirements.txt を参照してインストール
4. 環境変数の準備
   - プロジェクトルートに `.env` と（必要なら）`.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須環境変数（config.Settings で参照されるもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu API 用パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
   - オプション / デフォルト
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG / INFO / ...（デフォルト: INFO）
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）

例 .env（最小）:
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトから:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
   - 監査ログ専用 DB を別に作る場合:
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（例）

- 日次 ETL 実行（簡単なスクリプト例）
  - 目的: 市場カレンダー・株価・財務を差分取得して保存し、品質チェックまで実行する

  sample_run_etl.py:
  ```
  from datetime import date
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS 収集と保存）
  ```
  from kabusys.data import schema, news_collector
  conn = schema.init_schema("data/kabusys.duckdb")
  results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)
  ```

- 市場カレンダー夜間更新ジョブ
  ```
  from kabusys.data import schema, calendar_management
  conn = schema.init_schema("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved:", saved)
  ```

- J-Quants から ID トークンを取得（内部で自動使用されるため通常は不要）
  ```
  from kabusys.data import jquants_client as jq
  token = jq.get_id_token()  # settings.jquants_refresh_token を参照
  ```

- ロギングレベルは環境変数 LOG_LEVEL で制御できます（例: LOG_LEVEL=DEBUG）。

---

## 主要 API 概要（モジュール別）

- kabusys.config
  - settings: 環境変数を読む Settings インスタンス。settings.jquants_refresh_token などを利用。
  - 自動でプロジェクトルート（.git または pyproject.toml）を検出し `.env` / `.env.local` を読み込む。

- kabusys.data.schema
  - init_schema(db_path) → DuckDB 接続（全テーブル作成）
  - get_connection(db_path) → 既存 DB へ接続

- kabusys.data.jquants_client
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(...), save_market_calendar(...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) → 記事リスト
  - save_raw_news(conn, articles) → 新規挿入 ID リストを返す
  - save_news_symbols(conn, news_id, codes), run_news_collection(conn, ...)

- kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl(conn, target_date=None, ... ) → ETLResult

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None) → 品質問題リスト

- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - calendar_management.py
    - audit.py
    - quality.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（各ファイルは README 上で説明した責務を持ちます。strategy / execution / monitoring は今後の実装領域を想定しています。）

---

## 注意事項 / 運用上のポイント
- 環境変数は .env から自動ロードされますが、OS 環境変数が優先されます。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のレート制限（120 req/min）に合わせたレートリミッティングとリトライロジックが組み込まれています。大量データ取得時は注意してください。
- news_collector は外部 URL 取得時に SSRF 対策を行います（リダイレクト検査、プライベートアドレス拒否、最大受信バイト数制限等）。
- DuckDB の初期化は冪等（存在するテーブルは作成スキップ）です。複数プロセスでの同時初期化などは運用で注意してください。
- 監査ログは削除しない前提のスキーマ設計です。TimeZone は UTC 固定で扱います。

---

## 付記
この README はコードベースの実装内容（docstring / コメント）に基づいて作成しています。細かな実行方法・ CI / デプロイ方法・追加の依存関係はプロジェクトの pyproject.toml / requirements.txt / Makefile 等に従ってください。必要であればサンプルスクリプトや運用手順（systemd / cron / Airflow / Kubernetes での運用例）も追記します。