# KabuSys

日本株自動売買プラットフォーム用のライブラリ群。J-Quants などから市場データやニュースを取得して DuckDB に保存し、ETL・品質チェック・カレンダー管理・監査ログまで含むデータパイプライン基盤を提供します。

---

## 概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。主な目的は以下です。

- J-Quants API から株価日足・財務データ・マーケットカレンダーを安全に取得して保存する
- RSS からニュースを取得して正規化・保管し銘柄紐付けを行う
- DuckDB を用いたスキーマ管理、ETL、データ品質チェックを提供する
- 監査ログ（シグナル→発注→約定のトレース）用テーブルを初期化する
- 市場カレンダーに基づく営業日判定などのユーティリティを提供する

設計上の特徴として、API レート制御・リトライ・トークン自動更新・Look-ahead バイアス対策・冪等な DB 書き込み・SSRF 対策や XML 安全処理などが盛り込まれています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（認証、リトライ、レート制御、ページネーション対応）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への冪等保存（save_daily_quotes, save_financial_statements, save_market_calendar）

- data/pipeline.py
  - 差分 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 日次 ETL 統合エントリポイント（run_daily_etl）
  - 差分取得・バックフィル・品質チェック統合

- data/news_collector.py
  - RSS フィードの安全な取得（SSRF・Gzip Bomb 対策、defusedxml）
  - URL 正規化（トラッキング削除）・記事 ID のハッシュ化
  - raw_news 保存（冪等、INSERT ... RETURNING）と news_symbols の紐付け

- data/schema.py
  - DuckDB の DDL 定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) による初期化

- data/calendar_management.py
  - market_calendar 更新ジョブ、営業日判定、前後営業日の取得等

- data/audit.py
  - 監査ログテーブル（signal_events, order_requests, executions）と初期化関数
  - init_audit_db(db_path) で独立 DB を作成可能

- data/quality.py
  - 欠損／重複／スパイク／日付不整合検査
  - run_all_checks で一括実行

- config.py
  - .env/.env.local や環境変数の読み込み、自動ロード（プロジェクトルート検出）
  - 必須設定のラッパー（Settings クラス）

---

## 前提（依存・環境）

- Python 3.10 以上（PEP 604 の union types `X | None` を使用）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
- 環境変数または .env ファイルでの設定が必須な項目あり（下記参照）

pip の仮想環境を作ってから次をインストールしてください（プロジェクトに setup がある前提）:

```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# pip install -e .  # パッケージ化されている場合
```

---

## 環境変数（主な必須項目）

config.Settings で参照・必須とされる環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID

その他の任意設定：

- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / ...
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動読み込みを無効化

自動ロード:
- パッケージ内 config はプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` → `.env.local` の順で自動ロードします。テスト等で自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 (.env)：
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（最小）

1. リポジトリをクローンし、仮想環境を作成して依存をインストール。

2. .env をプロジェクトルートに作成し必要な環境変数を設定。

3. DuckDB スキーマの初期化:

Python REPL またはスクリプトで：

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
```

4. 監査ログ DB が別に必要なら：

```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要 API の例）

- J-Quants の ID トークンを取得：

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を自動参照
```

- 単体データ取得と保存（株価）：

```python
import duckdb
from kabusys.data import jquants_client as jq

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

- 日次 ETL の実行（推奨：init_schema 後に実行）：

```python
from kabusys.data import pipeline
from datetime import date
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB 接続
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

run_daily_etl は ETLResult を返し、取得件数・保存件数・品質チェック結果・エラー概要を含みます。

- RSS（ニュース）収集の例：

```python
from kabusys.data import news_collector
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")

# RSS ソースの指定（省略すると DEFAULT_RSS_SOURCES を使用）
sources = {"yahoo_finance": "https://news.yahoo.co.jp/rss/categories/business.xml"}
articles = news_collector.fetch_rss(sources["yahoo_finance"], source="yahoo_finance")
new_ids = news_collector.save_raw_news(conn, articles)
# 銘柄紐付けを行う場合は known_codes を渡して run_news_collection を使う
known_codes = {"7203", "6758", "9432"}  # 実運用では有効コードセットを用意
news_collector.run_news_collection(conn, sources=sources, known_codes=known_codes)
```

- カレンダー更新ジョブ（夜間バッチ想定）：

```python
from kabusys.data import calendar_management
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("calendar saved:", saved)
```

- 品質チェック手動実行：

```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

---

## 注意事項・設計上のポイント

- レート制御とリトライ: J-Quants クライアントは 120 req/min を想定したスロットリングと、指定ステータスでの指数バックオフリトライを行います。401 受信時はリフレッシュトークンから ID トークンを自動更新して 1 回だけ再試行します。

- 冪等性: DuckDB への保存関数は基本的に ON CONFLICT で重複排除（更新）を行い、再実行可能な ETL を想定しています。

- ニュース収集のセキュリティ: defusedxml による XML パース、SSRF 対策（リダイレクト先のスキーム・プライベートIP検査）、レスポンスサイズ上限（Gzip 解凍後含む）などが組み込まれています。

- カレンダー: market_calendar がない場合は曜日ベースのフォールバックを行うため、初回は簡易動作しますが正確な営業日判定のためにはカレンダー取得を推奨します。

- 環境変数自動ロード: config.py はプロジェクトルート（.git または pyproject.toml）を検出し .env/.env.local を自動的に読み込みます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

リポジトリの主要ファイル（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - execution/            （発注・取引実行関連の将来拡張用パッケージ）
  - strategy/             （戦略関連の将来拡張用パッケージ）
  - monitoring/           （監視関連の将来拡張用パッケージ）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - news_collector.py       — RSS ニュース取得・保存・銘柄抽出
    - schema.py               — DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py             — ETL パイプライン（差分更新・日次 ETL）
    - calendar_management.py  — マーケットカレンダーの管理・ユーティリティ
    - audit.py                — 監査ログテーブル定義・初期化
    - quality.py              — データ品質チェック

---

## 開発・貢献

- 新しい機能やバグ修正は PR を送ってください。README に沿うテストやサンプルコードがあるとレビューが早くなります。
- DB スキーマ変更を加える場合は data/schema.py の DDL を更新し、既存テーブルとの互換性やマイグレーション方針を明記してください。
- 外部 API のキーやシークレットは必ず .env（または環境変数）で管理し、リポジトリに含めないでください。

---

以上が KabuSys の README です。必要であれば、README に実行可能なサンプルスクリプトや .env.example のテンプレートを追記しますか？