# CHANGELOG

すべての重要な変更は Keep a Changelog のフォーマットに従って記録します。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース

### Added
- パッケージ基礎
  - kabusys パッケージを追加。バージョンは `0.1.0`（src/kabusys/__init__.py）。
  - パブリック API として `data`, `strategy`, `execution`, `monitoring` モジュールをエクスポート。

- 環境設定管理 (`src/kabusys/config.py`)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動読み込み:
    - プロジェクトルート（.git または pyproject.toml 存在）を起点に `.env` → `.env.local` の順で自動読み込みを行う（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - OS の既存環境変数は保護され、.env による上書きを防ぐ仕組み（protected set）。
    - `.env.local` は `.env` の値を上書き（override）する。
  - .env パーサーの実装（_parse_env_line）：
    - 空行やコメント行（先頭が `#`）を無視。
    - `export KEY=val` 形式に対応。
    - シングル・ダブルクォートされた値を正しく扱い、バックスラッシュによるエスケープを解釈。
    - クォート無しの値におけるインラインコメント取り扱い（`#` の直前が空白またはタブの場合にコメント扱い）。
  - .env ファイル読み込み時の例外処理（読み込み失敗時に warnings.warn を発行）。
  - Settings によるプロパティ（必須・任意設定）:
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション API: `kabu_api_password`（必須）、`kabu_api_base_url`（デフォルト: `http://localhost:18080/kabusapi`）
    - Slack: `slack_bot_token`（必須）、`slack_channel_id`（必須）
    - DB パス: `duckdb_path`（デフォルト `data/kabusys.duckdb`）、`sqlite_path`（デフォルト `data/monitoring.db`）
    - 実行環境: `env`（`development` / `paper_trading` / `live` のバリデーション）、`is_live/is_paper/is_dev` ヘルパー
    - ログレベル: `log_level`（`DEBUG/INFO/WARNING/ERROR/CRITICAL` のバリデーション）
  - 必須環境変数が未設定の場合は ValueError を送出する `_require` を実装。

- データスキーマ・DB 初期化 (`src/kabusys/data/schema.py`)
  - DuckDB 用のスキーマを定義（Data Lake 的な 3 層構造に準拠）:
    - Raw Layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed Layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature Layer: `features`, `ai_scores`
    - Execution Layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに対して適切な型・制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）を設定。
  - 頻出クエリに対するインデックスを作成（`idx_prices_daily_code_date` 等）。
  - テーブル作成順を依存関係に基づいて管理（外部キー依存を考慮）。
  - 公開 API:
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 指定した DuckDB ファイルに対してディレクトリを自動作成し、DDL／インデックスを適用して接続を返す。
      - テーブル作成は冪等（既存テーブルはスキップ）。
      - `":memory:"` でインメモリ DB をサポート。
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 既存 DB への接続を返す（スキーマ初期化は行わない。初回は `init_schema()` を呼ぶことを想定）。
  - DuckDB への依存を使用（duckdb.connect を使用した接続管理）。

- パッケージ構成（各サブパッケージの初期化ファイルを設置）
  - `src/kabusys/data/__init__.py`
  - `src/kabusys/strategy/__init__.py`
  - `src/kabusys/execution/__init__.py`
  - `src/kabusys/monitoring/__init__.py`
  - これらは将来的な実装用のプレースホルダ（空の __init__）。

### Changed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Fixed
- なし

### Security
- なし

注記:
- スキーマ定義内のコメントに DataSchema.md 参照があり、データモデリングの設計意図（Raw/Processed/Feature/Execution 層）を明示しています。
- .env 自動読み込みはプロジェクトルートをロケートできない場合にはスキップされます（配布後の環境でも意図しない読み込みを避けるため）。