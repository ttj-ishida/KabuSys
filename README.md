# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（データ取得・ETL・スキーマ・監査ログ等）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するための内部ライブラリ集合です。主に以下を提供します。

- J-Quants API からの市場データ（株価日足・財務・マーケットカレンダー）取得クライアント
- DuckDB を用いたデータスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ用スキーマ（シグナル → 発注 → 約定 のトレーサビリティ）

設計上の特徴:
- J-Quants API のレート制限（120 req/min）を尊重する RateLimiter 実装
- リトライ（指数バックオフ、401 は自動トークンリフレッシュ）／ページネーション対応
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- ETL は差分取得／バックフィルを標準とし、品質チェックは Fail-Fast ではなく問題を収集して返す

---

## 主な機能一覧

- data.jquants_client
  - get_id_token、fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar
  - save_daily_quotes、save_financial_statements、save_market_calendar（DuckDB への冪等保存）
  - 高信頼な HTTP リトライとレート制御、ページネーション対応

- data.schema
  - DuckDB のテーブル定義と初期化（init_schema / get_connection）

- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - 差分取得（最終取得日からの差分、バックフィル）、品質チェック実行

- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（まとめ実行、QualityIssue を返す）

- data.audit
  - 監査ログ用テーブル定義と初期化（init_audit_schema / init_audit_db）

- 設定管理（kabusys.config）
  - .env/.env.local の自動ロード（プロジェクトルート判定あり）
  - 必須環境変数検査、settings オブジェクト経由でアクセス

---

## 必要環境

- Python 3.10 以上（PEP604 の型記法などを使用）
- duckdb
- ネットワークアクセス（J-Quants API）

必要な Python パッケージはプロジェクト側で管理してください（例: requirements.txt / pyproject.toml）。

---

## 環境変数 / .env

kabusys.config.Settings で参照する主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env 読み込みを無効化

自動読み込み:
- プロジェクトルート（このモジュールファイルの親を辿り `.git` または `pyproject.toml` を見つけた場所）が見つかれば、
  そのルートの `.env` を先に読み、続けて `.env.local` を上書き読み込みします（OS 環境変数は保護されます）。

簡単な .env の例:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順（ローカル実行向け）

1. Python 環境を用意（3.10+）
2. 依存パッケージをインストール（例）
   - pip install duckdb
   - その他、プロジェクトで管理しているパッケージをインストール
3. プロジェクトルートに `.env`（必要な環境変数）を配置
4. DuckDB スキーマを初期化（次の「使い方」参照）

備考:
- テスト等で自動.envロードを抑制したい場合は、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（例）

以下は対話的 / スクリプトでの基本的な使用例です。

- DuckDB スキーマの初期化（ファイルに作成）
```python
from kabusys.config import settings
from kabusys.data import schema

conn = schema.init_schema(settings.duckdb_path)  # ファイルを作成して接続を返す
```

- 監査ログテーブルの初期化（既存 conn に追加）
```python
from kabusys.data import audit

audit.init_audit_schema(conn)
```

- J-Quants の ID トークン取得（明示的に）
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使用
```

- 単体データ取得（株価日足）
```python
from kabusys.data.jquants_client import fetch_daily_quotes

quotes = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
```

- データを DuckDB に保存（fetch の結果を保存）
```python
from kabusys.data import jquants_client as jq

saved = jq.save_daily_quotes(conn, quotes)
```

- 日次 ETL の一括実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # デフォルトで今日を対象、品質チェックを実行
print(result.to_dict())
```

ETL の振る舞い:
- カレンダー → 株価 → 財務 の順で差分取得を行います。
- 差分判定は DB の最終取得日を参照し、backfill_days（デフォルト 3）分遡って再取得します。
- 品質チェック（欠損・重複・スパイク・日付不整合）は run_all_checks で実行され、問題を列挙して返します。

---

## 重要な挙動・注意点

- J-Quants API のレート制限: 120 req/min（モジュール内で固定間隔スロットリングにより制御）
- HTTP リトライ:
  - ネットワークエラーや 408/429/5xx に対しては指数バックオフで最大 3 回までリトライ
  - 401 が返された場合は自動的にリフレッシュして 1 回リトライ（無限再帰を回避）
- DuckDB への保存は ON CONFLICT DO UPDATE を用いて冪等化
- 全てのタイムスタンプは UTC を前提に扱う箇所があります（監査ログ初期化で TimeZone を UTC に設定）
- settings は起動時に環境変数の存在を検査します（必須変数がなければ ValueError）

---

## ディレクトリ構成

リポジトリの主要構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（差分更新・品質チェック）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ（signal / order_request / executions）定義
    - pipeline.py            — ETL 実行ロジック
  - strategy/
    - __init__.py            — 戦略層（拡張ポイント）
  - execution/
    - __init__.py            — 発注・ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視周り（拡張ポイント）

主要なテーブル層（schema.py 内定義）:
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- Audit (監査): signal_events, order_requests, executions

---

## ログとデバッグ

- settings.log_level でログレベルを設定（環境変数 LOG_LEVEL）
- 各モジュールは標準的な logging でログ出力します。必要に応じてハンドラを設定してください。

---

## テスト / 開発のヒント

- 自動 .env 読み込みを無効にする:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- インメモリ DuckDB を使う（ユニットテスト）:
  - db_path に ":memory:" を渡して schema.init_schema(":memory:")

---

## 拡張ポイント

- strategy、execution、monitoring パッケージは現状空の初期化ファイルのみですが、戦略ロジック、注文ブローカー連携、監視アラート機能などを実装するための拡張ポイントとして用意されています。

---

必要に応じて README にサンプルスクリプトや CI／デプロイ手順を追記できます。追加したい内容（例: CLI、docker-compose、実行スクリプト例など）があれば教えてください。