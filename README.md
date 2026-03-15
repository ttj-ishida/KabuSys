# KabuSys

日本株向け自動売買基盤（ライブラリ）  
バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けの基盤ライブラリです。  
データ収集・スキーマ管理、環境設定、戦略・発注・モニタリングのためのモジュール構成を提供します。本リポジトリにはデータベーススキーマ定義、環境変数管理ロジック、基本パッケージ構成が含まれています。

主な目的:
- DuckDB を用いたデータスキーマの定義と初期化
- 環境変数（.env）を用いた設定管理
- 戦略・発注・モニタリング等の土台整備

---

## 機能一覧

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動ロード（必要に応じて無効化可）
  - export 形式、引用符付き値、エスケープ、インラインコメント等に対応したパース処理
  - 必須項目は Settings クラス経由で取得し、未設定時はエラーを送出

- データベース（DuckDB）スキーマ定義 & 初期化
  - Raw / Processed / Feature / Execution の多層テーブル設計
  - 必要なテーブル・インデックスを冪等に作成する init_schema 関数
  - ":memory:" を指定してインメモリ DB の利用が可能

- パッケージ構造（戦略・発注・モニタリングのためのモジュールプレースホルダ）
  - kabusys.strategy, kabusys.execution, kabusys.monitoring 等

---

## 必要条件

- Python >= 3.10
  - （型ヒントに PEP 604 の `|` を使用）
- 依存パッケージ
  - duckdb

必要に応じて他のライブラリ（kabu API クライアントや Slack SDK 等）を追加してください。

---

## インストール

仮想環境を作成してからインストールすることを推奨します。

例（venv + pip）:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb
# パッケージを開発インストールする場合（プロジェクトルートに setup/pyproject がある想定）
pip install -e .
```

---

## 環境変数（.env）設定

プロジェクトルートの `.env` / `.env.local` を自動読み込みします（読み込みは OS 環境変数より低優先度）。自動読み込みを無効化したい場合は、実行前に環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

優先順位:
1. OS 環境変数
2. .env.local
3. .env

Settings が参照する主な環境変数（必須項目は取得時にエラーになります）:

- J-Quants
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- 実行環境・ログ
  - KABUSYS_ENV (任意, デフォルト: development) — 有効値: development / paper_trading / live
  - LOG_LEVEL (任意, デフォルト: INFO) — 有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL

サンプル `.env`（README 用例）:

```
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_api_password"
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

パーサーの注意点:
- `export KEY=val` 形式を許容
- クォート付き値ではエスケープ文字を解釈
- クォート無しの値では `#` の直前が空白/タブの場合をコメントと判定

---

## セットアップ（データベース初期化）

DuckDB スキーマを作成するには `init_schema` を使用します。初回のみ実行すれば問題ありません（冪等）。

例:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# 環境設定経由でパスを取得して初期化
conn = init_schema(settings.duckdb_path)

# インメモリ DB を使う場合
# conn = init_schema(":memory:")
```

init_schema は duckdb の接続オブジェクト（DuckDBPyConnection）を返します。既存 DB に接続するだけの場合は `get_connection` を使ってください（スキーマ初期化は行いません）。

---

## 使い方（簡単なコード例）

- 設定取得:

```python
from kabusys.config import settings

token = settings.jquants_refresh_token
base_url = settings.kabu_api_base_url
is_live = settings.is_live
```

- データベース接続とクエリ実行:

```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.config import settings

# 初期化済みなら get_connection で接続
conn = get_connection(settings.duckdb_path)

# SQL 実行例
df = conn.execute("SELECT COUNT(*) FROM prices_daily").fetchdf()
print(df)
```

- 自動読み込みを無効化してから設定を読み込む（テスト等）:

```bash
KABUSYS_DISABLE_AUTO_ENV_LOAD=1 python -c "import kabusys; print('auto load disabled')"
# Windows (PowerShell)
$env:KABUSYS_DISABLE_AUTO_ENV_LOAD = "1"; python -c "import kabusys; print('auto load disabled')"
```

---

## ディレクトリ構成

本リポジトリの主要ファイル/ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py                 # パッケージ定義（__version__ 等）
    - config.py                   # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py                 # DuckDB スキーマ定義・初期化 (init_schema, get_connection)
    - strategy/
      - __init__.py               # 戦略モジュール（実装場所）
    - execution/
      - __init__.py               # 発注/取引実行モジュール（実装場所）
    - monitoring/
      - __init__.py               # モニタリング機能（実装場所）
- .env.example                    # （推奨）サンプル環境変数ファイル（リポジトリにあれば）

---

## 開発メモ / 補足

- settings.env の値は `development`, `paper_trading`, `live` のいずれかでなければエラーになります。
- `.env` の自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行います。プロジェクトルートが見つからない場合は自動ロードをスキップします。
- ログレベルの検証は環境変数取得時に行われ、不正な値は ValueError を発生させます。
- 今後、kabu API や Slack への実際の連携ロジック、戦略実行・オーダーマネージャ等の実装を行ってください。

---

必要であれば README に含めるサンプル .env.example を自動生成したり、セットアップスクリプトの例（Makefile / scripts/）を追加で作成することもできます。どの情報を追加したいか教えてください。