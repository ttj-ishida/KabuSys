# KabuSys

日本株の自動売買プラットフォーム向けのライブラリ群（部分実装）。  
データ取得、DB スキーマ初期化、監査ログ、データ品質チェックなどの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援する共通ライブラリです。本リポジトリでは主に次の機能を実装しています。

- J-Quants API クライアント（株価日足・財務データ・JPX カレンダー取得）
  - レート制御（120 req/min）およびリトライ（指数バックオフ）、401 の自動トークンリフレッシュに対応
  - ページネーション対応、取得時刻（UTC）を記録して Look-ahead bias を防止
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ（signal → order → execution のトレーサビリティ）用テーブル群
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 環境変数 / .env の読み込みと設定管理

パッケージのエントリポイント: `kabusys`（サブモジュール群: `data`, `strategy`, `execution`, `monitoring`）

---

## 主な機能一覧

- 設定管理
  - .env / .env.local の自動ロード（優先度: OS 環境変数 > .env.local > .env）
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による自動ロード無効化
  - 設定アクセス: `from kabusys.config import settings`
- J-Quants クライアント（`kabusys.data.jquants_client`）
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar
  - レートリミッタ、リトライ、トークンキャッシュ
- DuckDB スキーマ（`kabusys.data.schema`）
  - `init_schema(db_path)` で全テーブル／インデックス作成（冪等）
  - テーブル群は Raw / Processed / Feature / Execution 層に整理
- 監査スキーマ（`kabusys.data.audit`）
  - signal_events, order_requests, executions 等を作成する関数 `init_audit_schema(conn)` / `init_audit_db(path)`
  - 監査用インデックスの作成
- データ品質（`kabusys.data.quality`）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合のチェック関数
  - 各チェックは QualityIssue オブジェクトのリストを返す
  - `run_all_checks(conn, ...)` で一括実行

---

## 動作要件 / 依存

- Python 3.10+
- 必要パッケージ（最低限）
  - duckdb

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# さらに必要なパッケージがあれば追記
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 必要パッケージのインストール（上記参照）
3. プロジェクトルートに `.env` を作成（もしくは環境変数で設定）

推奨の環境変数（`.env` の例）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...

# データベースパス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 動作モード
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

.env 自動ロードの挙動:
- プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出（CWD に依存しない）
- 読み込み順序: OS 環境 > .env.local > .env
- テストなどで自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

---

## 使い方（基本例）

以下に基本的な利用例を示します。Python REPL やスクリプトで実行してください。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は .env / 環境変数から取得されます（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2) J-Quants から日足を取得して保存する
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# 銘柄コード・期間を指定して取得
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
n = save_daily_quotes(conn, records)
print(f"saved {n} records")
```

3) ID トークンを明示的に取得する
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して取得
```

4) 監査スキーマの初期化（既存の conn に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # conn は init_schema の返り値で良い
```

5) データ品質チェックの実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.table, issue.severity, issue.detail)
    for row in issue.rows:
        print("  ", row)
```

注意点:
- J-Quants 呼び出しはレート制御を行うため連続呼び出しに注意
- save_* 系は ON CONFLICT DO UPDATE を用いた冪等な保存を行います
- 時刻は取得時に UTC で記録されます（fetched_at 等）

---

## ディレクトリ構成

主なファイル／モジュール構成（src/tree ベース）:

- src/kabusys/
  - __init__.py
  - config.py                  -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント + DuckDB 保存
    - schema.py                -- DuckDB スキーマ定義・初期化
    - audit.py                 -- 監査ログスキーマ（signal/order/execution）
    - quality.py               -- データ品質チェック
  - strategy/
    - __init__.py              -- 戦略実装用パッケージ（空）
  - execution/
    - __init__.py              -- 発注／実行関連（空）
  - monitoring/
    - __init__.py              -- 監視／アラート関連（空）

テーブル層（schema.py に定義）:
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

監査（audit.py）:
- signal_events, order_requests, executions + 関連インデックス

---

## 設定キー一覧

主要な環境変数（必須は README 内で明示）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite (monitoring 用) パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 動作環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するフラグ（1 を設定）

---

## 開発・拡張メモ

- strategy / execution / monitoring パッケージは拡張用のプレースホルダです。実際の戦略や発注ロジックはこれらに実装してください。
- J-Quants クライアントはネットワークエラーや 429 制限に対してリトライを行いますが、運用ではさらにバックプレッシャーやバッチスケジューリングを検討してください。
- 監査ログは削除しない前提です（ON DELETE RESTRICT）。運用上の保存方針（保持期間）を検討してください。
- DuckDB のスキーマは冪等に作成されるため、初回起動時に `init_schema` を必ず走らせてください。

---

必要であれば、README に実行スクリプト（例: データ取得バッチ、ETL ワークフロー、CI 用コマンド）や .env.example を追記します。追加で欲しい内容があれば教えてください。