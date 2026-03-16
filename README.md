# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けに設計された Python パッケージ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、DuckDB スキーマ定義、監査ログなどを提供し、戦略・発注・監視モジュールと連携することを想定しています。

主な目的は：
- 市場データ（株価・財務・市場カレンダー）の安定的な取得と永続化
- データ品質の自動検査（欠損・スパイク・重複・日付不整合）
- 発注から約定までの監査ログ（トレーサビリティ）保持
- 戦略・実行・監視モジュールの基盤提供

バージョン: 0.1.0

---

## 機能一覧

- 環境変数/設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（OS環境変数優先）
  - 必須設定の明示・検証（例: JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ）・401 時の自動リフレッシュ
  - 取得時刻（UTC）を記録して Look-ahead バイアスを防止
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス作成、初期化関数 `init_schema` / `get_connection`

- ETL パイプライン (`kabusys.data.pipeline`)
  - 差分更新（最終取得日 + バックフィル考慮）
  - 日次 ETL エントリポイント `run_daily_etl`（カレンダー → 株価 → 財務 → 品質チェック）
  - 個別ジョブ（`run_prices_etl`, `run_financials_etl`, `run_calendar_etl`）
  - 品質チェックは Fail-Fast ではなく全件収集（結果は ETLResult に集約）

- 品質チェック (`kabusys.data.quality`)
  - 欠損データ検出、スパイク検出（前日比閾値）、重複チェック、日付整合性チェック
  - 問題は QualityIssue オブジェクトとして返却。重大度（error/warning）を含む

- 監査ログ（トレーサビリティ） (`kabusys.data.audit`)
  - シグナル → 発注要求 → 約定 の監査テーブル（UUID ベースの階層）
  - 発注の冪等キー（order_request_id）・ステータス管理
  - 別途初期化関数 `init_audit_schema` / `init_audit_db`

- パッケージ基盤
  - settings（環境設定）: J-Quants・kabuステーション・Slack・DB パス・実行環境判定など

※ strategy / execution / monitoring のパッケージ構成は用意されており、戦略や発注ロジックはここに実装していきます（現状はモジュール定義のみ）。

---

## 前提・依存

- Python 3.10 以上（型注釈に | を使用）
- 必須パッケージ（例）:
  - duckdb
- 標準ライブラリのみで動く箇所もありますが、データベース操作に duckdb が必要です。
- 実際の運用では J-Quants のリフレッシュトークンや kabuステーション のパスワード、Slack トークン等を設定する必要があります。

（プロジェクトの配布方法に応じて pyproject.toml / requirements.txt を用意して pip install してください）

---

## セットアップ手順

1. リポジトリをクローン / ワークディレクトリに移動。

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール（例）
   - pip install duckdb
   - その他プロジェクトが提供する requirements.txt または pyproject.toml があればそれを利用

4. 環境変数の設定
   - プロジェクトルートに `.env` を作成（`.env.local` は上書き用）
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - KABU_API_PASSWORD=<kabu_station_api_password>
     - SLACK_BOT_TOKEN=<slack_bot_token>
     - SLACK_CHANNEL_ID=<slack_channel_id>
   - 任意:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
   - 自動で .env を読み込ませたくない場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

例: .env の最低例
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. DuckDB スキーマの初期化
   - Python REPL / スクリプトで以下を実行して DB を作成・テーブルを初期化します。

例:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # settings.duckdb_path で .env の DUCKDB_PATH を参照
```

6. 監査ログを別途初期化する場合（任意）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

---

## 使い方（サンプル）

- 日次 ETL を実行して DuckDB にデータを入れる（最も典型的な操作）:

例: run_daily_etl を使った実行
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（既に存在する場合はスキップ）
conn = init_schema(settings.duckdb_path)

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn)

# 結果確認
print(result.to_dict())
if result.has_errors:
    print("ETL 中にエラーが発生しました:", result.errors)
if result.has_quality_errors:
    print("品質チェックにエラーが含まれます")
```

- 個別ジョブの実行:
  - 株価差分取得（例）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

- J-Quants API を直接呼んでデータ取得:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

id_token = get_id_token()  # settings からリフレッシュトークンを利用
quotes = fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,1,31))
```

- 品質チェックのみを実行:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

- ロギング設定:
  - 環境変数 LOG_LEVEL を設定すると settings.log_level で検証されます。アプリ起動側で logging.basicConfig(level=...) を行ってください。

---

## 設定（settings）解説

kabusys.config.Settings 経由で以下が取得可能です（プロパティ名）:

- jquants_refresh_token: J-Quants リフレッシュトークン（必須）
- kabu_api_password: kabuステーション API パスワード（必須）
- kabu_api_base_url: KABU API のベース URL（省略時ローカルデフォルト）
- slack_bot_token / slack_channel_id: Slack 通知用（必須）
- duckdb_path: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- sqlite_path: 監視用 SQLite パス（デフォルト data/monitoring.db）
- env: KABUSYS_ENV（development | paper_trading | live）
- log_level: LOG_LEVEL（DEBUG|INFO|...）
- is_live / is_paper / is_dev: env に基づく判定

.env 読み込みのルール:
- OS 環境変数 > .env.local > .env の順で優先度
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを行いません
- プロジェクトルートの判定は `.git` または `pyproject.toml` を起点に行われます

---

## ディレクトリ構成

リポジトリ内の主なファイルとディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
      - schema.py              — DuckDB スキーマ定義・初期化
      - pipeline.py            — ETL パイプライン（差分取得・日次実行）
      - quality.py             — データ品質チェック
      - audit.py               — 監査ログ（トレーサビリティ）初期化
      - pipeline.py
    - strategy/
      - __init__.py            — 戦略モジュールのエントリ（拡張箇所）
    - execution/
      - __init__.py            — 発注実装層（拡張箇所）
    - monitoring/
      - __init__.py            — 監視・アラートモジュール（拡張箇所）

主要なソースファイル:
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/schema.py
- src/kabusys/data/pipeline.py
- src/kabusys/data/quality.py
- src/kabusys/data/audit.py

---

## 開発メモ / 注意点

- J-Quants の API レート制限（120 req/min）を厳守する実装になっています。大量取得時は十分に考慮してください。
- jquants_client は 401 を受けた場合にリフレッシュトークンで ID トークンを再取得して 1 回だけ再試行します。
- DuckDB の INSERT は ON CONFLICT DO UPDATE を用いて冪等化しており、外部からの不整合に備えて品質チェックを行います。
- 品質チェックは重大エラーがあっても ETL を途中で止めず、問題を収集して呼び出し元に報告します。運用側での判断を想定しています。
- すべてのタイムスタンプは UTC の保存を基本としています（監査スキーマでは明示的に UTC にセット）。

---

## 今後の拡張案（参考）

- kabuAPI を利用した実際の発注処理の実装（kabusys.execution）
- 戦略実装のサンプルや戦略バージョン管理（kabusys.strategy）
- モニタリング・アラート（Slack 送信等）を組み込む（kabusys.monitoring）
- CLI/ジョブスケジューラ統合（cron / Airflow / Prefect 等）

---

## ライセンス / コントリビューション

プロジェクトのライセンス・コントリビュートルールはリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

必要であれば README に以下を追加できます:
- requirements.txt / pyproject.toml に基づくインストール手順の具体化
- CI / テストの実行方法
- 実運用でのベストプラクティス（シークレット管理、監査ログ運用）