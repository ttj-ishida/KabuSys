# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ収集、スキーマ管理、監査ログの初期化、J-Quants API クライアント等を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤構築を助けるためのライブラリ群です。主に以下を目的としています。

- J-Quants API からの市場データ（株価日足、財務データ、JPX カレンダー）取得
- DuckDB に基づく多層スキーマ（Raw / Processed / Feature / Execution）定義および初期化
- 監査ログ（シグナル→発注→約定のトレース）用テーブルの初期化
- 環境変数管理・設定読み込みユーティリティ
- 将来的な戦略・実行・監視モジュールのためのパッケージ構成

設計上の特徴:
- J-Quants API のレート制限（120 req/min）を守る RateLimiter を実装
- リトライ（指数バックオフ）・401 に対する自動トークンリフレッシュ対応
- データ取得時に fetched_at を UTC で記録して Look-ahead Bias を防止
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で再実行可能

---

## 主な機能一覧

- 環境設定管理（自動でプロジェクトルートの .env / .env.local を読み込み）
- J-Quants API クライアント
  - get_id_token（リフレッシュトークンから idToken を取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - API レート制限・リトライ・自動トークンリフレッシュ
- DuckDB スキーマ管理
  - init_schema(db_path) : 全テーブル・インデックスを作成
  - get_connection(db_path) : 既存 DB へ接続
- 監査ログ（audit）
  - init_audit_schema(conn) : 監査用テーブルを既存接続へ追加
  - init_audit_db(db_path) : 監査用 DB 初期化
- データ保存ユーティリティ
  - save_daily_quotes / save_financial_statements / save_market_calendar（冪等保存）

---

## 動作環境・依存

- Python 3.10 以上（型ヒントに | を使用）
- 主要依存パッケージ:
  - duckdb
- 標準ライブラリ: urllib, json, logging, datetime, pathlib など

インストール時は requirements を整備してください（本 README にはパッケージ化インストール例を記載）。

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb
   - （開発用）pip install -e .

4. 環境変数を準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くか、OS 環境変数として設定します。
   - 自動ロードは既定で有効。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

.env の例:
JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL などを想定しています。具体例:

KABUSYS の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

---

## 使い方（基本例）

以下は基本的な初期化・データ取得・保存フローのサンプルです。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数を参照して Path を返す
conn = init_schema(settings.duckdb_path)
```

2) J-Quants から日足を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# 例: 特定コード・期間を指定して取得
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# DuckDB 接続に保存（冪等: ON CONFLICT DO UPDATE）
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

3) 財務データ・カレンダーの取得・保存も同様
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

fin = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

4) ID トークンを直接取得したい場合
```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を使用
```

5) 監査ログ用テーブルを既存接続に追加
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # 既存の DuckDB 接続に監査テーブルを作成
```

注意点:
- fetch 系関数は内部でレート制御・リトライ・トークンリフレッシュを行います。
- save_* 系関数は PK の欠損行をスキップし、重複は UPDATE で上書きする設計です。
- 監査系はタイムゾーンを UTC に固定して保存します（init_audit_schema 内で SET TimeZone='UTC' を実行）。

---

## API（主要な公開関数の概要）

- kabusys.config
  - settings: Settings インスタンス（各種環境変数アクセス）
    - settings.jquants_refresh_token
    - settings.kabu_api_password
    - settings.kabu_api_base_url
    - settings.slack_bot_token
    - settings.slack_channel_id
    - settings.duckdb_path, settings.sqlite_path
    - settings.env, settings.log_level, settings.is_live / is_paper / is_dev

- kabusys.data.jquants_client
  - get_id_token(refresh_token: Optional[str]) -> str
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None) -> list[dict]
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int

- kabusys.data.schema
  - init_schema(db_path) -> duckdb.Connection
  - get_connection(db_path) -> duckdb.Connection

- kabusys.data.audit
  - init_audit_schema(conn) -> None
  - init_audit_db(db_path) -> duckdb.Connection

---

## ディレクトリ構成

パッケージの主要ファイル/ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（取得・保存）
      - schema.py                    — DuckDB スキーマ定義・初期化
      - audit.py                     — 監査ログ用テーブル定義・初期化
    - strategy/
      - __init__.py                  — 戦略モジュール（拡張ポイント）
    - execution/
      - __init__.py                  — 実行（発注）モジュール（拡張ポイント）
    - monitoring/
      - __init__.py                  — 監視モジュール（拡張ポイント）

---

## 注意事項・運用上のポイント

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）から行われます。CWD に依存せず動作します。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。
- J-Quants API のレート制限（120 req/min）を厳守する設計になっています。大量取得の際は適切に間隔を空けてください。
- すべてのタイムスタンプは UTC を基本とします（監査テーブルでは SET TimeZone='UTC' が実行されます）。
- DuckDB のスキーマは初期化処理が冪等になるよう設計されています。既存データの上書きに注意してください（ON CONFLICT が使われます）。

---

この README はコードベースの主要箇所を基に作成しています。戦略、実行、監視モジュールは拡張ポイントとして用意されており、プロジェクト要件に応じて実装を追加してください。必要であれば .env.example やより詳細な API 使用例、CI/デプロイ手順を追記できます。