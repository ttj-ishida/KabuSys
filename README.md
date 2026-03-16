# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ集です。データ取得（J-Quants）、ETL、データ品質チェック、DuckDB スキーマ定義、監査ログなど、アルゴリズム取引システムの基盤機能を提供します。

---

## 概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API からの株価・財務・市場カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB を用いた三層データレイヤ（Raw / Processed / Feature）と Execution / Audit テーブルの定義・初期化
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合の検出）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計上のポイント:
- API レート制限（120 req/min）を遵守する RateLimiter 実装
- 重要 API 呼び出しでのリトライ（指数バックオフ）、401 の際は自動トークンリフレッシュ
- 取得時刻（UTC の fetched_at）を記録し look-ahead bias を防止
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で安全

---

## 主な機能一覧

- data.jquants_client
  - J-Quants から日足（OHLCV）、財務四半期データ、JPX カレンダーを取得
  - レート制限・リトライ・トークン管理・ページネーション対応
  - DuckDB へ冪等に保存する save_* 関数
- data.schema
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックスや外部キーを含む DDL を提供
- data.pipeline
  - 日次 ETL の実装（差分更新・バックフィル・カレンダー先読み・品質チェック）
  - ETL 結果を ETLResult として返却
- data.quality
  - 欠損、重複、スパイク（前日比閾値）、将来日付・非営業日チェック
  - QualityIssue を返し、重大度（error/warning）を付与
- data.audit
  - 戦略→シグナル→発注→約定の監査テーブル群（冪等キー・タイムスタンプ・UTC 保持）
- config
  - .env ファイルおよび環境変数からアプリ設定を読み込む Settings
  - 自動 .env ロード機能（プロジェクトルート検出）と無効化フラグあり

※ strategy / execution / monitoring パッケージは（このスナップショットでは）パッケージ初期化のみ定義されています。

---

## 必要条件

- Python 3.10 以上（型注釈に | を使用）
- 依存パッケージ
  - duckdb
- 標準ライブラリ: urllib, json, logging, datetime 等

インストール例:
pip install duckdb

（プロジェクト全体をパッケージ化している場合は requirements を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb
4. 環境変数を設定（.env をプロジェクトルートに置くことが可能）
   - 必要な環境変数は次節を参照

---

## 環境変数（.env）

config.Settings が利用する主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須)
  - kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, 有効値: development, paper_trading, live) — デフォルト: development
- LOG_LEVEL (任意, 有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト: INFO

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を探索し、以下順で自動読み込みします:
  1. OS 環境変数（最優先）
  2. .env.local（存在する場合、OS を除き上書き）
  3. .env（存在する場合、OS に存在しないキーをセット）
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

簡単な .env の例:
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 初期化（DuckDB スキーマ作成）

Python インタラクティブまたはスクリプトで DuckDB スキーマを初期化できます。

例: メイン DB を初期化
from kabusys.data import schema
conn = schema.init_schema(schema_path := "<path>/kabusys.duckdb")
# settings を使う場合:
from kabusys.config import settings
conn = schema.init_schema(settings.duckdb_path)

監査ログ（audit）を別 DB に作る場合:
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

既に作成済みの DB に接続する場合は:
from kabusys.data import schema
conn = schema.get_connection(settings.duckdb_path)

Notes:
- init_schema は親ディレクトリを自動作成します（":memory:" を渡すとインメモリ DB）。
- init_audit_schema(conn) を呼んで既存接続に監査テーブルを追加できます。

---

## 使い方（代表的な API）

- J-Quants トークン取得
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を利用して取得

- 日足データ取得（ページネーション対応）
from datetime import date
records = jq.fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))

- DuckDB に保存（冪等）
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
jq.save_daily_quotes(conn, records)

- 日次 ETL 実行（推奨）
from kabusys.data import pipeline, schema
conn = schema.init_schema(":memory:")  # または settings.duckdb_path
result = pipeline.run_daily_etl(conn)
print(result.to_dict())

run_daily_etl の主な引数:
- target_date: 処理対象日（省略時は今日）
- id_token: テスト等で外部注入可能
- run_quality_checks: True/False
- spike_threshold: スパイク判定閾値（デフォルト 0.5）
- backfill_days: 最終取得日の何日前から再取得するか（デフォルト 3）

- 品質チェック単体実行
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i.check_name, i.severity, i.detail)

---

## 監査ログ（Audit）利用

- 監査スキーマ初期化（既存接続に追加）
from kabusys.data import audit
conn = schema.init_schema(settings.duckdb_path)
audit.init_audit_schema(conn)

- 監査 DB を別ファイルにする場合:
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

設計上、すべての TIMESTAMP は UTC で保存されます。order_request_id や execution_id などの UUID を用いたトレースを前提としています。

---

## 開発 / テストのヒント

- 自動 .env 読み込みを無効化:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  これによりテストで明示的に環境を制御できます。

- テスト用にインメモリ DuckDB を使う:
  conn = schema.init_schema(":memory:")

- jquants_client の外部呼び出し（実ネットワーク）を行いたくない場合は、get_id_token 等をモックしてください。pipeline.run_daily_etl は id_token を注入可能です。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

src/
  kabusys/
    __init__.py              # パッケージ定義
    config.py                # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py      # J-Quants API クライアント（取得・保存ロジック）
      schema.py              # DuckDB スキーマ定義・初期化
      pipeline.py            # ETL パイプライン（差分更新・品質チェック）
      audit.py               # 監査ログ（トレーサビリティ）DDL・初期化
      quality.py             # データ品質チェック
    strategy/
      __init__.py            # 戦略層（未実装の入り口）
    execution/
      __init__.py            # 発注実行層（未実装の入り口）
    monitoring/
      __init__.py            # 監視・アラート層（未実装の入り口）

---

## 付記（設計上の注意）

- J-Quants API のレート制限（120 req/min）に合わせた内部制御が組み込まれていますが、複数プロセスで同一トークンを使う場合はアプリ側での調整が必要です。
- DuckDB の ON CONFLICT による更新で冪等性を保証していますが、ETL 前後でスキーマ変更があると期待動作をしないことがあるため注意してください。
- Quality モジュールは Fail-Fast ではなく問題を収集して返す設計です。呼び出し側でエラー可否の判定を行ってください。

---

この README は現在のコードベース（data, config, pipeline, audit, quality の実装）に基づいています。strategy・execution・monitoring 層は今後の拡張ポイントです。必要であれば具体的な使い方・サンプルスクリプトや CI 設定のテンプレートも作成できます。どのサンプルが欲しいか教えてください。