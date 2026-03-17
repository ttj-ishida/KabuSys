# KabuSys

日本株自動売買プラットフォームのコアライブラリ（モジュール群）です。  
データ取得・ETL・スキーマ管理・品質チェック・ニュース収集・監査ログなど、自動売買システムに必要な基盤機能を提供します。

---

目次
- プロジェクト概要
- 機能一覧
- 動作環境 / 依存関係
- セットアップ手順
- 使い方（簡単な例）
- 環境変数（主要設定）
- ディレクトリ構成
- 開発時のヒント

---

## プロジェクト概要

KabuSys は日本株（JPX）の自動売買に必要なデータ基盤とユーティリティを集めたライブラリです。主に以下を目的としています：

- J-Quants API からの市場データ（株価日足・財務・カレンダー）取得
- RSS を用いたニュース収集と銘柄紐付け
- DuckDB を用いたデータスキーマ管理・永続化
- ETL（差分取得・バックフィル）パイプライン
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレース）
- 市場カレンダーの判定ユーティリティ（営業日判定・次/前営業日取得 等）

設計上の留意点：API レート制御、冪等性（ON CONFLICT）、Look-ahead bias を避けるための fetched_at 記録、SSRF 対策、XML の安全なパースなどを考慮しています。

---

## 機能一覧

主なモジュールと提供機能：

- kabusys.config
  - .env 自動読み込み（プロジェクトルート基準）
  - 環境変数ラッパ（settings オブジェクト）
- kabusys.data.jquants_client
  - J-Quants API クライアント（認証、ページネーション、リトライ、レートリミット）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
- kabusys.data.news_collector
  - RSS フィード取得、記事の正規化・前処理
  - raw_news への冪等保存（INSERT ... RETURNING）
  - 銘柄コード抽出・news_symbols 保存
  - SSRF / Gzip-bomb / XML Bomb対策済み
- kabusys.data.schema
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit 用テーブル）
  - init_schema / get_connection
- kabusys.data.pipeline
  - 日次 ETL（run_daily_etl）
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 差分取得・バックフィル・品質チェックの統合
- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（夜間バッチ用）
- kabusys.data.audit
  - 監査ログテーブルの初期化（init_audit_schema / init_audit_db）
  - トレーサビリティ用 DDL（signal_events, order_requests, executions）
- kabusys.data.quality
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - run_all_checks による一括実行
- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - （パッケージの雛形あり。戦略・発注・監視ロジックはここに実装）

---

## 動作環境 / 依存関係

- Python 3.10+（typing の Union などの記述を前提）
- 主な Python パッケージ
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, datetime, logging, hashlib, ipaddress, socket など）

依存パッケージはプロジェクトの requirements.txt / pyproject.toml に明示してください（本コードでは仮定）。

---

## セットアップ手順

1. リポジトリをクローン

   git clone <repository-url>
   cd <repository-root>

2. 仮想環境を作成して有効化（例: venv）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install -U pip
   pip install duckdb defusedxml
   # またはプロジェクトで pyproject.toml / requirements.txt がある場合:
   # pip install -e .[dev] など

4. 環境変数の設定

   - プロジェクトルートに `.env` または `.env.local` を作成することで自動読み込みされます。
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

   主要な環境変数（詳細は下記参照）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID
   - DUCKDB_PATH（例: data/kabusys.duckdb）
   - SQLITE_PATH（例: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live）
   - LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL）

5. DuckDB スキーマ初期化（最初に1回）

   Python REPL やスクリプトで:

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可

   監査ログ専用 DB を初期化する場合:

   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/audit.duckdb")

---

## 使い方（簡単な例）

以下は代表的な使い方の抜粋です。実運用ではログ設定や例外処理、監査記録等を追加してください。

- J-Quants の ID トークン取得

  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用して取得

- 日次 ETL 実行

  from datetime import date
  from kabusys.data import schema, pipeline
  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 個別に株価 ETL 実行

  from datetime import date, timedelta
  fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())

- ニュース収集ジョブ（RSS）

  from kabusys.data.news_collector import run_news_collection
  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # あらかじめ用意した銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- カレンダー夜間更新ジョブ

  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved {saved} records")

- 品質チェック（ETL 後）

  from kabusys.data import quality
  issues = quality.run_all_checks(conn, target_date=None)
  for issue in issues:
      print(issue.check_name, issue.severity, issue.detail)

- 環境設定オブジェクト利用

  from kabusys.config import settings
  print(settings.duckdb_path, settings.is_live)

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token の元になります。

- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード（発注系で使用）。

- KABU_API_BASE_URL
  - kabuAPI のベースURL（デフォルト: http://localhost:18080/kabusapi）。

- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
  - Slack 通知に使用するトークン / チャンネル ID。

- DUCKDB_PATH
  - DuckDB ファイルの保存先（デフォルト: data/kabusys.duckdb）。

- SQLITE_PATH
  - 監視用 SQLite のパス（デフォルト: data/monitoring.db）。

- KABUSYS_ENV
  - 実行環境。development / paper_trading / live のいずれか。(settings.env で検証)

- LOG_LEVEL
  - ログ出力レベル（DEBUG/INFO/...）。

注意: Settings 内の必須項目はアクセス時に例外を投げます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動 .env ロードを抑止し、個別に os.environ を設定してください。

---

## ディレクトリ構成

主要ファイル・モジュールの構成（抜粋）:

src/kabusys/
- __init__.py
- config.py
- execution/
  - __init__.py
- strategy/
  - __init__.py
- monitoring/
  - __init__.py
- data/
  - __init__.py
  - jquants_client.py       # J-Quants API クライアント + DuckDB 保存
  - news_collector.py       # RSS 収集・前処理・DB 保存
  - schema.py               # DuckDB スキーマ定義 / 初期化
  - pipeline.py             # 日次 ETL パイプライン
  - calendar_management.py  # 市場カレンダー管理・営業日判定
  - audit.py                # 監査ログテーブル定義 / 初期化
  - quality.py              # データ品質チェック

README には上記の主要機能を中心に記載しています。strategy / execution / monitoring は拡張ポイント（ユーザー独自の戦略や発注ロジックを実装）です。

---

## 開発時のヒント

- DB 初期化は一度だけ行うのが基本（init_schema）。開発中は ":memory:" を使うとテストが楽です。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI 等で不要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector は外部ネットワークアクセスを行うため、ユニットテスト時は _urlopen をモックするか、ネットワークアクセスを切る設定を行ってください。
- J-Quants API 呼び出しはレートリミット（120 req/min）やリトライロジックが組み込まれていますが、長時間・大量データ取得時は注意してください。
- DuckDB の SQL 実行ではプレースホルダ ("?") を使っているため SQL インジェクションのリスクを低減しています。ただし動的DDL等の挿入には注意してください。
- 監査ログは UTC での TIMESTAMP 保存を前提にしています（init_audit_schema は TimeZone を UTC に設定します）。

---

以上です。README の内容はコードベースの現状に合わせて簡潔にまとめています。必要であれば、具体的な .env.example、requirements.txt、CI ワークフロー、サンプルスクリプト（バッチや cron 用）なども追加で作成します。どの部分を詳しく補足しますか？