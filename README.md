# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。  
J-Quants API や kabuステーション を利用し、データ収集（ETL）、データ品質チェック、監査ログ（発注〜約定のトレーサビリティ）を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API からの市場データ取得（株価日足、財務、マーケットカレンダー）
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit）
- 日次 ETL パイプライン（差分取得、バックフィル、先読みカレンダー）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution の連鎖によるトレーサビリティ）
- 環境変数による設定管理（.env 自動読み込み、明示的設定可）

設計上の特徴：
- API レート制御（J-Quants: 120 req/min）の強制
- リトライ（指数バックオフ）とトークン自動リフレッシュ（401 の場合）
- DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL は Fail-Fast とはせず、品質チェック結果とエラーを収集して返却

---

## 主な機能一覧

- 環境設定管理（kabusys.config.Settings）
  - 自動で .env / .env.local をプロジェクトルートから読み込み（CWD 非依存）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークン → IDトークン）
  - レートリミット・リトライ・ページネーション対応
  - DuckDB へ保存する save_* 関数（save_daily_quotes 等）
- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path) で全テーブル・インデックスを作成
  - get_connection(db_path) で既存 DB に接続
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl(conn, ...)：市場カレンダー・株価・財務の差分取得 → 保存 → 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別ジョブも提供
  - 差分取得と backfill（既存最終取得日の数日前から取り直す）
- 品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合を SQL ベースで検出
  - QualityIssue オブジェクトで結果を返す
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルを提供
  - init_audit_schema(conn) / init_audit_db(db_path)

---

## 必要条件

- Python 3.10+
  - 型注釈（X | Y）やその他の構文を使用しています。
- 依存パッケージ（最低限）
  - duckdb
（その他は標準ライブラリのみ。実環境では HTTP/証券 API クライアント等が必要になる場合があります。）

例（仮想環境でのインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
# パッケージとしてインストールする場合:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンしてソースを準備
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨の .env キー例:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルトあり）

# Slack 通知（任意）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境/ログ
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
```

注意:
- 必須の環境変数が未設定の場合、kabusys.config.Settings のプロパティアクセス時に例外 (ValueError) が発生します。

---

## 使い方（簡単な例）

以下は Python スクリプトや REPL からの基本的な操作例です。

- DuckDB スキーマ初期化：
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は .env の DUCKDB_PATH を参照（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

- 監査スキーマ（audit）を初期化（既存接続へ追加）:
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

- 日次 ETL 実行:
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しないと今日が対象
print(result.to_dict())
```

- 個別ジョブ（価格のみ取得）:
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date(2026, 1, 1))
```

- J-Quants からデータ取得（直接呼び出す場合）:
```python
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))
# 保存は save_daily_quotes を利用
jq.save_daily_quotes(conn, records)
```

- 品質チェックを単独で実行:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## 環境変数と自動 .env 読み込みの挙動

- 自動読み込みの順序:
  OS 環境変数 > .env.local > .env
- 自動読み込みは、package の実体ファイル位置からプロジェクトルート（.git または pyproject.toml）を探索して行われます。CWD に依存しません。
- テストや CI で自動読み込みを無効にしたい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 主要モジュール API（サマリ）

- kabusys.config
  - settings: Settings インスタンス（各種設定をプロパティで取得）
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
- kabusys.data.quality
  - run_all_checks(conn, ...)
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## ディレクトリ構成

（リポジトリの主要ファイル一覧: src 内を抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/        # 発注周りの将来的な実装（空の __init__）
    - strategy/         # 戦略関連の将来的な実装（空の __init__）
    - monitoring/       # 監視関連（空の __init__）
    - data/
      - __init__.py
      - jquants_client.py    # J-Quants API クライアント + 保存ロジック
      - schema.py           # DuckDB スキーマ定義と初期化
      - pipeline.py         # ETL パイプライン
      - audit.py            # 監査ログスキーマ
      - quality.py          # データ品質チェック

---

## 運用上の注意 / 実装上のポイント

- J-Quants API のレート制限（120 req/min）に準拠するため内部でスロットリングしています。大量データ取得時は時間がかかる点に注意してください。
- トークン自動更新とリトライロジックを備えていますが、プロダクションではネットワーク障害や API サービス低下に対する追加の監視・アラートが必要です。
- DuckDB は軽量で高速ですが、監査ログ等は削除しない前提のためディスク管理（バックアップ、アーカイブ）を検討してください。
- run_daily_etl は各ステップで例外捕捉をし、処理を継続します。戻り値の ETLResult で errors / quality_issues を確認して運用判断をしてください。
- KABUSYS_ENV の値は development / paper_trading / live のいずれかにしてください。live を有効にする場合は特に発注ロジックの安全性を十分に確認してください。

---

## 開発・拡張

- strategy や execution モジュールは将来的に戦略ロジック・ブローカー連携を実装する想定です。
- ETL・品質チェックの SQL は DuckDB 上で実行されるため、必要に応じてクエリやインデックスを追加してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して意図した環境変数でテストを行うとよいです。

---

ご不明点や追加したいドキュメント（例: DataSchema.md、DataPlatform.md に紐づく詳細設計書、実行スクリプト例など）があれば教えてください。README に追記してお渡しします。