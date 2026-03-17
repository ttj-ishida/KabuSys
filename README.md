# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants API や RSS フィードから市場データとニュースを取得して DuckDB に格納し、ETL・品質チェック・監査ログのための機能群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を主目的としたモジュール群です。

- J-Quants API から株価（日足）・財務データ・JPXマーケットカレンダーを取得して DuckDB に保存
- RSS フィードからニュース記事を収集し正規化して保存、銘柄コードと紐付け
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、次/前営業日取得）
- 監査ログ（シグナル→発注→約定のトレース）用スキーマ初期化
- 設定は環境変数/.env をサポートし、配布後も安全に自動読み込みする仕組み

設計上の特徴：
- API レート制御（120 req/min）およびリトライ（指数バックオフ）
- 冪等性（DuckDB への INSERT は ON CONFLICT で重複処理）
- セキュリティ配慮（RSS の SSRF 対策、defusedxml による XML 安全化）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

---

## 主な機能一覧

- data/jquants_client.py
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）

- data/news_collector.py
  - RSS フィード取得（gzip 対応、サイズ制限、SSRF/リダイレクト検査）
  - 記事正規化（URL トラッキング除去、ID は URL の SHA-256）
  - save_raw_news / save_news_symbols（DuckDB へバルク保存）

- data/schema.py
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path), get_connection(db_path)

- data/pipeline.py
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl：日次 ETL（差分取得・バックフィル・品質チェックの統合）

- data/calendar_management.py
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job（夜間バッチでカレンダー更新）

- data/quality.py
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks（品質チェック統合）

- data/audit.py
  - 監査ログ用テーブル定義と初期化（init_audit_schema / init_audit_db）

- config.py
  - .env 自動読み込み（プロジェクトルート検出）
  - Settings クラス（必須環境変数の取得、環境判定ヘルパー）
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## 前提条件（推奨）

- Python 3.9+
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS ソース）

（実プロジェクトでは requirements.txt や pyproject.toml を利用してください。）

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. 仮想環境を作成して依存をインストール
   - 例:
     python -m venv .venv
     source .venv/bin/activate
     pip install duckdb defusedxml

3. 環境変数の設定
   - プロジェクトルートに .env を置くと自動読み込みされます（優先順位: OS 環境変数 > .env.local > .env）。
   - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時等）。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - 省略時デフォルト:
     - KABUSYS_ENV=development | paper_trading | live（省略時 development）
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO

5. .env の例（プロジェクトルート）
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG

---

## 使い方（代表的な例）

以下は Python REPL やスクリプト内で使う例です。

- スキーマ初期化（DuckDB ファイルを作成してテーブルを作る）
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

  - メモリ DB:
    conn = init_schema(":memory:")

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

  主な引数:
  - target_date: date オブジェクト（省略で today）
  - id_token: 明示的に ID トークンを渡すことも可能（テスト用）
  - run_quality_checks: 品質チェックを実行するか（デフォルト True）

- 市場カレンダーのみ更新（夜間バッチ）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)

- RSS ニュース収集
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection, init_schema
  conn = init_schema("data/kabusys.duckdb")
  # known_codes は銘柄抽出に使う有効コード集合（None なら紐付けをスキップ）
  results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  print(results)  # {source_name: saved_count}

- J-Quants のトークン取得（必要なとき）
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を使用して POST

- 監査ログスキーマ初期化（監査用テーブルを追加）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)

注意:
- jquants_client は内部でレートリミッタとリトライを持ちます。fetch_* 系はページネーション対応。
- news_collector では RSS の URL が http/https 以外、もしくは最終リダイレクト先がプライベートアドレスの場合は拒否されます。

---

## 実装上のポイント / 運用メモ

- 環境変数の自動ロード:
  - config._find_project_root() が .git または pyproject.toml を探索しプロジェクトルートを特定して .env/.env.local を読み込みます。
  - テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- ETL の差分取得:
  - 株価・財務は DB 側の最終日を参照して差分のみ取得。backfill_days により直近データの再取得で API の後出し修正に対応します。

- データ品質:
  - quality モジュールで欠損・スパイク（デフォルト 50%）・重複・日付不整合を検出。run_all_checks は検出結果を返すので呼び出し側で対応を取ります。

- 冪等性:
  - raw テーブルへの挿入は ON CONFLICT（DO UPDATE/DO NOTHING）で重複を抑止。news_collector は INSERT ... RETURNING を用いて新規挿入分のみを検出します。

- セキュリティ:
  - RSS 取得は defusedxml、SSRF 対策（リダイレクト検査/プライベートIP拒否）、レスポンスサイズ制限（10MB）で安全化。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - schema.py
    - jquants_client.py
    - pipeline.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - audit.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

主要ファイル説明:
- config.py: 環境変数ロードと Settings API
- data/schema.py: DuckDB スキーマ定義と初期化
- data/jquants_client.py: J-Quants API クライアント＆保存
- data/pipeline.py: ETL パイプライン（差分取得・統合）
- data/news_collector.py: RSS 取得、前処理、DB 保存
- data/quality.py: データ品質チェック
- data/audit.py: 監査ログスキーマ

---

## よくある質問 / 備考

- Q: テスト用に .env の自動読み込みを無効にしたい
  A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Q: DuckDB をメモリで使いたい
  A: init_schema(":memory:") を使用できます。

- Q: J-Quants のレート制限やトークン期限切れはどうなる？
  A: 内部で 120 req/min の固定間隔スロットリングとリトライ（408/429/5xx）を行い、401 は自動で1回トークンリフレッシュして再試行します。

---

必要であれば README に「コマンドライン実行例」「UnitTest 実行方法」「CI 設定例」などの追加セクションを追記します。どの情報を優先して追加しますか？