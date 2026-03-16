# KabuSys — 日本株自動売買システム

簡易説明書（README）

---

目次
- プロジェクト概要
- 主な機能
- 必要条件 / インストール
- 環境変数（.env）と自動ロード動作
- セットアップ手順（DB 初期化など）
- 使い方（主要 API の例）
- ディレクトリ構成
- トラブルシューティング / 注意点

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
主にデータ取得（J-Quants）・ETL パイプライン・データ品質チェック・DuckDB ベースのスキーマ定義・監査ログ（発注/約定トレース）などを提供します。  
設計上のポイントは以下です。

- J-Quants API からの株価（OHLCV）、財務データ、JPX カレンダー取得
- API レート制御（120 req/min）、リトライ、トークン自動リフレッシュ
- DuckDB を用いた3層（Raw / Processed / Feature）＋ Execution 層のスキーマ定義
- ETL の差分更新・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）

---

## 主な機能一覧

- データ取得
  - fetch_daily_quotes（株価日足、ページネーション対応）
  - fetch_financial_statements（四半期財務）
  - fetch_market_calendar（JPX カレンダー）
- データ保存（冪等）
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ ON CONFLICT 更新）
- ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl（上記まとめ、品質チェック含む）
- データ品質チェック
  - 欠損チェック / スパイク検出 / 重複 / 日付不整合
- スキーマ管理
  - init_schema（DuckDB の初期テーブル作成）
  - audit.init_audit_schema / init_audit_db（監査ログ用テーブル）
- 設定管理
  - 環境変数からの設定読み込み（自動 .env ロード機能あり）

---

## 必要条件 / インストール

- Python 3.10 以上（型記法により Python 3.10+ を想定）
- 依存ライブラリ（主要）
  - duckdb

推奨手順（プロジェクトルートで）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2. 必要パッケージをインストール
   - pip install duckdb

3. 開発インストール（パッケージ化されている場合）
   - pip install -e .

（プロジェクトが src 配下にあるため、手元で直接実行する場合はプロジェクトルートを PYTHONPATH に含めるか上記 editable install を推奨）

---

## 環境変数（.env）と自動ロード動作

settings（kabusys.config.Settings）は環境変数から設定を取得します。主要な変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用（必要に応じて）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)。デフォルト: development
- LOG_LEVEL — ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)。デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — SQLite モニタリング DB。デフォルト: data/monitoring.db

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探し、以下順で読み込みます:
  1. OS 環境変数（最優先）
  2. .env.local（存在すれば上書き）
  3. .env（存在すれば読み込み）
- 自動ロードを無効化する: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

.env の書き方の例（プロジェクトルートに作成）:

JQUANTS_REFRESH_TOKEN="xxxxxxxxxxxxxxxx"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順（DuckDB スキーマ初期化等）

1. DuckDB のスキーマを作成（初期化）:

Python REPL やスクリプトで:

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可

2. 監査ログテーブルを追加（必要な場合）:

from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)

または監査専用 DB を作る:

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")

3. ETL の実行（下記参照）

---

## 使い方（主要 API の例）

基本的な日次 ETL 実行例:

from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())

個別ジョブを呼ぶ（例: 株価のみ）:

from datetime import date
from kabusys.data.pipeline import run_prices_etl

saved_fetched, saved_count = run_prices_etl(conn, target_date=date.today())

J-Quants の直接呼び出し（テスト等）:

from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # refresh token は settings から取得
quotes = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,12,31))

監査ログ初期化（既存 conn に追加）:

from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)

品質チェックの実行:

from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i)

ログ設定と実行モード:
- KABUSYS_ENV によって is_live / is_paper / is_dev が切り替わります（settings.is_live 等）。
- LOG_LEVEL 環境変数でログレベルを制御してください。

運用例:
- run_daily_etl を cron / Airflow / 他のスケジューラから定期実行し、取得と品質チェックを自動化します。
- ETL 実行結果（ETLResult）を Slack 等に通知するロジックを追加できます（SLACK_BOT_TOKEN 他を利用）。

---

## ディレクトリ構成（主要ファイルと役割）

（プロジェクトの src 配下を想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 定義 (.env 自動ロード、必須チェック)
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証、レート制御、リトライ、fetch_* / save_*）
    - schema.py
      - DuckDB 用スキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（差分更新、backfill、品質チェック）
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - audit.py
      - 監査ログ用テーブル（signal / order_request / executions 等）、init_audit_schema
    - audit.py / schema.py の連携により監査トレースが可能
  - strategy/
    - __init__.py
    - （戦略ロジックを実装する場所）
  - execution/
    - __init__.py
    - （発注・ブローカ連携を実装する場所）
  - monitoring/
    - __init__.py
    - （運用監視・メトリクスのためのモジュール置き場）

---

## トラブルシューティング / 注意点

- Python バージョン: 本コードは型記法（A | B）を使用しているため Python 3.10 以降を想定しています。
- 環境変数未設定: Settings の必須プロパティ（JQUANTS_REFRESH_TOKEN 等）が未設定だと ValueError を投げます。 .env を用意してください。
- 自動 .env ロードが働かない場合:
  - プロジェクトルートが .git または pyproject.toml を持っているか確認
  - テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- レート制限: J-Quants は 120 req/min に合わせた内部レートリミッタを実装していますが、外部で大量同時実行すると制限に触れる可能性があります。
- 401 エラー: get_id_token による自動リフレッシュロジックがありますが、refresh_token が無効な場合は失敗します。refresh token を確認してください。
- DuckDB ファイルのパス: デフォルトは data/kabusys.duckdb。複数プロセスで同時アクセスする運用は注意（ロックや排他を検討）。
- 品質チェック: run_all_checks は警告・エラーを収集して返します。ETL 停止の判断は呼び出し側で行ってください（Fail-Fast ではない設計）。

---

必要に応じて README をプロジェクトの方針や運用フロー（例: CI/CD、Cron 設定、Slack 通知テンプレート、監査クエリ例）に合わせて拡張してください。README の追加項目やサンプルスクリプト作成を希望されれば、その内容に合わせて具体例を作成します。