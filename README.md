# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）。  
J-Quants API から市場データを取得して DuckDB に保存し、品質チェック・ニュース収集・カレンダー管理・監査ログなどデータ基盤と ETL を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを取得するクライアント
- DuckDB に対するスキーマ定義と初期化機能
- 日次 ETL（差分取得・バックフィル・品質チェック）のパイプライン
- RSS ベースのニュース収集と銘柄紐付け
- マーケットカレンダー管理（営業日判定、next/prev trading day 等）
- 監査ログ（signal → order → execution のトレース）用スキーマ

設計上、冪等性（ON CONFLICT による更新・重複排除）、API レート制御、リトライ、SSRF 対策、XML インジェクション対策などを考慮しています。

---

## 主な機能一覧

- J-Quants API クライアント
  - トークン自動リフレッシュ、指数バックオフによるリトライ、レートリミット（120 req/min）厳守
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB へ冪等保存する save_* 関数

- データベース（DuckDB）スキーマ管理
  - raw / processed / feature / execution / audit 層のテーブル定義
  - init_schema(db_path) による初期化

- ETL パイプライン
  - run_daily_etl: カレンダー取得 → 株価差分取得（backfill）→ 財務差分取得 → 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl : 個別ジョブ実行可能

- データ品質チェック
  - 欠損（OHLC 欠損）、スパイク検出、重複、日付不整合チェック
  - QualityIssue オブジェクトで詳細を返す

- ニュース収集
  - RSS から記事を取得し前処理（URL除去等）→ raw_news に冪等保存
  - 記事IDは URL 正規化の SHA-256（先頭32文字）
  - SSRF・Gzip bomb・XML 問題対策を実装

- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間差分更新

- 監査ログ
  - signal_events / order_requests / executions テーブルによるトレース
  - init_audit_schema による初期化

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.10+）

2. 必要パッケージをインストール（最低限）:
   - duckdb
   - defusedxml

   例:
   ```bash
   python -m pip install duckdb defusedxml
   ```

   （プロジェクト配布用の setup/pyproject があれば `pip install -e .` でインストールしてください）

3. 環境変数の設定（.env ファイル推奨）

   必須環境変数（実行に必要）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API のパスワード
   - SLACK_BOT_TOKEN       : Slack 通知で使用する Bot トークン
   - SLACK_CHANNEL_ID      : Slack 送信先チャンネル ID

   任意 / デフォルトあり:
   - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
   - LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL) — デフォルト: INFO
   - KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で自動 .env ロード無効化)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)

   自動読み込み:
   - パッケージはプロジェクトルート（.git または pyproject.toml）を探索し、OS環境変数 > .env.local > .env の順で自動ロードします。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. データベース初期化:
   - DuckDB のスキーマを作成するには以下を実行します（初回のみ）:

   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

   - 監査ログを別途有効化する場合:
   ```python
   from kabusys.data import audit
   audit.init_audit_schema(conn)  # 既存接続に監査テーブルを追加
   ```

---

## 使い方（例）

基本的な日次 ETL を実行する簡単な例:

```python
from kabusys.data import schema, pipeline

# DB 初期化（ファイルパスは設定に合わせて変更）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL（target_date を指定しない場合は今日）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

個別にニュース収集を実行する例:

```python
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")

# known_codes は銘柄抽出に使用する有効銘柄セット（None なら抽出スキップ）
known_codes = {"7203", "6758", "9984"}  # 例
stats = news_collector.run_news_collection(conn, known_codes=known_codes)
print(stats)
```

カレンダー夜間更新ジョブ:

```python
from kabusys.data import calendar_management, schema

conn = schema.init_schema("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved: {saved}")
```

J-Quants トークンを直接取得する例:

```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # 環境変数の JQUANTS_REFRESH_TOKEN を使用
```

設定値の参照:

```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env, settings.log_level)
```

ヒント:
- 自動 .env ロードを無効にして手動で設定したい場合は、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してから import してください。

---

## ディレクトリ構成

主なファイル / モジュール:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定の管理（自動 .env 読み込み）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save）
    - news_collector.py       — RSS ニュース収集・前処理・DB 保存
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - schema.py               — DuckDB スキーマ定義・初期化
    - calendar_management.py  — マーケットカレンダー管理（営業日判定等）
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログ（signal / order / execution）
    - pipeline.py             — ETL のオーケストレーション（差分取得・バックフィル）
  - strategy/                  — 戦略レイヤー（プレースホルダ）
  - execution/                 — 発注・ブローカー連携（プレースホルダ）
  - monitoring/                — 監視・メトリクス（プレースホルダ）

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / 推奨:
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV: development / paper_trading / live（動作モード）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

自動 .env の挙動:
- OS 環境変数 > .env.local > .env の順に読み込み（.env.local は .env を上書き）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化

サンプル .env（README 用の例）:
```
# .env.example
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 注意事項 / 実運用に関するメモ

- J-Quants API のレート制限（120 req/min）やリトライ動作はクライアント内で実装されていますが、運用側でもレートに配慮してください。
- ETL は差分更新とバックフィルを組み合わせて後出し（API の訂正）に耐える設計です。バックフィル日数はパラメータで調整可能です。
- DuckDB のスキーマは冪等に作成されます。運用前にスキーマを理解し、バックアップ運用を検討してください。
- ニュース収集は RSS ソースに依存します。既定のソースは Yahoo Finance（business）ですが、sources 引数で差し替えできます。
- セキュリティ: news_collector は SSRF・XML 脆弱性対策を施していますが、外部ソースの扱いには注意してください。
- 本ライブラリは戦略・注文実行レイヤー（strategy, execution）を含みますが、実ブローカー接続や資金管理を行う前に十分なテストとリスク管理を実施してください（特に live モード時）。

---

開発や利用で必要な追加情報があれば（導入手順の詳細、サンプル設定、CI/CD の例など）、用途に合わせて README を拡張します。