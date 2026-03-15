# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ/基盤実装）

---

## 概要

KabuSys は日本株の自動売買システムに必要な「データ基盤」「特徴量レイヤ」「発注／監査レイヤ」を提供する Python パッケージです。  
DuckDB を用いたスキーマ定義・初期化、環境変数ベースの設定管理、監査ログ（トレーサビリティ）用テーブルなど、戦略実装や実運用側で必要となる基盤機能を備えています。

主な設計方針：
- データは複数レイヤ（Raw / Processed / Feature / Execution）で管理
- 発注フローは監査（audit）テーブルにより UUID 連鎖で完全トレース可能
- 環境変数（.env）による設定管理と自動ロード機能

---

## 機能一覧

- 環境設定管理（.env 自動読み込み、保護された OS 環境変数の扱い）
  - 自動ロード条件: プロジェクトルート（.git または pyproject.toml が存在）を検出して `.env` → `.env.local` の順で読み込み（OS 環境変数が優先）
  - 自動ロードを無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブルを一括作成（冪等）
  - インデックスを含む最適化済みスキーマ
  - DB ファイルの親ディレクトリ自動作成
- 監査ログ（audit）テーブル
  - signal_events / order_requests / executions を含む監査用スキーマ
  - 発注の冪等キー（order_request_id）や証券会社別約定IDの扱い
  - すべてのタイムスタンプは UTC（init 時に TimeZone を UTC に設定）
- 設定（Settings）クラス
  - J-Quants、kabu API、Slack、データベースパス、実行環境（development/paper_trading/live）等をプロパティで取得
  - 必須キー未設定時に ValueError を発生

---

## 要件

- Python 3.10+
  - （型注釈に `|` を使用、`from __future__ import annotations` を含むため）
- 依存ライブラリの主要なもの
  - duckdb
- （将来的に）kabu API クライアントや Slack クライアント等を追加でインストールする可能性あり

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成して有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 依存ライブラリをインストール
   - 最低限 DuckDB をインストールします：
     ```
     pip install duckdb
     ```
   - パッケージを開発インストール（プロジェクトに pyproject.toml / setup がある場合）:
     ```
     pip install -e .
     ```

4. 環境変数を用意
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと、自動で読み込まれます（ただし OS 環境変数が優先される）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. `.env` の例（`.env.example` を参照してください）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabu API
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルト）

   # Slack
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development  # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単なコード例）

- 設定を取得する
  ```python
  from kabusys.config import settings

  # 必須キーは未設定だと ValueError を投げます
  token = settings.jquants_refresh_token
  print("env:", settings.env)
  print("is_live:", settings.is_live)
  ```

- DuckDB スキーマを初期化する（メイン DB）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # file path または ":memory:"
  # conn は duckdb.DuckDBPyConnection
  ```

  - 既存 DB に接続するだけなら get_connection() を使用:
    ```python
    from kabusys.data.schema import get_connection
    conn = get_connection(settings.duckdb_path)
    ```

- 監査ログ用スキーマを既存接続に追加する
  ```python
  from kabusys.data.audit import init_audit_schema

  # 既に init_schema() で作成した conn を渡す
  init_audit_schema(conn)
  ```

- 監査専用の DB を新規作成する場合
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

注意点：
- init_schema() は冪等（既存のテーブルがあればスキップ）です。
- init_schema() は DB ファイルの親ディレクトリが存在しない場合に自動で作成します。
- 監査スキーマは `SET TimeZone='UTC'` を実行して UTC 保存を保証します。

---

## 環境変数自動読み込みの詳細

- 読み込み対象ファイル（優先度の低い順）:
  1. `.env`（プロジェクトルート）
  2. `.env.local`（同、上書き）
- OS 環境変数は保護され、上書きされません（`.env.local` が override=True でも、既に OS 環境変数にあるキーは書き換えない）。
- 自動読み込みを無効にしたい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- プロジェクトルートは、`__file__` の親ディレクトリ群に `.git` または `pyproject.toml` が見つかった場所で検出します。見つからない場合は自動読み込み自体をスキップします。

---

## ディレクトリ構成

（コードベースの主要ファイル・モジュール構成）

- src/
  - kabusys/
    - __init__.py
    - config.py               # 環境設定管理（Settings）
    - data/
      - __init__.py
      - schema.py             # DuckDB スキーマ定義・init_schema / get_connection
      - audit.py              # 監査ログスキーマ（signal_events, order_requests, executions）
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（注）上記は現時点での主要モジュール。strategy、execution、monitoring はパッケージ化済みで、将来的な戦略ロジック・実行エンジン・監視機能の格納場所です。

---

## 備考 / 実運用上の注意

- audit（監査）テーブルは削除しない前提で設計されています（FK は ON DELETE RESTRICT）。監査証跡を維持してください。
- order_requests の `order_request_id` は冪等キーとして機能します。再送による二重発注を防ぐため、クライアントは同一の冪等キーを再利用してください。
- 監査スキーマはタイムゾーンを UTC に固定して記録します。アプリケーション側での日時取り扱いに注意してください。
- KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれかのみ有効です。

---

必要であれば、README に以下を追加できます：
- .env.example ファイルテンプレート
- よくあるエラーと対処
- CI / デプロイ方法
- サンプル戦略実装のテンプレート

ご希望があれば追記します。