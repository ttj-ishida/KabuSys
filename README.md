# KabuSys

日本株向け自動売買（バックテスト／運用）システムの骨組みを提供する Python パッケージです。  
データレイヤ（DuckDB スキーマ）、環境設定、監査ログ（発注から約定までのトレーサビリティ）などの基盤機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたライブラリ／フレームワークです。  
主に以下を提供します。

- DuckDB ベースのデータスキーマ（Raw / Processed / Feature / Execution 層）
- 発注〜約定〜ポジションまでの監査ログ（トレーサビリティ）
- 環境変数による設定管理（.env / .env.local の自動読み込み）
- Slack / J-Quants / kabuステーション API 用の設定取得インターフェース

現時点では各戦略や実行ロジックはスケルトンとして用意されており、拡張して使用します。

---

## 機能一覧

- DuckDB で利用する包括的なスキーマ定義と初期化
  - Raw 層: raw_prices, raw_financials, raw_news, raw_executions 等
  - Processed 層: prices_daily, fundamentals, news_articles 等
  - Feature 層: features, ai_scores 等
  - Execution 層: signals, signal_queue, orders, trades, positions, portfolio_performance 等
- 監査ログ（audit）モジュール
  - signal_events, order_requests, executions を定義
  - order_request_id を冪等キーとした発注追跡
  - すべてのタイムスタンプを UTC で保存する設計
- 環境設定管理（kabusys.config）
  - .env / .env.local を自動読み込み（プロジェクトルートは .git / pyproject.toml を探索）
  - 必須設定はプロパティ経由で取得すると未設定時に明示的にエラーを発生
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能
- インデックスの自動作成（頻出クエリに基づく最適化）

---

## セットアップ手順

前提:
- Python 3.10 以上（Path | None 等の記法を使用）
- pip が利用可能

1. リポジトリをクローン／配置
2. 依存パッケージをインストール（最低限 duckdb が必要）
   ```
   pip install duckdb
   ```
   （プロジェクトで他に必要なパッケージがあれば requirements.txt / pyproject.toml を参照して追加）

3. 環境変数の準備
   - プロジェクトルートに `.env`（必要なら `.env.local`）を作成します。
   - 自動読み込みはデフォルトで有効です。自動読み込みを無効にするには起動前に環境変数を設定します:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   例（.env の一例）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

   # kabu ステーション API
   KABU_API_PASSWORD=your_kabu_api_password
   # KABU_API_BASE_URL は省略時に http://localhost:18080/kabusapi が使われます

   # Slack
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678

   # DB（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境・ログ
   KABUSYS_ENV=development  # development / paper_trading / live
   LOG_LEVEL=INFO
   ```

4. データベーススキーマの初期化
   - Python スクリプトあるいは REPL で DuckDB スキーマを作成します（次節の使い方参照）。

---

## 使い方（簡易ガイド）

環境設定の読み取り、DuckDB スキーマの初期化、監査スキーマの初期化などの基本的な利用例を示します。

- 設定値（settings）を取得する:
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token  # 未設定なら ValueError を送出
  base_url = settings.kabu_api_base_url   # デフォルト: http://localhost:18080/kabusapi
  print(settings.env, settings.is_live, settings.log_level)
  ```

- DuckDB スキーマを初期化する:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  # settings.duckdb_path はデフォルト "data/kabusys.duckdb"
  conn = init_schema(settings.duckdb_path)
  # 以降 conn を使ってクエリ実行やトランザクションが可能
  ```

- 監査ログ（audit）テーブルを既存接続に追加する:
  ```python
  from kabusys.data.audit import init_audit_schema
  # conn は init_schema の戻り値など
  init_audit_schema(conn)
  ```

- 監査ログ専用 DB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/kabusys_audit.duckdb")
  ```

- DuckDB に接続するだけ（スキーマ初期化は行わない）:
  ```python
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  ```

- .env 読み込み動作について
  - パッケージインポート時にプロジェクトルート（.git または pyproject.toml）を探索し、`.env` と `.env.local`（後者は上書き）を自動で読み込みます。
  - 自動読み込みを抑止するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — 有効値: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — 有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

設定が不足している必須キーにアクセスすると ValueError が発生します。

---

## ディレクトリ構成

リポジトリ（src レイアウト）内の主なファイル・モジュール:

- src/kabusys/
  - __init__.py
    - __version__ = "0.1.0"
    - __all__ = ["data", "strategy", "execution", "monitoring"]
  - config.py
    - 環境変数読み込み・Settings クラス
  - data/
    - __init__.py
    - schema.py
      - DuckDB のテーブル定義と init_schema / get_connection
      - 層: Raw / Processed / Feature / Execution
    - audit.py
      - 監査用テーブル定義（signal_events, order_requests, executions）
      - init_audit_schema / init_audit_db
    - audit 用のインデックス定義あり
  - strategy/
    - __init__.py（戦略関連の拡張ポイント）
  - execution/
    - __init__.py（発注実行関連の拡張ポイント）
  - monitoring/
    - __init__.py（監視・メトリクス関連の拡張ポイント）

---

補足・設計意図
- DuckDB スキーマは冪等（CREATE TABLE IF NOT EXISTS）で定義されており、何度でも初期化可能です。
- 監査ログ側は発注の冪等性（order_request_id）やトレーサビリティを重視して設計しています。
- 全ての TIMESTAMP は UTC 保存を前提にしており、init_audit_schema では接続に対して SET TimeZone='UTC' を行います。
- このリポジトリはフレームワークのコア（データ層・設定・監査）を提供します。戦略やブローカー連携（発注実装）はプロジェクトに合わせて実装してください。

---

貢献・ライセンス等はリポジトリに合わせて追記してください。