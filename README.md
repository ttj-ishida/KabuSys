# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（プロトタイプ）。  
データ取得、DuckDB スキーマ定義、監査ログ、データ品質チェックなど、トレーディングシステムの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の目的で設計されたモジュール群です。

- J-Quants API からの市場データ（株価日足、財務データ、JPX マーケットカレンダー）取得
- データの永続化（DuckDB）とスキーマ管理（Raw / Processed / Feature / Execution / Audit）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 簡易な設定管理（.env / 環境変数の自動ロード）

設計上のポイント：
- J-Quants API へのアクセスはレート制限（120 req/min）と再試行（指数バックオフ）を備えています。
- 取得時刻（fetched_at）や監査用タイムスタンプは UTC ベースで記録されます。
- DuckDB への挿入は冪等（ON CONFLICT ... DO UPDATE）を目指しています。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）
  - 必須環境変数の取得（未設定時は例外）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

- J-Quants API クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンから id_token を取得）
  - レートリミット管理（120 req/min）
  - リトライ（最大 3 回）、401 受信時はトークン自動リフレッシュ（1 回のみ）
  - DuckDB へ保存する save_* 関数（raw_prices, raw_financials, market_calendar）

- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema(db_path) でスキーマ作成（冪等）
  - get_connection(db_path) で既存 DB へ接続

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL とインデックス
  - init_audit_schema(conn) / init_audit_db(db_path)

- データ品質チェック（kabusys.data.quality）
  - 欠損（OHLC）検出、スパイク（前日比）検出、重複チェック、日付不整合チェック
  - run_all_checks(conn, ...) でまとめて実行し QualityIssue のリストを返す

---

## 動作要件

- Python 3.10+
  - 型アノテーションで `X | None` などを使用しているため 3.10 以上を想定しています。
- 依存パッケージ
  - duckdb

インストール例:
pip install duckdb

（プロジェクト配布時は pyproject.toml / requirements.txt を用意してください）

---

## セットアップ手順

1. リポジトリをクローン／展開する
2. Python 環境の準備（推奨: 仮想環境）
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt もしくは pip install duckdb
3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を配置すると自動で読み込まれます。
   - `.env.local` が存在する場合は `.env` より優先して（上書き）読み込まれます。
   - 自動ロードを無効にする: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
4. DuckDB スキーマ初期化（例）
   - 以下の Python スニペットで DB を初期化できます（デフォルトパスは settings.duckdb_path）。

例: .env（抜粋・例）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

---

## 使い方（簡単な例）

以下は代表的な利用パターンです。Python REPL やスクリプトで実行してください。

- スキーマ初期化とデータ取得→保存

from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data import jquants_client as jq

# DuckDB を初期化（ファイルがなければ作成）
conn = init_schema(settings.duckdb_path)

# データ取得（例: 銘柄コード 7203 の 2023-01-01〜2023-12-31）
records = jq.fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))

# 保存（raw_prices テーブルへ、fetched_at は UTC で記録）
count = jq.save_daily_quotes(conn, records)
print(f"保存件数: {count}")

- 監査スキーマの初期化（既存接続へ追加）

from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)

- 監査専用 DB の作成

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")

- データ品質チェック

from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for issue in issues:
    print(issue.check_name, issue.table, issue.severity, issue.detail)
    for row in issue.rows:
        print("  ", row)

- id_token 取得（必要に応じて）

from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用

注意:
- jquants_client は内部でレート制御とリトライを行います（120 req/min, max 3 retries）。
- 401 エラー時はリフレッシュトークンを使って id_token を自動取得し 1 回だけ再試行します。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意): kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須): Slack 通知先チャンネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意): 環境（development | paper_trading | live）、デフォルト development
- LOG_LEVEL (任意): ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL）、デフォルト INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env 読み込みを無効化

自動読み込みについて:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` -> `.env.local` の順で読み込みます。
- OS 環境変数は保護され、.env の値で上書きされません（ただし .env.local は override=True のため上書きされます）。
- プロジェクトルートが見つからない場合は自動ロードをスキップします。

.env のパース挙動（主な仕様）:
- コメント（#）や先頭の `export KEY=val` 形式に対応
- シングル／ダブルクォート文字列内のエスケープ処理をサポート
- クォート無しの行では `#` の直前に空白がある場合をコメントと判定

---

## ディレクトリ構成

主要ファイル / モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定 / .env 自動ロード / Settings クラス
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - schema.py              — DuckDB スキーマ定義と init_schema / get_connection
    - audit.py               — 監査ログ（信号→発注→約定）DDL と初期化
    - quality.py             — データ品質チェック（QualityIssue 定義含む）
    - (その他: news/audit/…)
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

主要テーブル（DuckDB）:
- Raw: raw_prices, raw_financials, raw_news, raw_executions
- Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature: features, ai_scores
- Execution: signals, signal_queue, orders, trades, positions, portfolio_targets, portfolio_performance
- Audit: signal_events, order_requests, executions

---

## 開発・運用上の注意

- Python バージョンは 3.10 以上を推奨（型表記の互換性）。
- DuckDB のファイルパスは既存ディレクトリが無ければ自動作成されます。
- 監査テーブルは削除しない前提（FK は ON DELETE RESTRICT）。監査ログは保持する運用を想定してください。
- すべてのタイムスタンプは UTC で保存するよう初期化処理（init_audit_schema）がセットします。
- J-Quants API のレート制限（120 req/min）を尊重してください。クライアントは固定間隔スロットリングでこれを守りますが、並列化時の注意が必要です。
- save_* 関数は ON CONFLICT DO UPDATE により同じ主キーでの上書きを行い、冪等性を高めています。

---

この README はコードベースの現状（v0.1.0）に基づく概要と利用方法を示しています。追加のユースケース（バックテスト、ストラテジー実装、API 統合、運用監視など）は strategy/ や execution/、monitoring/ 以下に実装を追加してください。