# KabuSys

日本株向け自動売買システムのコアライブラリ（パイロット実装）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python モジュール群です。  
データ取得・永続化（DuckDB）から特徴量生成、シグナル生成、発注監査ログまでを想定したレイヤードアーキテクチャを提供します。本リポジトリはコアスキーマ・設定管理・監査ログの初期化を中心に実装されています。

主な設計方針：
- データは Raw / Processed / Feature / Execution の多層で管理
- 発注フローは監査可能（UUIDチェーン）で冪等性を担保
- 環境変数による設定管理（.env の自動読み込みをサポート）
- DuckDB を永続ストレージとして利用（軽量、ファイルベース）

---

## 機能一覧

- 設定管理（環境変数の読み込みとバリデーション）
  - 必須設定の抽出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_*）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 .env 読み込み無効化
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - export 構文、クォート、コメントのある .env 行の柔軟なパース

- DuckDB スキーマ定義と初期化
  - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
  - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature 層: features, ai_scores
  - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックスを含む冪等的な初期化（init_schema）
  - ":memory:" によるインメモリ DB 対応

- 監査ログ（Audit）モジュール
  - signal_events, order_requests, executions のテーブルとインデックス定義
  - 発注フローの完全なトレーサビリティ（order_request_id を冪等キーとして使用）
  - UTC のタイムスタンプ運用方針（init_audit_schema は TimeZone='UTC' を設定）

- パッケージ構成の土台（strategy / execution / monitoring のための名前空間）

---

## セットアップ手順

前提:
- Python 3.9+（typing の新構文を使用しているため、使用する Python バージョンに注意）
- duckdb パッケージ

1. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージのインストール
   ```
   pip install duckdb
   ```

3. 環境変数の設定
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD がセットされていると自動読み込みは無効化されます）。

   最低限設定が必要な環境変数（README 用サンプル）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   # 任意:
   KABUSYS_ENV=development  # development | paper_trading | live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   .env のパースは次をサポートします:
   - export KEY=val 形式
   - シングル/ダブルクォート内のエスケープ
   - 行頭の # や行末のコメント（クォート外、直前がスペース/タブの場合）  
   （詳細な挙動は kabusys.config モジュールに準拠します）

---

## 使い方（基本例）

- 設定を参照する
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  base_url = settings.kabu_api_base_url
  if settings.is_live:
      print("ライブ運用モード")
  ```

- DuckDB スキーマの初期化（ファイル DB）
  ```python
  from kabusys.data import schema

  conn = schema.init_schema("data/kabusys.duckdb")
  # conn は duckdb.DuckDBPyConnection を返す
  ```

  インメモリ DB を使う場合:
  ```python
  conn = schema.init_schema(":memory:")
  ```

- 既存 DB へ接続する（スキーマ初期化は行わない）
  ```python
  conn = schema.get_connection("data/kabusys.duckdb")
  ```

- 監査ログテーブルを既存接続に追加する
  ```python
  from kabusys.data import audit

  # 既に init_schema で作成した conn を渡す
  audit.init_audit_schema(conn)
  ```

- 監査専用 DB を新規作成して取得する
  ```python
  conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
  ```

- 自動 .env 読み込みを抑止してテスト等を行う
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  python -c "from kabusys.config import settings; print('disabled')"
  ```

---

## ディレクトリ構成

主要なファイル・モジュールと短い説明:

- src/kabusys/
  - __init__.py
    - パッケージエントリ。公開サブパッケージを定義（data, strategy, execution, monitoring）
  - config.py
    - 環境変数の自動読み込み・パース、設定項目のプロパティ（Settings クラス）
    - 必須項目は _require でチェックする
  - data/
    - __init__.py
    - schema.py
      - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
      - init_schema(db_path) / get_connection(db_path)
    - audit.py
      - 監査ログ用テーブル定義と初期化関数（init_audit_schema, init_audit_db）
    - audit は発注フローのトレーサビリティと冪等性を扱う
  - strategy/
    - __init__.py（戦略ロジック用名前空間）
  - execution/
    - __init__.py（発注ロジック用名前空間）
  - monitoring/
    - __init__.py（監視・メトリクス用名前空間）

（上記は本リポジトリに含まれる現状のファイル群と役割の一覧です。strategy / execution / monitoring は将来的に実装を追加するためのプレースホルダです。）

---

## 注意点 / 補足

- init_schema / init_audit_db は親ディレクトリが存在しない場合に自動で作成します。
- DuckDB の制約（CHECK, PRIMARY KEY, FOREIGN KEY）をスキーマレベルで多用しています。既存データのマイグレーション時は注意してください。
- 監査テーブルではタイムゾーンとして UTC を採用しているため、init_audit_schema は接続に対して TimeZone='UTC' を設定します。
- 環境変数のバリデーションは Settings のプロパティで行われます（例: KABUSYS_ENV は development, paper_trading, live のいずれか）。
- 本 README はコードベースの現状に基づくドキュメントです。実際の運用（証券会社 API、J-Quants API、Slack 通知など）と統合するには追加実装が必要です。

---

## 連絡 / 貢献

バグ報告、機能提案、プルリクエストは README と同じリポジトリの issue / PR にて受け付けてください。ドキュメントや型の追加だけでも歓迎します。

--- 

以上。README に含めたい追加情報（例: .env.example の完全なテンプレートや CI 手順など）があれば教えてください。必要に応じて追記します。