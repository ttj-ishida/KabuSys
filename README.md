# KabuSys

日本株向けの自動売買/データ基盤ライブラリ（KabuSys）。  
J-Quants API や RSS フィード等からデータを取得し、DuckDB に格納・品質チェック・ETL を実行するためのユーティリティ群を提供します。

主にデータ収集・ETL・カレンダー管理・監査ログの初期化・品質チェックに重点を置いたモジュール構成です。戦略、発注、モニタリングのレイヤーはパッケージ化されていますが、具体的実装は各自で追加する想定です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の目的で設計されています。

- J-Quants API から株価（日足）、財務（四半期 BS/PL）、及び JPX マーケットカレンダーを取得
- RSS フィードからニュース記事を収集し、記事と銘柄の紐付けを行う
- DuckDB にデータを冪等に保存（ON CONFLICT / DO UPDATE）して履歴を保持
- ETL パイプラインで差分更新・バックフィルを行い、品質チェック（欠損・スパイク・重複・日付不整合）を実行
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用テーブルを初期化
- JPX カレンダーに基づく営業日判定やカレンダー更新ジョブを提供

設計上の重要点：
- API レート制限、リトライ（指数バックオフ）、トークン自動リフレッシュに対応
- Look-ahead bias を防ぐために fetched_at や UTC タイムスタンプを明示的に扱う
- SSRF 対策、XML パースの安全化（defusedxml）など外部入力対策を実装

---

## 機能一覧

主な機能（モジュール別）：

- kabusys.config
  - .env（および .env.local）自動読み込み機能（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）

- kabusys.data.jquants_client
  - J-Quants API クライアント（取得・リトライ・レート制御・トークン自動更新）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）

- kabusys.data.news_collector
  - RSS フィード取得（gzip 対応、サイズ制限）
  - URL 正規化・トラッキングパラメータ除去、記事ID は SHA-256 ハッシュ（先頭32文字）
  - SSRF 対策（スキーム検証、プライベートIP 検出、リダイレクト時の検査）
  - raw_news / news_symbols への冪等保存

- kabusys.data.schema
  - DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）定義と初期化
  - init_schema(db_path) によるテーブル・インデックス作成

- kabusys.data.pipeline
  - 差分 ETL（株価・財務・カレンダー）と run_daily_etl による一括実行
  - 差分取得・backfill ロジック・品質チェックの統合

- kabusys.data.calendar_management
  - market_calendar の夜間更新ジョブ（calendar_update_job）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日ユーティリティ

- kabusys.data.audit
  - 監査ログ用テーブル（signal_events, order_requests, executions）と初期化補助
  - init_audit_db(db_path) で監査専用 DB を初期化

- kabusys.data.quality
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - QualityIssue 型で問題を返却し、run_all_checks で一括実行可能

（strategy / execution / monitoring パッケージはインターフェース用に用意されていますが、具体的な戦略・発注ロジックはプロジェクト側で実装します）

---

## セットアップ手順

前提：Python 3.9+（typing の一部構文に依存）

1. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2. 必要なパッケージをインストール
   最低依存：
   - duckdb
   - defusedxml

   例：
   - pip install duckdb defusedxml

   （プロジェクトをパッケージ化している場合は pip install -e . などを使ってインストールしてください）

3. 環境変数（.env）を準備
   プロジェクトルート（.git または pyproject.toml を基準）に `.env` を置くと自動で読み込まれます（`.env.local` は `.env` を上書き）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。必須変数の例は下記参照。

4. DuckDB の初期化（任意のタイミングで）
   - Python REPL やスクリプトから schema.init_schema() を呼んで DB を作成します（後述の使い方参照）。

---

## 環境変数

主な環境変数（settings で参照されるもの）：

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルトあり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live) デフォルト: development
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL) デフォルト: INFO

.example (.env.example) の例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意:
- .env のパースは一般的な shell 形式に準拠し、export 句・シングル/ダブルクォート・コメントを扱います。
- 自動読み込みはプロジェクトルートを .git または pyproject.toml により検出します。

---

## 使い方

以下は主要なユースケースの最小例です。実際にはエラーハンドリングやログ設定を行ってください。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH に基づく Path
conn = init_schema(settings.duckdb_path)
# これで全テーブルとインデックスが作成されます（冪等）
```

2) 監査ログ DB の初期化（専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

3) 日次 ETL 実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # 引数で target_date, id_token, run_quality_checks などを指定可能
print(result.to_dict())
```

run_daily_etl は以下を順に実行します：
- market_calendar の先読み更新
- 株価（日足）差分取得（backfill により過去数日分を再フェッチ）
- 財務データ差分取得
- 品質チェック（run_quality_checks=True の場合）

4) RSS ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# known_codes は銘柄抽出に使用する有効銘柄コードの集合（例: {'7203','6758',...}）
results = run_news_collection(conn, known_codes=set(["7203", "6758"]))
print(results)  # {source_name: 新規保存件数, ...}
```

5) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} calendar entries")
```

6) 直接 API 呼び出し（J-Quants）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.config import settings

token = get_id_token()  # settings.jquants_refresh_token を使用して id_token を取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,2,1))
```

---

## 主要 API（概要）

- settings (kabusys.config)
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path, settings.env, settings.log_level など

- data.schema
  - init_schema(db_path) -> duckdb connection
  - get_connection(db_path)

- data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, s, e)
  - calendar_update_job(conn, lookahead_days=90)

- data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - 個別のチェック関数（check_missing_data, check_spike, check_duplicates, check_date_consistency）

---

## 注意点 / 実装上のポイント

- J-Quants API はレート制限（120 req/min）があるため、クライアントは内部で RateLimiter による制御を行います。
- HTTP エラー時は指数バックオフで最大3回リトライ、401 の場合はリフレッシュトークンで自動的に再取得を試みます（1回のみ）。
- NewsCollector は SSRF、XML Bomb、gzip bomb、過大レスポンス対策を実装しています。URL 正規化・トラッキングパラメータ除去により記事の冪等性を担保します。
- DuckDB に格納する際は多くの箇所で ON CONFLICT / DO UPDATE / DO NOTHING を使って冪等性を保っています。
- データ品質チェックは Fail-Fast ではなく問題を収集して返す設計です。呼び出し側で結果に応じたアクション（停止・通知など）を実装してください。

---

## ディレクトリ構成

パッケージルート（src/kabusys） の主要ファイル一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - calendar_management.py
    - audit.py
    - quality.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

各ファイルの役割は上の「機能一覧」を参照してください。

---

必要に応じて README にサンプルの .env.template やデータモデル図（DataSchema.md）・外部 API の利用制約を追記すると、導入者にとって親切です。必要であれば README を拡張して運用手順（cron で ETL を回す例、Slack 通知の仕組み、監査ログの運用方針など）も追加します。ご希望があればその点も作成します。