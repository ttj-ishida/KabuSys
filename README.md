# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。データ取得（J‑Quants 等）、ETL、データスキーマ（DuckDB）、ニュース収集、品質チェック、監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は日本株の市場データ・財務データ・ニュースなどを自動で収集・保管し、戦略・発注系モジュールへ供給するための基盤ライブラリです。本リポジトリは主に次の機能群を実装しています。

- J‑Quants API クライアント（株価日足・財務データ・市場カレンダー）
  - レート制限・リトライ・自動トークンリフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し Look‑ahead Bias を回避
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（日次差分更新、バックフィル、品質チェック）
- ニュース収集（RSS）と銘柄コード抽出・DB 保存（SSRF対策・XML脆弱性対策）
- マーケットカレンダー管理（営業日判定、next/prev trading day 等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計上、冪等性（ON CONFLICT）・トランザクション・安全な XML/HTTP 処理・明示的な UTC 運用を重視しています。

---

## 主な機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
- data.schema
  - init_schema(db_path): DuckDB スキーマを初期化して接続を返す
  - get_connection(db_path)
- data.pipeline
  - run_daily_etl(...): 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
- data.news_collector
  - fetch_rss(url, source): RSS 取得 & パース（defusedxml 使用）
  - save_raw_news(conn, articles) / save_news_symbols / run_news_collection
  - SSRF/プライベートアドレス対策、gzip/サイズ上限、トラッキング除去
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job: 夜間のカレンダー差分更新
- data.quality
  - check_missing_data / check_duplicates / check_spike / check_date_consistency / run_all_checks
- data.audit
  - 監査ログ用DDL と init_audit_schema / init_audit_db（Order/Execution のトレース）

---

## セットアップ手順

前提
- Python 3.9+（typing の union 型などが使われています。環境に合わせて適宜調整してください）
- pip が利用可能であること

1. リポジトリをクローン（またはプロジェクトルートに移動）
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 必要な依存をインストール

例（最小限の依存）:
```
pip install duckdb defusedxml
```
※ 実際のプロジェクトでは pyproject.toml / requirements.txt を用意しているはずです。プロジェクトに合わせて追加パッケージ（例: slack_sdk 等）をインストールしてください。

4. 環境変数の設定
- プロジェクトルートに `.env` と（必要なら）`.env.local` を置くと自動で読み込まれます（kabusys.config による自動ロード）。
- 自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（例）:
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: one of {development, paper_trading, live}（デフォルト development）
- LOG_LEVEL: one of {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト INFO）

例 .env（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本的な実行例）

以下は Python REPL やスクリプトから利用する例です。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Settings.duckdb_path で Path オブジェクトを返します
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出に使う有効コードの集合（省略すると抽出をスキップ）
known_codes = {"7203", "6758"}
stats = run_news_collection(conn, known_codes=known_codes)
print(stats)  # {source_name: 新規保存件数, ...}
```

4) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

5) 監査ログスキーマの初期化（監査専用 DB を分ける場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

6) 直接 J‑Quants API を呼ぶ（トークン取得やフェッチ）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes

token = get_id_token()  # settings.jquants_refresh_token を元に取得（自動リフレッシュ対応）
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
```

注意点：
- J‑Quants の API レート上限（120 req/min）を内部で制御しています。
- HTTP 408/429/5xx に対する指数バックオフリトライ、401 時の自動トークンリフレッシュを実装しています。
- news_collector は defusedxml を使い XML Bomb 等を防ぎ、SSRF 対策も実装しています。

---

## ディレクトリ構成

主要ファイル・モジュールの構成（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py      # J‑Quants API クライアント（取得・保存ロジック）
    - news_collector.py      # RSS ニュース収集・保存・銘柄抽出ロジック
    - schema.py              # DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py # 市場カレンダー管理（営業日判定・更新ジョブ）
    - audit.py               # 監査ログ（signal / order_request / executions）
    - quality.py             # データ品質チェック
    - (その他 ETL 関連モジュール)
  - strategy/                # 戦略関連（空 __init__ のみ・戦略実装を追加可能）
  - execution/               # 発注/ブローカー連携（空 __init__ のみ）
  - monitoring/              # 監視用コード（空 __init__ のみ）

補足:
- settings（kabusys.config.Settings）を通して環境変数を取得する設計です。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）から行われます。

---

## 運用上の注意・設計上のポイント

- 全てのタイムスタンプは可能な限り UTC で扱う設計です（fetched_at 等）。
- DuckDB への INSERT は冪等性を考慮し ON CONFLICT を利用しています。
- ニュース収集は受信上限バイト数・gzip 解凍後上限を設け、XML パースは defusedxml を使用しています。
- J‑Quants API にはレート制限があるため、短時間に大量リクエストを送らない運用を心がけてください。
- KABUSYS_ENV によって実運用モード（development / paper_trading / live）を切り替えられます。live モードではより慎重な運用が必要です。

---

## 開発・寄稿

- 追加の戦略や実際の発注実装は strategy/ と execution/ に実装してください。
- テストを書く際は環境変数の自動ロードを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）するとテストの独立性が保てます。
- DB 初期化やマイグレーション時はバックアップを取り、運用中の DB を上書きしないよう注意してください。

---

README の内容は現状のコードベース（src/kabusys）に基づいてまとめています。詳しい API 使用例や運用フロー（cron、CI、監視設定など）は実運用要件に合わせて追記してください。