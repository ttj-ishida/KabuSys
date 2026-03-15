# KabuSys

日本株自動売買システム向けの共通ユーティリティ群（データ取得・スキーマ定義・監査ログなど）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株に関するデータ収集・保存・監査のための基盤ライブラリです。  
主に以下を提供します。

- J-Quants API クライアント（株価日足、財務データ、JPX カレンダー取得）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ（シグナル → 発注 → 約定 のトレースを保持）
- 環境変数ベースの設定管理（.env 自動読み込み機能）

設計上のポイント:
- API レート制限（120 req/min）遵守（固定間隔の RateLimiter）
- リトライ・指数バックオフ、401 受信時の自動トークンリフレッシュ
- 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias の抑止
- DuckDB への挿入は冪等（ON CONFLICT DO UPDATE）

---

## 機能一覧

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）
  - 必須環境変数チェック
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化
  - KABUSYS_ENV 値検証（development / paper_trading / live）
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - get_id_token（リフレッシュトークン → idToken）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - レート制御・リトライ・トークンキャッシュ機構
- DuckDB スキーマ（src/kabusys/data/schema.py）
  - init_schema(db_path) で全テーブルとインデックスを作成
  - get_connection(db_path) で既存 DB に接続
  - 標準的な Raw / Processed / Feature / Execution 層のテーブル定義を含む
- 監査ログ（src/kabusys/data/audit.py）
  - init_audit_schema(conn) で監査用テーブルを追加
  - init_audit_db(db_path) で監査用 DB を初期化（UTC タイムゾーンを設定）
  - シグナル → 発注 → 約定 のトレーサビリティを UUID 連鎖で実現

---

## 必要条件

- Python 3.9+
- 必要なパッケージ例（プロジェクトに requirements が無ければ最低限）:
  - duckdb

インストール例（仮）:
```
pip install duckdb
# またはプロジェクト配布に合わせて
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して依存をインストール
3. プロジェクトルートに `.env`（と必要なら `.env.local`）を作成

.env に設定すべき主要な環境変数（例）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — 値: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — 値: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

自動 .env 読み込み:
- パッケージ読み込み時にプロジェクトルート（.git or pyproject.toml）を起点に `.env` と `.env.local` を自動で読み込みます。
- 既存の OS 環境変数は上書きされません（`.env.local` は override=True で上書きするが OS 環境は保護されます）。
- 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

---

## 使い方（基本例）

以下は代表的な利用例です。実際はアプリ（戦略・発注エンジン）から呼び出して利用します。

- DuckDB スキーマ初期化（ファイル DB）
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# 以後 conn を使ってクエリや保存処理を行う
```

- DuckDB をインメモリで初期化
```python
from kabusys.data import schema

conn = schema.init_schema(":memory:")
```

- J-Quants から日足を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
from kabusys.data import schema
import duckdb

# DB 初期化（既存ファイルがあれば init_schema は冪等）
conn = schema.init_schema("data/kabusys.duckdb")

# トークンは内部で settings.jquants_refresh_token を参照するため、通常は省略可能
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# 保存（冪等: ON CONFLICT DO UPDATE）
save_daily_quotes(conn, records)
```

- 財務データやカレンダーの取得・保存は同様:
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar

- id token を明示的に取得（必要に応じて）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用
```

- 監査ログテーブルの初期化（既存 conn に追加）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
init_audit_schema(conn)  # UTC を設定して監査用テーブルを作成
```

- 監査専用 DB を別に作る場合
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 注意点 / 実装上の振る舞い

- API レート制限:
  - J-Quants: 120 req/min を固定間隔で守る実装（_RateLimiter）。
- リトライ:
  - ネットワークエラーや 408 / 429 / 5xx に対して最大 3 回の指数バックオフリトライ。
  - 401 を受け取った場合はリフレッシュを試みて 1 回だけ再試行。
- ページネーション:
  - fetch_* 系は pagination_key に対応し、全ページを取得する。
- データ保存:
  - save_* 系は ON CONFLICT DO UPDATE で冪等性を保証する。
  - PK 欠損のレコードはスキップしてログに警告を出す。
- タイムゾーン:
  - 監査ログ初期化では SET TimeZone='UTC' を実行し、UTC 保存を前提とする。
- .env のパース:
  - export KEY=val、シングル/ダブルクォート、行内コメントなどに対応。
  - コメントはクォートなしの場合に '#' の直前が空白またはタブのときのみコメントとみなすなどの仕様。

---

## ディレクトリ構成

（ソースの主要部分を抜粋）
```
src/
  kabusys/
    __init__.py           # パッケージ定義（__version__, __all__）
    config.py             # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py   # J-Quants API クライアント（取得・保存ロジック）
      schema.py           # DuckDB スキーマ定義・初期化
      audit.py            # 監査ログ（signal → order → execution トレース）
      audit.py
      ...                 # （将来的に news, executions など追加）
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py
```

---

## 開発メモ / 拡張ポイント

- strategy / execution / monitoring パッケージはインタフェース骨格を提供する想定。各戦略やブローカー連携はこの上に実装してください。
- DuckDB スキーマは DataPlatform.md / DataSchema.md に基づく多層構造（Raw → Processed → Feature → Execution）。必要に応じて列・インデックスを拡張できます。
- 監査ログは削除しない前提設計です。FK は ON DELETE RESTRICT を基本としています。

---

## ライセンス・貢献

（ここには実プロジェクトに合わせたライセンスや貢献ルールを追記してください）

---

README は以上です。サンプルコードの追加や、CI／デプロイ手順、環境変数の .env.example 作成などを追加したい場合は教えてください。