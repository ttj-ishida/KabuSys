# KabuSys — 日本株自動売買システム

KabuSys は日本株向けの自動売買基盤の骨組みを提供する Python パッケージです。データ層（DuckDB）でのスキーマ定義、環境変数による設定管理、戦略/発注/モニタリング用のモジュール構成の雛形を含みます。

バージョン: 0.1.0

---

## 主要機能

- 環境変数 / .env 管理
  - プロジェクトルート（.git または pyproject.toml）を起点に `.env` と `.env.local` を自動で読み込み
  - `export KEY=val`、クォート、エスケープ、行末コメントなどを考慮した柔軟なパース
  - OS 環境変数 > .env.local > .env の優先度
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- 設定アクセス（Settings クラス）
  - J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）等のアクセサを提供
  - 必須変数未設定時は明確な例外を投げる

- DuckDB ベースのスキーマ定義と初期化
  - Raw / Processed / Feature / Execution の多層スキーマを定義
  - インデックス作成、外部キー考慮済みの作成順で安全に初期化
  - インメモリ（":memory:"）やファイルベースで利用可能

- モジュール構成（戦略、発注、モニタリングの雛形）
  - 将来的な拡張を考慮したパッケージ構造

---

## 必要条件

- Python 3.10+
- 必要パッケージ（例）: duckdb

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動

   ```
   git clone <repository-url>
   cd <repository-dir>
   ```

2. 仮想環境作成（任意）および有効化

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージのインストール

   最低限 DuckDB が必要です。パッケージ配布設定があれば次のようにインストールできます。

   ```
   pip install --upgrade pip
   pip install duckdb
   # または開発時はパッケージを editable インストール
   pip install -e .
   ```

4. 環境変数ファイルの作成

   プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成します。必須の環境変数の例:

   ```
   # .env の例
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   注: OS 環境変数が優先されます。自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB スキーマ初期化

   以下のコマンドでデータベースとテーブル群を作成できます。

   ```
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

---

## 使い方（基本例）

- 設定値にアクセスする

  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  print(settings.env, settings.log_level)
  if settings.is_live:
      print("ライブモードです")
  ```

- スキーマを初期化する（プログラムから）

  ```python
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  ```

- 既存 DB に接続する

  ```python
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  tables = conn.execute("SHOW TABLES").fetchall()
  print(tables)
  ```

- 自動 .env 読み込みをテストやユニットテストで無効化する

  環境変数を事前に設定するか、起動前に次を設定してください:

  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

- config のバリデーションについて

  - KABUSYS_ENV は `development`, `paper_trading`, `live` のいずれかでなければなりません。
  - LOG_LEVEL は `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` のいずれかでなければなりません。
  - 必須変数（例: JQUANTS_REFRESH_TOKEN 等）が未設定だと ValueError が発生します。

---

## ディレクトリ構成

以下は主要ファイルの構成（抜粋）です:

- src/
  - kabusys/
    - __init__.py
    - config.py               — 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py             — DuckDB スキーマ定義・初期化関数（init_schema, get_connection）
    - strategy/
      - __init__.py           — 戦略モジュール（雛形）
    - execution/
      - __init__.py           — 発注/実行モジュール（雛形）
    - monitoring/
      - __init__.py           — モニタリングモジュール（雛形）

主なファイル:
- src/kabusys/config.py
- src/kabusys/data/schema.py

---

## 開発メモ / 実装上の注意

- .env の自動読み込みは、パッケージが置かれた実際のプロジェクトルート（.git または pyproject.toml を含む）を探索して行います。CWD に依存しないため、インストール後の挙動が安定します。
- .env のパースはシェル風の記法（export、クォート、エスケープ、行内コメント）に対して堅牢性を高めていますが、複雑なシェル展開（$VAR の展開等）は行いません。
- DuckDB のスキーマは冪等（既存テーブルは上書きしない）で初期化されます。外部キーやインデックスの作成順を考慮しています。

---

この README は現状のコードベースをもとにした利用ガイドです。戦略実装、発注ロジック、モニタリング機能はこれから拡張するための雛形を提供しています。質問や改善提案があればお知らせください。