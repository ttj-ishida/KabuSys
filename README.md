# KabuSys — 日本株自動売買プラットフォーム（ミニマム実装）

KabuSys は日本株のデータ取得・ETL・監査・ニュース収集を想定したライブラリ群です。
J-Quants や kabuステーションと連携し、DuckDB を用いたデータ基盤（Raw / Processed / Feature /
Execution / Audit レイヤー）を備えています。本リポジトリはコアコンポーネントの実装を含み、
ETL パイプライン、ニュース収集、カレンダー管理、データ品質チェック、監査ログ等を提供します。

---

目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 環境変数（.env）
- 初期化・使い方（例）
- よく使う API（コードスニペット）
- ディレクトリ構成

---

## プロジェクト概要

- J-Quants API から株価日足・財務データ・市場カレンダーを取得するクライアントを提供
- DuckDB をバックエンドとしたスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS を用いたニュース収集と銘柄紐付け（SSRF対策やサイズ制限、トラッキングパラメータ除去を実装）
- マーケットカレンダー管理（営業日判定、next/prev/trading_days、nightly update job）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上のポイント：
- API レート制限順守（J-Quants は 120 req/min。RateLimiter を実装）
- 自動トークンリフレッシュ、リトライ（指数バックオフ）、冪等性（ON CONFLICT を使用）
- セキュリティ配慮（RSS の defusedxml、SSRF 対策、レスポンスサイズ制限）

---

## 主な機能一覧

- jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
- data.pipeline
  - run_daily_etl: カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック
  - run_prices_etl, run_financials_etl, run_calendar_etl
- data.schema
  - init_schema / get_connection: DuckDB スキーマ定義・初期化
- data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
  - URL 正規化、記事ID生成、SSRF/サイズ対策
- data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- data.audit
  - 監査用テーブル初期化（signal_events, order_requests, executions）とインデックス

---

## 前提条件

- Python 3.10 以上（型注釈で `X | Y` を使用しているため）
- pip が使用可能
- 推奨パッケージ（必須）
  - duckdb
  - defusedxml

（その他、標準ライブラリの urllib 等を使用）

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows PowerShell
   ```

3. 必要パッケージのインストール

   最低限の依存をインストールする例：

   ```
   pip install duckdb defusedxml
   ```

   （プロジェクトに pyproject.toml / requirements.txt があればそれを使用してください）
   開発中は編集可能インストールも推奨:

   ```
   pip install -e .
   ```

4. 環境変数の設定（.env ファイルを用意）

   プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 環境変数（.env の例）

必須（実行する機能による）:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...

オプション（デフォルト値あり）:
- KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
- LOG_LEVEL=INFO|DEBUG|...  （デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  （自動 .env ロードを無効化）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABU_API_BASE_URL=http://localhost:18080/kabusapi

例（.env）:

```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

注意: コード中に settings というクラスがあり、必須変数が未設定だと ValueError が発生します。

---

## 初期化（DB スキーマ作成）

DuckDB ファイルを初期化してスキーマを作成するには Python から:

```python
from kabusys.data.schema import init_schema

# ファイルパス例（デフォルトは data/kabusys.duckdb）
conn = init_schema("data/kabusys.duckdb")
# 返り値は duckdb.DuckDBPyConnection
```

監査（audit）スキーマのみを追加する場合:

```python
from kabusys.data.schema import get_connection
from kabusys.data.audit import init_audit_schema

conn = get_connection("data/kabusys.duckdb")
init_audit_schema(conn)
```

---

## 使い方（よくある実行例）

- 日次 ETL を実行する（ターゲット日を省略すると本日扱い）

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブを実行する

```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードのセット（例: {'7203', '6758'}）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203', '6758'})
print(res)  # {source_name: 新規保存件数}
```

- カレンダーの夜間アップデートジョブ

```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

- J-Quants の ID トークン取得（内部で settings の JQUANTS_REFRESH_TOKEN を使う）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings から自動取得
print(token)
```

---

## 主要 API（概要）

- kabusys.config.settings
  - settings.jquants_refresh_token / kabu_api_password / slack_bot_token / slack_channel_id
  - settings.duckdb_path / sqlite_path / env / log_level / is_live / is_paper / is_dev

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続（テーブルとインデックスを作成）
  - get_connection(db_path) -> 既存 DB への接続

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - check_missing_data, check_spike, check_duplicates, check_date_consistency

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, s, e)
  - calendar_update_job(conn, lookahead_days=90)

---

## 実行上の注意 / 守るべき点

- J-Quants のレート制限（120 req/min）を超えないよう注意。jquants_client は内部で固定間隔スロットリングを行います。
- API 呼び出し時のリトライやトークン自動リフレッシュが組み込まれていますが、クレデンシャル管理は安全に行ってください。
- RSS 取得時は外部 URL の検証（スキーム・プライベートIPブロック・サイズチェック）を行っています。プロキシ環境・社内ネットワークからのアクセス時は挙動を確認してください。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作成されます。複数プロセスで同時書き込みする場合は注意（DuckDB の同時書き込み制限）。

---

## ディレクトリ構成

（抜粋 — 実際のリポジトリでは他ファイルがあるかもしれません）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント + 保存
      - news_collector.py            — RSS ニュース収集・保存
      - pipeline.py                  — ETL パイプライン
      - calendar_management.py       — マーケットカレンダー管理
      - schema.py                    — DuckDB スキーマ定義・初期化
      - audit.py                     — 監査ログ用スキーマ
      - quality.py                   — データ品質チェック
    - strategy/
      - __init__.py                  — 戦略層（拡張ポイント）
    - execution/
      - __init__.py                  — 発注実行層（拡張ポイント）
    - monitoring/
      - __init__.py                  — 監視周り（拡張ポイント）

主要ファイルの役割：
- schema.py: DB のテーブル・インデックス定義（Raw/Processed/Feature/Execution）
- jquants_client.py: API 呼び出し（レート制御、リトライ、token refresh）
- pipeline.py: 差分 ETL の実装（バックフィル、品質チェック）
- news_collector.py: RSS 収集 → raw_news 保存 → 銘柄紐付け

---

## 拡張ポイント / 今後の実装候補

- 戦略（strategy）層の実装（シグナル生成アルゴリズム）
- execution 層の具体的なブローカー連携（kabuステーションとの送受信）
- モニタリング・アラート（Slack通知の実装、既に設定項目は存在）
- 単体テスト・CI、型チェック（mypy）や静的解析の追加
- packaging（pyproject.toml / setup.cfg）整備

---

何か特定の部分の README に追記してほしい（例: 実運用での運用手順、Docker 化、サンプル .env.example の自動生成、動作確認方法など）があれば教えてください。