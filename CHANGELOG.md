# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog 規約に従い、セマンティック バージョニングを採用します。

# 変更履歴

## [Unreleased]
（現在の開発中の変更はここに記載します）

## [0.1.0] - 2026-03-15
初回公開リリース

### Added
- パッケージメタ情報
  - パッケージ名とバージョンを定義: kabusys.__version__ = "0.1.0"
  - パッケージ公開モジュール一覧を定義: kabusys.__all__ = ["data", "strategy", "execution", "monitoring"]

- 環境変数・設定管理モジュール (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動ロード機能:
    - プロジェクトルート（.git または pyproject.toml を探索）を起点に .env, .env.local を自動読み込み。
    - OS 環境変数を保護し、.env.local は .env を上書き（.env.local は override=True）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - .env パーサーの実装:
    - 空行・コメント（# 始まり）を無視。
    - export KEY=val 形式に対応。
    - シングル・ダブルクォートされた値のエスケープ処理に対応（バックスラッシュのエスケープ）。
    - クォートなし値に対しては '#' の直前が空白/タブの場合にインラインコメントとみなす挙動。
    - 不正行はスキップ。
  - .env 読み込み時の挙動:
    - ファイル読み込みエラーは warnings.warn で警告を発行してスキップ。
    - override フラグと protected キーセットにより既存 OS 環境変数の上書きを制御。
  - Settings による取得可能な設定項目（プロパティ）:
    - JQUANTS_REFRESH_TOKEN (必須)
    - KABU_API_PASSWORD (必須)
    - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須)
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb), SQLITE_PATH (デフォルト: data/monitoring.db)
    - KABUSYS_ENV の検証（development|paper_trading|live）
    - LOG_LEVEL の検証（DEBUG|INFO|WARNING|ERROR|CRITICAL）
    - ヘルパープロパティ: is_live, is_paper, is_dev
  - settings = Settings() を公開（モジュールレベルの単一インスタンス）

- DuckDB スキーマ定義・初期化モジュール (kabusys.data.schema)
  - 3 層のスキーマ設計（Raw / Processed / Feature）および Execution 層のDDLを追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して妥当性制約（CHECK）、PRIMARY KEY、必要な FOREIGN KEY を定義。
  - 検索パフォーマンス向上のためのインデックス群を定義（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) を実装:
    - 指定したパスに対してディレクトリを自動作成（":memory:" は例外）。
    - 全 DDL とインデックスを順次実行してスキーマを作成（冪等）。
    - 初期化済みの duckdb 接続を返す。
  - get_connection(db_path) を実装:
    - 既存の DuckDB へ接続を返す（スキーマ初期化は行わない。初回は init_schema を使用することを想定）。

- パッケージ構成（プレースホルダモジュール）
  - 空のパッケージ初期化ファイルを配置: kabusys.data.__init__, kabusys.execution.__init__, kabusys.strategy.__init__, kabusys.monitoring.__init__（将来的な拡張用）

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Notes / Migration
- 初回セットアップ:
  - DuckDB を使用する場合は、kabusys.data.schema.init_schema(settings.duckdb_path) を呼び出してスキーマを作成してください。
  - .env ファイルはプロジェクトルート（.git または pyproject.toml があるディレクトリ）に配置してください。テスト等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 環境変数の必須項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）が未設定の場合、Settings のプロパティアクセス時に ValueError が発生します。

### Security
- 環境変数の上書き保護機構を導入（OS 環境変数は protected として扱われ、意図しない上書きを防止）。

---

（以降のバージョンはここに追記してください）