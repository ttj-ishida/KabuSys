# KabuSys

日本株自動売買システム用ライブラリ（KabuSys）。  
データ取得・ETL、データ品質チェック、DuckDBスキーマ定義、監査ログ（発注→約定トレース）などを提供するモジュール群です。

バージョン: 0.1.0

---

## 概要

KabuSys は主に次を目的とした内部ライブラリです。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得するクライアント
- DuckDB を用いたデータスキーマ定義・初期化
- ETL（差分取得・保存）パイプライン（idempotent）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）

設計上の特徴：

- API レート制御（120 req/min）
- リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
- 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を抑制
- DuckDB への保存は ON CONFLICT DO UPDATE による冪等性を確保

---

## 機能一覧

- データ取得（jquants_client）
  - 株価日足（OHLCV）: fetch_daily_quotes
  - 財務データ（四半期 BS/PL）: fetch_financial_statements
  - JPX マーケットカレンダー: fetch_market_calendar
  - 認証: get_id_token（リフレッシュトークン → idToken）
- DuckDB スキーマ（data.schema）
  - Raw / Processed / Feature / Execution 層テーブル定義
  - init_schema(db_path) による初期化
  - get_connection(db_path) で接続取得
- ETL（data.pipeline）
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl: 日次 ETL（カレンダー取得 → 株価 → 財務 → 品質チェック）
  - 差分取得・backfill ロジックを内蔵
- 品質チェック（data.quality）
  - 欠損チェック、スパイク検出、重複、日付不整合
  - run_all_checks でまとめて実行
- 監査ログ（data.audit）
  - signal_events, order_requests, executions テーブル
  - init_audit_schema / init_audit_db による初期化
- 設定管理（config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - Settings クラス経由で環境変数にアクセス
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## セットアップ手順

※ プロジェクトは src/ 配下のパッケージ構成を前提としています。

1. Python 環境の作成（推奨: venv）:
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージをインストール（例: duckdb が必要）:
   - 簡易:
     ```
     pip install duckdb
     ```
   - パッケージとして開発インストール可能（プロジェクトルートに setup/pyproject がある前提）:
     ```
     pip install -e .
     ```

3. 環境変数 (.env) を準備:
   プロジェクトルートに `.env`（または `.env.local`）を作成してください。最低でも以下は設定する必要があります（Settings にて必須指定）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   その他（任意/デフォルトあり）:
   - KABUS_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development / paper_trading / live; デフォルト development)
   - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

   自動読み込みを無効にする場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

4. DuckDB スキーマ初期化:
   Python REPL またはスクリプトから初期化します（デフォルト path は settings.duckdb_path）:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

5. 監査ログ（別途）初期化（必要に応じて）:
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)  # conn は init_schema の接続
   ```

---

## 使い方（例）

- 簡単な日次 ETL 実行例:
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を渡して特定日を指定可能
  print(result.to_dict())
  ```

- J-Quants から特定銘柄の株価を直接取得:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes

  records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  ```

- id_token を明示的に取得（テストや直アクセス時）:
  ```python
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- 品質チェック単体実行:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- audit テーブル初期化（監査ログ専用 DB を作る場合）:
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

注意点:
- Settings の必須環境変数が未設定だと ValueError が送出されます。例: settings.jquants_refresh_token を参照するコードを呼ぶ前に `.env` を正しく設定してください。
- J-Quants クライアントは内部でレート制御・リトライを行いますが、呼び出し頻度に注意してください。

---

## ディレクトリ構成

主要ファイルと役割（プロジェクトルートの src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存関数）
    - schema.py             — DuckDB スキーマ定義・初期化
    - pipeline.py           — ETL パイプライン（差分更新・品質チェック）
    - quality.py            — データ品質チェック
    - audit.py              — 監査ログ（signal/order_request/executions）
    - pipeline.py           — ETL 実装（同上）
    - audit.py              — 監査ログスキーマ（同上）
  - strategy/
    - __init__.py           — 戦略関連（将来的に拡張）
  - execution/
    - __init__.py           — 発注・実行関連（将来的に拡張）
  - monitoring/
    - __init__.py           — モニタリング関連（将来的に拡張）

（README に掲載の構成はコードベースの抜粋に基づきます）

---

## トラブルシューティング

- .env が読み込まれない:
  - プロジェクトルートが `.git` または `pyproject.toml` を基準に検出されます。これらがない場合は自動ロードしません。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていないか確認してください。
- Settings で ValueError が発生:
  - 必要な環境変数が未設定です。エラーメッセージに従い `.env` を整備してください。
- DuckDB 接続エラー:
  - ファイルパスの親ディレクトリが存在しないと自動作成されますが、書き込み権限やファイルロックに注意してください。
- J-Quants API 関連:
  - レート制限・HTTP エラーはモジュール側でリトライされますが、429 応答時は Retry-After ヘッダに従います。
  - 401 が返るとトークンを自動でリフレッシュして再試行します（1 回のみ）。

---

## 開発メモ / 拡張ポイント

- strategy/ と execution/ は将来的に戦略実装・発注ブリッジなどを拡張するための空パッケージです。
- モニタリング（Slack通知等）は config の設定を活用して実装可能です（SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）。
- ETL の品質チェックは fail-fast しない設計です。呼び出し側で結果の severities を見て運用判断してください。

---

必要があれば README にサンプル .env.example、CLI の使い方（cron/airflow 連携例）、テスト手順なども追記します。どの情報を優先して追加しますか？