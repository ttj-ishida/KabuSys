# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・データ基盤ライブラリ群です。J-Quants や kabuステーション 等の外部 API から市場データを取得して DuckDB に蓄積し、ETL・品質チェック・監査ログ・発注フローの基盤を提供します。

主な設計方針:
- レート制限・リトライ・トークン自動リフレッシュなど API 安全性を重視
- DuckDB を中心とした冪等（idempotent）なデータ保存
- ETL の差分更新・バックフィル・品質チェックを統合
- シグナル→発注→約定までトレース可能な監査ログ設計

---

## 機能一覧

- 環境・設定管理
  - .env/.env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数の取得とバリデーション
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - API レート制御（120 req/min 固定間隔スロットリング）
  - 再試行（指数バックオフ、最大 3 回）・401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）記録による Look-ahead Bias の抑制
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution（監査・発注）階層のテーブル定義
  - 初期化ユーティリティ（init_schema / init_audit_schema）
- ETL パイプライン
  - 差分更新（最終取得日ベース）と backfill（デフォルト 3 日）
  - カレンダーの先読み（デフォルト 90 日）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL の統合エントリ（run_daily_etl）
- データ品質チェック
  - 欠損データ、スパイク、主キー重複、日付不整合の検出
  - 問題は QualityIssue オブジェクトとして収集（Fail-Fast ではなく全件収集）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル
  - UUID ベースの冪等キーと時刻（UTC）管理

---

## セットアップ手順

前提:
- Python 3.10 以上（コードベースは型注釈に `X | None` を利用）
- DuckDB を使用します

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 最小限: duckdb
     - pip install duckdb
   - 必要に応じてロギングや Slack 通知等のクライアントを追加してください（本リポジトリ内に直接依存定義は含まれていません）。

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` または `.env.local` を置くと自動でロードされます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（少なくとも ETL や API 利用に必要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン（必要に応じて）
- SLACK_CHANNEL_ID: Slack に通知するチャンネル ID

任意 / デフォルト設定
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）

.env の例（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本例）

以下はライブラリを使って DuckDB スキーマを初期化し、日次 ETL を実行する最小サンプルです。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリを自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 監査ログテーブルの初期化（既存接続へ追加）
```python
from kabusys.data import audit

# init_schema() で得た conn を渡して監査テーブルを初期化
audit.init_audit_schema(conn)
```

3) 日次 ETL 実行
```python
from kabusys.data import pipeline
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
result = pipeline.run_daily_etl(conn)  # target_date を指定することも可

print(result.to_dict())
```

4) J-Quants API を直接使ってデータ取得→保存
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
import duckdb
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用して取得
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2022,1,1), date_to=date(2022,1,31))
jq.save_daily_quotes(conn, records)
```

注意点:
- get_id_token() から取得した id_token はモジュールキャッシュされ、ページネーション間で共有されます。401 が返った場合は自動でリフレッシュして 1 回リトライする実装です。
- ETL は各ステップで例外を捕捉して処理を継続する設計のため、戻り値の ETLResult を参照して問題の有無を判断してください。

---

## 主要 API の説明（抜粋）

- kabusys.config.settings
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live / is_paper / is_dev

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(id_token: str | None, code: str | None, date_from: date | None, date_to: date | None) -> list[dict]
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int

- kabusys.data.schema
  - init_schema(db_path) -> duckdb connection
  - get_connection(db_path) -> duckdb connection

- kabusys.data.pipeline
  - run_prices_etl(conn, target_date, ...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(...) -> ETLResult

- kabusys.data.quality
  - run_all_checks(conn, target_date, reference_date, spike_threshold) -> list[QualityIssue]

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## ディレクトリ構成

リポジトリ内の主要ファイル / モジュール構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロードと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント実装（取得・リトライ・レート制御・保存）
    - schema.py
      - DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution）
    - pipeline.py
      - ETL パイプライン（差分取得、backfill、品質チェック）
    - audit.py
      - 監査ログ用スキーマと初期化（signal_events / order_requests / executions）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py
    - （戦略関連モジュールを追加する場所）
  - execution/
    - __init__.py
    - （発注・ブローカー連携実装を追加する場所）
  - monitoring/
    - __init__.py
    - （監視・アラート関連を追加する場所）

---

## 注意事項・運用上のヒント

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。CI やテスト時に自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかを指定してください。live モードでは実際の発注が行われる想定のため、十分なテストと安全策を講じてください。
- DuckDB の初期化は一度行えば再度スキーマを作成しません（冪等）。監査ログは init_schema() の後に init_audit_schema() を呼ぶ運用を推奨します。
- J-Quants のレート制限・リトライロジックは実装済みですが、大量データ取得・バックフィル時は API 利用制限に注意してください。
- 品質チェックは重大度に応じて ETL 停止を呼び出し側で判断する設計です。自動運用では重大な品質エラー発生時に通知・人手介入する仕組みを併設してください（例: Slack 通知、監視ダッシュボード）。

---

この README はコードベースの現状（version 0.1.0）をもとに作成しています。戦略実装（strategy/*）や発注連携（execution/*）、監視（monitoring/*）は拡張を想定したプレースホルダが用意されています。必要に応じて README を更新して運用手順や依存関係を明確化してください。