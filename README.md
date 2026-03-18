# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。データ取得（J‑Quants）、ETL、ニュース収集、DuckDBスキーマ、データ品質チェック、監査ログ（発注→約定トレース）など、自動売買システムの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータプラットフォームと自動売買ワークフローを支える内部ライブラリです。主な責務は以下の通りです。

- J‑Quants API から株価（日足）・財務・マーケットカレンダーを取得して DuckDB に保存
- RSS フィードからニュースを収集して前処理・DB保存・銘柄紐付け
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- DuckDB に対するスキーマ初期化（Raw / Processed / Feature / Execution / Audit 層）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレース）用テーブル定義

設計上のポイント:
- J‑Quants のレート制限（120 req/min）遵守（内部 RateLimiter）
- リトライ（指数バックオフ、401 時はトークン自動リフレッシュ）
- データ取得時に fetched_at を UTC で記録して Look‑ahead Bias を防止
- DuckDB への保存は冪等（ON CONFLICT）で重複を排除
- ニュース収集は SSRF 対策・レスポンスサイズ制限・XML セキュリティ対策を実装

---

## 主な機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - レート制御・リトライ・トークン自動更新対応
- data.news_collector
  - fetch_rss: RSS フィード取得（gzip対応・XML検証・SSRF対策）
  - save_raw_news / save_news_symbols / run_news_collection
  - URL 正規化（utm 等の除去）、SHA-256 ベース記事ID生成、銘柄コード抽出
- data.schema
  - init_schema: DuckDB の全テーブル・インデックスを作成（Raw/Processed/Feature/Execution）
  - get_connection: 既存 DB に接続
- data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
  - 差分取得・バックフィル・品質チェックの統合
- data.calendar_management
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - calendar_update_job: 夜間のカレンダー差分更新
- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
  - QualityIssue 型による詳細な検出結果
- data.audit
  - 監査ログ用テーブル作成（signal_events / order_requests / executions 等）
  - init_audit_schema / init_audit_db

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部記法を利用しています。環境に合わせて適宜調整してください）
- DuckDB（Python パッケージ）
- defusedxml（XML の安全なパースのため）

例: pip を使った最小インストール
```
pip install duckdb defusedxml
```

推奨: プロジェクトに requirements.txt を用意する場合は上記を追加してください。

環境変数（必須）
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（本実装では設定を参照するプロパティあり）
- SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID: Slack チャネル ID

任意（デフォルト有り）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

.env 自動読み込み:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` を自動読み込みします。
- 読み込み順: OS環境変数 > .env.local > .env
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（コード例）

以下は主要な操作の最小例です。適宜ログ設定や例外処理を追加して運用してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema, get_connection

# ファイルに永続化する場合
conn = init_schema("data/kabusys.duckdb")

# またはインメモリ
# conn = init_schema(":memory:")
```

2) 日次 ETL 実行（J‑Quants からデータ取得→保存→品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

ETLResult フィールド:
- target_date: 処理対象日
- prices_fetched / prices_saved: 株価の取得・保存数
- financials_fetched / financials_saved: 財務データの取得・保存数
- calendar_fetched / calendar_saved: カレンダーの取得・保存数
- quality_issues: 品質チェックで検出された問題リスト
- errors: 実行中に発生したエラー概要文字列リスト

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄コードの集合（例:  "7203", "6758" 等）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

4) RSS を直接フェッチして記事を解析する
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for art in articles:
    print(art["id"], art["datetime"], art["title"])
```

5) 監査スキーマ初期化（発注/約定トレース用）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 重要な実装・運用上の注意

- J‑Quants API のレート制限は厳守する必要があります（内部で 120 req/min に合わせた制御あり）。
- ネットワーク障害やサーバエラー（429/408/5xx）に対しては自動リトライ（指数バックオフ）する設計です。401 は自動的にトークンリフレッシュして 1 回リトライします。
- ETL は差分更新かつバックフィルを行い、API 側での後出し修正を吸収する設計です。
- DuckDB に対する挿入は多くが ON CONFLICT を使い冪等性を担保しています。外部から直接テーブルを弄る場合は注意してください。
- news_collector は SSRF や XML BOM/XXE、gzip bomb、メモリ DoS などへの対策を実装していますが、運用環境ではさらにリクエスト先のホワイトリスト運用等の追加制限を検討してください。
- カレンダー情報がない場合は土日フォールバックで判定しますが、明確なJPXカレンダー取得を推奨します。

---

## ディレクトリ構成

リポジトリの主要ファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数管理・自動 .env ロード
  - data/
    - __init__.py
    - jquants_client.py      — J‑Quants API クライアント（取得・保存ロジック）
    - news_collector.py      — RSS ニュース収集・前処理・銘柄抽出・保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py — マーケットカレンダー管理・営業日判定
    - audit.py               — 監査ログスキーマ（信頼できるトレーサビリティ）
    - quality.py             — データ品質チェック
  - strategy/                 — 戦略モジュール（未実装のエントリポイント）
  - execution/                — 発注・約定モジュール（未実装のエントリポイント）
  - monitoring/               — 監視用モジュール（プレースホルダ）

---

## トラブルシューティング

- 環境変数が不足している場合:
  - config.Settings のプロパティ（例: settings.jquants_refresh_token）が ValueError を投げます。必要な環境変数を .env へ追加してください。
- DuckDB 接続エラー:
  - 指定パスの親ディレクトリが存在しない場合、init_schema は自動で作成します。get_connection を用いる場合はパスを確認してください。
- RSS 取得でエラーが多い場合:
  - タイムアウト、ホストのプライベート IP 判定、またはレスポンスサイズ超過の可能性があります。ログを確認して対象フィードを検証してください。

---

## 参考・拡張ポイント

- 実運用では Slack 通知や監視ジョブ（cron / Airflow など）と組み合わせて ETL の成功/失敗をアラートすることを推奨します。
- strategy / execution モジュールに戦略ロジック・ブローカー接続を実装し、audit テーブルに記録することで取引フローの完全トレーサビリティを確保できます。
- known_codes（銘柄集合）は銘柄マスタを別途保持し、news_collector の銘柄抽出に利用してください。

---

ライセンスや貢献ルールなどのメタ情報はこの README に追加してください。必要ならサンプルの requirements.txt や .env.example を生成することも可能です。