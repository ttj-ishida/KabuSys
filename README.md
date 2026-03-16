# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ（KabuSys）。  
J-Quants API からマーケットデータや財務データを取得し、DuckDB に保存・管理するための ETL、品質チェック、監査ログ機能を提供します。

バージョン: 0.1.0

主な目的:
- J-Quants から株価・財務・カレンダーを差分取得して永続化（DuckDB）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注・監査向けスキーマ定義（監査テーブルの初期化）
- ETL パイプライン（差分更新、バックフィル、先読み）

---

## 機能一覧

- 環境設定
  - .env / .env.local 自動ロード（プロジェクトルートの検出、無効化オプションあり）
  - 必須設定値の取り扱い（未設定時に例外を投げる）

- データ取得（J-Quants クライアント）
  - fetch_daily_quotes: 日足（OHLCV）をページネーション対応で取得
  - fetch_financial_statements: 四半期財務データ取得
  - fetch_market_calendar: JPX マーケットカレンダー取得
  - HTTP レート制限厳守（120 req/min）、リトライ（指数バックオフ、最大3回）、401 時のトークン自動リフレッシュ（1回）

- 永続化（DuckDB 用ユーティリティ）
  - idempotent な保存（ON CONFLICT DO UPDATE）: raw_prices, raw_financials, market_calendar など
  - スキーマ初期化: data.schema.init_schema(db_path)
  - 監査ログ（audit）テーブル初期化: init_audit_schema / init_audit_db

- ETL パイプライン
  - 差分取得ロジック（最終取得日に基づく差分 + backfill）
  - 市場カレンダーの先読み（デフォルト 90 日）
  - 日次 ETL 実行: run_daily_etl（各ステップの独立エラーハンドリング）
  - ETL 実行結果のデータクラス（ETLResult）

- データ品質チェック
  - 欠損データ検出（OHLC 欠損）
  - スパイク検出（前日比による閾値判定、デフォルト 50%）
  - 重複チェック（主キー重複）
  - 日付整合性チェック（未来日付、非営業日のデータ）
  - run_all_checks でまとめて実行し、QualityIssue オブジェクトのリストを返す

---

## セットアップ手順

前提
- Python 3.10 以上（型記法・Union 演算子 `|` を使用）
- pip が利用可能

1. リポジトリをクローン（あるいはプロジェクトソースを入手）
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージのインストール
   - 現時点で主に必要なのは duckdb（HTTP は標準ライブラリの urllib を使用）
   ```bash
   pip install duckdb
   ```
   - 開発・パッケージ管理に合わせて `pip install -e .` などを使ってください（プロジェクトに setup/pyproject がある想定）。

4. 環境変数設定
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` として以下の変数を設定してください（.env.example 等に合わせる）。

   必須:
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - KABU_API_PASSWORD=<kabu_station_api_password>
   - SLACK_BOT_TOKEN=<slack_bot_token>
   - SLACK_CHANNEL_ID=<slack_channel_id>

   任意／デフォルトあり:
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live) デフォルト development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) デフォルト INFO

   自動ロードを無効にする場合:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（主な例）

以下は Python からの利用例です。適宜ログ設定・例外処理を追加して下さい。

- DuckDB スキーマ初期化（1回だけ）
```python
from kabusys.data import schema

# ファイル DB を初期化
conn = schema.init_schema("data/kabusys.duckdb")

# またはインメモリ
# conn = schema.init_schema(":memory:")
```

- 監査ログ専用スキーマ初期化（既存の conn に追加）
```python
from kabusys.data import audit
audit.init_audit_schema(conn)
```

- 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())

# ETL 実行結果の確認
print(result.to_dict())
if result.has_errors:
    print("ETL 中にエラー発生:", result.errors)
if result.has_quality_errors:
    print("品質チェックで重大な問題が検出されました")
```

- J-Quants の生データ取得だけ行う例（ID トークンを明示的に渡すことも可能）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

# モジュールはトークンを内部キャッシュし、自動でリフレッシュします。
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
```

- データ品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## 重要な実装上の注意点 / 動作仕様

- 環境変数の自動読み込み
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を検索）から `.env` と `.env.local` を自動的に読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定します。

- J-Quants クライアント
  - レート制限: 120 req/min（固定間隔スロットリングで制御）
  - リトライ: 最大 3 回（指数バックオフ、429 の場合は Retry-After ヘッダ優先）
  - 401 受信時: リフレッシュトークンで ID トークンを取得して 1 回だけ再試行
  - ページネーション対応: pagination_key を用いて全件を取得
  - 取得時刻の記録: 保存時に fetched_at を UTC ISO8601 形式で保存し、Look-ahead Bias を防ぐ

- 永続化
  - DuckDB に対しては INSERT ... ON CONFLICT DO UPDATE を用い、冪等性を担保
  - 先に schema.init_schema() でテーブルを作成しておくこと

- ETL の差分ロジック
  - 初回ロード時は最小データ日（_MIN_DATA_DATE = 2017-01-01）から取得
  - 差分更新・バックフィル: 最終取得日の数日前から再取得することで API の後出し修正に対応（デフォルト backfill_days = 3）
  - 市場カレンダーは先読み（デフォルト 90 日）して営業日調整に使用

- 品質チェック
  - Fail-Fast ではなくすべてのチェック結果を収集して返す（呼び出し元が閾値に応じて判断する）
  - スパイク判定のデフォルト閾値は 50%

---

## ディレクトリ構成

プロジェクトの主要なファイル/ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得 + 保存）
    - schema.py              # DuckDB スキーマ定義 / init_schema / get_connection
    - pipeline.py            # ETL パイプライン（差分取得・run_daily_etl 等）
    - audit.py               # 監査ログ（signal / order_request / executions）初期化
    - quality.py             # データ品質チェック
    - pipeline.py
  - strategy/
    - __init__.py
    # （戦略モジュールを配置）
  - execution/
    - __init__.py
    # （発注・ブローカー連携モジュールを配置）
  - monitoring/
    - __init__.py
    # （Slack 連携などのモニタリング用コードを配置）

その他:
- .env, .env.local           # プロジェクトルートに置くと自動読み込みされる
- data/                     # データディレクトリ（デフォルトの DuckDB ファイル等）

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

推奨 / デフォルトあり:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) default: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) default: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動読み込みを無効化

---

## 付記 / 今後の拡張案

- strategy / execution / monitoring モジュールの具体実装（戦略ロジック、ブローカー API アダプタ、Slack 通知等）
- テスト群（ユニット・統合テスト）および CI の整備
- 更なる ETL 効率化（並列化や差分検出の最適化）
- メトリクス収集（Prometheus 等）による稼働監視

---

必要があれば、README をプロジェクトの実際のパッケージング手順（pyproject.toml / setup.cfg を用いた pip 配布）や CI 用の実行例、具体的な .env.example のテンプレートに拡張して作成します。どの部分をより詳しく書くか指定してください。