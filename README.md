# KabuSys

日本株自動売買システムのコアライブラリ（軽量モジュール群）。  
データ取得、DuckDB スキーマ定義、監査ログ（トレーサビリティ）、環境設定ユーティリティなど、自動売買プラットフォームの基盤となる機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株用自動売買システムの基盤コンポーネント群です。本リポジトリの主な目的は以下です。

- 外部データソース（現在は J-Quants API）からの市場データ・財務データ・マーケットカレンダー取得
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）のスキーマ定義・初期化
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）を専用スキーマで永続化
- 環境変数/.env 管理ユーティリティ
- API 呼び出し時のレート制御・リトライ・トークン自動リフレッシュ等の実装

注: strategy / execution / monitoring のパッケージ初期化ファイルは用意されていますが、ここで示されたコードでは主に data 関連機能と config, audit, schema を実装しています。

---

## 機能一覧

- 環境変数読み込み・管理
  - プロジェクトルートの `.env` / `.env.local` を自動ロード（必要に応じて無効化可能）
  - 必須環境変数を Settings で簡単に取得
- J-Quants API クライアント（data/jquants_client.py）
  - 日足（OHLCV）・財務データ（四半期）・マーケットカレンダー取得
  - レート制限（120 req/min）に基づくスロットリング
  - リトライ（指数バックオフ）と 401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し look-ahead bias を防止
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ管理（data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義
  - 初期化関数 init_schema(db_path) で一括作成（冪等）
  - インデックス定義（頻出クエリの高速化）
- 監査ログ（data/audit.py）
  - signal_events / order_requests / executions のテーブル定義
  - order_request_id による冪等（再送による二重発注防止）
  - すべての TIMESTAMP を UTC で扱う設計（init_audit_schema は SET TimeZone='UTC' を実行）
  - init_audit_db(db_path) で監査専用 DB の初期化も可能
- ユーティリティ
  - 型変換補助（_to_float / _to_int）
  - DuckDB 接続取得ユーティリティ

---

## セットアップ手順

必要条件:
- Python 3.10 以上（PEP 604 の | 型ヒントを利用しているため）
- pip

推奨: 仮想環境を利用してください。

1. 仮想環境の作成と有効化（例: venv）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 依存パッケージのインストール
   - 本リポジトリは主に標準ライブラリと duckdb を使用します。duckdb をインストールしてください:
     ```
     pip install duckdb
     ```
   - （プロジェクト配布用に pyproject.toml / requirements.txt がある場合はそちらに従ってください）

3. 環境変数の準備
   - プロジェクトルートに `.env`（および機密用の `.env.local`）を配置します。自動ロードはデフォルトで有効です。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 (.env.example):
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
# 任意: KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知用)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（省略時は data/kabusys.duckdb 等に保存）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行モード: development / paper_trading / live
KABUSYS_ENV=development

# ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下はライブラリを使った基本的なワークフロー例です。

1) DuckDB スキーマの初期化（ファイル DB）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Path オブジェクトを返します（.env の DUCKDB_PATH を参照）
conn = init_schema(settings.duckdb_path)
# conn は duckdb の接続オブジェクト (DuckDBPyConnection)
```

2) J-Quants から日足を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)  # 既存 DB に接続（init_schema を先に実行推奨）
records = fetch_daily_quotes(code="7203")    # トヨタ等、銘柄コードを指定可能。省略で全銘柄
n_saved = save_daily_quotes(conn, records)
print(f"saved {n_saved} records")
```

3) 財務データやマーケットカレンダーの取得も同様:
```python
from kabusys.data.jquants_client import fetch_financial_statements, fetch_market_calendar, save_financial_statements, save_market_calendar

fin_records = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin_records)

cal_records = fetch_market_calendar()
save_market_calendar(conn, cal_records)
```

4) 監査ログの初期化（監査専用 DB を使う場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
# または既存の conn を渡して init_audit_schema(conn)
```

注意点:
- J-Quants API 呼び出しは内部でレート制御（120 req/min）とリトライを行います。大量取得時は時間がかかります。
- トークン（JQUANTS_REFRESH_TOKEN）は Settings 経由で必須取得されます。未設定だと ValueError が発生します。
- 監査ログテーブルは TIMESTAMP を UTC で扱うよう初期化されます。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化します

---

## ディレクトリ構成

本コードベースに含まれる主なファイル / ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロード・Settings 定義
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得 + DuckDB への保存関数）
    - schema.py
      - DuckDB テーブル定義・初期化関数（Raw / Processed / Feature / Execution）
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）定義・初期化
    - (その他データ関連モジュールを配置可能)
  - strategy/
    - __init__.py (戦略モジュールのエントリポイント)
  - execution/
    - __init__.py (発注・ブローカー連携など)
  - monitoring/
    - __init__.py (監視・メトリクス収集)
- その他:
  - README.md（本ファイル）
  - .env / .env.local（環境依存、実運用時に作成）

---

## 実運用上の注意・設計ポイント

- J-Quants API のレート制限（120 req/min）は厳守してください。本クライアントは固定間隔スロットリングを採用していますが、複数プロセスで同一 API を叩く場合は注意が必要です。
- トークン管理: get_id_token() はリフレッシュトークンから id_token を取得し、モジュールレベルでキャッシュします。401 受信時は 1 回トークンを自動更新してリトライします。
- DuckDB のスキーマは冪等に作成されます。初回のみ init_schema を呼ぶことでテーブルが揃います。
- 監査ログは削除しない前提で設計されています（ON DELETE RESTRICT 等）。履歴保存を重視する設計です。
- すべての TIMESTAMP は UTC で扱うポリシーです（監査ログ初期化時に SET TimeZone='UTC' を行います）。

---

ご質問や追加のドキュメント（例: DataSchema.md, DataPlatform.md、運用手順、CI/CD 設定など）が必要であれば教えてください。必要に応じて README にサンプルワークフローや運用チェックリストを追記します。