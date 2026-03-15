# KabuSys

日本株自動売買システム用ライブラリ（KabuSys）。データ取得、スキーマ管理、監査ログ、取引実行や戦略モジュールの基盤機能を提供します。

主な設計方針：
- データ取得時の Look-ahead Bias を防ぐため取得時刻（UTC）を記録
- API レート制御とリトライロジックを備え堅牢な外部 API 呼び出しを実現
- DuckDB を用いた冪等な永続化（ON CONFLICT DO UPDATE / PK）
- 監査ログによるシグナル→発注→約定の完全トレーサビリティ

バージョン: 0.1.0

---

## 機能一覧

- 環境変数 / .env 自動ロードと設定取得（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込み
  - 必須値チェックと型検証（env, log_level など）
  - 自動ロードの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - 固定間隔レートリミッタ（120 req/min を想定）
  - リトライ（指数バックオフ）、401 受信時の自動トークンリフレッシュ
  - ページネーション対応、取得時刻（fetched_at）を保存
  - DuckDB への冪等保存用ユーティリティ（save_* 関数）
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - init_schema() / get_connection() を提供
- 監査ログ（kabusys.data.audit）
  - シグナル、発注要求、約定の監査テーブルとインデックス
  - init_audit_schema() / init_audit_db()
- パッケージ基盤（strategy / execution / monitoring に拡張用の入口を準備）

---

## 要件

- Python 3.10+
- 依存パッケージ（主に）:
  - duckdb
- 標準ライブラリ: urllib, json, datetime, logging, pathlib など

（実際のプロジェクトでは pyproject.toml や requirements.txt に依存関係を明示してください）

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb
   - （開発中は pip install -e . などでローカルインストール）
4. 環境変数を設定
   - プロジェクトルートに `.env` もしくは `.env.local` を作成すると自動で読み込まれます（読み込み優先: OS env > .env.local > .env）。
   - 自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env（テンプレート）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# kabuステーション
KABU_API_PASSWORD=your_kabu_password
# KABU_API_BASE_URL はデフォルトで http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

必須の環境変数:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

（設定が不足すると Settings 属性アクセス時に ValueError が発生します）

---

## 使い方（簡単な例）

以下は DuckDB スキーマ初期化→J-Quants から日足取得→保存 の最小例です。

```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# DuckDB ファイルを初期化（:memory: も使用可）
conn = init_schema("data/kabusys.duckdb")

# 例: 特定銘柄の2023-01-01〜2023-12-31の日足を取得して保存
from datetime import date
records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
count = save_daily_quotes(conn, records)
print(f"saved {count} rows")
```

トークンを明示的に使う場合:
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

id_token = get_id_token()  # settings.jquants_refresh_token を使用して ID token を取得
quotes = fetch_daily_quotes(id_token=id_token, code="7203")
```

監査ログ初期化:
```python
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

監査専用 DB を別に作成する場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

重要な挙動（注意点）
- jquants_client は内部でレートリミットを管理（120 req/min 相当の固定間隔）します。
- 最大リトライ回数は 3 回（408/429/5xx の場合に再試行、429 の場合は Retry-After 優先）。
- 401 を受け取ると設定に従いリフレッシュトークンで ID トークンを再取得し 1 回だけ再試行します。
- 保存関数は冪等（重複時は UPDATE）です。

---

## API サマリ（主要な関数 / モジュール）

- kabusys.config
  - settings: Settings インスタンス
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev
  - 自動 .env ロード機能（プロジェクトルート検出）

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(id_token: str|None, code: str|None, date_from: date|None, date_to: date|None) -> list[dict]
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB connection（スキーマ作成）
  - get_connection(db_path) -> DuckDB connection

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

- 拡張ポイント
  - kabusys.strategy, kabusys.execution, kabusys.monitoring: 将来的な戦略、発注、監視ロジックの配置場所

---

## ディレクトリ構成

（プロジェクトルート直下に `src/` を置くレイアウトの想定）

src/
- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得＋保存）
    - schema.py               — DuckDB スキーマ定義と初期化
    - audit.py                — 監査ログ（シグナル・発注・約定）
    - (その他: raw / utils 等を追加可能)
  - strategy/
    - __init__.py             — 戦略モジュールのエントリポイント（拡張用）
  - execution/
    - __init__.py             — 発注実行モジュールのエントリポイント（拡張用）
  - monitoring/
    - __init__.py             — モニタリング用のエントリポイント（拡張用）

プロジェクトルート:
- .env, .env.local, pyproject.toml, README.md, など

---

## 開発者向けメモ / 注意点

- Python の型ヒントに union 型（|）や from __future__ annotations を使用しているため Python 3.10+ を推奨します。
- DuckDB のファイルパスは settings.duckdb_path で管理されます。":memory:" を渡すとインメモリ DB を使用できます。
- audit モジュールはタイムゾーンを UTC に固定します（`SET TimeZone='UTC'`）。
- .env パーサはシンプルな実装だが、クォートとエスケープ、行末コメント処理を考慮しています。特殊ケースがある場合は .env の書式を調整してください。
- 実運用では `KABUSYS_ENV=live` のとき発注モジュール等の動作を厳格に管理してください（ここでは発注ロジック自体は含まれていません）。

---

問題や改善要望があれば README を更新するか、各モジュールの docstring を参照してください。