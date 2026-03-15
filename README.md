# KabuSys

日本株自動売買システム（ライブラリ部分）

バージョン: 0.1.0

概要:
KabuSys は日本株の自動売買に必要なデータ層（Raw / Processed / Feature / Execution）と監査ログ（トレーサビリティ）を DuckDB 上に定義・初期化するためのモジュール群、および環境変数ベースの設定管理を提供するライブラリです。戦略や発注ロジック、モニタリング周りの拡張点を備えています。

---

## 主な機能

- 環境変数からのアプリ設定読み取り（自動 .env ロード機能）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - OS 環境変数 > .env.local > .env の優先順位
  - 必須設定が未定義の場合は例外を発生させるヘルパー
- DuckDB 用スキーマ定義と初期化
  - Raw / Processed / Feature / Execution 各レイヤーのテーブル DDL（冪等に作成）
  - 実用的なインデックス作成
  - init_schema / get_connection API を提供
- 監査ログ（トレーサビリティ）用スキーマ
  - シグナル → 発注要求 → 約定 の連鎖をトレースするテーブル群
  - 冪等キー（order_request_id）や状態遷移管理、UTC タイムスタンプ運用
  - init_audit_schema / init_audit_db API を提供

---

## 必要要件

- Python 3.10 以上（型アノテーションで `X | Y` を使用）
- duckdb Python パッケージ
- （利用する外部 API に応じて）各種トークンやクライアントライブラリ

推奨インストール（例）
- 仮想環境を作成して依存をインストールする:
  - python -m venv .venv
  - source .venv/bin/activate あるいは .venv\Scripts\activate
  - pip install duckdb
  - pip install -e .  （パッケージ化されている場合）

---

## 環境変数（設定項目）

このプロジェクトは環境変数から設定を読み込みます。以下はコード上で参照される主なキーです。

必須（未設定時は例外）:
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — 有効値: development, paper_trading, live （デフォルト: development）
- LOG_LEVEL — 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL （デフォルト: INFO）

自動 .env ロード制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env ファイルを読み込む処理を無効化します（テストなどで利用）。

.env 読み込みの挙動:
- プロジェクトルートの判定はパッケージ配置場所から .git または pyproject.toml をさかのぼって行うため、CWD に依存しません。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- .env のパースは export 形式やクォート、コメントを考慮した実装になっています。

.example のサンプル（README 用）:
（実際は .env.example を参照して作成してください）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージのインストール
   - pip install duckdb
   - （パッケージとして配布している場合）pip install -e .

4. 環境変数設定
   - プロジェクトルートに .env を作成するか、OS 環境変数で設定してください。
   - 自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方（基本例）

まずは DuckDB スキーマを初期化して接続を得ます。

Python REPL やスクリプトから（ファイルパス指定）:
```python
from kabusys.data.schema import init_schema, get_connection
from pathlib import Path

# ファイルに永続化する場合
db_path = Path("data/kabusys.duckdb")
conn = init_schema(db_path)  # テーブルとインデックスを作成して接続を返す

# あるいは既存 DB に接続するだけ
conn2 = get_connection(db_path)
```

インメモリ DB（テスト用）:
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

監査ログ（audit）を別 DB に初期化する例:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

設定（環境変数）にアクセスする例:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
is_live = settings.is_live
duckdb_path = settings.duckdb_path  # Path オブジェクト
```

設定未定義時は _require 関数により ValueError が発生します。

注意点:
- init_schema はディレクトリがなければ自動で親ディレクトリを作成します。
- init_schema / init_audit_schema は冪等（既に存在するテーブルはスキップ）です。
- 監査ログは UTC タイムゾーンで TIMESTAMP を運用する想定です（init_audit_schema は SET TimeZone='UTC' を実行します）。

---

## ディレクトリ構成（抜粋）

このリポジトリの主要ファイル・モジュール構成は次のとおりです。

- src/
  - kabusys/
    - __init__.py
    - __version__ = "0.1.0"
    - config.py                — 環境変数・設定管理（自動 .env 読み込み含む）
    - data/
      - __init__.py
      - schema.py              — DuckDB スキーマ定義 & init_schema / get_connection
      - audit.py               — 監査ログ（トレーサビリティ）テーブル定義 & init_audit_schema
      - (その他: audit, monitoring 用モジュール)
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主要な API:
- kabusys.config.settings — 設定取得用オブジェクト（プロパティで各種設定を取得）
- kabusys.data.schema.init_schema(db_path) -> duckdb connection
- kabusys.data.schema.get_connection(db_path) -> duckdb connection
- kabusys.data.audit.init_audit_schema(conn)
- kabusys.data.audit.init_audit_db(db_path) -> duckdb connection

---

## 開発メモ / 注意事項

- Python の型アノテーションに `X | Y` を使用しているため Python 3.10 以上が必要です。
- .env パーサはクォートや export 形式をサポートします。細かな動作は config._parse_env_line を参照してください。
- 監査レイヤーの設計は「削除しない」「UTC 保存」「冪等キー」などを前提としたものです。プロダクション運用時はバックアップ / 保守方針を検討してください。
- 実際の取引（kabu API 呼び出しや Slack 通知等）は本リポジトリの別モジュール（execution / monitoring / strategy）で実装します。これらは拡張ポイントとして提供されています。

---

もし README に追記してほしい情報（例: 実際の .env.example のテンプレート、CI / テスト手順、パッケージ配布方法など）があれば教えてください。