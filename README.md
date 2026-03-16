# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得・スキーマ定義・監査ログ・データ品質チェックなど、トレーディング基盤の基礎機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、J-Quants API などの外部データソースから日本株データを取得し、DuckDB 上に整ったスキーマで保存・管理するためのモジュール群です。  
主な目的は以下のとおりです。

- J-Quants からの日次株価・財務データ・マーケットカレンダーの取得（自動レート制御・リトライ・トークンリフレッシュ付き）
- DuckDB に対するスキーマ定義と初期化（Raw / Processed / Feature / Execution の多層スキーマ）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- 環境変数管理（.env 自動ロード機能）

設計上の留意点：
- API レート制限（J-Quants: 120 req/min）を尊重する RateLimiter を実装
- リトライ（指数バックオフ）・401 時のトークン自動再発行
- データ取得時に fetched_at を UTC で記録して Look-ahead Bias を抑制
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）を意識

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード（必要に応じて無効化可能）
  - 必須環境変数の検査（例: JQUANTS_REFRESH_TOKEN 等）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - get_id_token（リフレッシュトークンから id_token 取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - API レート制御・リトライ・トークン自動リフレッシュ
  - DuckDB へ保存するユーティリティ: save_daily_quotes / save_financial_statements / save_market_calendar
- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path) により全テーブル・インデックスを作成（冪等）
  - get_connection(db_path) で既存 DB に接続
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL と初期化関数
  - init_audit_schema(conn) / init_audit_db(db_path)
- データ品質チェック（kabusys.data.quality）
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks でまとめて実行し QualityIssue のリストを返す

---

## 動作環境・依存

- Python 3.10 以上（PEP 604 の型記法 (A | B) を使用）
- 主要依存パッケージ（例）
  - duckdb
- ネットワークアクセス: J-Quants API を利用するためインターネット接続が必要

（実際のセットアップに必要なパッケージは pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. Python 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージのインストール（例）
   ```bash
   pip install duckdb
   # もしパッケージ配布を想定しているなら:
   # pip install -e .
   ```

3. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml がある場所）に `.env` や `.env.local` を置くと自動でロードされます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須の環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   オプション
   - KABU_API_BASE_URL: kabu API のベース（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（モニタリング）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: environment（development / paper_trading / live）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN="your_refresh_token"
   KABU_API_PASSWORD="your_kabu_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   DUCKDB_PATH="data/kabusys.duckdb"
   ```

4. DuckDB スキーマ初期化
   Python REPL やスクリプトからスキーマを初期化します。

   例:
   ```python
   from kabusys.config import settings
   from kabusys.data import schema

   conn = schema.init_schema(settings.duckdb_path)
   ```

5. 監査ログの初期化（必要に応じて）
   既存 conn に監査テーブルを追加する場合:
   ```python
   from kabusys.data import audit
   audit.init_audit_schema(conn)
   ```
   新しく監査用 DB を作る場合:
   ```python
   conn_audit = audit.init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主要ユースケース）

以下は代表的な利用例です。実際のアプリケーションでは例外処理やログ出力、バックオフ／ジョブスケジューラ等を組み合わせてください。

1) J-Quants から日次株価を取得して DuckDB に保存する
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings

# DB 接続の準備
conn = init_schema(settings.duckdb_path)

# データ取得（例: 銘柄コード 7203 について過去1か月分）
from datetime import date, timedelta
today = date.today()
records = fetch_daily_quotes(code="7203", date_from=today - timedelta(days=30), date_to=today)

# DuckDB に保存（冪等）
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

2) 財務データやマーケットカレンダーも同様に fetch_* → save_* を使用可能
- fetch_financial_statements / save_financial_statements
- fetch_market_calendar / save_market_calendar

3) データ品質チェックの実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)  # 全件チェック
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
```

4) 監査ログへの書き込み（アプリ側で適宜 INSERT 実行）
監査テーブルは init_audit_schema() により作成されます。order_request_id を冪等キーとして利用し、二重発注を防止する設計です。

---

## 重要な実装上の注意点

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストなどで自動ロードを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のレート制限を守るため、内部で固定間隔の RateLimiter を利用しています（120 req/min）。
- HTTP エラー時にはリトライ（指数バックオフ）を行います。401 はトークンの自動リフレッシュを試行します（ただし無限再帰を防ぐ設計）。
- DuckDB に保存する際は ON CONFLICT DO UPDATE により冪等性を担保しています。
- 監査ログのタイムスタンプは UTC で保存する前提です（init_audit_schema は TimeZone='UTC' を設定します）。

---

## ディレクトリ構成

リポジトリ内の主要ファイルとディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境設定・.env ロード・settings
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得・保存ロジック）
    - schema.py              -- DuckDB スキーマ定義・初期化
    - audit.py               -- 監査ログテーブル定義・初期化
    - quality.py             -- データ品質チェック機能
  - strategy/
    - __init__.py            -- 戦略関連モジュール配置場所（拡張用）
  - execution/
    - __init__.py            -- 発注・ブローカー連携関連（拡張用）
  - monitoring/
    - __init__.py            -- 監視・メトリクス関連（拡張用）

README の記載はここまでですが、実際に運用する際は以下も検討してください：

- 運用用ジョブスケジューラ（cron / airflow / prefect 等）による定期取得
- 監視・アラート（Slack 連携機能の活用）
- テスト用のモック / VCR で外部 API 呼び出しを制御
- データバックアップ・バージョニング方針

---

## 連絡先・貢献

このリポジトリの目的はトレーディング基盤の基礎機能の提供です。Issue や Pull Request を歓迎します。大きな設計変更や互換性のある API の追加は事前に Issue で議論してください。