CHANGELOG
=========
(本ファイルは "Keep a Changelog" の形式に準拠しています。)

Unreleased
----------

なし

0.1.0 - 2026-03-15
------------------

Added
- 初期リリース。パッケージ名: kabusys (バージョン 0.1.0)
- パッケージ公開 API:
  - kabusys.__version__ = "0.1.0"
  - kabusys.__all__ に data, strategy, execution, monitoring を登録（各モジュールはパッケージとして存在）。
- 環境設定モジュール (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを導入。
  - 自動ロードの挙動:
    - プロジェクトルートを .git または pyproject.toml を基準に探索して自動的に .env と .env.local を読み込む（CWD に依存しない実装）。
    - OS 環境変数の保護: 既存の環境変数は上書きされない（._env.local は override=True として読み込み可能だが OS 環境変数は保護される）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサの強化:
    - 空行・コメント行（#で始まる行）を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートされた値をバックスラッシュエスケープを考慮して正しくデコード。
    - クォート無し値では、直前がスペースまたはタブの場合に '#' をコメントとして扱う（インラインコメント処理の制御）。
  - 必須値取得ヘルパー _require を提供（未設定時は ValueError を送出）。
  - Settings が提供する主な設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV の検証（許容値: development, paper_trading, live）
    - LOG_LEVEL の検証（許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - ヘルパープロパティ: is_live, is_paper, is_dev
- DuckDB スキーマ定義・初期化モジュール (kabusys.data.schema)
  - 3 層（Raw / Processed / Feature）+ Execution 層のテーブル定義を導入。
  - 主なテーブル（抜粋）:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対する型チェック・制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）を明示。
  - 頻出クエリに備えたインデックス定義を追加（例: idx_prices_daily_code_date、idx_signal_queue_status、idx_orders_status 等）。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定した DuckDB ファイルに対してスキーマを作成（既存テーブルはスキップ：冪等）。
      - db_path の親ディレクトリが存在しない場合は自動作成。
      - ":memory:" を指定してインメモリ DB を使用可能。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない。初回は init_schema を使用）。
- パッケージ構成
  - 以下のサブパッケージを作成（初期は空の __init__）:
    - kabusys.execution
    - kabusys.strategy
    - kabusys.data
    - kabusys.monitoring

Notes / Usage
- 環境変数の自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。
- 初回起動時は以下を実行して DuckDB スキーマを作成することを推奨:
  - from kabusys.data.schema import init_schema
  - init_schema(settings.duckdb_path)  # settings は kabusys.config.settings
- 必須の環境変数が足りない場合、Settings のプロパティアクセスで ValueError が発生します。.env.example を参照して .env を用意してください。
- このリリースは初版のため、後続でストラテジー、実行ロジック、監視機能、データ収集コネクタなどを実装予定。

Deprecated / Removed / Security / Fixed
- なし（初期リリース）

Breaking Changes
- なし（初期リリース）