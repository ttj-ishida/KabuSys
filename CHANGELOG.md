# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティック バージョニングを採用しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-15

初回リリース。以下の機能・初期実装を含みます。

### Added
- パッケージ初期化
  - パッケージルート: `kabusys`。バージョン情報 `__version__ = "0.1.0"` を定義し、公開モジュールとして `data`, `strategy`, `execution`, `monitoring` を `__all__` に設定。

- 環境設定（kabusys.config）
  - 環境変数/設定管理モジュールを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートを `.git` または `pyproject.toml` を基準に探索して特定（CWDに依存せずパッケージ配布後も機能）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能（テスト用途など）。
    - OS の既存環境変数は保護され、`.env.local` による上書きは可能だが保護対象（protected）には影響しないように実装。
  - 高度な .env パーサを実装:
    - `export KEY=val` 形式のサポート。
    - シングル/ダブルクォートされた値を考慮（バックスラッシュによるエスケープ処理を実装）。クォート内のインラインコメントを無視。
    - クォートなし値では、直前がスペース/タブの `#` をコメントとみなす処理。
    - 無効行やコメント行をスキップ。
  - `.env` 読み込み失敗時は警告を発行。
  - `Settings` クラスを公開（`settings` インスタンスを提供）。主なプロパティ:
    - J-Quants / Kabuステーション / Slack の必須トークン取得（未設定時は ValueError を送出）。
    - Kabu API のデフォルト base URL を指定可能（`http://localhost:18080/kabusapi`）。
    - データベースパスのデフォルト: DuckDB -> `data/kabusys.duckdb`、SQLite -> `data/monitoring.db`（`~` 展開対応）。
    - 環境 (`KABUSYS_ENV`) 値検証（`development`, `paper_trading`, `live` のみ許容）。
    - ログレベル (`LOG_LEVEL`) 値検証（`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）。
    - `is_live` / `is_paper` / `is_dev` のブール判定プロパティ。

- データ層（kabusys.data.schema）
  - DuckDB 用のスキーマ定義と初期化機能を提供。
  - レイヤー構成に基づいたテーブル群を導入:
    - Raw Layer: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed Layer: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature Layer: `features`, `ai_scores`
    - Execution Layer: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに適切な型制約・CHECK 制約・主キー・外部キーを設定。
  - よく使われるクエリパターンに基づくインデックスを定義:
    - 例: `idx_prices_daily_code_date`, `idx_features_code_date`, `idx_signal_queue_status`, `idx_orders_status` 等。
  - スキーマ初期化関数 `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection` を実装:
    - 指定したファイルパスの親ディレクトリを自動作成（`:memory:` は除く）。
    - DDL とインデックスを順に実行して冪等にテーブル作成を行う。
    - 初期化済みの DuckDB 接続を返却。
  - 既存 DB へ接続するユーティリティ `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection` を追加（スキーマ初期化は行わない）。

- サブパッケージ骨組み
  - `kabusys.execution`, `kabusys.strategy`, `kabusys.data`, `kabusys.monitoring` のパッケージ空イニシャライザを追加（今後の拡張点として準備）。

### Changed
- 該当なし（初回リリースのため）。

### Fixed
- 該当なし（初回リリースのため）。

### Removed
- 該当なし（初回リリースのため）。

### Notes / 備考
- .env 読み込みの挙動はプロジェクトルート検出と OS 環境変数保護に依存するため、CI/テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを抑制することを推奨します。
- DuckDB 初期化時は `init_schema` を呼び出してからアプリケーションを運用してください。`get_connection` は既に初期化済みの DB に接続するための関数です。

--- 

（この CHANGELOG はリポジトリ内の現在のコード内容から推測して作成しています。実際の変更履歴やリリースノートはコミット履歴・リリース計画に応じて適宜更新してください。）