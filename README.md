# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants API 等からマーケットデータ・財務データ・ニュースを収集し、DuckDB に保存して ETL・品質チェック・監査ログを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API を使った株価・財務・マーケットカレンダーの差分取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- RSS からのニュース収集と記事→銘柄紐付け（SSRF/XML 爆弾対策、トラッキングパラメータ除去）
- DuckDB 上のスキーマ管理（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン、品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計方針として、冪等性（ON CONFLICT）、トレーサビリティ（fetched_at / created_at の記録）、安全性（SSRF/XML 対策）が重視されています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レートリミット、リトライ、トークン自動更新）
  - news_collector: RSS 取得、前処理、DuckDB への冪等保存、銘柄抽出
  - schema: DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）
  - calendar_management: JPX カレンダー管理・営業日ロジック・夜間更新ジョブ
  - audit: 監査ログ用スキーマ（signal/order_request/execution のトレーサビリティ）
  - quality: データ品質チェック群（欠損・重複・スパイク・日付不整合）
- config:
  - 環境変数読み込み機能（.env / .env.local の自動読み込み、プロジェクトルート検出、必須値検査）
- strategy / execution / monitoring: プレースホルダ（パッケージ構成用）

安全・運用上の配慮:
- J-Quants API の 120 req/min を守る RateLimiter 実装
- ネットワークエラー・HTTP 5xx に対する指数バックオフリトライ
- RSS 取得時の SSRF / private IP ブロック、gzip サイズ制限、defusedxml 使用
- DuckDB への書き込みは冪等操作（ON CONFLICT）を採用

---

## セットアップ手順

前提
- Python 3.10 以上（typing の `X | Y` 構文を使用）
- DuckDB を Python から利用可能にするため `duckdb` パッケージ
- XML パースに `defusedxml`

推奨パッケージのインストール例:

```bash
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
```

（プロジェクトに requirements.txt がある場合はそれを使用してください。）

.env の設定
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動的に読み込まれます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）

任意 / デフォルト
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 (.env):

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

1) DuckDB スキーマ初期化

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Path オブジェクト
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行する（株価 / 財務 / カレンダーの差分取得と品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn)  # target_date を省略すると today
print(result.to_dict())
```

3) ニュース収集ジョブの実行（RSS 取得 → raw_news に保存 → 銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄コードの集合（抽出フィルタ）
known_codes = {"7203", "6758", "9984"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

4) カレンダーの夜間更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

5) 監査スキーマの初期化（signal/order_requests/executions）

```python
from kabusys.data.audit import init_audit_schema

# 既存の conn に監査テーブルを追加
init_audit_schema(conn, transactional=True)
```

6) J-Quants API を直接使う例（ID トークン取得 / データ取得）

```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,2,1))
```

注意点:
- run_daily_etl 等は内部で例外をキャッチし続行するため、戻り値（ETLResult）の errors フィールドや quality_issues を確認して運用判断を行ってください。
- テスト時に自動 .env ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

## 主要 API の説明（抜粋）

- config.settings
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
  - settings.slack_bot_token / slack_channel_id
  - settings.duckdb_path / sqlite_path
  - settings.env / log_level / is_live / is_paper / is_dev

- data.schema
  - init_schema(db_path) -> DuckDB 接続（テーブル作成、冪等）
  - get_connection(db_path)

- data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl

- data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)

- data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

- data.calendar_management
  - is_trading_day(conn, date)
  - next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job(conn, lookahead_days=90)

- data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成

（src 配下の主要ファイルを抜粋）

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

主要な SQL テーブル群は data/schema.py に定義されています（raw_prices/raw_financials/raw_news/market_calendar/…／signals/orders/trades/positions/…／audit 用テーブル等）。

---

## 運用上の注意・補足

- J-Quants API 制限: 120 req/min を守るためモジュールに RateLimiter が組み込まれています。大量取得時は注意してください。
- 認証: get_id_token はリフレッシュトークンから id_token を発行し、id_token の自動リフレッシュと 401 リトライを実装しています。
- DuckDB: デフォルト DB パスは settings.duckdb_path（data/kabusys.duckdb）。複数環境で共有しないよう運用してください（テストでは ":memory:" を使用可）。
- セキュリティ: RSS 取得では defusedxml と SSRF 対策、受信サイズ制限を実施していますが、外部 URL の扱いには常に注意してください。
- テスト: config モジュールはプロジェクトルート検出に __file__ を利用するため、テスト時の .env 読み込みは環境変数で制御できます。

---

必要であれば README に「開発フロー」「CI 設定例」「詳細な .env.example」や「実行スクリプト（例: cron / systemd / Airflow）」などを追加できます。どの情報を優先して追記しますか？