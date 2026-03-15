# KabuSys

日本株自動売買システムのコアライブラリ（KabuSys）。  
データ取得、スキーマ管理、監査ログ、設定管理の基盤を提供します。

---

## プロジェクト概要

KabuSys は次のような要件を満たすことを目的としたライブラリ／パッケージです。

- J-Quants API などから市場データ（OHLCV、財務データ、マーケットカレンダー等）を取得
- DuckDB を用いた三層データレイヤ（Raw / Processed / Feature）と Execution 層のスキーマ管理
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）の管理
- 環境変数（.env）ベースの設定管理（自動ロード機能）
- API レート制限・リトライ・トークン自動リフレッシュ等の堅牢な API クライアント設計

現状、strategy / execution / monitoring パッケージはプレースホルダ（初期化済み）です。データ取得・保存・スキーマ初期化・監査スキーマに重点があります。

---

## 主な機能一覧

- 環境設定管理
  - .env ファイルおよび OS 環境変数からの設定読み込み
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う
  - 必須変数チェックと便利なプロパティ（settings.<name>）

- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）・財務（四半期）・マーケットカレンダー取得
  - ページネーション対応
  - API レート制限（120 req/min）を固定間隔スロットリングで順守
  - リトライ（指数バックオフ、最大 3 回）、408/429/5xx を対象
  - 401 時はリフレッシュトークンで自動リフレッシュして再試行（1 回）
  - 取得時刻（fetched_at）を UTC で保存して Look-ahead バイアスを防止
  - DuckDB への保存は ON CONFLICT DO UPDATE による冪等性

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution のテーブル DDL を定義
  - インデックス定義と依存順に基づく作成
  - init_schema(db_path) で初期化（":memory:" も可）
  - get_connection(db_path) で既存 DB に接続

- 監査ログ（src/kabusys/data/audit.py）
  - signal_events / order_requests / executions の監査テーブルを定義
  - order_request_id を冪等キーとして二重発注を防止
  - 全 TIMESTAMP を UTC で保存する設計（init_audit_schema が SET TimeZone='UTC' を実行）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供

---

## 必要条件

- Python 3.10 以上（typing の Union/Annotated 等の記法を利用）
- duckdb パッケージ
- ネットワーク接続（J-Quants API 等）
- 環境変数管理のため .env を使用する場合は UTF-8 エンコードのファイル

（プロジェクトの実行に必要な他の依存パッケージは別途 requirements.txt 等で管理してください）

---

## インストール（ローカル開発向け）

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して有効化
3. 必要なパッケージをインストール（例）

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb

（プロジェクトが requirements.txt を持つ場合は `pip install -r requirements.txt`）

---

## 環境変数（.env）と設定

KabuSys は .env ファイル（プロジェクトルート）を自動読み込みします（環境変数が既に設定されている場合は上書きされませんが、.env.local は上書き可能）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須)
  - Slack チャンネル ID
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意、'development'|'paper_trading'|'live', デフォルト: development)
- LOG_LEVEL (任意、DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト: INFO)

.env の簡易例:

# .env (例)
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意: .env のパースはシンプルなシェル風記法に対応しています（export プレフィックスやクォート、インラインコメント等に対応）。

---

## セットアップ手順（DB スキーマ初期化）

以下は Python シェルやスクリプト内での初期化例です。

- DuckDB スキーマ（全テーブル）を作成:

from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクトを返す
conn = init_schema(settings.duckdb_path)

- 監査ログテーブルを既存の接続に追加:

from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)

- 監査専用 DB を作成する場合:

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")

init_schema は冪等なので何度実行しても既存テーブルが存在すればスキップします。

---

## 使い方（代表的な例）

- J-Quants から日足データを取得して DuckDB に保存する例:

from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")

- 財務データを取得して保存:

from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
records = fetch_financial_statements(code="7203")
n = save_financial_statements(conn, records)

- マーケットカレンダーを取得して保存:

from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar
cal = fetch_market_calendar()
n = save_market_calendar(conn, cal)

- ID トークンを直接取得（必要なら）:

from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して取得

注意点:
- fetch_* 関数は内部でトークンキャッシュを保持し、ページネーション時にトークンを共有します。
- API のレート制限（120 req/min）に従うため、連続リクエスト時はスロットリングが入ります。
- 401 が返った場合はリフレッシュトークンで自動更新を試みます（1 回限定）。

---

## ログ・デバッグ

- ログレベルは環境変数 `LOG_LEVEL` で制御します（デフォルト: INFO）。
- jquants_client は内部で logger を用いて情報／警告を出力します（リトライ・スリープ・スキップ等の情報）。

---

## ディレクトリ構成

リポジトリの主要ファイルと概要:

src/kabusys/
- __init__.py               : パッケージエントリ（version）
- config.py                 : 環境変数・設定読み込みロジック（.env 自動ロード、Settings クラス）
- data/
  - __init__.py
  - jquants_client.py       : J-Quants API クライアント（取得・保存・リトライ・レート制御）
  - schema.py               : DuckDB スキーマ定義と初期化（Raw/Processed/Feature/Execution）
  - audit.py                : 監査ログ（signal_events / order_requests / executions）
  - audit.py                : 監査用 DB 初期化ユーティリティ
  - (other data modules)    : 将来的なデータ取得・ETL 向けモジュール
- strategy/
  - __init__.py             : 戦略関連パッケージ（現在はプレースホルダ）
- execution/
  - __init__.py             : 発注/ブローカー連携関連（プレースホルダ）
- monitoring/
  - __init__.py             : 監視・メトリクス関連（プレースホルダ）

プロジェクトルート:
- .env, .env.local          : 環境変数（プロジェクトルートに置く）
- pyproject.toml / setup.py : パッケージ設定（存在する場合）

---

## 開発メモ / 注意事項

- .env 自動ロードはプロジェクトルートを .git または pyproject.toml で特定します。テスト等で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のスキーマは大量のテーブル・インデックスを作成します。ストレージを配置するディレクトリは適宜設定してください（settings.duckdb_path）。
- 監査ログは削除しない前提（ON DELETE RESTRICT）で設計されています。監査記録の永続化を重視します。
- API のリトライ対象は 408/429/5xx とネットワークエラー。429 の場合 Retry-After ヘッダを優先して待機します。
- jquants_client の各 save_* 関数は与えられたレコードで PK 欠損がある行をスキップし、その件数をログ出力します。

---

必要に応じて README を拡張し、使用例や CLI、CI 設定、運用手順（本番切替、リスク管理チェックリスト等）を追加してください。ご希望があれば実際のサンプルスクリプトやテンプレート .env.example を追記します。