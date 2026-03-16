# KabuSys

日本株自動売買のためのデータプラットフォーム＆ETLライブラリ。  
J-Quants API から市場データ・財務データ・マーケットカレンダーを取得し、DuckDB に保存・管理するためのモジュール群と、データ品質チェック／監査ログを含みます。

- パッケージ名: `kabusys`
- バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたライブラリです。

- J-Quants API からのデータ取得（株価日足、財務データ、JPX マーケットカレンダー）
- DuckDB を用いた三層データレイヤ（Raw / Processed / Feature）および実行・監査レイヤのスキーマ定義と初期化
- 差分ETL（バックフィル含む）、冪等な保存（ON CONFLICT DO UPDATE）
- データ品質チェック（欠損／スパイク／重複／日付不整合）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- レート制御（J-Quants の制限を守る固定間隔スロットリング）、リトライ、401 によるトークン自動リフレッシュ

---

## 機能一覧

- data.jquants_client
  - J-Quants API クライアント（認証、ページネーション、リトライ、レート制御）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
- data.schema
  - DuckDB のスキーマ定義（Raw/Processed/Feature/Execution）
  - init_schema(db_path) による初期化
- data.audit
  - 監査ログテーブルの定義と初期化（signal_events, order_requests, executions）
  - init_audit_schema(conn) / init_audit_db(db_path)
- data.pipeline
  - 日次 ETL の実行（差分取得、保存、品質チェック）
  - get_last_price_date 等の差分管理ユーティリティ
  - run_daily_etl による一括処理（カレンダー→株価→財務→品質チェック）
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks による一括チェック
- config
  - 環境変数読み込み（.env / .env.local をプロジェクトルートから自動読み込み）
  - settings オブジェクト経由で設定値を取得
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能
- strategy / execution / monitoring
  - パッケージプレースホルダ（戦略・発注・監視ロジックの拡張ポイント）

---

## 要件

- Python 3.10+
  - 型表記に `X | None` 等を使用しているため Python 3.10 以上を想定しています。
- 依存パッケージ（主に）
  - duckdb

（プロジェクト側で setuptools/pyproject.toml に依存を定義してください）

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. パッケージと依存のインストール
   - pip install -U pip
   - pip install duckdb
   - （開発版のローカルインストール）pip install -e .
4. 環境変数を設定（次節参照）

---

## 環境変数（.env）

パッケージ起動時、プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から自動で `.env` と `.env.local` が読み込まれます。OS 環境変数が優先され、`.env.local` は `.env` の上書きに使われます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- Slack (通知用)
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (省略可、デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (省略可、デフォルト: data/monitoring.db)
- 実行環境
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO

サンプル `.env`:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## データベース初期化

DuckDB スキーマの初期化は `kabusys.data.schema.init_schema` を使用します。ファイルベース DB またはインメモリ DB を指定できます。

例（ファイルベース）:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

例（インメモリ、テスト用）:

```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

監査ログを別DBに初期化する（または既存接続に追加）:

```python
from kabusys.data.audit import init_audit_schema, init_audit_db

# 既存の conn にテーブルを追加
init_audit_schema(conn)

# 監査専用 DB を作る場合
audit_conn = init_audit_db("data/audit_kabusys.duckdb")
```

---

## ETL（日次パイプライン）の実行例

日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）を実行する簡単な例:

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（既存ファイルに接続してなければ作成）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn)

# 結果の確認
print(result.to_dict())
if result.has_errors:
    print("ETL 中にエラーが発生しました:", result.errors)
if result.has_quality_errors:
    print("品質チェックでエラーが検出されました")
```

テスト用にインメモリ DB を使う場合:

```python
conn = init_schema(":memory:")
result = run_daily_etl(conn, target_date=date(2022, 1, 1))
```

run_daily_etl は内部で `jquants_client` を呼び、取得・保存・品質チェックを実施します。各処理は独立してエラーハンドリングされ、一部失敗しても他処理は継続します（結果にエラー一覧が積まれます）。

---

## jquants_client の利用例

直接 API を呼ぶ場合の例:

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.config import settings
from datetime import date

token = get_id_token()  # refresh token から id token を取得
rows = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))
```

save_* 系を使って DuckDB に保存する:

```python
from kabusys.data.jquants_client import save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = save_daily_quotes(conn, rows)
print(f"saved: {saved}")
```

実装上の注意点:

- レート制限: 120 req/min を守るため固定間隔スロットリングを行います。
- リトライ: 408/429/5xx 等に対して指数バックオフで最大 3 回リトライします。429 の場合は Retry-After ヘッダを優先。
- 401 受信時: トークンを自動でリフレッシュして 1 回リトライします（ただし無限再帰は防止）。
- 保存処理は冪等（ON CONFLICT DO UPDATE）です。

---

## 品質チェック（quality）

`kabusys.data.quality` は以下のチェックを行います。

- 欠損データ検出（open/high/low/close の欠損）
- 重複チェック（主キー重複）
- スパイク検出（前日比の絶対変動が閾値を超える場合、デフォルト 50%）
- 日付不整合（未来日付、market_calendar による非営業日データ）

一括実行:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

`QualityIssue` はチェック名・テーブル・重大度・詳細・サンプル行を持ち、呼び出し側は重大度に応じて処理を中止するかどうか判断します。

---

## 監査ログ（audit）

監査ログはシグナルから発注・約定までのトレーサビリティを維持します。`data.audit.init_audit_schema(conn)` により以下のテーブルを初期化します：

- signal_events
- order_requests（order_request_id が冪等キー）
- executions（broker_execution_id をユニークに保持）

設計上のポイント:

- すべての TIMESTAMP は UTC 保存（init_audit_schema は接続で TimeZone='UTC' を実行）
- 発注は order_request_id を冪等キーとして二重発注を防ぐ
- 監査ログは削除しない前提（ON DELETE RESTRICT）

---

## 使い方（まとめ）

- 環境変数を設定（.env）
- DuckDB スキーマを初期化: `init_schema(settings.duckdb_path)`
- 日次 ETL を実行: `run_daily_etl(conn)`
- 品質チェック: `run_all_checks(conn)`
- 監査ログを有効化: `init_audit_schema(conn)` または `init_audit_db(path)`

---

## ディレクトリ構成

以下はこのコードベースの主要ファイル／ディレクトリ構成です:

- src/kabusys/
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
    - jquants_client.py
    - schema.py
    - pipeline.py
    - audit.py
    - quality.py

---

## 注意事項 / 設計上の留意点

- Python バージョンは 3.10 以上を想定しています（型ヒント等）。
- J-Quants の API 制限と信頼性に配慮した実装（レート制御、リトライ、トークン自動更新）が組み込まれていますが、運用時は API レートやエラー傾向に応じた調整が必要です。
- ETL は差分更新を行いますが、初回ロードや大幅な backfill が必要な場合は適切な date_from を指定してください。
- DuckDB のファイルはバックアップ/配置に注意してください（共有ファイルの同時書き込みなど）。

---

## ライセンス / 貢献

（ここにライセンス情報や貢献方法を記載してください。）

---

不明点や追加したいサンプル（例えば戦略層・発注フローのサンプルコード等）があれば教えてください。README を用途に合わせて拡張します。