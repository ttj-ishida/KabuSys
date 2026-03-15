# Changelog

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

## [0.1.0] - 2026-03-15

### Added
- 初期リリース。パッケージ `kabusys` の骨組みを追加。
  - パッケージバージョン: `0.1.0`
  - パッケージトップ: `src/kabusys/__init__.py`（公開モジュール: `data`, `strategy`, `execution`, `monitoring`）

- 環境設定管理モジュールを追加（`src/kabusys/config.py`）。
  - `.env` ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 自動ロードの探索はパッケージ内のファイル位置を起点にプロジェクトルート（`.git` または `pyproject.toml`）を探索して判定。
    - 読み込み優先順位: OS 環境変数 > .env.local（上書き） > .env（既存を上書きしない）。
    - 自動ロードを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
    - OS の環境変数は保護（protected set）され、明示的に上書きされない限り保持される。
  - .env パーサーを実装（`_parse_env_line`）。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメントの解釈（クォート有無での振る舞い差異）などに対応。
  - 必須環境変数取得ヘルパー `_require`（未設定時は `ValueError` を送出）。
  - `Settings` クラスを公開（インスタンス: `settings`）。
    - J-Quants / kabuステーション / Slack / DB パス 等のプロパティを提供。
    - `duckdb` / `sqlite` のデフォルトパスをサポート（`Path` を返す）。
    - `KABUSYS_ENV` の検証（`development`, `paper_trading`, `live` のいずれか）と `LOG_LEVEL` の検証（`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）。
    - 環境判定用プロパティ: `is_live`, `is_paper`, `is_dev`。

- DuckDB ベースのデータスキーマ定義と初期化機能を追加（`src/kabusys/data/schema.py`）。
  - 3層＋実行層の論理構造に基づくテーブル群を定義:
    - Raw Layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed Layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature Layer: `features`, `ai_scores`
    - Execution Layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに対して適切な型定義・CHECK 制約・PRIMARY KEY・FOREIGN KEY を設定（データ整合性の担保）。
  - 頻出クエリに備えたインデックス群を定義（コード×日付スキャン、ステータス検索、JOIN 支援など）。
  - DDL は冪等（`CREATE TABLE IF NOT EXISTS`）で設計。
  - 初期化 API:
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`:
      - 指定したパスの DuckDB を初期化して接続を返す。親ディレクトリを自動作成。`:memory:` をサポート。
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`:
      - 既存 DB へ接続（スキーマ初期化は行わない）。初回は `init_schema` を使用することを想定。

- 監査ログ（トレーサビリティ）モジュールを追加（`src/kabusys/data/audit.py`）。
  - シグナルから約定に至るフローを UUID 連鎖で追跡可能にする監査テーブル群を定義。
    - テーブル: `signal_events`, `order_requests`, `executions`
    - 設計方針:
      - 発生したシグナル・発注（エラーや棄却を含む）をすべて永続化。
      - `order_request_id` は冪等キーとして機能。
      - 外部キーは監査の不変性を保つため `ON DELETE RESTRICT` を採用。
      - `created_at` / `updated_at` を含める設計（アプリ側で更新時に `current_timestamp` を設定する想定）。
      - `executions` 側で `broker_execution_id` をユニーク制約（証券会社提供の約定 ID を冪等キーとして扱う）。
      - すべての TIMESTAMP を UTC で保存するため、初期化時に `SET TimeZone='UTC'` を実行。
  - インデックス群を用意（シグナル検索、状態別キュー検索、broker_order_id/実行検索など）。
  - 初期化 API:
    - `init_audit_schema(conn: duckdb.DuckDBPyConnection) -> None`:
      - 既存の DuckDB 接続に監査ログテーブル群とインデックスを追加（冪等）。
    - `init_audit_db(db_path: str | Path) -> duckdb.DuckDBPyConnection`:
      - 監査ログ専用の DuckDB ファイルを初期化して接続を返す。親ディレクトリ自動作成、UTC によるタイムゾーンを設定。

- サブパッケージのプレースホルダを追加:
  - `src/kabusys/execution/__init__.py`
  - `src/kabusys/strategy/__init__.py`
  - `src/kabusys/monitoring/__init__.py`
  - （現時点では実装はないが、パッケージ構成と公開 API の骨組みを用意）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の取扱いやファイル読み込みで OS 環境を保護する仕組み（protected set）を導入。
- .env の読み込みは明示的に無効化可能（テスト時の誤動作防止）。

注:
- 実行・戦略・モニタリングの具体的ロジックはまだ実装されていません。Data / Audit / Config による基盤が整備された段階の初期リリースです。