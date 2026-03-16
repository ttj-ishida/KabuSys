# KabuSys

日本株向けの自動売買／データ基盤コンポーネント群です。  
J-Quants API からマーケットデータ・財務データ・マーケットカレンダーを取得して DuckDB に格納し、ETL・品質チェック・監査ログの仕組みを提供します。売買戦略や注文実行部分との連携を想定した基盤ライブラリです。

主な目的：
- J-Quants からの差分取得（ページネーション・レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB による冪等的なデータ永続化（ON CONFLICT DO UPDATE）
- 日次 ETL パイプライン（市場カレンダー → 株価 → 財務）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

---

## 機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - API レート制限（120 req/min）に対応するスロットリング
  - 408/429/5xx に対する指数バックオフ付きリトライ
  - 401 発生時はリフレッシュトークンで自動的に ID トークンを更新して再試行
  - ページネーション対応
  - 取得時刻（UTC, fetched_at）を記録して look-ahead bias を防止

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義、外部キー考慮のテーブル作成順
  - 監査ログ用スキーマ（signal_events / order_requests / executions）

- ETL パイプライン
  - 差分更新（DB の最終取得日を確認して未取得分のみ取得）
  - バックフィル（最終取得日の数日前から再取得して後出し修正を吸収）
  - 市場カレンダーの先読み（デフォルト 90 日）
  - 個別ジョブ（prices, financials, calendar）と統合 run_daily_etl

- データ品質チェック
  - 必須カラムの欠損検出（OHLC 欠損）
  - 前日比スパイク検出（閾値デフォルト 50%）
  - 主キー重複検出
  - 将来日付・非営業日の検出
  - 問題は QualityIssue のリストで返し、呼び出し側で重大度に応じて対処

- 環境設定管理
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から自動読み込み（必要に応じて無効化可）
  - settings オブジェクト経由で設定取得（必須のキーが未設定の場合は例外）

---

## 必要条件

- Python 3.10+
- duckdb
- （ネットワーク経由で J-Quants にアクセスするための環境）
- （kabuステーションや Slack と連携する場合はそれらの認証情報）

例（仮想環境・パッケージインストール）:
- python -m venv .venv
- source .venv/bin/activate
- pip install duckdb

※ 実プロジェクトでは pyproject.toml / requirements.txt に依存関係をまとめてください。

---

## セットアップ手順

1. リポジトリをクローン／展開する
2. 仮想環境を作成して依存パッケージ（少なくとも duckdb）をインストール
3. プロジェクトルートに .env（と必要なら .env.local）を作成して環境変数を設定
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
4. DuckDB スキーマを初期化する（例: data/kabusys.duckdb を作成）

簡単な初期化例（Python REPL またはスクリプト）:
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

監査スキーマを追加する場合:
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)

---

## 環境変数（.env）

自動ロード対象: プロジェクトルートの `.env` → `.env.local`（`.env.local` が優先して上書き）  
自動ロードを無効化する: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（例）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token のベース。
- KABU_API_PASSWORD (必須)
  - kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, デフォルト: development)
  - 有効値: development, paper_trading, live
- LOG_LEVEL (任意, デフォルト: INFO)
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

例 (.env):
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（基本）

- DuckDB スキーマ初期化
  - data/schema.init_schema(db_path) でデータベースと全テーブルを作成します（冪等）。
  - 監査ログは data.audit.init_audit_schema(conn) で追加できます。

- 日次 ETL 実行（最も一般的な起点）
  - data.pipeline.run_daily_etl(conn, target_date=None, ...) を呼ぶと、以下を順に行います:
    1. 市場カレンダー ETL（先読み）
    2. 株価日足 ETL（差分 + バックフィル）
    3. 財務データ ETL（差分 + バックフィル）
    4. 品質チェック（オプション）
  - 戻り値は ETLResult オブジェクト。to_dict() で内容を確認できます。

簡単な実行例:
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)
print(result.to_dict())

- 個別 API 呼び出し
  - J-Quants から直接取得したい場合:
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=..., date_to=...)
# 保存
jq.save_daily_quotes(conn, records)

- 品質チェックを個別に実行:
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=...)

- 環境設定参照:
from kabusys.config import settings
token = settings.jquants_refresh_token
is_live = settings.is_live

---

## 開発・テストのヒント

- 自動 .env ロードを無効にしてテスト時に独自に環境を設定したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット
- jquants_client のテスト:
  - ネットワーク呼び出しが発生するため、id_token を引数として注入すると再現性のあるテストが書きやすいです（モジュール内でトークンキャッシュを持っています）。
- DuckDB をインメモリで使う場合は db_path に ":memory:" を指定してください（init_schema(":memory:")）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py  (パッケージ定義, __version__=0.1.0)
- config.py    (環境変数・設定管理; .env 自動読み込み、settings オブジェクト)
- data/
  - __init__.py
  - jquants_client.py   (J-Quants API クライアント: 取得・保存ロジック、レート制御・リトライ)
  - schema.py          (DuckDB スキーマ定義・初期化)
  - pipeline.py        (ETL パイプライン: run_daily_etl 等)
  - audit.py           (監査ログスキーマ初期化)
  - quality.py         (データ品質チェック)
- strategy/
  - __init__.py        (戦略関連モジュールのプレースホルダ)
- execution/
  - __init__.py        (注文実行関連のプレースホルダ)
- monitoring/
  - __init__.py        (監視・メトリクス関連のプレースホルダ)

補足:
- Data 層は Raw / Processed / Feature / Execution の 3 層（＋監査）に分かれ、DDL とインデックスが schema.py にまとまっています。
- jquants_client.py は fetched_at を UTC で記録し、重複挿入を避けるため insert ... ON CONFLICT DO UPDATE を使用しています。

---

以上が README の概要です。README に追加したい具体的なサンプル（たとえば .env.example ファイルの完全テンプレートや、run_daily_etl の cron/ジョブ化サンプルなど）があれば、その内容に合わせて追記します。