# KabuSys

日本株向け自動売買プラットフォームのライブラリ群。データ取得（J-Quants）、ETL、ニュース収集、DuckDBスキーマ定義、データ品質チェック、マーケットカレンダー管理、監査ログなど、自動売買システムのデータ基盤とトレーサビリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を備えたモジュール群です。

- J-Quants API からの市場データ（株価・財務・カレンダー）取得と DuckDB への保存（冪等）
- RSS ベースのニュース収集と記事→銘柄の紐付け
- DuckDB によるスキーマ定義（Raw / Processed / Feature / Execution 層）と初期化ユーティリティ
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- JPX カレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（シグナル→発注→約定までのトレース用スキーマ）
- データ品質チェック（欠損、スパイク、重複、日付不整合の検出）
- 環境変数設定管理（.env 自動ロード、必須設定チェック）

設計上のポイント:
- API のレート制御（J-Quants: 120 req/min）やリトライ・トークン自動更新を実装
- DuckDB への保存は ON CONFLICT を用いた冪等化
- ニュース収集は SSRF 対策、XML の安全パース、受信サイズ制限を実施
- 全てのタイムスタンプや監査ログはトレーサビリティを確保

---

## 機能一覧

- config
  - .env 自動読み込み（プロジェクトルート検出）／自動無効化フラグあり
  - 必須設定取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）
- data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レートリミッタ、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - DuckDB へ冪等保存（save_* 関数）
- data.news_collector
  - RSS 取得（gzip 対応）、XML 安全パース、URL 正規化（utm 等除去）
  - 記事ID = 正規化 URL の SHA-256 の先頭 32 文字（冪等）
  - raw_news 保存（INSERT ... RETURNING）、news_symbols 紐付け
  - SSRF / プライベート IP ブロック、レスポンスサイズ上限
- data.schema
  - Raw / Processed / Feature / Execution 層のテーブル DDL
  - init_schema(db_path) で DuckDB 初期化
- data.pipeline
  - run_daily_etl: カレンダー→株価→財務→品質チェックの一括 ETL
  - 差分更新、バックフィル（デフォルト 3 日）、calendar lookahead（デフォルト 90 日）
- data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - calendar_update_job: 夜間カレンダー差分取得ジョブ
- data.audit
  - 監査用スキーマ（signal_events / order_requests / executions）と初期化
  - init_audit_schema / init_audit_db
- data.quality
  - 欠損、スパイク、重複、日付不整合チェック
  - run_all_checks でまとめて実行

---

## 前提（依存関係）

最低限の実行には以下パッケージが必要です（プロジェクトの requirements に合わせてください）:

- Python 3.9+
- duckdb
- defusedxml

例:
pip install duckdb defusedxml

（パッケージ化されていれば pyproject / requirements を参照してインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -e .    （パッケージがセットアップ可能な場合）
   - または最低限:
     - pip install duckdb defusedxml

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動で読み込まれます
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須（主に）:
     - JQUANTS_REFRESH_TOKEN  (J-Quants のリフレッシュトークン)
     - KABU_API_PASSWORD      (kabuステーション API パスワード)
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視DB等: data/monitoring.db）

   ※ settings オブジェクト（kabusys.config.settings）から各値を取得します。未設定の必須キーは ValueError を送出します。

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで:
     from kabusys.data import schema
     conn = schema.init_schema(settings.duckdb_path)

---

## 使い方（主な API・実行例）

以下は最小限の利用例です。実際にはログ設定・例外処理を追加してください。

- DuckDB スキーマ初期化
  ```
  from kabusys.config import settings
  from kabusys.data import schema

  conn = schema.init_schema(settings.duckdb_path)
  ```

- 日次 ETL の実行
  ```
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema

  conn = schema.init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を渡すことも可
  print(result.to_dict())
  ```

  run_daily_etl は ETLResult を返します。品質チェックの結果やエラーはそこに含まれます。

- ニュース収集ジョブ
  ```
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = duckdb.connect(str(settings.duckdb_path))
  known_codes = {"7203", "6758", ...}  # 有効銘柄コードのセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  ```

- 個別 RSS フェッチ（テスト）
  ```
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"])
  ```

- 監査スキーマ初期化
  ```
  from kabusys.data import schema as data_schema
  from kabusys.data import audit

  conn = data_schema.init_schema(settings.duckdb_path)
  audit.init_audit_schema(conn, transactional=True)
  # または専用 DB: audit.init_audit_db("data/audit.duckdb")
  ```

- カレンダーバッチジョブ
  ```
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 品質チェックのみ実行
  ```
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

---

## 環境変数/設定一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

設定は kabusys.config.settings 経由で利用します。

---

## ディレクトリ構成

パッケージは src/kabusys 以下に配置されています。主なファイル:

- src/kabusys/
  - __init__.py
  - config.py               # 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py     # J-Quants API クライアント（取得 + 保存）
    - news_collector.py     # RSS ニュース収集・保存
    - schema.py             # DuckDB スキーマ定義と init_schema
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py# カレンダー管理（営業日判定/更新ジョブ）
    - audit.py              # 監査ログスキーマ / init_audit_db
    - quality.py            # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

※ strategy、execution、monitoring パッケージはプレースホルダで、別途戦略や発注実装を追加する想定です。

---

## 運用上の注意点

- J-Quants の API レート制限（120 req/min）を超えないよう設計されていますが、運用環境で他のクライアントと共有する場合は注意してください。
- .env に機密情報を置く場合はアクセス権や CI 設定に注意してください。
- DuckDB ファイルをバックアップ・管理する運用ルールを設けてください（データ破損やロールバック時の対処）。
- ニュース収集では外部 URL をダウンロードします。SSRF 対策や受信サイズ上限を実装していますが、信頼できるソース構成を推奨します。
- audit スキーマは UTC タイムゾーンを前提に動作します。

---

## 開発・貢献

- コードスタイルやテスト、CI の方針に沿ってプルリクエストを送ってください。
- 大きな設計変更やスキーマ変更は DataPlatform.md / 互換性ポリシーに従い、移行手順を明記してください。

---

ご不明点や追加したい使い方（具体的な ETL スケジュール例、戦略統合サンプルなど）があれば教えてください。README に追記します。