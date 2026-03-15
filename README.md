# KabuSys

日本株向けの自動売買システム向けライブラリ（基盤モジュール群）。
市場データ収集・スキーマ定義、戦略/発注/モニタリングのための基礎機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム構築に役立つ共通モジュール群です。  
主に以下を提供します。

- 環境変数経由の設定管理（自動的にプロジェクトルートの .env を読み込み）
- DuckDB を用いた多層データスキーマ（Raw / Processed / Feature / Execution）
- 戦略・実行・モニタリングのためのパッケージ骨組み

このリポジトリはライブラリとして import して利用されることを想定しています。

---

## 主な機能一覧

- 設定管理（kabusys.config.Settings）
  - 必須/任意の環境変数をプロパティで取得
  - 自動 .env 読み込み（プロジェクトルートを .git または pyproject.toml から検出）
  - 自動読み込みの無効化オプションあり
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の層に対応したテーブル DDL を用意
  - インデックス定義、外部キー配慮の作成順を考慮
  - init_schema() で初期化（冪等）、get_connection() で接続取得
- パッケージ構成に応じたモジュールプレースホルダ
  - kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring

---

## 必要条件

- Python 3.9+（typing | Path 等を使用）
- duckdb Python パッケージ

（プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン / ダウンロード
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb
   - （開発時）pip install -e . など
4. 環境変数の準備
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成
   - 必須キーを設定（下に一覧あり）

---

## 環境変数（主要）

必須（未設定だと Settings の該当プロパティ呼び出し時に例外）:

- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルトあり:

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABUS_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、自動で .env をロードする処理を無効化できます（テスト等で利用）

.env の自動ロードの優先度（実装ロジック）:
- OS 環境変数（既に存在するキー）は保護され、上書きされません
- 次にプロジェクトルートの `.env` を読み込み（既存キーは上書きなし）
- さらに `.env.local` を読み込み（.env の値を上書き）
- プロジェクトルートはこのパッケージのファイル位置から親方向に `.git` または `pyproject.toml` を探して決定します。見つからない場合は自動ロードをスキップします。

.env のパースはシェル風の簡易仕様に対応しています（export プレフィックス、シングル/ダブルクォート、エスケープ、行末コメントの扱い等をサポート）。

---

## 使い方（簡単な例）

設定の利用例（Python）:

```python
from kabusys.config import settings

# 必須プロパティにアクセスすると、未設定なら ValueError が発生します
token = settings.jquants_refresh_token
kabu_url = settings.kabu_api_base_url
print("env:", settings.env)
```

DuckDB スキーマを初期化する例:

```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# ファイルベース DB を初期化
conn = init_schema(settings.duckdb_path)

# またはテスト用にインメモリ DB を初期化
mem_conn = init_schema(":memory:")

# 既存 DB へ接続する場合（初回は init_schema を呼ぶこと）
conn2 = get_connection(settings.duckdb_path)
```

自動 .env 読み込みを無効化してテストしたい場合:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print('auto env load disabled')"
```

---

## ディレクトリ構成

このリポジトリの主要ファイル/ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py                # パッケージのメタ情報（__version__）
    - config.py                  # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py                # DuckDB スキーマ定義・初期化 (init_schema, get_connection)
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

README と同階層に pyproject.toml 等が存在する可能性があり、config はそれらを手掛かりにプロジェクトルートを決定します。

---

## 開発メモ

- schema.init_schema は冪等にテーブルとインデックスを作成します。既存テーブルは上書きされません。
- DuckDB のファイルパスの親ディレクトリがなければ自動で作成します。
- settings のプロパティは実行時に環境変数を参照するため、import 時点で必須変数チェックは行われません（プロパティアクセス時にチェック）。
- .env のパースは一般的なケースに対応していますが、複雑な shell 構文はサポート外です。

---

必要に応じて、戦略実装・発注ロジック・監視機能をこの基盤の上に実装していってください。