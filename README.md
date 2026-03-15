# KabuSys

日本株向けの自動売買システム用ライブラリ（骨組み）。  
本リポジトリはデータスキーマ定義、環境設定読み込み、及び戦略・実行・監視モジュールのベースを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、以下のような自動売買に必要なレイヤーを想定したパッケージ構成を提供します。

- データ収集・保存（Raw / Processed / Feature / Execution 層）
- 環境変数ベースの設定管理（.env 自動読み込み機能付き）
- DuckDB を用いたスキーマ定義・初期化
- 戦略（strategy）、発注（execution）、監視（monitoring）モジュールのためのパッケージ入れ物

現状は主に設定管理とデータベーススキーマ初期化の機能が実装されています。戦略や実行の具体実装は各モジュールに追加していきます。

---

## 主な機能一覧

- 環境変数/`.env` ファイルの自動読み込み
  - プロジェクトルート（`.git` または `pyproject.toml` を基準）を自動検出
  - `.env` → `.env.local` の順で読み込み（OS 環境変数は優先）
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動読み込みを抑止可能
  - export 形式や引用符付き値、行内コメントなど一般的な `.env` 表記を考慮してパース
- 設定オブジェクト `kabusys.config.settings`
  - 必須項目は参照時に未設定なら例外を投げる（明示的エラー）
  - J-Quants / kabu API / Slack / DB パス / 実行環境切替（development/paper_trading/live）などを提供
- DuckDB スキーマ定義と初期化 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution 層のテーブルをDDLで定義
  - インデックス作成も実行
  - `init_schema(db_path)` で DB を作成・テーブル定義を実行（冪等）
  - `get_connection(db_path)` で既存 DB へ接続（スキーマ初期化は行わない）

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈で `|` を使用しているため）
- pip が利用可能

1. リポジトリをクローン／取得

2. 仮想環境を作成して有効化（推奨）
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 必要パッケージのインストール
   - 本コードベースで必須なのは duckdb です。将来的に外部 API 用パッケージ（Slack クライアント等）が必要になる場合があります。
   - 例:
     - pip install duckdb

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数設定
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を作成します。
   - 自動読み込み仕様:
     - OS 環境変数 > .env.local > .env
     - プロジェクトルートは `.git` または `pyproject.toml` を基準に検出されます。
     - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで利用）。

必要な環境変数（参照時に未設定だと例外になります）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルト値あり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABUS_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

例: .env の雛形
```
# .env
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C0123456789"

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方（簡単な例）

- 設定の参照
```py
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 未設定だと ValueError を送出
print(settings.duckdb_path)            # Path オブジェクト
print(settings.is_live)
```

- DuckDB スキーマ初期化
```py
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection

# settings.duckdb_path に基づいて DB･テーブルを作成
conn = init_schema(settings.duckdb_path)

# 以降、conn を用いてクエリ実行
df = conn.execute("SELECT count(*) FROM prices_daily").fetchdf()
```

- 既存 DB へ接続（初期化不要）
```py
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

- 自動 .env 読み込みを無効にしてテストしたい場合
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
# またはプロセス起動時に環境変数を指定
KABUSYS_DISABLE_AUTO_ENV_LOAD=1 python your_script.py
```

エラーハンドリングの注意:
- 設定項目（上で示した必須キー）を参照するとき、未設定だと ValueError が発生します。起動前に必須環境変数をセットしてください。

---

## ディレクトリ構成

以下はこのコードベースの主要ファイル・ディレクトリ構成です。

- src/kabusys/
  - __init__.py               — パッケージ情報（__version__ 等）
  - config.py                 — 環境変数／設定管理（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - schema.py               — DuckDB の DDL 定義と init_schema / get_connection
  - strategy/
    - __init__.py             — 戦略モジュール用のパッケージプレースホルダ
  - execution/
    - __init__.py             — 発注・実行モジュール用のパッケージプレースホルダ
  - monitoring/
    - __init__.py             — 監視・モニタリング用のパッケージプレースホルダ

主なファイルの役割:
- config.py: プロジェクトルート自動検出、.env ファイルパーサ、Settings クラス（環境変数の取得・検証）。
- data/schema.py: 各レイヤー（Raw/Processed/Feature/Execution）のテーブル DDL を定義し、DuckDB に対してテーブル作成・インデックス作成を実行する。`init_schema` は親ディレクトリを自動作成します。

---

## トラブルシューティング

- ValueError: 環境変数が未設定
  - 必須環境変数（JQUANTS_REFRESH_TOKEN 等）が設定されているか確認してください。
- .env が読み込まれない
  - 自動読み込みはプロジェクトルート（`.git` または `pyproject.toml`）を基準に行います。プロジェクトルートが検出されないと自動読み込みはスキップされます。
  - 自動読み込みを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` が設定されていないか確認してください。
- duckdb が import できない
  - duckdb を pip 等でインストールしてください（pip install duckdb）。

---

この README は現時点での実装に基づいたガイドです。戦略・実行・監視の具体的実装は今後拡張していく想定です。機能追加や使い方に関する要望があればお知らせください。