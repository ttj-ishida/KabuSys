# KabuSys

日本株自動売買プラットフォーム向けのライブラリ群。  
データ取得・ETL、DuckDB スキーマ定義、データ品質チェック、監査ログなどを提供し、戦略・発注層と連携して自動売買システムを構築するための基盤を提供します。

主な設計方針：
- J-Quants API からのデータ取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いた三層データレイヤ（Raw / Processed / Feature）と実行・監査レイヤ
- ETL は差分取得・冪等保存（ON CONFLICT DO UPDATE）・品質チェックを実行
- 監査ログによりシグナルから約定までをトレース可能に保つ

---

## 機能一覧
- 環境変数/設定管理（自動的にプロジェクトルートの `.env` / `.env.local` を読み込み）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レートリミット制御、リトライ、401→トークン自動リフレッシュ
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution レイヤ）
- 監査ログスキーマ（signal / order_request / executions）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 冪等保存（INSERT ... ON CONFLICT DO UPDATE）をサポート

---

## 動作環境
- Python 3.10 以上（型注釈に union 型（X | Y）を使用）
- 依存パッケージ（例）
  - duckdb
- ネットワーク接続: J-Quants API など外部 API へアクセス可能であること

必要最低限のインストール例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# プロジェクトを editable install する場合（パッケージ化されていれば）
# pip install -e .
```

---

## 環境変数（.env）
プロジェクトは `.env` と `.env.local` をプロジェクトルートから自動読み込みします（OS 環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（例）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト INFO）

簡易 `.env.example`（README 用）:
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発用）
1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール（例: duckdb）
4. プロジェクトルートに `.env` を配置して必要な環境変数を設定
5. DuckDB スキーマを初期化

例:
```bash
git clone <repo_url>
cd <repo_dir>
python -m venv .venv
source .venv/bin/activate
pip install duckdb

# プロジェクトルートに .env を作成する
cp .env.example .env
# 必要な値を編集

# Python REPL やスクリプトでスキーマ初期化
python - <<'PY'
from kabusys.config import settings
from kabusys.data import schema
conn = schema.init_schema(settings.duckdb_path)
print("DuckDB initialized:", settings.duckdb_path)
PY
```

---

## 使い方（主要ユースケース）

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data import schema

conn = schema.init_schema(settings.duckdb_path)
```
- 初回は DB ファイルの親ディレクトリを自動作成します。
- ":memory:" を渡すとインメモリ DB を使用します。

2) 監査ログスキーマの初期化（既存接続に追加）
```python
from kabusys.data import audit
audit.init_audit_schema(conn)
```
または監査専用 DB を初期化：
```python
audit_conn = audit.init_audit_db("data/audit.duckdb")
```

3) J-Quants API トークン取得（内部で settings.jquants_refresh_token を参照）
```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # settings からリフレッシュトークンを読み取る
```

4) 日次 ETL の実行
```python
from kabusys.config import settings
from kabusys.data import schema, pipeline

conn = schema.get_connection(settings.duckdb_path)  # 既に init_schema 済みを想定
result = pipeline.run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
# ETLResult で取得/保存件数、品質問題（quality_issues）、errors を確認可能
```

5) データ品質チェックを個別に実行
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

6) J-Quants からのデータ取得（直接呼び出し例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
```
- レート制限（120 req/min）やリトライはライブラリが自動制御します。

---

## 主要 API（概要）
- kabusys.config.settings
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live/is_paper/is_dev
- kabusys.data.schema
  - init_schema(db_path) -> DuckDB connection
  - get_connection(db_path) -> DuckDB connection
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None) -> str
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) / save_financial_statements / save_market_calendar
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...) -> ETLResult
  - run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.quality
  - run_all_checks(conn, ...) -> list[QualityIssue]
  - 個別チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## 注意点 / 実装上の要点
- 自動.envロード:
  - プロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を読み込みます。
  - `.env.local` は `.env` を上書きします（ただし OS の環境変数は保護されます）。
  - テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants クライアント:
  - レート制限（120 req/min）を固定間隔スロットリングで保証
  - リトライ: 指数バックオフ、最大 3 回（408/429/5xx を対象）
  - 401 受信時はリフレッシュして 1 回リトライ
  - 取得時に fetched_at を UTC タイムスタンプで記録して Look-ahead Bias を抑制
- 保存処理:
  - DuckDB への保存は ON CONFLICT DO UPDATE により冪等に実施
- ETL:
  - 差分取得を行い、デフォルトで最終取得日の数日前（backfill_days=3）から再取得して後出し修正を吸収
  - 品質チェックはエラーを収集するが、個別エラーが発生しても可能な限り処理を続行する（呼び出し側での判定が必要）
- 監査ログ:
  - シグナル→発注→約定のトレーサビリティを UUID で連鎖
  - すべての TIMESTAMP は UTC で保存する方針（init_audit_schema で SET TimeZone='UTC' を実行）

---

## ディレクトリ構成
以下は主要なパッケージとファイル（提供されたコードベースに基づく）：

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/                 (発注・約定管理関連のためのパッケージ)
      - __init__.py
    - strategy/                  (戦略関連のパッケージ)
      - __init__.py
    - monitoring/                (監視・メトリクス関連)
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py        (J-Quants API クライアント)
      - schema.py                (DuckDB スキーマ定義・初期化)
      - pipeline.py              (ETL パイプライン)
      - audit.py                 (監査ログスキーマ)
      - quality.py               (データ品質チェック)

その他、プロジェクトルートには通常以下が存在する想定です（このリポジトリでは省略されている可能性があります）:
- pyproject.toml / setup.cfg / requirements.txt
- .gitignore
- README.md（本ファイル）
- .env.example

---

## トラブルシューティング
- 環境変数が見つからない（ValueError）
  - settings の必須プロパティは未設定だと ValueError を投げます。`.env` の設定や OS 環境変数を確認してください。
- DuckDB のスキーマがない/テーブルがない
  - schema.init_schema() を実行して初期化してください。既存 DB に接続する場合は schema.get_connection() を使います。
- J-Quants リクエストが 401 で失敗する
  - リフレッシュトークン設定（JQUANTS_REFRESH_TOKEN）を確認してください。get_id_token を手動で呼び出してトークン発行を確認できます。
- レートリミットに達する
  - ライブラリはレート制限を守るよう設計されていますが、外部コードで並列に多数のリクエストを飛ばすと影響するので注意してください。

---

## ライセンス / 貢献
この README はコードベースの抜粋に基づく導入ドキュメントです。実際のプロジェクトでは LICENSE、CONTRIBUTING、CHANGELOG 等をリポジトリに追加して運用してください。

---

必要であれば、README に下記を追加できます：
- 実行のためのサンプルスクリプト（airflow / cron 巡回用）
- CI/CD 用の db 初期化手順
- 詳細な品質チェックの出力サンプル
- 実運用での注意点（バックテスト・paper_trading 運用フロー）