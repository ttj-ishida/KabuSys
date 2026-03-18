# KabuSys

日本株自動売買システム用の内部ライブラリ群（データ取得・ETL・監査・ニュース収集・スキーマ管理など）

## プロジェクト概要
KabuSys は日本株の自動売買プラットフォームを支える内部ライブラリ群です。  
主に以下を提供します。

- J-Quants API からの市場データ（株価日足、財務データ、JPX カレンダー）取得クライアント
- DuckDB を使ったデータスキーマ定義と初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース（RSS）収集と銘柄紐付け
- マーケットカレンダー管理（営業日判定、翌営業日/前営業日の計算）
- 監査ログ（シグナル → 発注 → 約定のトレース用テーブル群）

設計上のポイント：
- API レート制限・リトライ・トークン自動リフレッシュに対応
- DuckDB への保存は冪等（ON CONFLICT / DO UPDATE / DO NOTHING）を意識
- ニュース収集で SSRF / XML Bomb / 大容量レスポンス対策を実装
- データ品質チェックを実行し、問題を収集（Fail-Fast は行わない）

---

## 機能一覧
- data/schema.py: DuckDB のテーブル定義と初期化 (`init_schema`, `get_connection`)
- data/jquants_client.py: J‑Quants API クライアント（ID トークン取得、データ取得、DuckDB への保存）
  - RateLimiter（120 req/min）、リトライ、401 時の自動リフレッシュ
- data/pipeline.py: 日次 ETL（差分取得、バックフィル、品質チェック）と個別 ETL ジョブ
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- data/news_collector.py: RSS フィード取得・パース・前処理・DuckDB 保存（raw_news, news_symbols）
  - URL 正規化、トラッキングパラメータ除去、SSRF 防御、gzip サイズ制限
- data/calendar_management.py: カレンダー更新ジョブ、営業日判定、next/prev_trading_day、get_trading_days
- data/quality.py: データ品質チェック（欠損、重複、スパイク、日付不整合）
- data/audit.py: 監査ログ用テーブル定義と初期化（signal_events, order_requests, executions）
- config.py: 環境変数読み込みと Settings（.env 自動読み込み、必須設定チェック）
- その他: strategy、execution、monitoring 用のパッケージプレースホルダ

---

## 要件
- Python 3.10+
- 必須パッケージ（例）:
  - duckdb
  - defusedxml

（現状プロジェクトルートに pyproject.toml 等があればそれに従ってください。最小限動作させるには上記パッケージが必要です。）

インストール例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## セットアップ手順

1. リポジトリを取得してパッケージを Python パスに置く（開発モードでの利用を想定）
   - 例: プロジェクトルートを PYTHONPATH に含めるか、pip の editable インストールを行う

2. 環境変数 / .env ファイル
   - `kabusys.config` はプロジェクトルート（`.git` または `pyproject.toml` を基準）を探索して自動的に `.env` / `.env.local` を読み込みます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション（デフォルト値あり）:
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

3. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから呼び出します。デフォルトの DB パスは settings.duckdb_path。
   ```python
   from kabusys.config import settings
   from kabusys.data import schema

   # ファイルパス文字列や Path を指定して初期化
   conn = schema.init_schema(settings.duckdb_path)  # data/kabusys.duckdb にテーブルを作成
   # またはメモリ DB:
   # conn = schema.init_schema(":memory:")
   ```

4. 監査ログ専用 DB 初期化（必要に応じて）
   ```python
   from kabusys.data import audit
   conn_audit = audit.init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主な利用例）

以下はライブラリを直接利用する基本的な例です。実運用ではジョブスケジューラ（cron、Airflow など）から呼ぶことを想定しています。

- 日次 ETL を実行する例:
```python
from kabusys.config import settings
from kabusys.data import schema, pipeline

conn = schema.init_schema(settings.duckdb_path)
result = pipeline.run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- 個別ジョブ（価格 ETL / 財務 ETL / カレンダー ETL）:
```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")
# 例: 価格 ETL を本日の営業日までで実行
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
```

- J-Quants クライアントを直接使ってデータ取得と保存:
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")

# トークンは settings から内部取得されるため通常は省略可能
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
jq.save_daily_quotes(conn, records)
```

- RSS ニュース収集の例:
```python
from kabusys.data import news_collector, schema
conn = schema.get_connection("data/kabusys.duckdb")

results = news_collector.run_news_collection(
    conn,
    sources={"yahoo_business": "https://news.yahoo.co.jp/rss/categories/business.xml"},
    known_codes={"7203","6758"}  # 有効な銘柄コードセット（抽出用）
)
print(results)  # {source_name: 新規保存件数}
```

- カレンダー更新ジョブ:
```python
from kabusys.data import calendar_management, schema
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved calendar rows:", saved)
```

---

## 主要設計メモ / 注意点
- J-Quants API は 120 req/min のレート制限に対応（モジュール内に RateLimiter）。
- API リクエストは最大 3 回の指数バックオフリトライ（408/429/5xx 対象）、401 はトークン自動リフレッシュを1回試行。
- DuckDB に対する保存は冪等を重視（ON CONFLICT DO UPDATE / DO NOTHING を活用）。
- ニュース収集は SSRF・XML 攻撃・大容量レスポンスに対する防御ロジックを含む。
- データ品質チェックは Fail-Fast ではなく、問題をすべて収集して呼び出し元で判断する設計。
- config はプロジェクトルート探索で .env を自動読み込みします。テストや CI で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）
以下は主要モジュールとファイルの一覧です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント（取得/保存）
    - news_collector.py       # RSS ニュース収集・保存・銘柄抽出
    - schema.py               # DuckDB スキーマ定義・初期化
    - pipeline.py             # ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py  # マーケットカレンダー管理・ジョブ
    - audit.py                # 監査ログテーブル定義・初期化
    - quality.py              # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記以外に必要に応じて CLI/ジョブスクリプトや運用用ラッパーを作成してください。）

---

## よくある質問 / トラブルシュート
- .env が読み込まれない:
  - プロジェクトルートの判定は `.git` または `pyproject.toml` を基準とします。自動読み込みを期待するならプロジェクトルートに該当ファイルがあることを確認してください。
  - 自動読み込みを無効化している場合（KABUSYS_DISABLE_AUTO_ENV_LOAD）やテスト環境では手動で環境変数を設定してください。

- DuckDB の接続エラー:
  - 指定したパスの親ディレクトリが存在しない場合、schema.init_schema は自動で親ディレクトリを作成しますが、パーミッション等を確認してください。

- J-Quants から 401 が返る:
  - jquants_client は 401 を検知すると内部でリフレッシュを試行します。リフレッシュに失敗する場合は設定されたリフレッシュトークン（JQUANTS_REFRESH_TOKEN）を確認してください。

---

README は以上です。必要であれば、運用向けの cron/airflow のジョブ定義テンプレートや、Docker コンテナ化手順、追加のユースケース（戦略実行や発注モジュールの連携方法）についても作成できます。どの情報を追加しますか？