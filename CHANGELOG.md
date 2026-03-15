# CHANGELOG

すべての変更は Keep a Changelog の慣例に従い記載しています。  
このプロジェクトはまだ初期段階のバージョンをリリースしています。

## [Unreleased]

- 現在未リリースの変更はありません。

## [0.1.0] - 2026-03-15

### Added
- パッケージの初期リリース。
  - パッケージルート: `src/kabusys/__init__.py`
    - バージョン: `0.1.0`
    - 初期エクスポート: `["data", "strategy", "execution", "monitoring"]`
- 環境設定モジュール: `src/kabusys/config.py`
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルート判定を .git または `pyproject.toml` により行い、CWD に依存しない実装。
    - 読み込み優先順位: OS 環境変数 > `.env.local` > `.env`。
    - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
    - OS の既存環境変数を保護するための protected キー集合を使用。
  - .env のパーサ実装（堅牢なパース仕様）
    - 空行や `#` で始まる行は無視。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォートされた値のエスケープ（バックスラッシュ）に対応。
    - クォートなし値に対するインラインコメント判定は、`#` の直前がスペース/タブの場合のみコメントと認識。
  - 必須設定取得ヘルパー `_require` と、アプリケーション設定ラッパ `Settings` を提供。
    - J-Quants / kabuAPI / Slack / DB パス等のプロパティを定義。
    - `KABUSYS_ENV`（development, paper_trading, live）と `LOG_LEVEL` のバリデーション。
    - 環境判定プロパティ: `is_live`, `is_paper`, `is_dev`。
  - 既定値: `KABUS_API_BASE_URL` のデフォルトと DB パスのデフォルト等を設定。
- データ層（DuckDB）スキーマ・初期化モジュール: `src/kabusys/data/schema.py`
  - データレイヤーを 3 層（Raw / Processed / Feature）および Execution 層で設計・定義。
  - テーブル定義（DDL）を多数追加:
    - Raw Layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed Layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature Layer: `features`, `ai_scores`
    - Execution Layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに適切な型チェック、制約（CHECK, PRIMARY KEY, FOREIGN KEY）を定義。
  - 頻出クエリを想定したインデックスを多数追加（銘柄×日付スキャン、ステータス検索等）。
  - 公開 API:
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection` : DB ファイルの親ディレクトリを自動作成し、冪等的にスキーマを初期化して接続を返す（`:memory:` 対応）。
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection` : 既存 DB に接続（スキーマ初期化は行わない）。
- 監査ログ（トレーサビリティ）モジュール: `src/kabusys/data/audit.py`
  - シグナルから約定に至るトレーサビリティ用の監査テーブル群を定義。
    - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）を設計。
    - テーブル: `signal_events`, `order_requests`, `executions`
    - 設計原則（例）:
      - すべてのイベントを永続化（エラーや棄却を含む）
      - `order_request_id` を冪等キーとして設計
      - 監査ログは削除しない（FK は ON DELETE RESTRICT）
      - すべての TIMESTAMP は UTC で保存（初期化時に `SET TimeZone='UTC'` を実行）
      - `updated_at` はアプリ側で更新時に current_timestamp を設定する運用
    - ステータス遷移・チェック制約を定義（`order_requests.status`, `order_type` の整合性チェック等）。
  - インデックス群を定義（信号検索、日付/銘柄、broker_order_id、status によるキュー取得など）。
  - 公開 API:
    - `init_audit_schema(conn: duckdb.DuckDBPyConnection) -> None` : 既存接続に監査テーブルを追加（UTC タイムゾーンを設定）。
    - `init_audit_db(db_path: str | Path) -> duckdb.DuckDBPyConnection` : 監査専用 DB を初期化して接続を返す。
- モジュール・パッケージ構成（空の初期化ファイルを含む）
  - `src/kabusys/data/__init__.py`
  - `src/kabusys/execution/__init__.py`
  - `src/kabusys/strategy/__init__.py`
  - `src/kabusys/monitoring/__init__.py`
  - これによりパッケージ名空間を確立し、今後の実装拡張に備える。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes / 開発者向けメモ
- DuckDB スキーマ初期化関数は冪等であり、既存テーブルがある場合はスキップします。初回利用時は必ず `init_schema()`（および監査用に `init_audit_schema()` または `init_audit_db()`）を呼んでください。
- 環境変数の自動ロードはプロジェクトルートの判定に基づき行われるため、パッケージ配布後も正しく動作する設計になっています。ユニットテスト等で自動ロードを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 監査ログは UTC 保存を前提にしているため、アプリケーションレイヤでの時刻管理に注意してください。