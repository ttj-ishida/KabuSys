# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買基盤ライブラリです。市場データの格納・加工、特徴量生成、発注・約定管理のためのスキーマや設定管理を提供します。本リポジトリはコアのデータスキーマ定義と環境設定周りのユーティリティを含みます。

## 概要

- DuckDB を用いた3層構造（Raw / Processed / Feature）＋発注管理のデータスキーマを提供します。
- 環境変数・.env ファイルの自動読み込みと型安全な設定取得インターフェースを備えています。
- 発注・実行・監視、戦略モジュールのプレースホルダ（パッケージ構成）を定義しています。

この README はライブラリの使い方、セットアップ手順、ディレクトリ構成を示します。

## 主な機能一覧

- 環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に検出）
  - 環境変数必須チェック（例: JQUANTS_REFRESH_TOKEN など）
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- データスキーマ管理（kabusys.data.schema）
  - DuckDB 用のDDLを定義（Raw, Processed, Feature, Execution 層）
  - テーブル作成およびインデックス作成（冪等）
  - DB 初期化関数: init_schema(db_path)
  - 既存DB接続取得: get_connection(db_path)

- パッケージ骨組み（kabusys.strategy, kabusys.execution, kabusys.monitoring）
  - 将来的な戦略/実行/監視ロジックの拡張ポイント

## 必要条件

- Python 3.10 以上（型ヒントに `A | B` 形式を使用しているため）
- pip
- 依存パッケージ（最低限）
  - duckdb

インストール例:
```
python -m pip install duckdb
```

（プロジェクトで requirements.txt / pyproject.toml があればそちらを参照してください）

## セットアップ手順

1. リポジトリをクローン / ソースを取得
2. Python（3.10+）環境を用意し、依存パッケージをインストール
   ```
   python -m pip install --upgrade pip
   python -m pip install duckdb
   ```
3. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（ただし OS 環境変数が優先されます）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。
   - 必須環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション / デフォルト値:
     - KABUSYS_ENV (default: development) — 有効値: development / paper_trading / live
     - LOG_LEVEL (default: INFO) — 有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
   - .env の例（プロジェクトルート/.env）:
     ```
     JQUANTS_REFRESH_TOKEN="your_refresh_token"
     KABU_API_PASSWORD="your_kabu_pass"
     SLACK_BOT_TOKEN="xoxb-..."
     SLACK_CHANNEL_ID="C01234567"
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. データベーススキーマの初期化
   - DuckDB ファイルを指定してスキーマを作成します。親ディレクトリがなければ自動作成されます。

   例:
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```

## 使い方

- 設定の使用例
  ```python
  from kabusys.config import settings

  # 必須トークン取得（未設定だと ValueError を送出）
  token = settings.jquants_refresh_token

  # 実行環境確認
  if settings.is_live:
      print("ライブモードです")
  ```

- DB 初期化（再掲）
  ```python
  from kabusys.data.schema import init_schema, get_connection

  conn = init_schema("data/kabusys.duckdb")
  # または既存DBへ接続（スキーマ初期化はしない）
  conn2 = get_connection("data/kabusys.duckdb")
  ```

- .env 読み込みの振る舞い（ポイント）
  - 起動時にプロジェクトルート（.git または pyproject.toml のある階層）を探し、見つかれば `.env` → `.env.local` の順で読み込みます。
  - `.env.local` は `.env` の上書きに使えますが、OS 環境変数は保護されます（OS 環境変数は上書きされません）。
  - `export KEY=value` 形式やシングル/ダブルクォート、エスケープシーケンス、行末のコメントを考慮したパーサを使用しています。

## ディレクトリ構成

リポジトリの主要ファイルを整理すると以下のようになります（抜粋）:

- src/
  - kabusys/
    - __init__.py                 # パッケージ情報（__version__ 等）
    - config.py                   # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py                 # DuckDB スキーマ定義・初期化 API (init_schema, get_connection)
    - strategy/
      - __init__.py               # 戦略モジュール用プレースホルダ
    - execution/
      - __init__.py               # 発注・実行モジュール用プレースホルダ
    - monitoring/
      - __init__.py               # 監視（Slack 等）モジュール用プレースホルダ

主要コンポーネント説明:
- kabusys/config.py: .env ロード、設定取得用プロパティ（settings インスタンス）を提供。
- kabusys/data/schema.py: 全テーブル・インデックスの DDL を保持し、init_schema() により必要テーブルを作成します。:memory: を指定すればインメモリ DuckDB を利用可能。

## 開発メモ / 注意点

- Python バージョンは 3.10 以上を推奨します（構文要件）。
- .env 自動ロードはプロジェクトルートの検出に依存するため、開発中は .git または pyproject.toml がルートにあることを確認してください。CI やテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して挙動を制御できます。
- init_schema() は冪等（既に存在するテーブルは再作成しません）。初回のみ呼び出してください。
- 現状このリポジトリはコアスキーマと設定管理を提供する段階です。戦略ロジックや実際の API 通信・発注ロジックは将来的に拡張してください。

---

不明点や追加で欲しいサンプル（たとえば戦略実行フローやサンプル .env.example など）があればお知らせください。必要に応じて README にコード例や図を追加します。