# KabuSys

日本株自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得・ETL・データ品質チェック・ニュース収集・監査ログ・DBスキーマなど、戦略・実行層の下支えとなる共通機能を提供します。

---

## 特徴（概要 / 設計方針）

- J-Quants API 経由で株価（日足）・財務データ・JPX カレンダーを取得し DuckDB に保存
  - レート制限（120 req/min）に合わせたレートリミッタ実装
  - リトライ（指数バックオフ）、401 時の自動トークンリフレッシュを実装
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias の抑止
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）
- RSS ベースのニュース収集（defusedxml を用いた安全な XML パース、SSRF 防止、サイズ制限）
  - URL 正規化 → SHA-256 ハッシュ（先頭32文字）で記事ID生成 → raw_news に冪等保存
  - 記事から銘柄コード（4桁）抽出して news_symbols に紐付け
- データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 各チェックは QualityIssue を返し、重大度に応じた運用判断が可能
- マーケットカレンダー管理（営業日判定 / 次営業日等のユーティリティ）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 設定は環境変数 / .env ファイルで管理。パッケージ起動時に自動で .env / .env.local を読み込み

---

## 機能一覧（主な公開 API）

- 設定
  - `from kabusys.config import settings`（J-Quants トークン、DB パス、Slack などを取得）
- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- スキーマ / DB 初期化（kabusys.data.schema）
  - init_schema(db_path)
  - get_connection(db_path)
- ETL パイプライン（kabusys.data.pipeline）
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(conn, target_date=None, ...)
- ニュース収集（kabusys.data.news_collector）
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day(conn, d), next_trading_day(...), prev_trading_day(...), get_trading_days(...)
  - calendar_update_job(conn, lookahead_days=...)
- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)
- 品質チェック（kabusys.data.quality）
  - check_missing_data(...)
  - check_spike(...)
  - check_duplicates(...)
  - check_date_consistency(...)
  - run_all_checks(...)

---

## 前提 / 必要環境

- Python 3.10+
- 必須パッケージ（主なもの）
  - duckdb
  - defusedxml
- （任意）J-Quants API 利用のためのリフレッシュトークン、kabu API・Slack の認証情報

requirements.txt がない場合は最低限以下をインストールしてください:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン / ソースを用意
2. 仮想環境を用意（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （その他）必要なパッケージをプロジェクトに合わせて追加
4. 環境変数 / .env を用意
   - パッケージは起動時にプロジェクトルートの `.env` と `.env.local` を自動読み込みします（OS環境変数が優先）。
   - 自動読み込みを無効化する場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
5. DB スキーマ初期化
   - 例: python REPL / スクリプト内で
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")

---

## 使い方（簡単な例）

- スキーマを初期化して日次 ETL を実行する（最小例）:

```python
from kabusys.data import schema, pipeline

# DB 初期化（ファイルパスは settings.duckdb_path 等と合わせても良い）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（今日のデータを取得して品質チェックまで実行）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブを実行する:

```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存DBへ接続
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット（実運用では全銘柄セットを用意）

results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数, ...}
```

- 監査 DB を初期化する:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- カレンダー更新バッチ:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print("calendar saved:", saved)
```

- 設定の参照:

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必須: JQUANTS_REFRESH_TOKEN が .env に設定されていること
print(settings.duckdb_path)            # Path オブジェクト
print(settings.env, settings.is_live)
```

---

## セキュリティ・堅牢性設計のポイント

- J-Quants クライアントはレート制限・リトライ・トークン自動更新を実装
- ニュース収集では defusedxml を使用、gzipサイズ制限、SSRF 対策（リダイレクト検査・プライベートIP拒否）
- DuckDB への書き込みは冪等性を重視（ON CONFLICT）し、ETL は差分更新で API コールを最小化
- すべてのタイムスタンプは UTC で扱う方針（監査 DB 初期化時に TimeZone を UTC に固定）

---

## ディレクトリ構成

主要ファイル / モジュールの一覧（src 以下）:

- src/kabusys/
  - __init__.py
  - config.py                 （環境変数 / 設定管理）
  - data/
    - __init__.py
    - jquants_client.py       （J-Quants API クライアント + DuckDB 保存ユーティリティ）
    - news_collector.py       （RSS ニュース収集・前処理・保存）
    - schema.py               （DuckDB スキーマ定義 / 初期化）
    - pipeline.py             （ETL パイプライン / run_daily_etl 等）
    - calendar_management.py  （マーケットカレンダーユーティリティ / バッチ）
    - audit.py                （監査ログスキーマ / 初期化）
    - quality.py              （データ品質チェック）
  - strategy/                  （戦略層: パッケージプレースホルダ）
  - execution/                 （実行層: パッケージプレースホルダ）
  - monitoring/                （監視層: パッケージプレースホルダ）

---

## 注意点 / 運用メモ

- .env 自動読み込み
  - パッケージはアプリ起動時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し `.env` / `.env.local` を読み込みます。
  - テストや特別な起動で自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Python バージョン
  - 型注釈で `|` を使っているため Python 3.10 以降を想定しています。
- DuckDB ファイル
  - デフォルトは `data/kabusys.duckdb`（settings.duckdb_path）。ファイルのバックアップ、権限管理を運用で行ってください。
- ログ
  - 各モジュールは標準の logging を利用します。運用時はハンドラを設定してログの集約（ファイル / stdout / 外部監視）を行ってください。

---

README はここまでです。必要であれば以下の追加を作成します：
- .env.example のテンプレート
- requirements.txt / pyproject.toml のサンプル
- 実運用用の cron / systemd / DAG（Airflow）例
- 詳細な API 使用例（パラメータ説明）