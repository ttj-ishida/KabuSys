# CHANGELOG

すべての注目すべき変更点はこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  
参考: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 今後の変更をここに記載します。

## [0.1.0] - 2026-03-15
最初の公開リリース。日本株自動売買システムの基礎モジュール群を追加しました。

### Added
- パッケージの基本情報
  - src/kabusys/__init__.py にバージョン情報（0.1.0）とパッケージ公開API（data, strategy, execution, monitoring）を追加。

- 環境変数・設定管理
  - src/kabusys/config.py を追加。
    - .env ファイル（および .env.local）と OS 環境変数から設定を自動読み込みする仕組みを実装。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、パッケージ配布後も動作するように __file__ から親ディレクトリを探索する実装を提供。
      - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テストや特殊環境向け）。
    - .env の行解析ロジックを実装（_parse_env_line）。
      - export KEY=val フォーマット対応。
      - シングル/ダブルクォート内でのバックスラッシュエスケープに対応。
      - 非クォート値では '#' がコメントと見なされる条件を厳密化（直前がスペース/タブの場合のみ）。
    - .env 読み込み時の上書き制御（override）と OS 環境変数保護（protected）に対応。
    - Settings クラスを公開（settings インスタンス）。
      - 必須設定を取得する _require() を実装し、未設定時には ValueError を送出。
      - 主要プロパティ:
        - JQUANTS_REFRESH_TOKEN（必須）
        - KABU_API_PASSWORD（必須）
        - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
        - SLACK_BOT_TOKEN（必須）
        - SLACK_CHANNEL_ID（必須）
        - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
        - SQLITE_PATH（デフォルト: data/monitoring.db）
        - KABUSYS_ENV（development / paper_trading / live の検証）
        - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
      - 環境（is_live / is_paper / is_dev）ヘルパーを提供。

- データベーススキーマ（DuckDB）
  - src/kabusys/data/schema.py を追加。
    - DataSchema.md 想定の 3 層（Raw, Processed, Feature）と Execution 層に基づくテーブル定義を実装。
    - 用意された主なテーブル:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに整合性制約（PRIMARY KEY, CHECK, FOREIGN KEY）を設定。
    - 頻出クエリを考慮したインデックス定義を追加（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status 等）。
    - 公開 API:
      - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - 指定 DB を初期化して全テーブル・インデックスを作成（冪等）。
        - db_path の親ディレクトリが存在しない場合は自動作成。
        - ":memory:" を指定してインメモリ DB を使用可能。
      - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - 既存 DB への接続を返す（スキーマ初期化は行わない）。

- パッケージ構成プレースホルダ
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を追加（将来的な機能拡張のためのパッケージ初期ファイル）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Notes / migration
- .env 自動ロードを行うため、プロジェクトルート（.git または pyproject.toml が存在）をパッケージ内で検出します。配布済み環境やワークツリーが存在しない環境では自動ロードがスキップされます。自動ロードを強制で無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）が未設定の場合、settings の該当プロパティアクセス時に ValueError が発生します。アプリケーション起動前に .env を準備するか OS 環境変数を設定してください。
- DuckDB スキーマを初期化する際は init_schema() を最初に呼ぶことを推奨します。既存 DB をそのまま利用する場合は get_connection() を使用してください。