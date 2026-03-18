# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
J-Quants API などから市場データ・財務データ・ニュースを取得し、DuckDB に蓄積・品質チェック・監査ログ管理・ETL を行うためのモジュールを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・カレンダーデータの取得（レートリミット・リトライ・トークン自動更新対応）
- RSS からのニュース収集（正規化、SSRF 対策、トラッキングパラメータ除去）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution / Audit）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日の検索、夜間カレンダー更新ジョブ）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計上の留意点: レート制御、指数バックオフのリトライ、Idempotent な DB 操作（ON CONFLICT）、SSRF 対策、UTC ベースのタイムスタンプなど。

---

## 主な機能一覧

- 環境・設定管理
  - .env 自動読み込み（プロジェクトルート: `.git` または `pyproject.toml` を基準）
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN など）
- J-Quants クライアント (`kabusys.data.jquants_client`)
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レートリミット（120 req/min）、リトライ（最大 3 回）、401 時のトークン自動リフレッシュ
  - DuckDB へ冪等的保存（save_* 系）
- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィード取得（gzip 対応）、XML の安全パース（defusedxml）
  - URL 正規化・トラッキングパラメータ除去、記事 ID の SHA-256 ハッシュ
  - SSRF 対策（スキーム検証、プライベート IP 検査、リダイレクト検査）
  - raw_news / news_symbols への冪等保存
- データスキーマ管理 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution / Audit 層のテーブル作成
  - init_schema / get_connection
- ETL パイプライン (`kabusys.data.pipeline`)
  - run_daily_etl: カレンダー→株価→財務→品質チェックの統合実行
  - 差分更新・バックフィル対応
- カレンダー管理 (`kabusys.data.calendar_management`)
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job（夜間バッチ）
- 監査ログ (`kabusys.data.audit`)
  - signal_events, order_requests, executions など監査テーブルの初期化
  - init_audit_schema / init_audit_db
- 品質チェック (`kabusys.data.quality`)
  - 欠損・スパイク・重複・日付不整合の検出
  - run_all_checks でまとめて実行

---

## 必要条件

- Python 3.10 以上（型記法に union operator `|` を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml
- その他標準ライブラリ（urllib, json, hashlib, ipaddress, socket, logging 等）

※プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください。

---

## セットアップ手順

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb defusedxml

   （ローカルのパッケージ管理方法に合わせてください。プロジェクト配布に pyproject.toml がある場合は pip install -e .）

3. データベース初期化（DuckDB）
   - Python REPL またはスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - 監査ログ用 DB を別に作る場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

4. 環境変数（.env）を準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: 通知先チャンネル ID

オプション（デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env 読み込みを無効化

例 (.env)
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## 使い方（基本例）

- 設定読み取り
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)

- DB 初期化
  from kabusys.data.schema import init_schema
  conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行（最小例）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- 個別 ETL
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  run_calendar_etl(conn, date.today())
  run_prices_etl(conn, date.today())
  run_financials_etl(conn, date.today())

- ニュース収集
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758"}  # 例: 有効銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- カレンダー夜間更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved calendar rows: {saved}")

- 監査スキーマ初期化（既存接続へ追加）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- 品質チェック（単体）
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i)

注意:
- J-Quants へのリクエストは 120 req/min に制限されています。jquants_client は内部でレート制御・リトライを行いますが、アプリケーション側でも過剰なリクエストを避けてください。
- run_daily_etl は各ステップで例外を捕捉してログに残し、可能な限り処理を継続します。戻り値の ETLResult を確認してエラー・品質問題の有無を判断してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

src/
  kabusys/
    __init__.py
    config.py                      # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py            # J-Quants API クライアント + 保存ロジック
      news_collector.py            # RSS ニュース収集・保存
      schema.py                    # DuckDB スキーマ定義・初期化
      pipeline.py                  # ETL パイプライン実装
      calendar_management.py       # マーケットカレンダー管理
      audit.py                     # 監査ログスキーマ初期化
      quality.py                   # データ品質チェック
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py

README.md（本ファイル）

---

## 開発・テストのヒント

- 自動 .env 読み込みをテストから無効化する:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- network / HTTP 呼び出しはモックしやすいように設計されています（例: news_collector._urlopen を差し替え可能）。
- DuckDB の ":memory:" を使えばインメモリ DB で単体テストが容易です:
  conn = init_schema(":memory:")

---

## セキュリティ注意事項

- .env に機密情報（トークンやパスワード）を含める際は Git 管理下に置かないでください（`.env.local` を .gitignore に追加する等）。
- news_collector は SSRF 対策、XML Bomb 対策（defusedxml）、受信サイズ制限を実装していますが、外部 URL を扱う際は常に注意してください。
- すべての TIMESTAMP は UTC を基本としています。監査ログ初期化時に TimeZone を UTC に固定します。

---

## 貢献・ライセンス

この README はコードベースに基づく概要・利用手順の簡易ドキュメントです。実際のパッケージ公開時には pyproject.toml / requirements.txt / CONTRIBUTING.md / LICENSE を追加してください。

ご不明点や、README の補足・具体的なコマンド例（CI 用・Docker 用など）が必要であれば教えてください。