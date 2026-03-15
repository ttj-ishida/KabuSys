# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買システム向けライブラリです。市場データの取り込み〜特徴量生成〜シグナル生成〜発注・約定・ポジション管理、さらに監査ログまでを想定したデータレイヤー・インフラを提供します。

主な用途は内部ライブラリとして戦略開発・バックテスト・本番運用で共通に使える「データスキーマ」「環境設定」「監査ログ基盤」の提供です。

---

## 機能一覧

- 環境変数管理
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み
  - export 形式、クォート・エスケープ、コメントに対応
  - 自動読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応
- 設定オブジェクト
  - settings オブジェクトから J-Quants / kabu API / Slack / DB パスなどを取得
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証
- DuckDB ベースのスキーマ初期化
  - Raw / Processed / Feature / Execution の多層スキーマ定義
  - インデックス定義、外部キーを考慮したテーブル作成順序（冪等）
  - init_schema() / get_connection() API
- 監査ログ（Audit）
  - シグナル→発注要求→約定の追跡が可能な監査テーブル群
  - 冪等キー（order_request_id / broker_execution_id）設計
  - UTC タイムゾーン保存ポリシー、ステータス管理
  - init_audit_schema() / init_audit_db() API

---

## セットアップ手順

前提: Python 3.8+（型注釈の記載から 3.9+ を想定しますが、互換性はご自身で確認してください）

1. リポジトリをクローンする
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - 必要なパッケージ例: duckdb
   ```bash
   pip install -U pip
   pip install duckdb
   # パッケージを開発インストールする場合
   pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を作成してください。自動読み込みはパッケージインポート時に行われます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルトがあるもの）
     - KABUSYS_ENV (default: development) — 値: development / paper_trading / live
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - LOG_LEVEL (default: INFO)

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN="xxx"
   KABU_API_PASSWORD="yyy"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C0123456789"
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方

以下は代表的な API の使い方例です。

- 設定値の参照
  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)  # 環境変数が未設定だと ValueError が発生
  print(settings.kabu_api_base_url)      # デフォルト値を返すことがある
  print(settings.is_live, settings.env)
  ```

- DuckDB スキーマの初期化（メイン DB）
  ```python
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)
  # conn は duckdb.DuckDBPyConnection
  ```

- 既存 DB への接続（スキーマ初期化は行わない）
  ```python
  conn = schema.get_connection("data/kabusys.duckdb")
  ```

- 監査ログ（Audit）テーブルの初期化（既存接続に追加）
  ```python
  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn)  # conn は init_schema で取得した接続など
  ```

- 監査ログ専用 DB を作る
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

注意点:
- init_schema / init_audit_db は冪等です。既存テーブルがあればスキップされます。
- init_audit_schema は UTC で TIMESTAMP を保存するように "SET TimeZone='UTC'" を実行します。

---

## ディレクトリ構成

主要ファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py                # パッケージのメタ情報（バージョン等）
    - config.py                  # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py                # DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
      - audit.py                 # 監査ログテーブル定義・初期化
      - audit.py
      - audit.py
      - audit.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py

（実際のリポジトリにはさらにモジュールや実装が追加される想定です）

---

## 実装上の注意 / 補足

- .env 自動読み込み
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml）から `.env` と `.env.local` を順に読み込みます。OS 環境変数が優先され、`.env.local` は上書きモードで読み込まれます。
  - テスト等で自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - .env のパースはシェル風の export 表記、クォートとバックスラッシュエスケープ、コメント処理（クォートあり/なしの扱い差）をサポートします。

- スキーマ設計
  - Raw → Processed → Feature → Execution の多層設計により、ETL と監査を明確に分離しています。
  - 監査モデルはシグナルからブローカー約定までの完全なトレーサビリティを意識した設計です（冪等キーやステータス管理を含む）。

---

必要であれば README に以下を追加できます:
- 開発フロー・テストの実行方法
- CI / CD の設定例
- 詳細なデータモデル図（DataSchema.md / DataPlatform.md 参照）
- サンプル戦略のテンプレート

追加したい内容があれば教えてください。