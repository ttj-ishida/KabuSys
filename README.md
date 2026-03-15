# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。本リポジトリはデータレイヤ（Raw / Processed / Feature / Execution）、監査ログ（トレーサビリティ）、環境設定管理、および発注/戦略/モニタリングのための基盤モジュール群を提供します。

---

## 概要

- DuckDB をデータストアとして用い、マーケットデータ・ファンダメンタル・ニュース・発注／約定・ポジション等を多層スキーマで永続化します。
- 監査ログ（signal → order_request → execution の追跡）を別途初期化可能で、完全なトレーサビリティを確保します。
- .env / 環境変数ベースで設定管理を行い、自動でプロジェクトルートから .env / .env.local を読み込みます（必要に応じて無効化可能）。
- 発注・戦略・モニタリング用の名前空間を備えており、戦略実装やブローカー連携の拡張ポイントを提供します。

---

## 主な機能一覧

- 環境変数／.env 自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- 設定ラッパー（settings）を経由した安全な環境変数アクセス（必須チェック付き）
- DuckDB スキーマ初期化（init_schema）:
  - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
  - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature Layer: features, ai_scores
  - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種インデックスを自動作成
- 監査ログ（audit）初期化:
  - signal_events, order_requests, executions テーブルおよび監査用インデックス
  - すべてのタイムスタンプは UTC で保存（init_audit_schema が SET TimeZone='UTC' を実行）
- DB 初期化は冪等（既存テーブルがあればスキップ）
- DuckDB の ":memory:" を利用したインメモリ DB 対応

---

## セットアップ手順

前提: Python 3.9+（コードは型ヒントに Union 型演算子を利用）、pip が利用可能であること。

1. リポジトリをクローン / 取得

2. 開発環境にパッケージをインストール（プロジェクトをパッケージ化している前提）
   - ローカル開発インストール（setup がある場合）:
     - pip install -e .
   - 必要な依存パッケージ（最小）:
     - duckdb
     - （Slack 等の連携を使う場合は対応ライブラリを追加）
   例:
   ```
   pip install duckdb
   ```

3. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（読み込み順: OS 環境変数 > .env.local > .env）。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
   KABU_API_PASSWORD="your_kabu_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡易ガイド）

基本的にはライブラリをインポートして関数を呼びます。以下に代表的な使い方を示します。

- 設定値の取得
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  is_live = settings.is_live
  db_path = settings.duckdb_path  # pathlib.Path
  ```

- DuckDB スキーマ初期化（全テーブル・インデックスを作成）
  ```python
  from kabusys.data import schema
  conn = schema.init_schema(settings.duckdb_path)  # ":memory:" でインメモリ
  # conn は duckdb.DuckDBPyConnection
  ```

- 既存 DB へ接続（スキーマを初期化しない）
  ```python
  conn = schema.get_connection(settings.duckdb_path)
  ```

- 監査ログの初期化（既存の接続に監査テーブルを追加）
  ```python
  from kabusys.data import audit
  # 既に init_schema で conn を取得済みならそれを使う
  audit.init_audit_schema(conn)
  ```

- 監査専用 DB の初期化（別 DB に監査ログを分離したい場合）
  ```python
  conn_audit = audit.init_audit_db("data/audit.duckdb")
  ```

- 自動 .env 読み込みを無効化してテスト実行
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  python -c "from kabusys.config import settings; print('auto load disabled')"
  ```

注意:
- init_schema / init_audit_schema は冪等で、既存テーブルはそのままにします。
- 監査スキーマは UTC タイムゾーンで TIMESTAMP を保存するように設定されます（init_audit_schema 内で SET TimeZone='UTC' を実行）。

---

## ディレクトリ構成

（重要なファイル・モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py               (パッケージエントリ、バージョン)
    - config.py                 (環境変数・設定管理)
    - data/
      - __init__.py
      - schema.py               (DuckDB スキーマ定義・初期化: init_schema, get_connection)
      - audit.py                (監査ログスキーマ定義・初期化: init_audit_schema, init_audit_db)
      - audit.py                (監査用インデックス含む)
      - (その他 data 関連ユーティリティ)
    - strategy/
      - __init__.py             (戦略用名前空間: 拡張ポイント)
    - execution/
      - __init__.py             (発注/ブローカー連携用名前空間)
    - monitoring/
      - __init__.py             (モニタリング用名前空間)
- pyproject.toml / setup.cfg / .gitignore 等（プロジェクトルート）

---

## 注意事項 / 補足

- 環境変数が必須とされているキーを参照すると、未設定の場合は ValueError が発生します（settings の _require 実装による）。
- .env のパースは比較的柔軟です（export プレフィックス、シングル／ダブルクォート、インラインコメントの処理等をサポート）。
- DuckDB のパスとして ":memory:" を渡すとインメモリ DB を利用できます（テスト向け）。
- 監査ログ設計は削除を想定しておらず、FOREIGN KEY は ON DELETE RESTRICT を採用しています（監査証跡保持）。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかでなければなりません。

---

必要であれば、README に以下を追加できます:
- 完全な .env.example ファイル
- 依存パッケージ一覧（requirements.txt）
- CI / テスト実行手順
- 実運用時の運用フロー（シグナルから発注・監査までの具体例）

必要な追加情報を教えてください。