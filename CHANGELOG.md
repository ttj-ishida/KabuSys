CHANGELOG
=========

すべての重要な変更点を追跡します。本ファイルは「Keep a Changelog」形式に従います。

[非公開/将来の変更]
------------------

- Unreleased: なし

0.1.0 - 2026-03-15
-----------------

Added
- 初期公開リリース。
- パッケージ構成
  - パッケージルート: `kabusys`。`src/kabusys/__init__.py` にて __version__ = "0.1.0" とパブリックモジュールリスト (__all__) を定義。
  - 空のモジュールエントリを用意: `kabusys.execution`, `kabusys.strategy`, `kabusys.data`, `kabusys.monitoring`（将来的な実装向けのプレースホルダ）。
- 環境設定モジュール (`src/kabusys/config.py`)
  - .env/.env.local の自動読み込み機能を実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に `__file__` から探索して特定（CWD に依存しない挙動）。
    - 自動読み込みを無効化するために環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用可能（テスト用途など）。
    - 読み込み順序: OS 環境変数 > `.env.local` > `.env`。既存の OS 環境変数は保護される（protected）。
    - ファイル読み込み失敗時は警告を発生させる。
  - .env のパース機能（`_parse_env_line`）を実装。
    - 空行・コメント行（先頭が `#`）を無視。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォートされた値に対してバックスラッシュによるエスケープを考慮して閉じクォートまでを正しく抽出。
    - クォートなしの値は `#` の直前がスペースまたはタブの場合にコメントとみなして切り捨てる挙動。
  - 環境変数読み込み時の上書きルール:
    - `override=False` の場合は未設定のキーのみ設定。
    - `override=True` の場合は protected（OS 環境変数集合）を除いて上書き。
  - 必須環境変数チェック `_require()` を実装し、未設定時は ValueError を送出。
  - Settings クラスを提供（インスタンス `settings` を公開）。主なプロパティ:
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション API: `kabu_api_password`（必須）、`kabu_api_base_url`（デフォルト "http://localhost:18080/kabusapi"）
    - Slack: `slack_bot_token`（必須）、`slack_channel_id`（必須）
    - データベースパス: `duckdb_path`（デフォルト "data/kabusys.duckdb"）、`sqlite_path`（デフォルト "data/monitoring.db"）
    - システム設定: `env`（`development|paper_trading|live` のバリデーション）、`log_level`（`DEBUG/INFO/WARNING/ERROR/CRITICAL` のバリデーション）
    - ユーティリティ: `is_live`, `is_paper`, `is_dev`
- DuckDB スキーマ定義と初期化 (`src/kabusys/data/schema.py`)
  - ドメインを意識した 3 層（Raw / Processed / Feature）＋Execution レイヤのテーブル定義を実装。
    - Raw レイヤ: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed レイヤ: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature レイヤ: `features`, `ai_scores`
    - Execution レイヤ: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに適切な型チェック、NOT NULL 制約、主キー、外部キー（必要箇所）を定義。
  - インデックスを複数定義して、銘柄×日付スキャンやステータス検索などの頻出クエリをサポート（例: `idx_prices_daily_code_date`, `idx_signal_queue_status` 等）。
  - 公開 API:
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - DB ファイルの親ディレクトリを自動作成（`:memory:` をサポート）。
      - DDL を順序に沿って実行し、冪等にテーブル・インデックスを作成して接続オブジェクトを返す。
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 既存の DB に接続するための関数（スキーマ初期化は行わない。初回は init_schema を使用）。
  - DataSchema.md を想定した設計（コメントあり）。
- その他
  - ドキュメンテーション文字列と型注釈（Python 3.10+ の union 表現など）を多数追加し、API の使い方や振る舞いが明示されている。
  - DB 初期化関数は `duckdb` を直接使用する実装であり、ファイルベース・インメモリの両方をサポート。

Changed
- なし（初期リリースのため）

Fixed
- なし

Removed
- なし

Notes
- 初回起動時は必須環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）を設定してください。未設定の場合、Settings の各プロパティアクセスで ValueError が発生します。
- DB をファイルで利用する場合、`init_schema()` は DB ファイルの親ディレクトリを自動作成します。インメモリ DB をテストで使う場合は `":memory:"` を渡してください。
- .env の自動読み込みはプロジェクトルートの検出に依存するため、配布後やインストール環境でも動作するように __file__ を起点に探索する実装になっています。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化してください。