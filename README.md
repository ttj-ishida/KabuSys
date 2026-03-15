# KabuSys

日本株向け自動売買システムの基盤ライブラリ（KabuSys）。データレイヤ（Raw / Processed / Feature / Execution）、監査ログ、環境設定管理など自動売買に必要なインフラ機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は自動売買システムの「土台」を提供するライブラリです。主な責務は以下の通りです。

- 環境変数 / .env の柔軟な読み込みと管理
- DuckDB を用いたデータベーススキーマ（市場データ、特徴量、発注・約定・ポジション等）の定義と初期化
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマの定義と初期化
- 戦略・実行・監視のためのパッケージ分割（strategy / execution / monitoring は今後実装を想定）

設計上、データは多層（Raw / Processed / Feature / Execution / Audit）で整理され、冪等性・インデックス等を考慮したDDLが用意されています。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロード
  - export プレフィックス・クォート・コメントなど一般的な .env 構文に対応
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 設定アクセサ（settings）で必須値チェックや環境（development / paper_trading / live）判定を提供

- DuckDB スキーマ管理（data.schema）
  - Raw レイヤー（raw_prices / raw_financials / raw_news / raw_executions）
  - Processed レイヤー（prices_daily / market_calendar / fundamentals / news_articles / news_symbols）
  - Feature レイヤー（features / ai_scores）
  - Execution レイヤー（signals / signal_queue / portfolio_targets / orders / trades / positions / portfolio_performance）
  - テーブル作成の冪等性、頻出クエリに対するインデックス定義
  - init_schema(db_path) により DB の初期化と接続取得が可能（":memory:" もサポート）
  - get_connection(db_path) により既存 DB へ接続（初回は init_schema を推奨）

- 監査ログ（data.audit）
  - signal_events / order_requests / executions の監査用テーブル群
  - order_request_id を冪等キーとして二重発注防止を想定
  - 全 TIMESTAMP を UTC で保存（init_audit_schema は TimeZone を UTC に設定）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションに pipe 型を使用しているため）
- duckdb が必要

手順例:

1. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   - 必須: duckdb
   - その他はプロジェクトに合わせて追加してください。

   例:
   ```
   pip install duckdb
   ```

3. （開発時）パッケージを editable インストール（pyproject/セットアップがある前提）
   ```
   pip install -e .
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env` として下記キーを設定します（例を参照）。
   - 自動ロードは .git または pyproject.toml のあるディレクトリを起点に行われます。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   .env 例:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_api_password
   # (省略可能) KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789

   # DB パス（任意。デフォルトは data/kabusys.duckdb 等）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development     # development / paper_trading / live
   LOG_LEVEL=INFO
   ```

---

## 使い方

基本的な利用例を示します。

- 設定の参照
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  print(settings.kabu_api_base_url)
  print(settings.is_live)
  ```

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema, get_connection

  # ファイル DB を初期化して接続を取得（親ディレクトリを自動作成）
  conn = init_schema("data/kabusys.duckdb")

  # 既存 DB に接続（スキーマ初期化は行わない）
  conn2 = get_connection("data/kabusys.duckdb")
  ```

- 監査ログの初期化（既存接続へ追加）
  ```python
  from kabusys.data.audit import init_audit_schema

  # conn は init_schema() で作成した duckdb 接続
  init_audit_schema(conn)
  ```

- 監査ログ専用 DB を作る場合
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- 自動環境読み込みの無効化（テスト向け）
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

注意点:
- init_schema は冪等（既存テーブルがあればスキップ）なので安全に実行できます。
- init_audit_schema は接続に対して監査テーブルを追加します。UTC タイムゾーンで TIMESTAMP を保存するため、接続時に TimeZone='UTC' に設定します。

---

## ディレクトリ構成

現在のコードベースの主要ファイル・構成は以下のとおりです（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py  - 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py  - DuckDB スキーマ定義と初期化（init_schema / get_connection）
      - audit.py   - 監査ログ用スキーマ（init_audit_schema / init_audit_db）
      - (その他: audit/audit-related)
    - strategy/
      - __init__.py  - 戦略関連（将来的な実装用）
    - execution/
      - __init__.py  - 発注・約定関連（将来的な実装用）
    - monitoring/
      - __init__.py  - 監視関連（将来的な実装用）

---

## 追加の設計メモ（参考）

- データレイヤは Raw → Processed → Feature → Execution と分離されており、それぞれのテーブルに対してインデックスを作成しているため、大量データのスキャン性能を考慮しています。
- 監査ログは削除しない前提（ON DELETE RESTRICT）で設計され、order_request_id と broker_execution_id 等によるトレーサビリティを保証します。
- .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープシーケンス、コメント処理など一般的なシェル形式に寄せた実装になっています。

---

何か特定の機能（戦略の実装例、kabu API 連携、Slack 通知の統合など）についてドキュメントやサンプルコードが必要であれば教えてください。README を拡張してサンプルワークフローやよくある運用手順（ペーパートレード切替、監査ログの参照クエリ例など）を追加できます。