# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買プラットフォームの基盤となるライブラリです。
データ層（DuckDBスキーマ）、環境設定管理、戦略・実行・モニタリング用のパッケージ構成を提供します。

---

## 概要

- DuckDB を用いたローカルデータベーススキーマ（原データ、整形済みデータ、特徴量、発注/約定管理）を定義・初期化するモジュールを含みます。
- 環境変数（.env）ベースの設定管理を行い、J-Quants や kabuステーション API、Slack 通知などに必要な設定値をラップします。
- 将来的に戦略（strategy）、実行（execution）、監視（monitoring）モジュールで自動売買機能を実装するための土台を提供します。

---

## 主な機能一覧

- 環境変数の自動ロード（プロジェクトルートの .env / .env.local → OS 環境変数より下位）
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
  - クォートやコメント、`export KEY=val` 形式に対応したパーサ実装
- 設定アクセサ（settings）
  - J-Quants リフレッシュトークン、kabu API パスワード、Slack トークン／チャンネル等をプロパティとして取得
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL のバリデーション
- DuckDB スキーマ管理
  - raw / processed / feature / execution の 3 層（+ execution）に対応したテーブル群の DDL
  - 必要なインデックス作成
  - init_schema(db_path) でスキーマの冪等初期化（parent ディレクトリ自動作成）
  - :memory: を指定してインメモリ DB として動作可能
- パッケージ構成（strategy、execution、monitoring 用のパッケージプレースホルダ）

---

## 必要条件

- Python 3.10+
  - （ソース中で型ヒントに PEP 604 の `X | Y` を使用しているため）
- 必須 Python パッケージ（最低限）
  - duckdb

インストールは適宜プロジェクトの配布方法に合わせてください（pip、poetry 等）。例:

```bash
# 開発時（プロジェクトルートで）
python -m pip install -U pip
python -m pip install -e .  # setup / pyproject がある想定
# もしくは最低限 duckdb をインストール
python -m pip install duckdb
```

（本リポジトリに requirements.txt / pyproject.toml がある場合はそれに従ってください。）

---

## セットアップ手順

1. リポジトリをクローン／取得する
2. Python 3.10 以上の仮想環境を作成して有効化する
3. 依存パッケージをインストールする（少なくとも duckdb）
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定する

推奨の .env に含めるキー（例）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=...

# kabuステーション API
KABU_API_PASSWORD=...
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXXX

# DB パス（任意。デフォルトは data/kabusys.duckdb）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development  # development / paper_trading / live
LOG_LEVEL=INFO
```

注意:
- 自動的に `.env` と `.env.local` がプロジェクトルートから読み込まれます（OS 環境変数が優先）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## 使い方

以下は主要なモジュールの使い方例です。

- 設定（settings）を使う

```python
from kabusys.config import settings

# 必須値は未設定だと ValueError を投げる
token = settings.jquants_refresh_token
kabu_pw = settings.kabu_api_password

# 環境判定
if settings.is_live:
    print("本番モードです")
```

- DuckDB スキーマを初期化する

```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクトを返す（デフォルト: data/kabusys.duckdb）
db_path = settings.duckdb_path

# スキーマ作成（冪等）
conn = init_schema(db_path)

# 以降は conn を使ってクエリを実行できます
with conn:
    rows = conn.execute("SELECT name FROM sqlite_master LIMIT 10").fetchall()  # DuckDB の情報取得例
```

- インメモリ DB を使う（テスト向け）

```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

- 既存 DB に接続する（スキーマ初期化は行わない）

```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

---

## 環境変数と設定項目（要確認）

必須（未設定時はエラー）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション / デフォルトあり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live。デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO)

---

## ディレクトリ構成

プロジェクト（src 配下）のおおまかなファイル構成:

- src/
  - kabusys/
    - __init__.py               (パッケージ初期化、__version__ 等)
    - config.py                 (環境変数 / 設定管理)
    - data/
      - __init__.py
      - schema.py               (DuckDB スキーマ定義と init_schema / get_connection)
    - strategy/
      - __init__.py             (戦略モジュールのプレースホルダ)
    - execution/
      - __init__.py             (注文・実行ロジックのプレースホルダ)
    - monitoring/
      - __init__.py             (監視 / ロギング / 通知関連のプレースホルダ)

- .env, .env.local              (プロジェクトルートに置く想定)
- pyproject.toml / setup.cfg 等（存在する場合、パッケージ化設定）

---

## 開発/運用上の注意

- config.py の自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を起点に行います。CWD に依存しないため、パッケージ配布後も安定して動作します。
- .env パーサはシェル風の記法（export、シングル/ダブルクォート、コメント）に多く対応していますが、特殊な記法には注意してください。
- DuckDB のテーブル DDL は多くのチェック制約や外部キーを含みます。スキーマ変更は互換性に注意して行ってください。
- `KABUSYS_ENV` を `live` に設定する際は、本当に実運用であることを確認し、テスト環境と鍵・トークンを混在させないよう注意してください。

---

README は上記の内容を基に随時拡張してください。戦略・実行・監視の実装が追加され次第、利用例や CLI / デーモンの起動方法、テスト手順、CI 設定などを追加することを推奨します。