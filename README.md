# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）  
本リポジトリは、データレイヤ（Raw / Processed / Feature）、発注・約定・ポジション管理、監査ログ（トレーサビリティ）を想定したスキーマ定義と環境設定ユーティリティを提供します。

## 概要
- DuckDB を用いたオンディスク／インメモリのデータベース初期化機能を提供します。
- データは 3 層（Raw / Processed / Feature）＋Execution（発注〜約定）で管理されるスキーマを含みます。
- 発注フローのトレーサビリティを担保する監査ログスキーマ（UUID 連鎖）を提供します。
- 環境変数の読み込み・管理（.env 読み込み、必須キーチェック等）ユーティリティを提供します。

バージョン: 0.1.0

## 主な機能一覧
- 環境設定管理（kabusys.config.Settings）
  - .env / .env.local の自動読み込み（優先度: OS 環境変数 > .env.local > .env）
  - 必須環境変数の取得（未設定時は例外発行）
  - 環境（development / paper_trading / live）、ログレベル判定ユーティリティ
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）
  - .env の柔軟なパース（export プレフィックス、クォート、コメント扱い など）
- データベーススキーマ初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 各レイヤーのテーブル定義
  - インデックス定義（頻出クエリ向け）
  - init_schema(db_path) → DuckDB 接続を返す（:memory: に対応）
  - get_connection(db_path) → 既存 DB へ接続（スキーマ作成は行わない）
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions 等の監査テーブル
  - init_audit_schema(conn) で既存接続へ監査テーブルを追加
  - init_audit_db(db_path) で監査専用 DB を初期化
  - すべての TIMESTAMP は UTC で保存（初期化時に TimeZone を UTC に設定）
- パッケージ構成（strategy / execution / monitoring 用のプレースホルダモジュール）

## 必要な環境変数（主なもの）
下記は Settings クラスが参照する主な環境変数です（必須は README 内で明記）。

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルト値あり）:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
- KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db

自動 .env 読み込み制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、自動で .env/.env.local を読み込む仕組みを無効化できます。

.env の読み込みルール（概要）:
- 検出順: OS 環境変数 > .env.local > .env
- 行は `KEY=VALUE`、`export KEY=VALUE` を許可
- 値はシングル/ダブルクォートで囲める（エスケープ対応）
- クォートなしの値では `#` の直前が空白タブの場合にコメントとみなす

## セットアップ手順

1. Python 環境を用意（推奨: 3.8+）
2. 依存ライブラリをインストール
   - 本リポジトリで明示しているライブラリ: duckdb
   - 例:
     ```
     pip install duckdb
     ```
   - （パッケージとして配布する場合は pyproject.toml / setup.cfg に依存を追加してください）

3. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成するか、OS 環境変数を設定します。
   - 簡易例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
     KABU_API_PASSWORD="your_kabu_password"
     SLACK_BOT_TOKEN="xoxb-xxx"
     SLACK_CHANNEL_ID="C0123456789"
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. データベーススキーマを初期化（後述の使い方参照）

## 使い方（例）

- 環境設定の取得例
  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)  # 必須: 未設定なら ValueError
  print(settings.duckdb_path)            # デフォルト: data/kabusys.duckdb
  print(settings.is_live)                # KABUSYS_ENV == "live" の場合 True
  ```

- DuckDB スキーマ初期化（メイン DB）
  ```python
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # conn は duckdb の接続オブジェクト（duckdb.DuckDBPyConnection）
  ```

- 監査ログスキーマを既存接続へ追加
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.audit import init_audit_schema

  conn = init_schema(":memory:")   # またはファイルパス
  init_audit_schema(conn)
  ```

- 監査専用 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  ```

- 既存 DB に接続（スキーマ作成を行わない）
  ```python
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  ```

- 自動 .env 読み込みを無効化してテスト実行したい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  python -c "from kabusys.config import settings; print('disabled')"
  ```

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                   # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py                 # DuckDB スキーマ定義・初期化
      - audit.py                  # 監査ログ（トレーサビリティ）テーブル
      - audit.py
      - audit.py
    - strategy/
      - __init__.py               # 戦略関連プレースホルダ
    - execution/
      - __init__.py               # 発注・実行関連プレースホルダ
    - monitoring/
      - __init__.py               # 監視関連プレースホルダ

（実際のコードベースは上記ファイルに更に実装を追加していく想定です）

## 実装上の留意点 / 補足
- DuckDB のテーブル・インデックスは初期化時に作成され、冪等（存在する場合はスキップ）です。
- 監査ログは削除しない前提（FK は ON DELETE RESTRICT）で設計されています。
- すべての監査系 TIMESTAMP は UTC で保存されます（init_audit_schema で TimeZone をセット）。
- .env のパースは実運用で見かけるフォーマット（export プレフィックス、クォート、エスケープ、コメント）に配慮していますが、特殊なケースでは注意してください。

---

問題や要望があれば README の改善／サンプルコードの追加など対応します。