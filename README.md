# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリ群です。  
データ収集（J-Quants / RSS）、ETL パイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした内部ライブラリ群です。

- J-Quants API から株価・財務・カレンダーを安全に取得して DuckDB に保存する
- RSS フィードからニュースを収集して記事・銘柄紐付けを行う
- 日次 ETL（差分取得、バックフィル、品質チェック）を実行する
- JPX マーケットカレンダーを管理し、営業日の判定や前後営業日の取得を提供する
- 発注〜約定の監査ログ（トレーサビリティ）スキーマを提供する

設計上の注目点:
- API レート制御・リトライ・トークン自動リフレッシュ
- Look-ahead バイアス防止のため取得時刻（UTC）を保存
- DuckDB を用いた冪等な保存（ON CONFLICT / INSERT ... RETURNING）
- SSRF / XML Bomb / 大容量レスポンス対策を施した RSS 取得

---

## 主な機能一覧

- データ取得（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得
  - レートリミット管理、指数バックオフリトライ、401 の自動トークン更新
  - DuckDB への冪等保存関数（save_daily_quotes 等）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの安全な取得（SSRF 回避、gzip サイズ制限、defusedxml）
  - URL 正規化・トラッキングパラメータ除去・SHA256 による記事ID生成
  - raw_news / news_symbols への安全な一括保存（トランザクション、チャンク）

- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層をカバーする DDL
  - 初期化関数 init_schema / get_connection

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新、バックフィル、カレンダー先読み
  - run_daily_etl: 日次 ETL の統合エントリポイント
  - 品質チェック実行（kabusys.data.quality と連携）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job による夜間差分更新

- 品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク、重複、日付不整合の検出
  - QualityIssue で問題を集約

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル初期化
  - 発注フローを UUID 連鎖でトレース可能に

---

## 前提 / 依存関係

- Python 3.10 以上（型ヒントの union 表記等を利用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml

プロジェクトルートに requirements.txt がある場合はそれを使用してください。ここでは最小限の例:

pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install -r requirements.txt
   - または最低限:
     - pip install duckdb defusedxml

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（コード中で _require により必須化されているもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意:
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - LOG_LEVEL (DEBUG / INFO / ...)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DB スキーマ初期化（DuckDB）
   - Python REPL やスクリプトから:
     ```
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```
   - インメモリで試す:
     ```
     conn = init_schema(":memory:")
     ```

6. 監査ログテーブルの初期化（任意）
   ```
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（主要な例）

- 日次 ETL の実行（最も基本的な利用例）
  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を渡すことも可
  print(result.to_dict())
  ```

- 手動で株価を取得して保存
  ```
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  token = get_id_token()  # リフレッシュトークンから id_token を取得
  recs = fetch_daily_quotes(id_token=token, date_from=some_date, date_to=some_date)
  saved = save_daily_quotes(conn, recs)
  ```

- RSS ニュース収集
  ```
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes が与えられれば銘柄抽出と news_symbols への保存も行う
  result = run_news_collection(conn, known_codes={"7203", "6758"})
  print(result)  # {source_name: saved_count, ...}
  ```

- カレンダー更新（夜間ジョブ）
  ```
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved {saved} records")
  ```

- 品質チェックを個別に実行
  ```
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- 監査スキーマの初期化（別 DB で分離する場合）
  ```
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

---

## 主要 API（概要）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.duckdb_path, settings.env, settings.log_level など

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(...)
  - save_market_calendar(...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles) -> list of inserted ids
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)
  - extract_stock_codes(text, known_codes)

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB connection (DDL 実行)
  - get_connection(db_path) -> DuckDB connection

- kabusys.data.pipeline
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(...)

- kabusys.data.calendar_management
  - is_trading_day(conn, date)
  - next_trading_day(conn, date)
  - prev_trading_day(conn, date)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - QualityIssue dataclass を返す

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## 注意点 / 実運用でのヒント

- 環境変数自動読み込み:
  - プロジェクトルート（.git または pyproject.toml が見つかる）を基準に `.env` と `.env.local` を自動でロードします。
  - OS 環境変数が優先され、.env.local は .env を上書きします（ただし既存の OS 環境変数は保護されます）。
  - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- J-Quants API:
  - レート制限 120 req/min を厳守するため内部で RateLimiter を利用しています。
  - HTTP 408/429/5xx に対するリトライと、401 の場合はリフレッシュトークンで id_token を再取得して 1 回リトライする挙動があります。

- ニュース収集:
  - 最大受信サイズは 10MB に制限してあり、gzip 展開後も同様のチェックが入ります。
  - リダイレクト先のホストがプライベート IP の場合はブロックされます（SSRF 対策）。

- DuckDB:
  - 初回は init_schema() を実行して必須テーブルとインデックスを作成してください。
  - 大量挿入はチャンク（news_collector）で処理しておりトランザクションでラップされます。

- ロギング:
  - 標準の logging モジュールを利用しています。環境変数 `LOG_LEVEL` でレベルを調整してください。

---

## 開発者向けディレクトリ構成

（省略可能なファイルは簡略化しています）

src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      schema.py
      pipeline.py
      calendar_management.py
      audit.py
      quality.py
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py

主なソースファイル:
- src/kabusys/config.py — 環境変数 / 設定管理
- src/kabusys/data/jquants_client.py — J-Quants API クライアント & DuckDB 保存
- src/kabusys/data/news_collector.py — RSS 収集・前処理・保存
- src/kabusys/data/schema.py — DuckDB スキーマ定義と初期化
- src/kabusys/data/pipeline.py — ETL パイプライン
- src/kabusys/data/calendar_management.py — カレンダー管理
- src/kabusys/data/audit.py — 監査ログスキーマ
- src/kabusys/data/quality.py — データ品質チェック

---

必要であれば、README に CI / デプロイ手順、サンプル cron ジョブ、Slack 通知の実装例（slack_bot_token を使った通知ラッパー）などを追記します。どの部分を詳しく書くか指示をください。