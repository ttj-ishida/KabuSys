# KabuSys

日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。  
データ取得（J-Quants）、ETL（差分取得／バックフィル）、DuckDB スキーマ管理、データ品質チェック、監査ログ用スキーマなどを備え、戦略／発注／監視モジュールと連携して自動売買システムを構築できます。

バージョン: 0.1.0

---

## 概要

KabuSys は次の機能を提供します。

- J-Quants API からの株価（日足）・財務・マーケットカレンダー取得（ページネーション対応）
- API レート制御（120 req/min 固定間隔スロットリング）とリトライ・トークン自動リフレッシュ
- DuckDB を利用した三層（Raw / Processed / Feature）＋実行／監査スキーマの定義・初期化
- ETL パイプライン（差分取得／バックフィル／品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）の集約
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマと初期化ユーティリティ
- 環境変数による設定管理（.env/.env.local の自動ロード、必要値の検証）

設計上の目標は、冪等性（ON CONFLICT DO UPDATE）およびトレーサビリティ確保、外部 API に対する安全な呼び出しです。

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（refresh token から id token 取得）
  - save_* 関数で DuckDB に冪等保存
  - レート制限 & 再試行 & 401 のトークンリフレッシュ対応

- data.schema
  - init_schema(db_path) : DB と全テーブル（Raw/Processed/Feature/Execution）を作成
  - get_connection(db_path) : 既存 DB へ接続

- data.audit
  - init_audit_schema(conn) : 監査ログテーブルを追加
  - init_audit_db(db_path) : 監査ログ専用 DB 初期化

- data.pipeline
  - run_daily_etl(conn, target_date=None, ...) : 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl : 個別ジョブ

- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks(conn, ...)

- config
  - Settings クラス経由で設定値を参照（必須チェックあり）
  - .env/.env.local の自動ロード（プロジェクトルートを .git または pyproject.toml で判定）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能

---

## 必要条件

- Python 3.10+
- 依存パッケージ（最低限）:
  - duckdb
- ネットワークアクセス（J-Quants API）

（プロジェクト配布時は pyproject.toml / requirements.txt を参照してください。）

---

## 環境変数

必須（アプリケーションが機能するために設定が必要）:

- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション / デフォルト:

- KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト `INFO`
- KABU_API_BASE_URL — デフォルト `http://localhost:18080/kabusapi`
- DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
- SQLITE_PATH — デフォルト `data/monitoring.db`
- KABUSYS_DISABLE_AUTO_ENV_LOAD — `1` を設定すると .env 自動ロードを無効化

.env の読み込み順序:
1. OS 環境変数（優先）
2. .env.local（存在すれば上書き）
3. .env

.env ファイルは shell 形式（export を含む行にも対応）で記述可能です。未設定の必須変数を参照すると ValueError が投げられます。

---

## セットアップ手順（開発環境）

1. リポジトリをクローン／チェックアウト
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb
   - （プロジェクト配布時は pip install -e . や requirements.txt を使用）
4. .env を作成して必要な環境変数を設定
   - 例:
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     KABU_API_PASSWORD=your_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456
5. （任意）KABUSYS_ENV, DUCKDB_PATH 等を設定

---

## 使い方（簡単な例）

以下は典型的な初期化と日次 ETL 実行のサンプルです。

1) DuckDB スキーマを初期化して接続を取得する

```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリが自動作成される）
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 監査ログスキーマを追加する（必要な場合）

```python
from kabusys.data import audit

audit.init_audit_schema(conn)
# または監査用専用 DB を作る場合:
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL を実行する

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl, get_connection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定しなければ今日で実行

print(result.to_dict())
if result.has_errors:
    print("ETL 中にエラーが発生しました:", result.errors)
if result.has_quality_errors:
    print("品質チェックで重大な問題が発生しました")
```

4) 直接 J-Quants データを取得して保存する（テスト用途など）

```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
import duckdb
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

注意: jquants_client は内部で rate limiting / retry / token refresh を行います。テスト時は settings.jquants_refresh_token を差し替えるか、id_token を直接渡せます。

---

## よく使う API（抜粋）

- config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path, settings.env, settings.is_live など

- data.schema
  - init_schema(db_path) -> DuckDB 接続
  - get_connection(db_path) -> DuckDB 接続（スキーマ初期化は行わない）

- data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - save_daily_quotes(conn, records)
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar

- data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

---

## 注意点 / 実装上のポイント

- J-Quants API のレートリミット（120 req/min）に合わせた固定間隔スロットリングを内部で行っています。
- リトライは最大 3 回、408/429/5xx の場合に指数バックオフ（429 の場合は Retry-After を優先）を行います。
- 401 応答を受けた場合はリフレッシュトークンで id_token を自動再取得して 1 回リトライします（再再試行しません）。
- DuckDB テーブル作成は冪等（CREATE TABLE IF NOT EXISTS）。INSERT は ON CONFLICT DO UPDATE を利用して同一主キーの更新／上書きを行います。
- ETL の差分更新は DB に保存されている最終日から backfillDays 分さかのぼって再取得する設計です（デフォルト backfill_days=3）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われ、テスト等で無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル／フォルダ（抜粋）は以下のとおりです。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得/保存）
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログスキーマ
    - pipeline.py
  - strategy/
    - __init__.py            — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py            — 発注／ブローカー連携用（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視／メトリクス用（拡張ポイント）

（README に記載のない補助モジュール・ドキュメント等はリポジトリ内を参照してください。）

---

## 開発・拡張のヒント

- 戦略や実行ロジックは strategy/ と execution/ に実装し、signal_queue / orders / executions テーブルを介して統合することを想定しています。
- 監査ログは削除しない方針（ON DELETE RESTRICT）で設計されているため、監査データは append-only 的に扱うのが推奨です。
- データ品質チェックは ETL の最後に run_all_checks でまとめて実行され、重大度（error/warning）を見て呼び出し側で運用判断を行えます。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを抑制し、テスト用の環境変数を注入してください。

---

必要であれば、README に含めるサンプルスクリプトや CI／デプロイ手順、運用チェックリスト（バックフィル手順・障害対応フロー等）を追加します。どの情報を補足したいか教えてください。