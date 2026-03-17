# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
J-Quants や RSS を使ったデータ収集、DuckDB ベースのスキーマ、ETL パイプライン、ニュース収集、監査ログなどを提供します。

## 主な特徴
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - API レート制御（120 req/min）、リトライ（指数バックオフ）、401 自動リフレッシュ対応
  - フェッチ時刻（fetched_at）を UTC で記録し Look-ahead Bias を抑制
- DuckDB ベースのスキーマ
  - Raw / Processed / Feature / Execution / Audit 層を想定したテーブル群を提供
  - 冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）を前提とした保存関数
- ETL パイプライン
  - 差分更新・バックフィル・品質チェック（欠損・重複・スパイク・日付不整合）を実行
- ニュース収集モジュール
  - RSS 取得 → テキスト前処理 → DuckDB へ冪等保存 → 銘柄コード紐付け
  - SSRF 対策、Gzip / size 制限、XML パースの安全化（defusedxml）
- 監査ログ（audit）
  - シグナル→発注要求→約定のトレーサビリティ用テーブル群を初期化
- 設定管理
  - .env / .env.local / 環境変数から設定を自動ロード（プロジェクトルート検出）

---

## 機能一覧（抜粋）
- kabusys.config
  - .env 自動読み込み、必須キーの取得（例: JQUANTS_REFRESH_TOKEN）
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.quality
  - 複数の品質チェック（欠損 / 重複 / スパイク / 日付不整合）
- kabusys.data.audit
  - init_audit_schema, init_audit_db（監査ログ用テーブル群）

---

## セットアップ手順

前提
- Python 3.10 以上（Union 型表記や型ヒントで | を使用）
- DuckDB, defusedxml を使います

1. リポジトリを取得
   git clone <リポジトリURL>
   cd <リポジトリ>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install duckdb defusedxml
   # またはパッケージを編集インストールする場合:
   pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動的に読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。
   - 必要な環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知に使うボットトークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネルID（必須）
   - 任意 / デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/…（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）

例: .env
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

---

## 使い方（基本例）

以下は Python REPL / スクリプト内での最小の使用例です。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を作成して全テーブルを作成
conn = init_schema("data/kabusys.duckdb")
```

2) 監査ログ用スキーマ（別 DB）初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

3) 日次 ETL を実行（J-Quants からデータ取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を省略すると今日を基準に実行
print(result.to_dict())
```

4) ニュース（RSS）を収集して保存
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# known_codes を渡すと記事中の4桁銘柄コードを検出し news_symbols に紐付けます
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

5) カレンダー更新ジョブ（夜間バッチ向け）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} records")
```

6) 品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

注意点:
- jquants_client の API 呼び出しはレート制御とリトライを備えていますが、実行時には J-Quants の利用規約やレート制限に注意してください。
- run_daily_etl() は内部で calendar → prices → financials → quality の順に実行し、各ステップは独立して例外処理されています。

---

## 環境変数（まとめ）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env の自動ロードを無効化

設定は .env / .env.local / OS 環境変数で行えます。ロード順は OS > .env.local > .env（config.py のコメント参照）。プロジェクトルートの検出は .git または pyproject.toml を基準に行われます。

---

## ディレクトリ構成（主要ファイル）
（リポジトリの src/kabusys 以下を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（.env 自動読込）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（フェッチ + 保存関数）
    - news_collector.py      — RSS ニュース収集・前処理・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py            — ETL パイプライン（差分更新 / backfill / 品質チェック）
    - calendar_management.py — マーケットカレンダー管理（営業日判定・更新ジョブ）
    - audit.py               — 監査ログ用テーブル初期化（order_request / executions 等）
    - quality.py             — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

各モジュールはそれぞれの責務（データ取得、保存、検査、監査など）に分離されています。DuckDB テーブルは冪等に作成／更新されるように設計されています。

---

## 運用上の注意 / ベストプラクティス
- 本リポジトリは実運用の要件（証券会社との約定処理、資金管理、リスク制御）を含むため、本番運用前に十分なテストを行ってください。
- 監査ログ（audit）を有効にすると、シグナルから約定までのトレースが可能になります。init_audit_schema / init_audit_db を利用して監査用テーブルを作成してください。
- .env.local は機密情報を含めることがあるため、バージョン管理には含めないでください。
- DuckDB のパフォーマンスやファイル保全のため、バックアップ戦略を検討してください。
- J-Quants API の仕様変更やレート制限は随時確認してください。

---

ご要望があれば、README に CI/CD の設定例、cron でのバッチ実行例、サンプル .env.example、あるいは運用チェックリスト (監視/アラート) などを追加できます。