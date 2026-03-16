# KabuSys

日本株向け自動売買システム用ライブラリ / ツールセット

このリポジトリは、J-Quants API から市場データを取得して DuckDB に保存し、
品質チェック・監査ログ・ETL パイプラインを提供する基盤モジュール群です。
戦略・発注・監視は別モジュール（strategy / execution / monitoring）で実装します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の機能を持つデータ基盤・運用基盤ライブラリです。

- J-Quants API からの日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution を UUID 連鎖でトレース）
- 環境変数による設定管理（.env 自動ロード機能）

設計上のポイント:
- J-Quants API のレート制限（120 req/min）を固定間隔スロットリングで遵守
- リトライ（指数バックオフ、最大 3 回）、401 での自動トークンリフレッシュ
- DuckDB への INSERT は冪等（ON CONFLICT DO UPDATE）
- 品質チェックは Fail-Fast とせず全件収集して呼び出し元が判断可能

---

## 主な機能一覧

- data/jquants_client.py
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - get_id_token（リフレッシュトークンから id_token を取得）
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - レートリミッタ、リトライ、401 自動リフレッシュ実装

- data/schema.py
  - DuckDB 用のテーブル定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) で DB 初期化（テーブル作成・インデックス作成）
  - get_connection

- data/pipeline.py
  - run_daily_etl(conn, target_date=...)：日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl（差分更新・バックフィル対応）
  - ETLResult により実行結果を構造化

- data/quality.py
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks による一括実行、QualityIssue レポートを返却

- data/audit.py
  - 監査ログ用テーブルの初期化（signal_events / order_requests / executions）
  - init_audit_schema(conn) / init_audit_db(db_path)

- config.py
  - 環境変数読み込み補助（.env/.env.local の自動読み込み）
  - Settings クラス（必須変数の検証・便利プロパティ）
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 必要条件

- Python 3.10 以上（typing の | 演算子などを使用）
- duckdb
- 標準ライブラリ（urllib, json, logging 等）
- （オプション）プロジェクトをパッケージとしてインストールする場合は setuptools / pyproject ベースのツール

requirements.txt がある場合はそちらを参照してください。最低限は duckdb をインストールしてください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリを取得
   - git clone ...

2. 仮想環境作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. pip を更新し依存をインストール:
   - python -m pip install --upgrade pip
   - pip install duckdb
   - （プロジェクトを editable インストールしたい場合）pip install -e .

   ※ requirements.txt / pyproject.toml がある場合はそれに従ってください。

4. 環境変数の準備 (.env):
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` を作成すると自動で読み込まれます。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

例: .env（最低必要項目）
    JQUANTS_REFRESH_TOKEN=あなたの_jquants_リフレッシュトークン
    KABU_API_PASSWORD=あなたの_kabuステーション_パスワード
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    # 任意
    KABUSYS_ENV=development
    LOG_LEVEL=INFO
    DUCKDB_PATH=data/kabusys.duckdb
    KABU_API_BASE_URL=http://localhost:18080/kabusapi

---

## 環境変数（Settings）

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動読み込みを無効化
- KABUSYS_AUTO_ENV_ROOT を使わない場合はプロジェクトルート探索で .env/.env.local を読み込み
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

注意:
- .env のパースはシェル風の簡易パーサを実装しています（export KEY=VAL、クォート、コメント処理などに対応）。
- Settings は未設定の必須環境変数に対して ValueError を送出します。

---

## 使い方（代表的な例）

以下は README の目的上のサンプルです。実際はロガー設定やエラーハンドリングを追加してください。

- DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema

# デフォルトパスは settings.duckdb_path と合わせること
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（デフォルトで今日を対象に実行）

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # オプションで target_date / id_token 等を指定可能
print(result.to_dict())
```

- 個別 API 呼び出し例（トークン明示注入）

```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
id_token = get_id_token()  # settings.jquants_refresh_token から取得
records = fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,1,31))
saved = save_daily_quotes(conn, records)
```

- 監査ログテーブルの初期化（既存 conn に追加）

```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)  # 監査ログ用テーブルを追加（UTC タイムゾーン指定）
```

- 品質チェックの実行（個別利用）

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=None)  # list[kabusys.data.quality.QualityIssue]
for i in issues:
    print(i)
```

---

## 実装上の注意（運用・開発者向け）

- J-Quants API 周り
  - レート制限: 120 req/min（モジュール内の _RateLimiter が固定間隔でスロットリング）
  - リトライ: 最大 3 回、408/429/5xx を対象に指数バックオフ。429 の場合は Retry-After ヘッダを優先。
  - 401 が来た場合はリフレッシュトークンで id_token を自動更新して再試行（ただし無限再帰防止あり）。
  - 取得時に fetched_at を UTC タイムスタンプで保存し、look-ahead bias を防ぐ設計。

- DuckDB への保存
  - save_* 関数は ON CONFLICT DO UPDATE を用いて冪等性を確保。
  - init_schema は親ディレクトリがなければ自動作成します（":memory:" はインメモリ DB）。

- ETL
  - デフォルトのバックフィルは 3 日（backfill_days）で、最終取得日の数日前から再取得して API 後出し修正を吸収。
  - ETL の各ステップは独立して例外処理を行い、1 ステップ失敗でも他ステップの処理を続行する（結果オブジェクトに errors を格納）。

- 品質チェック
  - 各チェックは QualityIssue のリストを返す。呼び出し側は severity を見て停止・警告などの処理を行ってください。
  - スパイク判定のデフォルト閾値は 50%（設定可能）。

---

## ディレクトリ構成

（重要なファイルのみ抜粋）

- src/kabusys/
  - __init__.py            — パッケージのバージョン等
  - config.py              — 環境変数と設定読み込み
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得・保存ロジック）
    - schema.py            — DuckDB スキーマ定義・init_schema/get_connection
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - quality.py           — データ品質チェック
    - audit.py             — 監査ログ（signal/order_request/executions）
    - pipeline.py
  - strategy/
    - __init__.py          — 戦略モジュール（拡張用）
  - execution/
    - __init__.py          — 発注/約定管理モジュール（拡張用）
  - monitoring/
    - __init__.py          — 監視/メトリクスモジュール（拡張用）

---

## 開発メモ / 補足

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を元に行います。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。
- 時刻は監査テーブル初期化で UTC を採用（init_audit_schema 内で SET TimeZone='UTC' を実行）。
- SQLite（SQLITE_PATH）はモニタリング用など拡張用途を想定しています（settings で管理）。

---

必要であれば、README に含める実行スクリプト例（systemd/cron 用のラッパー、Dockerfile、CI ワークフローなど）や .env.example のテンプレートも作成します。どの情報を追加しますか？