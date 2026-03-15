# KabuSys

日本株向け自動売買プラットフォーム（モジュール基盤）

バージョン: 0.1.0

このリポジトリは、データ取得・整形（Data）、特徴量生成（Feature）、戦略（Strategy）、発注/約定（Execution）、監視（Monitoring）を想定した日本株用自動売買システムの骨組みを提供します。DuckDB を用いたローカルデータ管理と監査ログ（トレーサビリティ）機能を備えています。

主なモジュール
- kabusys.config: 環境変数 / 設定管理（.env 自動読み込み、要設定項目の取得）
- kabusys.data: DuckDB のスキーマ定義・初期化（data.schema, data.audit）
- kabusys.strategy: 戦略層（雛形）
- kabusys.execution: 発注・約定処理（雛形）
- kabusys.monitoring: 監視・メトリクス（雛形）

---

## 機能一覧

- 環境設定の自動読み込み
  - プロジェクトルートに存在する `.env` / `.env.local` を自動で読み込む（優先度: OS環境変数 > .env.local > .env）
  - 自動読み込みを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - .env の解析はクォート・エスケープ・コメントを考慮した独自実装

- 設定オブジェクト（Settings）
  - 必須トークンやパスをプロパティ経由で取得（例: `settings.jquants_refresh_token`）
  - 環境（development / paper_trading / live）やログレベルの検証を行う

- DuckDB ベースのスキーマ定義（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル群を定義
  - 主要クエリを想定したインデックスを作成
  - 初期化は冪等（既存テーブルがあればスキップ）

- 監査（audit）テーブル（data.audit）
  - シグナル→発注要求→約定に至るトレーサビリティをUUIDチェーンで保証
  - 発注要求は冪等キー（order_request_id）を持ち、実運用での二重発注防止を想定
  - 監査用テーブルはタイムゾーンを UTC に固定して保存

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に `X | Y` 形式を使用しているため）
- pip が使用可能

1. レポジトリをチェックアウトして作業ディレクトリへ移動

2. 依存ライブラリをインストール
   - 最低限必要なのは DuckDB
   - 例:
     ```
     pip install duckdb
     ```
   - 開発中にパッケージとしてインストールする場合（プロジェクトに pyproject.toml/setup がある場合）:
     ```
     pip install -e .
     ```

3. 環境変数（.env）を作成
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）が自動検出され、その下の `.env` と `.env.local` が読み込まれます。
   - 必須項目（実行時に Settings のプロパティを呼ぶと ValueError が出る）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルトがある設定:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO

   - 簡単な .env 例:
     ```
     JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
     KABU_API_PASSWORD="your_kabu_api_password"
     SLACK_BOT_TOKEN="xoxb-..."
     SLACK_CHANNEL_ID="C01234567"
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. 自動 .env 読み込みを無効化したい場合
   - テスト等で自動読み込みを無効にする:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（サンプル）

- 設定へアクセス:
  ```python
  from kabusys.config import settings

  print(settings.env)  # development / paper_trading / live
  token = settings.jquants_refresh_token
  ```

- DuckDB スキーマを初期化（ファイル DB またはインメモリ）:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  # デフォルトパスを使用
  conn = init_schema(settings.duckdb_path)

  # インメモリ DB を使う場合
  conn = init_schema(":memory:")

  # 作成後、テーブル一覧を確認
  print(conn.execute("SHOW TABLES").fetchall())
  ```

- 監査ログ（audit）テーブルを既存コネクションに追加:
  ```python
  from kabusys.data.audit import init_audit_schema
  # conn は init_schema で得た duckdb connection
  init_audit_schema(conn)

  # または専用ファイルで監査DBを作る
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- .env 自動読み込みの挙動
  - 実行時に OS 環境変数が最優先で採用されます。
  - 次に `.env.local`、最後に `.env`。`.env.local` は `.env` を上書きできます。
  - OS 環境にあるキーは上書きされません（保護されます）。
  - 自動読み込みを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

注意点
- 監査 DB 初期化時（init_audit_schema）は明示的に TimeZone を UTC に設定します（すべての TIMESTAMP は UTC で保存）。
- Settings の `env` は "development", "paper_trading", "live" のいずれかでなければ例外が投げられます。
- Settings の `log_level` は大文字で指定する必要があります（例: INFO）。

---

## ディレクトリ構成

リポジトリの主要ファイル/ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py               (パッケージ定義、バージョン)
    - config.py                 (環境変数・設定管理、自動 .env 読み込み)
    - data/
      - __init__.py
      - schema.py               (DuckDB スキーマ定義・初期化: Raw/Processed/Feature/Execution)
      - audit.py                (監査ログ用スキーマ・初期化)
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
    - strategy/
      - __init__.py             (戦略モジュールのエントリ)
    - execution/
      - __init__.py             (発注/約定モジュールのエントリ)
    - monitoring/
      - __init__.py             (監視モジュールのエントリ)

（注）上記は主要ファイルの抜粋です。実装が不足しているモジュール（strategy, execution, monitoring）は拡張のためのプレースホルダとして用意されています。

---

## 設計上の重要ポイント / 補足

- データ層は Raw → Processed → Feature → Execution の4層で設計されています。SQL スキーマは各層を分離して整合性を保つように定義されています。
- 監査ログ（audit）は、ビジネス的なトレーサビリティを重視したスキーマ設計になっており、発生した全イベントを削除せずに保存する前提です（FK は ON DELETE RESTRICT 等）。
- .env パーサーはシェル風の書式（export キーワード、クォート、エスケープ、コメント）に対して柔軟に対応します。

---

必要であれば、以下を追加で用意できます:
- 開発用の requirements.txt / pyproject.toml サンプル
- CI 用の DB 初期化スクリプト
- strategy / execution のサンプル実装（例: シンプルなモメンタム戦略、ペーパー取引用の注文シミュレーター）

ご希望があれば README を拡張します。