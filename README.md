# KabuSys

日本株向け自動売買プラットフォームのライブラリ（KabuSys）。  
データ取得（J-Quants）、DuckDB によるデータ格納、監査ログ用スキーマなど、自動売買システムの基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を主な目的とするライブラリです。

- J-Quants API から株価日足・財務データ・JPX カレンダーを取得するクライアント
- DuckDB を用いた多層スキーマ（Raw / Processed / Feature / Execution）定義と初期化
- 発注〜約定に関する監査ログ（トレーサビリティ）用スキーマ
- 環境変数管理（.env 自動ロード、必須検証）とランタイム設定

設計上のポイント:
- API レート制限（120 req/min）を守る固定間隔スロットリング
- 指数バックオフを用いたリトライ、401 時の自動トークンリフレッシュ
- データ取得時の fetched_at 記録（Look-ahead Bias 防止）
- DuckDB への保存は冪等（ON CONFLICT ... DO UPDATE）で重複更新を回避

---

## 機能一覧

- 環境設定管理（settings）
  - 必須環境変数の検証、.env/.env.local の自動読み込み（プロジェクトルート検出）
  - 環境（development, paper_trading, live）・ログレベル検証

- J-Quants API クライアント（kabusys.data.jquants_client）
  - get_id_token（リフレッシュトークンから id_token を取得）
  - fetch_daily_quotes（株価日足、ページネーション対応）
  - fetch_financial_statements（四半期財務、ページネーション対応）
  - fetch_market_calendar（市場カレンダー）
  - save_* 系関数で DuckDB へ冪等保存（raw_prices, raw_financials, market_calendar）

- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema: データ層（Raw/Processed/Feature/Execution）のテーブルとインデックスを作成
  - get_connection: 既存 DB への接続取得

- 監査ログ（kabusys.data.audit）
  - init_audit_schema / init_audit_db: 発注フローの監査テーブル（signal_events, order_requests, executions）を初期化
  - 監査設計は UUID 連鎖・冪等性・UTC タイムスタンプを前提

---

## セットアップ手順

前提:
- Python 3.9+（型アノテーションや一部構文を前提）
- ネットワーク環境（J-Quants API へ接続可能）
- 必要なパッケージ（例: duckdb）

仮想環境を作成してパッケージをインストールする例:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb
# 開発用途: pip install -e .
```

依存の最低限:
- duckdb
（プロジェクトルートに requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）

環境変数（必須）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード
- SLACK_BOT_TOKEN       : 通知用 Slack Bot トークン
- SLACK_CHANNEL_ID      : 通知送信先 Slack チャンネル ID

オプション/デフォルト:
- KABUSYS_ENV           : development | paper_trading | live （デフォルト: development）
- LOG_LEVEL             : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視 DB などで使用する SQLite パス（デフォルト: data/monitoring.db）

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）を検出し、.env → .env.local の順に読み込みます。
- テスト等で自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

サンプル .env（README 用例）:

```
# 必須
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# オプション
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本）

以下はライブラリを使った典型的なワークフローの例です。

1) DuckDB スキーマ初期化

```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリは自動作成されます）
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

2) J-Quants からデータ取得して保存（例: 日足）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# conn は上で取得した DuckDB 接続
records = fetch_daily_quotes(code="7203")  # 例: トヨタ(7203)
n = save_daily_quotes(conn, records)
print(f"saved {n} records")
```

fetch_* 関数はページネーションに対応しており、認証トークンは内部でキャッシュ・自動リフレッシュされます。レート制限（120 req/min）・リトライ・バックオフはクライアント側で制御されます。

3) 監査ログスキーマの初期化

通常は data.schema.init_schema で作った conn を渡して初期化します:

```python
from kabusys.data import audit

# 既存の DuckDB 接続に監査テーブルを追加
audit.init_audit_schema(conn)
```

あるいは監査専用 DB を単独で作成する場合:

```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/audit.duckdb")
```

4) 環境設定の参照

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env)       # development / paper_trading / live
print(settings.is_live)
```

エラー例: 必須環境変数が未設定の場合、settings のプロパティ参照時に ValueError が上がります。

---

## 主要 API（抜粋）

- kabusys.config.settings
  - jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id, duckdb_path, env, log_level, is_live, is_paper, is_dev

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(id_token: str | None = None, code: str | None = None, date_from: date | None = None, date_to: date | None = None) -> list[dict]
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int

- kabusys.data.schema
  - init_schema(db_path) -> duckdb connection
  - get_connection(db_path) -> duckdb connection

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path) -> duckdb connection

---

## ディレクトリ構成

リポジトリ（src を含む場合）の想定構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                     # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py           # J-Quants API クライアント（取得＋保存ロジック）
      - schema.py                   # DuckDB スキーマ定義・初期化
      - audit.py                    # 監査ログスキーマ（発注・約定トレース）
      - audit.py
      - ...
    - strategy/
      - __init__.py                 # 戦略関連モジュール（拡張点）
    - execution/
      - __init__.py                 # 発注/接続モジュール（拡張点）
    - monitoring/
      - __init__.py                 # 監視・メトリクス用（拡張点）

実際のファイルは上記からさらに拡張される想定です。strategy / execution / monitoring はフレームワークの拡張ポイントとして空のパッケージから始まっています。

---

## 運用上の注意

- J-Quants API のレート制限（120 req/min）に注意してください。クライアントは内部で固定間隔スロットリングを行いますが、大量並列リクエストは避けてください。
- DuckDB のファイルパスは settings.duckdb_path で調整できます。運用時は適切なバックアップ／永続化対策を検討してください。
- すべての監査ログ TIMESTAMP は UTC を想定しています（init_audit_schema は SET TimeZone='UTC' を実行します）。
- 自動 .env 読み込みは便利ですが、テスト時などに副作用が必要な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- 本ライブラリは基盤機能を提供します。実際の発注処理（証券会社 API 連携）、リスク管理、戦略ロジックは別モジュール／アプリ側で実装してください。

---

## 開発・拡張

- strategy / execution / monitoring は拡張ポイントとしてパッケージが用意されています。戦略のバージョニングやシグナル生成、発注コネクタ（kabuステーション等）を実装して組み合わせてください。
- DuckDB スキーマを変更する場合は互換性（既存データ、外部キー、インデックス）に注意してください。DDL は schema.py に集約されています。

---

疑問点や追加のドキュメント（例: DataSchema.md, DataPlatform.md、各 API の詳細使用例）を望まれる場合はお知らせください。README を用途に合わせて追記します。