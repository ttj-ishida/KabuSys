# KabuSys

日本株自動売買プラットフォームのための軽量ライブラリ。市場データの保存・スキーマ定義、環境設定の読み込み、戦略・発注・監視のための基盤モジュール群を提供します（現状はスキーマと設定管理が中心実装されています）。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム構築に必要な共通機能をまとめたパッケージです。主な役割は次の通りです。

- 環境変数/`.env` ファイルからの設定読み込みと管理
- DuckDB を利用したデータレイヤ（Raw / Processed / Feature / Execution）のスキーマ定義と初期化
- 戦略、実行、監視のためのモジュール群（骨組み）

現在の実装では設定管理（`kabusys.config`）と DuckDB スキーマ初期化（`kabusys.data.schema`）が主要な機能として提供されています。

---

## 機能一覧

- 環境設定
  - `.env` / `.env.local` ファイルまたは OS 環境変数からの自動読み込み
  - export 形式、クォート（エスケープ含む）、コメントのパースに対応
  - 自動ロードはプロジェクトルート（`.git` もしくは `pyproject.toml`）を起点に行う
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- 設定取得 API
  - `kabusys.config.settings` オブジェクトから各種設定値を取得（例: `settings.jquants_refresh_token`）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル DDL 定義
  - インデックス作成
  - `init_schema(db_path)` によるデータベースファイルの初期化（冪等）
  - `get_connection(db_path)` による既存 DB への接続取得

- モジュール構成（今後実装される想定）
  - `kabusys.strategy`：戦略ロジック
  - `kabusys.execution`：発注・約定管理
  - `kabusys.monitoring`：監視・ログ送信など

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションの記法などを使用しているため）
- pip が利用可能

1. 仮想環境を作成・有効化（推奨）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. 必要パッケージをインストール
   - duckdb など最低限の依存を入れてください。
     - pip install duckdb
   - （パッケージをプロジェクトとしてインストールする場合）
     - プロジェクトルートに pyproject.toml / setup がある想定で:
       - pip install -e .

3. 環境変数 / .env の準備
   - プロジェクトルート（`.git` や `pyproject.toml` があるディレクトリ）に `.env` や `.env.local` を置くと自動で読み込みます（既定: OS > .env.local > .env の優先度）。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須となる主要な環境変数（コード上で必須扱いとなるもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルト値あり）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（有効値: development / paper_trading / live、デフォルト: development）
- LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）

例: .env の雛形
```
# 必須
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="kabu_api_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C12345678"

# 任意
DUCKDB_PATH="data/kabusys.duckdb"
SQLITE_PATH="data/monitoring.db"
KABUSYS_ENV="development"
LOG_LEVEL="INFO"
```

---

## 使い方

主に設定の参照方法と DuckDB スキーマ初期化の例を示します。

1. 設定値の参照
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
kabu_url = settings.kabu_api_base_url
is_live = settings.is_live
db_path = settings.duckdb_path  # pathlib.Path
```

環境変数が未設定の場合は、必須プロパティは ValueError を送出します（例: `JQUANTS_REFRESH_TOKEN` が未設定なら例外）。

2. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# デフォルトパスに初期化
conn = init_schema(settings.duckdb_path)

# メモリ内 DB として初期化（テスト用途）
mem_conn = init_schema(":memory:")
```

`init_schema` は指定したパスの親ディレクトリを自動作成し、テーブル・インデックスをすべて作成します（既存の場合はスキップされ、冪等です）。既存 DB に接続するだけなら `get_connection(db_path)` を使用してください。

3. 簡単なクエリ実行例
```python
conn = init_schema("data/kabusys.duckdb")
# pandas を使ってデータ取得等も可能
df = conn.execute("SELECT * FROM prices_daily WHERE code = '7203' ORDER BY date DESC LIMIT 10").df()
```

---

## .env パーサの挙動（補足）

- 行先頭の `export ` を許容（例: export KEY=val）
- シングル/ダブルクォートされた値内のバックスラッシュエスケープ処理に対応
- クォートなしの場合、`#` の直前がスペースまたはタブであればコメント扱い
- 自動ロード順序:
  1. OS 環境変数（既に設定されているものは保護される）
  2. .env（override=False のため既存 OS 環境変数を上書きしない）
  3. .env.local（override=True：.env や既存のユーザ環境変数を上書き。ただし OS 環境変数は保護される）
- もしプロジェクトルートが見つからない（`.git` と `pyproject.toml` のどちらも見つからない）場合、自動ロードはスキップされる

---

## ディレクトリ構成

（プロジェクトの主要ファイルを抜粋した構成）

- src/
  - kabusys/
    - __init__.py            # パッケージ初期化（version, __all__）
    - config.py              # 環境設定読み込みと Settings API
    - data/
      - __init__.py
      - schema.py            # DuckDB スキーマ定義と init_schema / get_connection
    - strategy/
      - __init__.py          # 戦略モジュール（将来的な拡張箇所）
    - execution/
      - __init__.py          # 発注・実行モジュール（将来的な拡張箇所）
    - monitoring/
      - __init__.py          # 監視・アラート関連（将来的な拡張箇所）

---

## 開発メモ / 注意点

- Python バージョンは 3.10 以上を想定（型記法に `|` を使用）。
- `.env.example` を参考に `.env` を作成すること（`Settings._require` が未設定時に案内メッセージを出します）。
- 自動ロードの振る舞いをテスト等で切り替える場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用してください。
- DuckDB のスキーマは外部キーや制約を多用しているため、DDL の順序や削除時の挙動に注意してください（`ON DELETE CASCADE` / `ON DELETE SET NULL` を利用）。

---

必要であれば README に以下を追加できます:
- API リファレンス（関数・クラスの詳細）
- .env.example の完全なテンプレート
- CI / テストの手順
- サンプル戦略・テストデータの利用方法

ご希望があれば追記・修正します。