# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ（KabuSys）

このリポジトリは、日本株のデータ取得・ETL・品質管理・監査ログ・発注トレースを想定した内部ライブラリ群です。J-Quants API を用いたマーケットデータ取得、DuckDB を用いたデータレイク（スキーマ設計含む）、ETL パイプライン、品質チェック、監査ログ初期化機能などを提供します。

## 主な特徴（機能一覧）

- 環境変数管理
  - プロジェクトルートの `.env` / `.env.local` を自動で読み込み（無効化可）。
  - 必須環境変数の検証とラップ用 Settings オブジェクト。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダーの取得。
  - API レート制御（120 req/min）と固定間隔スロットリング。
  - リトライロジック（指数バックオフ、最大 3 回）、401 時のトークン自動リフレッシュ。
  - 取得時刻（fetched_at）を UTC で付与。
  - DuckDB への冪等的保存（ON CONFLICT DO UPDATE）。

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義を持ち、初期化関数で作成。
  - インデックスや外部キー、データ整合性チェック用の制約を定義。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日ベース）、バックフィルによる後出し修正の吸収。
  - 市場カレンダー先読み（デフォルト 90 日）。
  - 品質チェック実行（欠損・スパイク・重複・日付不整合）。
  - ETL 実行結果を ETLResult オブジェクトで返却。

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合を検出。
  - 問題は QualityIssue オブジェクトとして全件収集（Fail-Fast ではない）。

- 監査ログ・トレーサビリティ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定まで UUID ベースで完全トレース可能なテーブル群を提供。
  - 発注の冪等性を考慮した設計（order_request_id を冪等キーとして使用）。

## 必要要件（主な依存）

- Python 3.10+（typing の Union | Optional 構文を利用）
- duckdb
- 標準ライブラリ（urllib, json, logging, datetime, pathlib など）

（プロジェクト全体の依存は pyproject.toml / requirements.txt に記載するのが望ましいです。ここでは duckdb を最低限インストールしてください。）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# 必要に応じて他パッケージを追加
```

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を作成・有効化する。

2. 必要な Python パッケージをインストールする（duckdb など）。

3. 環境変数を設定する
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。自動読み込みはデフォルトで有効です（プロジェクトルートは `.git` または `pyproject.toml` を基準に検出されます）。
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテスト用）。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効にする場合に 1 を設定

例 .env（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# オプション
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## 使い方（簡単な例）

以下は最低限の操作例です。プロジェクト内のモジュール API を直接呼び出します。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリが存在しない場合は自動作成）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（市場カレンダー・株価・財務を差分取得して保存、品質チェックを実行）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) J-Quants API を直接呼んでデータ取得（テストや部分取得用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を利用して取得
records = fetch_daily_quotes(id_token=token, date_from=None, date_to=None)
print(len(records))
```

4) 監査ログテーブルを追加で初期化（既存の DuckDB 接続に追加）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

5) 監査専用 DB を作る場合
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

## 設計・運用上の注意点

- J-Quants API レート制限: 120 req/min に合わせ固定間隔でスロットリングします。大量取得の際は遅延が発生します。
- リトライ: 408/429/5xx 等のネットワーク系エラーは指数バックオフで最大 3 回リトライします。401 は自動でトークンリフレッシュを試みます（1 回）。
- ETL の差分更新: デフォルトで最終取得日の数日前（backfill_days=3）から再取得して「後出し修正」を吸収します。
- 品質チェックは Fail-Fast ではなく全件収集します。呼び出し元が重大度（error/warning）に応じた動作を決定してください。
- DuckDB の初期化は idempotent（既存テーブルはそのまま）です。
- すべてのタイムスタンプは UTC を基本に扱っています（監査ログ初期化時に SET TimeZone='UTC' を設定します）。

## ディレクトリ構成

以下は主なファイル・モジュール配置（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数・設定管理（Settings）
    - execution/               — 発注・実行関連（未実装 stubs）
      - __init__.py
    - strategy/                — 戦略層（未実装 stubs）
      - __init__.py
    - monitoring/              — 監視・メトリクス（未実装 stubs）
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
      - schema.py              — DuckDB スキーマ定義・初期化
      - pipeline.py            — ETL パイプライン（差分取得・品質チェック）
      - audit.py               — 監査ログスキーマと初期化
      - quality.py             — データ品質チェック
      - pipeline.py
      - audit.py
      - quality.py

（プロジェクトルートには pyproject.toml や .git がある想定で、config.py はそれを基に .env を自動検出します。）

## API 要約（主要関数）

- kabusys.config.settings: 環境変数をラップした Settings オブジェクト
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int

- kabusys.data.schema
  - init_schema(db_path) -> duckdb connection
  - get_connection(db_path) -> duckdb connection

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...) -> ETLResult

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...) -> list[QualityIssue]
  - 個別チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency

- kabusys.data.audit
  - init_audit_schema(conn) -> None
  - init_audit_db(db_path) -> duckdb connection

## 開発メモ / 拡張案（参考）

- strategy / execution / monitoring パッケージに具体的な戦略やブローカー連携、監視ダッシュボード実装を追加可能。
- ETL の並列化やジョブスケジューラ（Airflow / Dagster 等）との連携で運用性を向上可能。
- 品質チェックに自動修復（補間やアラート通知）機能を追加することも検討。

---

README に記載して欲しい追加情報（例: 実運用での注意、CI/テスト実行方法、依存バージョン定義など）があれば教えてください。必要に応じてサンプル .env.example や quickstart スクリプトも作成します。