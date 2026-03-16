# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ（プロトタイプ）

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。  
主に次を提供します。

- J-Quants API からの市場データ取得（株価日足・財務情報・市場カレンダー）
- DuckDB を用いたデータスキーマ定義と永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・保存・品質チェック）
- 監査ログ（戦略→シグナル→発注→約定のトレーサビリティ）

設計上のポイント:
- API レート制御（120 req/min）とリトライ（指数バックオフ、401 自動リフレッシュ対応）
- データ取得時に fetched_at を UTC で記録し、Look-ahead Bias に配慮
- DuckDB へは冪等的に保存（ON CONFLICT DO UPDATE）
- 品質チェックは Fail-Fast ではなく、問題を網羅的に収集して呼び出し元で判断可能にする

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（認証、ページネーション、レート制御、リトライ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar

- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema / get_connection

- data/pipeline.py
  - 日次 ETL（run_daily_etl）および個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 差分更新、バックフィル、品質チェック呼出し

- data/quality.py
  - データ品質チェック（欠損、スパイク、重複、日付整合性）
  - run_all_checks（QualityIssue のリストを返す）

- data/audit.py
  - 監査ログ用スキーマ（signal_events / order_requests / executions）と初期化ヘルパー
  - init_audit_schema / init_audit_db

- config.py
  - 環境変数管理（.env 自動読み込み、必須キー取得ヘルパー、環境種別判定）
  - 環境変数で KABUSYS_ENV（development / paper_trading / live）を制御
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

- strategy/, execution/, monitoring/
  - パッケージプレースホルダ（戦略・発注・監視ロジック用）

---

## 前提 / 必要環境

- Python 3.10 以上（| 型注釈などを使用）
- 必要な Python パッケージ（例）
  - duckdb
  - （標準ライブラリ：urllib 等を使用）
- J-Quants のリフレッシュトークン（API 利用）
- kabuAPI（kabuステーション）パスワード（発注モジュール利用時）
- Slack トークン/チャンネル（モニタリング用通知がある場合）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... または適切にプロジェクトを配置

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb
   - 必要に応じて他のライブラリを追加（例: Slack SDK 等）

   （プロジェクトに setup.py/pyproject.toml があれば）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を配置すると、config.py が自動読み込みします（CWD ではなくファイルの位置からプロジェクトルートを探索します）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   最低限必要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C12345678
   - (任意) DUCKDB_PATH=data/kabusys.duckdb
   - (任意) SQLITE_PATH=data/monitoring.db
   - (任意) KABUSYS_ENV=development|paper_trading|live
   - (任意) LOG_LEVEL=INFO

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_pass
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（簡単な例）

以下は Python スクリプト内で ETL を初期化して実行する例です。

1) DuckDB スキーマ初期化:
```
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数から取得されます（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2) 監査ログスキーマを追加（必要な場合）:
```
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

3) 日次 ETL を実行:
```
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# 省略時 target_date は今日
result = run_daily_etl(conn, target_date=None)

# 結果の確認
print(result.to_dict())
if result.has_errors:
    print("ETL 中にエラーが発生しました:", result.errors)
```

4) J-Quants の個別 API 呼び出し例:
```
from kabusys.data.jquants_client import fetch_daily_quotes

# モジュールは内部でトークンをキャッシュし自動リフレッシュします
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

5) 品質チェック (単独実行):
```
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

---

## 環境変数 / 設定（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（発注機能利用時に必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須として定義されている）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env の自動読み込みを無効にする

config.py の Settings API からアクセス可能:
- from kabusys.config import settings
- settings.jquants_refresh_token, settings.duckdb_path, settings.is_live など

---

## ディレクトリ構成

（リポジトリの src レイアウトを反映）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/                # 発注・ブローカー連携用パッケージ（未実装箇所あり）
      - __init__.py
    - strategy/                 # 戦略ロジック格納パッケージ（未実装箇所あり）
      - __init__.py
    - monitoring/               # 監視・アラート用パッケージ（未実装箇所あり）
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py       # J-Quants API クライアント（取得・保存）
      - schema.py               # DuckDB スキーマ定義・初期化
      - pipeline.py             # ETL パイプライン実装
      - audit.py                # 監査ログスキーマと初期化
      - quality.py              # データ品質チェック

---

## 開発上の注意点 / 実運用でのポイント

- J-Quants のレート制限（120 req/min）を厳守するため、jquants_client は内部でスロットリングを実施します。複数プロセスで同時に API を叩く場合はレート制御を工夫してください。
- DuckDB ファイルのパスは settings.duckdb_path で指定します。ファイルのバックアップ・排他制御（複数プロセス）に注意してください。
- run_daily_etl は品質チェックでエラーが見つかっても自動的には ETL を止めません。呼び出し元（運用スクリプト）で result.has_quality_errors / has_errors を判定してアクションを取ってください。
- 監査ログ（audit）は UTC タイムゾーンで運用を想定しています。init_audit_schema は接続に SET TimeZone='UTC' を実行します。
- .env のパースは Bash 系の .env 形式にある程度対応しています（export あり、クォート、コメントなど）。

---

## ライセンス / 責任

このリポジトリ自体にはライセンス表記が含まれていないため、実際に公開する際は適切なライセンスファイルを追加してください。  
また、本コードは投資助言を目的とするものではなく、実際の資金運用を行う場合は十分な検証と責任ある運用設計が必要です。

---

必要であれば README に「実行例の Python スクリプト」や「.env.example」のテンプレート、CI / デプロイ手順、テスト手順（pytest）などを追記します。どの情報を優先して追加しましょうか？