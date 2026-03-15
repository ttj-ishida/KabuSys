# KabuSys

バージョン: 0.1.0

日本株自動売買システム（ライブラリ）。市場データ取得〜特徴量生成〜シグナル生成〜発注・トレード記録までを想定したモジュール群を提供します。内部的に DuckDB を用いたローカルデータベーススキーマを提供し、環境変数ベースで各種 API トークンや接続先を管理します。

## 概要

- Python パッケージとして設計されており、モジュールは以下のサブパッケージを想定しています:
  - kabusys.data: データ取得／保存／スキーマ
  - kabusys.strategy: 戦略・シグナル生成
  - kabusys.execution: 発注ロジック・注文管理
  - kabusys.monitoring: 監視・通知（Slack 等）
- DuckDB を用いた永続化（デフォルト path: `data/kabusys.duckdb`）をサポート。インメモリモード（`:memory:`）も使用可能。
- 環境変数（.env ファイル）から設定を読み込み、Settings クラス経由でアクセス可能。

## 主な機能一覧

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（優先度: OS 環境変数 > .env.local > .env）
  - 自動読み込み無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - .git または `pyproject.toml` を基準にプロジェクトルートを特定
  - 複雑なクォート・コメントの取り扱いに対応した .env パーサ
- DuckDB スキーマ定義（冪等なテーブル作成）
  - Raw / Processed / Feature / Execution の層でテーブルを定義
  - 頻出クエリに対するインデックスも作成
  - 初期化 API: `init_schema(db_path)`、既存 DB 接続: `get_connection(db_path)`
- 設定プロパティ（例）
  - J-Quants / kabuステーション API トークン
  - Slack トークン・チャンネル ID
  - DB のパス（DuckDB / SQLite）
  - 実行環境フラグ（development / paper_trading / live）
  - ログレベルの検証

## 必要な環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり／条件付き）:
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL) — デフォルト: INFO
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（任意）

.env を用いる場合は `.env.example` を参考に作成してください（プロジェクトルートに配置）。

.env の自動読み込みについて:
- OS 環境変数が優先され、.env.local は .env を上書きします。
- プロジェクトルートが特定できない場合は自動読み込みをスキップします。
- クォートやエスケープ、インラインコメントの扱いを考慮したパーサを実装しています。

## セットアップ手順

1. Python 環境準備（推奨: 仮想環境）
   - python3.8+ を用意
   - venv 使用例:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```

2. 依存パッケージをインストール
   - プロジェクトに requirements.txt / pyproject.toml がある想定です。一般的には以下をインストールします:
     - duckdb
     - その他 API クライアント（J-Quants / kabu API / slack client 等）
   - 例:
     ```bash
     pip install duckdb
     # pip install -r requirements.txt
     # または pip install -e .
     ```

3. 環境変数を設定
   - 環境変数を直接設定するか、プロジェクトルートに `.env` / `.env.local` を作成します。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

4. データベーススキーマ初期化
   - DuckDB を初期化してテーブル・インデックスを作成します（初回のみ）。
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     # もしくはメモリ DB を試す場合:
     # conn = init_schema(":memory:")
     ```

## 使い方（基本例）

- 設定の参照:
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  base_url = settings.kabu_api_base_url
  is_live = settings.is_live
  ```

- DuckDB スキーマ初期化（再掲）:
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # テーブル作成・接続を返す
  # 既存 DB に接続（初期化は行わない）
  conn2 = get_connection(settings.duckdb_path)
  ```

- 自動読み込みを無効化してテストを行う場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

- サブパッケージ（概要）:
  - kabusys.data: schema 初期化やデータ保存、DuckDB 操作
  - kabusys.strategy: 戦略ロジック・特徴量利用
  - kabusys.execution: シグナル→注文処理、発注 API 連携
  - kabusys.monitoring: Slack 通知等の監視機能

（各サブパッケージの詳細実装はコードベースを参照してください）

## ディレクトリ構成

プロジェクトの主要ファイル / ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py                 # パッケージ定義、__version__ = "0.1.0"
    - config.py                   # 環境変数/設定管理
    - data/
      - __init__.py
      - schema.py                 # DuckDB スキーマ定義・初期化 API
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

その他トップレベル（想定）:
- .env, .env.local                # プロジェクトルートに配置（自動読み込み対象）
- pyproject.toml / setup.cfg      # パッケージ設定（存在すればプロジェクトルート判定に使用）
- data/                           # デフォルトの DB 保存先（例: data/kabusys.duckdb）

## 開発メモ / 注意点

- init_schema は冪等（既存テーブルは上書きしない）ため何度実行しても安全です。
- get_connection はスキーマ初期化を行わないので、初回は必ず init_schema を呼ぶことを推奨します。
- .env のパースはクォート・エスケープ・コメント処理に対応しています。特殊なフォーマットを使う場合は注意してください。
- KABUSYS_ENV は厳格に "development", "paper_trading", "live" のいずれかでなければエラーになります。
- LOG_LEVEL も事前定義された値のみ許容します。
- DuckDB のファイルパスに指定するディレクトリが存在しない場合、init_schema が親ディレクトリを自動作成します。

---

追加の利用例や、各サブパッケージ（strategy / execution / monitoring）の具体的な API ドキュメントが必要であれば、どの部分を優先して詳述するか教えてください。README に追記して整理します。