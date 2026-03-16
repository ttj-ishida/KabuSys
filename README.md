# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（プロトタイプ）

このリポジトリは、J-Quants API を利用したデータ取得、DuckDB による永続化、ETL パイプライン、データ品質チェック、監査ログ（トレーサビリティ）を備えた日本株自動売買システムのコアコンポーネントを提供します。

---

## 概要

- J-Quants API から株価日足・財務データ・マーケットカレンダー等を取得し、DuckDB に保存します。
- ETL は差分更新（バックフィル対応）で冪等に動作します（ON CONFLICT DO UPDATE）。
- データ品質チェック（欠損、スパイク、重複、日付不整合）を実行できます。
- 監査ログ（signal → order_request → execution のトレーサビリティ）テーブルを備えています。
- レート制御（120 req/min）、リトライ、トークン自動リフレッシュ等の堅牢な HTTP ロジックを実装。

主要言語・依存:
- Python >= 3.10（型注釈で | を使用）
- duckdb

---

## 主な機能一覧

- 環境変数管理（自動 .env ロード、保護、必須チェック）
- J-Quants クライアント（認証、ページネーション、リトライ、レート制御）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_* 系関数で DuckDB に保存（冪等）
- DuckDB スキーマ定義・初期化（data.schema.init_schema）
  - Raw / Processed / Feature / Execution 層のテーブル群
- ETL パイプライン（差分取得・保存・品質チェック）
  - run_daily_etl：日次 ETL の一括実行
- 品質チェックモジュール（欠損・スパイク・重複・日付不整合）
  - run_all_checks
- 監査ログ（signal_events, order_requests, executions）初期化
  - init_audit_schema / init_audit_db

設計上のポイント:
- レート制御: 120 req/min（固定間隔スロットリング）
- リトライ: 指数バックオフ、最大 3 回（408, 429, 5xx 等）
- 401 受信時にリフレッシュして 1 回リトライ
- fetched_at / created_at は UTC を利用
- ETL は可能な限り継続し、問題は収集して呼び出し元に返す（Fail-Fast ではない）

---

## 前提（Requirements）

- Python 3.10+
- pip install duckdb

（実プロジェクトでは追加の依存がある可能性があります。requirements.txt がある場合はそれを使用してください。）

例:
```bash
python -m pip install --upgrade pip
python -m pip install duckdb
```

ソースツリーを editable install する場合:
```bash
python -m pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. 仮想環境を作成して有効化（推奨）
3. 依存ライブラリをインストール（例: duckdb）
4. 必要な環境変数を設定（下記参照）
5. DuckDB スキーマを初期化

例（Unix 系）:
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install duckdb
```

DuckDB スキーマ初期化（Python）:
```python
from kabusys.data.schema import init_schema

# デフォルト: data/kabusys.duckdb
conn = init_schema("data/kabusys.duckdb")
```

---

## 環境変数（.env 例）

パッケージはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

必須（Settings で require されるもの）:
- JQUANTS_REFRESH_TOKEN  -- J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      -- kabuステーション API のパスワード（実行系で使用）
- SLACK_BOT_TOKEN        -- Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       -- Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV            -- 開発環境: development / paper_trading / live（default: development）
- LOG_LEVEL              -- ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（default: INFO）
- KABU_API_BASE_URL      -- kabu API のベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH            -- DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH            -- SQLite パス（監視・モニタリング用, default: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD -- 自動 .env 読み込みを無効化する場合に 1 を設定

.example:
```
# .env
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

注意:
- パーサはシェル風の `export KEY=val` とクォートやコメントをある程度サポートします。
- OS 環境変数が優先され、.env.local は .env を上書きします。

---

## 使い方（サンプル）

以下はライブラリを使った基本的な操作例です。

1) スキーマ初期化（DuckDB）
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())

print(result.to_dict())
```

ETL の戻り値は ETLResult（fetched/saved 数、quality_issues、errors 等）です。

3) J-Quants のトークン確認 / 取得
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
print(id_token)
```

4) 監査ログ（audit）スキーマを追加
```python
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

5) 品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

---

## 主要 API の説明（簡易）

- kabusys.config.settings: 環境変数からの設定取得（プロパティ形式）
- kabusys.data.jquants_client:
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(...), save_market_calendar(...)
- kabusys.data.schema:
  - init_schema(db_path) - DuckDB のスキーマ初期化
  - get_connection(db_path)
- kabusys.data.pipeline:
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.quality:
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.audit:
  - init_audit_schema(conn), init_audit_db(db_path)

---

## 注意点 / 設計のポイント

- レート制御: J-Quants API に対して 120 req/min を守るため、固定間隔のスロットリングを行います。
- リトライ: ネットワーク障害や 429/408/5xx を対象に指数バックオフで最大 3 回リトライします。429 の場合は Retry-After を尊重します。
- 401 処理: 401 が来た場合は J-Quants の id_token を自動でリフレッシュして 1 回だけ再試行します（無限再帰を防止）。
- データ永続化: DuckDB への挿入は ON CONFLICT DO UPDATE を使い冪等性を確保します。
- 時刻: fetched_at/created_at は UTC を使用する設計です（監査ログでは SET TimeZone='UTC' を実行）。
- ETL の堅牢性: 各ステップは例外を内部で捕捉し、可能な限り他のステップは継続します。戻り値で エラー/品質問題 を報告します。

---

## ディレクトリ構成

主要ファイルとディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得・保存ロジック）
    - schema.py              -- DuckDB スキーマ定義・初期化
    - pipeline.py            -- ETL パイプライン（差分取得・保存・品質チェック）
    - quality.py             -- データ品質チェック
    - audit.py               -- 監査ログ（トレーサビリティ）初期化
    - pipeline.py
    - audit.py
  - strategy/
    - __init__.py            -- 戦略モジュール（実装場所）
  - execution/
    - __init__.py            -- 発注 / 実行関連（実装場所）
  - monitoring/
    - __init__.py            -- モニタリング用（実装場所）

（上記は現在のコードベースの抜粋です。戦略・実行・監視の詳細実装はこれからの実装想定箇所です。）

---

## 開発上のヒント

- 自動 .env 読み込みを無効にしたい（テストなど）の場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- DuckDB をインメモリで使う場合は `db_path=":memory:"` を渡して init_schema を呼び出せます。
- 実際の運用では J-Quants のレートや証券会社 API の要件に合わせた追加のレート制御やスロットリングが必要です。
- 監査ログは削除しない前提（ON DELETE RESTRICT）で設計されています。更新は監査証跡を残す方針で行ってください。

---

必要に応じて README に追加したい内容（例: CI/テストの実行方法、より詳細な .env の例、Slack 通知の使い方、kabu API の発注フローの例など）があれば教えてください。README をその要件に合わせて拡張します。