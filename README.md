# KabuSys

日本株自動売買システムのライブラリ群（データ収集・ETL・品質チェック・監査ログ用モジュール群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームの基盤ライブラリです。  
主に以下を提供します：

- J-Quants API を使った市場データ（株価日足、財務、JPXカレンダー）の取得・保存
- RSS からのニュース収集と銘柄紐付け
- DuckDB を利用したスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）初期化機能

設計の要点として、API レート制限の厳守、リトライ・トークン自動リフレッシュ、データの冪等保存（ON CONFLICT）、Look-ahead バイアス防止のための fetched_at 記録などを重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants からのデータ取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - DuckDB への保存（save_daily_quotes / save_financial_statements / save_market_calendar）
  - レートリミティング（120 req/min）とリトライ（指数バックオフ、401時はトークン自動リフレッシュ）

- data/news_collector.py
  - RSS フィード取得（fetch_rss）、記事の正規化・前処理、記事ID生成（URL正規化→SHA-256）
  - raw_news への冪等保存（save_raw_news）、記事と銘柄コード紐付け（save_news_symbols / _save_news_symbols_bulk）
  - セキュリティ対策（defusedxml、SSRF対策、応答サイズ制限、gzip解凍後のサイズチェック）

- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution のテーブルとインデックス）
  - init_schema(db_path) で DB 初期化

- data/audit.py
  - 監査用スキーマ（signal_events / order_requests / executions）と初期化（init_audit_schema / init_audit_db）
  - UTC タイムゾーン固定、冪等キー・ステータス管理

- data/pipeline.py
  - 日次 ETL（run_daily_etl）および個別ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 差分更新、バックフィル、品質チェック（quality.run_all_checks）

- data/quality.py
  - 欠損検出、重複検出、スパイク検出、日付整合性チェック（run_all_checks）

- data/calendar_management.py
  - カレンダー夜間バッチ（calendar_update_job）、営業日判定・検索（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）

- config.py
  - .env 自動読み込み（プロジェクトルートの .env / .env.local を優先読み込み）
  - 必須設定の取得（Settings クラス）
  - 利用可能な環境: development / paper_trading / live

---

## セットアップ手順

前提:
- Python 3.10 以上（型アノテーションに `X | None` 形式を使用）
- pip

推奨パッケージ（最低限）:
- duckdb
- defusedxml

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用してください）

環境変数設定:
- プロジェクトルート（.git または pyproject.toml のある階層）に `.env` および任意で `.env.local` を置くと自動読み込みされます。テストなどで自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（例）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx

# kabuステーションAPI
KABU_API_PASSWORD=your_kabu_password
# 任意: KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack（通知等に利用する想定）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

以下は Python REPL またはスクリプトからの利用例です。

1) DuckDB スキーマ初期化

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 監査ログ用 DB 初期化（別DBにしたい場合）

```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL 実行（市場データの差分取得・保存・品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- run_daily_etl は内部で calendar → prices → financials → 品質チェック の順で処理します。
- J-Quants のトークンは Settings から自動取得（環境変数 JQUANTS_REFRESH_TOKEN）。

4) RSS ニュース収集ジョブ

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う有効な銘柄コードの集合（例: {"7203", "6758", ...}）
res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(res)  # {source_name: 新規保存件数}
```

5) カレンダー更新ジョブ（夜間バッチ想定）

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

6) 品質チェック単体実行

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

---

## 設定・動作上の注意点

- .env 自動ロード:
  - 自動的にプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を探索し、`.env` と `.env.local` を読み込みます。
  - 既に OS 環境変数に設定済みのキーは `.env` によって上書きされませんが、`.env.local` は上書きを許可します（ただし OS 環境変数は保護されます）。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- J-Quants API:
  - レート制限 120 req/min を守るため内部でスロットリングしています。
  - HTTP エラーやネットワークエラー時は最大 3 回のリトライ（指数バックオフ）を行います。401 はリフレッシュトークンで自動トークン更新を試みた上で再試行します。
  - 取得したデータには fetched_at を付与し、いつシステムがそのデータを取得したかを記録します（Look-ahead Bias 防止）。

- News Collector のセキュリティ対策:
  - defusedxml を用いた XML パース（XML Bomb 対策）
  - URL スキーム検証（http/https のみ）
  - SSRF 対策のためリダイレクト先やホストを検査し、プライベートアドレスへのアクセスを拒否
  - レスポンスサイズ上限（デフォルト 10MB）と gzip 解凍後のサイズチェック

- DuckDB:
  - init_schema() は冪等でテーブルを作成します。既存 DB に対しては get_connection() を使って接続してください。
  - 監査スキーマは init_audit_schema / init_audit_db で追加できます。監査ログは UTC タイムゾーンで保存するよう設定されます。

- Python バージョン:
  - 型ヒントや構文により Python 3.10 以上を想定しています。

---

## ディレクトリ構成

リポジトリの主要ファイル／ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント（fetch_*, save_*）
    - news_collector.py       # RSS 収集・前処理・DB保存
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  # カレンダー管理（営業日判定・更新ジョブ）
    - schema.py               # DuckDB スキーマ定義・init_schema
    - audit.py                # 監査ログ（signal/order/execution）定義・初期化
    - quality.py              # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

- （プロジェクトルート）
  - .env.example (推奨)
  - pyproject.toml / .git (プロジェクトルート検出に使用)

---

## 開発者向けメモ

- ロギングレベルは環境変数 `LOG_LEVEL`（デフォルト INFO）で制御されます。
- 環境切替は `KABUSYS_ENV`（development / paper_trading / live）で行い、settings.is_live / is_paper / is_dev プロパティで判定できます。
- テスト時に .env の自動読み込みを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- news_collector._urlopen はテスト用にモック差し替え可能です。

---

## ライセンス・その他

このドキュメントはコードベースから自動生成した README 例です。実運用前に依存関係や外部 API の利用条件（J-Quants 等）、証券会社 API の取り扱い（kabu ステーション等）に関する契約・セキュリティ要件を必ず確認してください。

必要であれば README にサンプル .env.example、追加の CLI 実行例、CI 設定やデプロイ手順（systemd / k8s など）も追記します。どの情報を追加したいか教えてください。