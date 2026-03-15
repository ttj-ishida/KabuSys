# KabuSys

KabuSys は日本株向けの自動売買基盤（ライブラリ）です。データ収集・加工、特徴量生成、戦略、発注・監査ログなどを想定したモジュール群を含み、DuckDB を使ったデータストレージスキーマの初期化や環境設定管理を提供します。

バージョン: 0.1.0

---

## 主な特徴

- 環境変数 / .env ベースの設定管理（自動ロード機能付き）
- DuckDB ベースの多層データスキーマ（Raw / Processed / Feature / Execution）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を別モジュールで初期化
- 発注・実行・監視用の基本的なテーブル定義（signals, orders, trades, positions 等）
- 開発 / ペーパー取引 / ライブ切替を環境変数で制御

---

## 機能一覧

- 設定管理（kabusys.config.Settings）
  - 必須環境変数の取得（例: JQUANTS_REFRESH_TOKEN 等）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - KABUSYS_ENV / LOG_LEVEL / DB パスの取得
- データスキーマ（kabusys.data.schema）
  - init_schema(db_path) : DuckDB データベース初期化（テーブル・インデックス作成）
  - get_connection(db_path) : 既存 DB への接続取得
  - 主要テーブル: raw_prices, prices_daily, features, ai_scores, signals, orders, trades, positions, portfolio_performance 等
- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn) : 既存接続に監査テーブル（signal_events, order_requests, executions）を追加
  - init_audit_db(db_path) : 監査専用 DB を初期化して接続を返す
- パッケージ構造の骨組み（strategy, execution, monitoring）を想定（拡張可能）

---

## セットアップ手順

前提: Python 3.9+（typing 演算に Path | None などを利用）。依存パッケージとして duckdb が必要です。

1. リポジトリを取得（例）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - 最低限 duckdb が必要です:
     ```
     pip install duckdb
     ```
   - 開発時はプロジェクトの requirements / pyproject に従ってください（本リポジトリに依存定義がある場合）。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に自動で `.env` と `.env.local` を読み込みます。
   - 自動ロードを無効にするには環境変数を設定してください:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意/既定値
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi

   - .env の例（簡易）
     ```
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```

---

## 使い方（簡単なサンプル）

- Settings の利用例
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  print("env:", settings.env)
  print("is_live:", settings.is_live)
  ```

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.config import settings

  # 設定からパスを取得して初期化（親ディレクトリがなければ自動作成される）
  conn = init_schema(settings.duckdb_path)

  # またはインメモリ DB
  conn_mem = init_schema(":memory:")
  ```

- 監査ログの初期化（既存接続に追加する）
  ```python
  from kabusys.data.audit import init_audit_schema

  # 上で取得した conn に監査テーブルを追加
  init_audit_schema(conn)
  ```

- 監査専用 DB を作成する場合
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- 注意点
  - init_schema / init_audit_schema は冪等（既にテーブルがあればスキップ）です。
  - init_audit_schema はタイムゾーンを UTC にセットしてからテーブルを作成します（TIMESTAMP は UTC 想定）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py            - パッケージ初期化、バージョン定義（0.1.0）
  - config.py              - 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - schema.py            - DuckDB スキーマ定義と初期化 API（init_schema, get_connection）
    - audit.py             - 監査ログスキーマ／初期化（init_audit_schema, init_audit_db）
    - audit.py に定義された主なテーブル:
      - signal_events, order_requests, executions
  - strategy/
    - __init__.py          - 戦略層用のプレースホルダ（拡張ポイント）
  - execution/
    - __init__.py          - 発注実行層用のプレースホルダ（拡張ポイント）
  - monitoring/
    - __init__.py          - 監視・モニタリング層のプレースホルダ

---

## 実装上の注意 / 補足

- .env パーサーはシェル風のクォートやコメントを一定程度扱います（export プレフィックス対応、クォート内のエスケープ処理、コメント処理など）。
- 自動で `.env` / `.env.local` を読み込む際、既に OS 環境にあるキーは保護されます（.env は上書きされない。`.env.local` は override 可能だが OS 環境は保護）。
- データベースの親ディレクトリが存在しない場合は自動作成します。
- 監査ログは削除を前提としない設計（FK に ON DELETE RESTRICT を採用）で、冪等キーによる二重発注防止などを考慮しています。

---

## 今後の拡張ポイント（例）

- strategy/ に具体的な戦略の実装（特徴量→シグナル生成）
- execution/ にブローカー接続（kabuステーション API 連携）の具体実装
- monitoring/ にメトリクス／Slack 通知等の実装
- テスト用ユーティリティと CI セットアップ

---

必要に応じて README を拡張します（依存一覧、開発ルール、コードスタイル、例示的な .env.example の完全版など）。追加したい項目があれば教えてください。