# KabuSys

日本株向け自動売買システムのライブラリ（開発中）

バージョン: 0.1.0

概要:
- 市場データ取得・整形、特徴量作成、シグナル生成、発注・約定の監査ログ管理までを想定した内部ライブラリ群を含みます。
- 永続化には DuckDB（ローカルファイルまたはインメモリ）を使用します。
- 環境変数／.env による設定管理、監査ログのための専用スキーマなどを提供します。

主な機能
- 環境設定読み込み（.env / .env.local / OS 環境変数）
  - 自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
  - 設定は `kabusys.config.settings` 経由で参照できます。
  - 主要な必須設定例:
    - JQUANTS_REFRESH_TOKEN
    - KABU_API_PASSWORD
    - SLACK_BOT_TOKEN
    - SLACK_CHANNEL_ID
  - システム設定:
    - KABUSYS_ENV: development / paper_trading / live
    - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
- DuckDB 用スキーマ定義・初期化（data.schema）
  - Raw / Processed / Feature / Execution 層を含むテーブル群を DDL として定義
  - インデックス定義、依存関係を考慮したテーブル作成順で冪等に初期化
  - 関数:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - DuckDB ファイルの親ディレクトリを自動作成し、全テーブル・インデックスを作成して接続を返す
      - ":memory:" を指定してインメモリ DB を利用可能
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB へ接続（スキーマ初期化は行わない）
- 監査ログ（data.audit）
  - シグナル→発注要求→約定 のトレーサビリティを保証する監査テーブル群
  - すべての TIMESTAMP を UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）
  - 関数:
    - init_audit_schema(conn: duckdb.DuckDBPyConnection) -> None
      - 既存接続に監査テーブルを追加（冪等）
    - init_audit_db(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 監査ログ専用の DuckDB を作成して接続を返す

セットアップ手順（開発環境向け）
1. Python 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必須: duckdb
   - 例:
     pip install duckdb

   （プロジェクトがパッケージ化されている場合）
   - editable インストール:
     pip install -e .

3. 設定ファイル（.env）を準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` として必要なキーを置きます。
   - 例 (簡易):
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   - .env.local がある場合は .env の値を上書きします（ただし OS 環境変数は保護されます）。
   - 自動ロードをテスト等で無効にするには:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（基本例）

- 設定値を取得する:
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path  # Path オブジェクト

- DuckDB スキーマ初期化（ファイル DB を作成してテーブルを作る）:
  from kabusys.data.schema import init_schema
  conn = init_schema(settings.duckdb_path)
  # conn は duckdb の接続オブジェクト

- 既存 DB に接続する（スキーマは作成しない）:
  from kabusys.data.schema import get_connection
  conn = get_connection(settings.duckdb_path)

- 監査ログスキーマを既存接続に追加する:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  # もしくは専用 DB を作る:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

注意点
- init_schema / init_audit_db は親ディレクトリが存在しない場合に自動作成します。
- init_audit_schema は UTC タイムゾーンを設定します。監査ログは UTC で保存されます。
- config の必須キーが欠如していると Settings のプロパティで ValueError を送出します。
- settings.env の値は (development, paper_trading, live) のいずれかでなければなりません。
- LOG_LEVEL は (DEBUG, INFO, WARNING, ERROR, CRITICAL) のいずれかでなければなりません。

ディレクトリ構成
- src/
  - kabusys/
    - __init__.py                # パッケージメタ（__version__ = "0.1.0"）
    - config.py                  # 環境変数 / .env 読み込み・Settings クラス
    - data/
      - __init__.py
      - schema.py                # DuckDB スキーマ定義・初期化 (init_schema, get_connection)
      - audit.py                 # 監査ログスキーマ (init_audit_schema, init_audit_db)
      - audit.py                 # 監査用のテーブル定義
      - audit.py                 # （重複記載はなく、このファイルに監査DDLがある）
      - audit.py                 # （上記は実装上の説明。実際は1ファイル）
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
      - audit.py
    - strategy/
      - __init__.py               # 戦略関連パッケージ（未実装のプレースホルダ）
    - execution/
      - __init__.py               # 発注・実行関連パッケージ（未実装のプレースホルダ）
    - monitoring/
      - __init__.py               # モニタリング関連（未実装のプレースホルダ）

（注）上記ツリーはこのコードベースに含まれる主要ファイルを抜粋しています。

開発・拡張のヒント
- 新しいデータテーブルを追加する場合は data/schema.py に DDL を追加し、_ALL_DDL リストに順序を考慮して挿入してください。
- 監査テーブルを拡張する場合は data/audit.py に DDL とインデックスを追加し、init_audit_schema で作成されるようにしてください。
- .env パーサはクォートやエスケープ、行内コメントに対応しています。細かい仕様に合わせて .env を記述してください。

ライセンス / 貢献
- （ここにプロジェクトのライセンス情報や貢献ルールを記載してください）

お問い合わせ
- （リポジトリ内の issue や開発連絡先をここに記載してください）

以上。README の内容は必要に応じてプロジェクト固有の手順（パッケージング、CI、依存関係）に合わせて追記してください。