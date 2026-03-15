CHANGELOG
=========
この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
このファイルはコードベースの実装内容から推測して作成しています。

フォーマット:
- 変更はセマンティックバージョニングに従います。
- 日付はリリース日を示します。

未リリース
---------
（現在なし）

[0.1.0] - 2026-03-15
-------------------
Added
- 初期リリース。パッケージ名: kabusys、バージョン 0.1.0。
- パブリック API:
  - kabusys.settings: 環境変数ベースの設定取得を行う Settings インスタンスを提供。
  - kabusys.data.schema.init_schema(db_path): DuckDB データベースを初期化し、スキーマ（テーブル・インデックス）を作成して接続を返す。
  - kabusys.data.schema.get_connection(db_path): 既存の DuckDB データベースへ接続を返す（初期化は行わない）。
- 環境変数・設定管理（src/kabusys/config.py）:
  - .env ファイルと環境変数を組み合わせて設定を読み込む自動ロード機構を実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml を親ディレクトリで探索）を基準に行うため、CWD に依存せずパッケージ配布後も動作する設計。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env と .env.local の読み込み順:
    - OS 環境変数 > .env.local（override=True）> .env（override=False）
    - OS 環境変数は protected として上書きを防止。
  - .env パーサ (_parse_env_line) の実装:
    - 空行とコメント行（# で始まる行）を無視。
    - "export KEY=val" 形式をサポート。
    - 値がシングルクォート/ダブルクォートで囲まれている場合、バックスラッシュによるエスケープを考慮して対応する閉じクォートまでを取得（以降の inline comment を無視）。
    - クォートなしの場合、'#' をコメントとみなすのはその直前がスペースまたはタブのときのみ（inline # を許容する厳密な処理）。
  - .env ファイル読み込み失敗時には warnings.warn を発行してエラーを上書きしない安全な挙動。
  - 必須環境変数取得ヘルパ _require を実装し、未設定時は ValueError を送出。
  - Settings で提供される設定プロパティ:
    - J-Quants / kabuステーション / Slack / データベースパスなど（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH 等）。
    - システム設定: KABUSYS_ENV（development, paper_trading, live のみ許容）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容）を検証して取得。
    - is_live / is_paper / is_dev のブール判定プロパティを提供。
- DuckDB ベースのスキーマ（src/kabusys/data/schema.py）:
  - 3 層（Raw / Processed / Feature）＋ Execution 層に対応するテーブル群を定義。
  - Raw layer: raw_prices, raw_financials, raw_news, raw_executions
  - Processed layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature layer: features, ai_scores
  - Execution layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な型・CHECK 制約・PRIMARY KEY・外部キーを定義（例: side は 'buy'|'sell'、order_type は 'market'|'limit'|'stop' 等）。
  - 頻出クエリに備えたインデックス群を用意（銘柄×日付、status 検索、orders.signal_id、trades.order_id、news_symbols.code 等）。
  - init_schema は与えられた db_path の親ディレクトリを自動作成し、":memory:" をサポートする。
  - スキーマ作成は冪等（すでに存在するテーブル・インデックスはスキップ）。
- パッケージ構成:
  - src/kabusys/__init__.py にて __version__ = "0.1.0"、__all__ = ["data", "strategy", "execution", "monitoring"] を公開。
  - strategy、execution、monitoring、data のサブパッケージ初期化ファイルを配置（将来の実装拡張を想定した骨格）。

Changed
- （初版につき該当なし）

Fixed
- （初版につき該当なし）

注記 / 補足
- 設定周りや DB スキーマは初期設計段階の実装に基づいています。実運用の際は必要に応じて環境変数の命名やデフォルト値、制約（データ型・CHECK 条件）、インデックス設計等を見直してください。
- .env パーサは POSIX シェルの全ての表現を再現するものではなく、本プロジェクトでの想定使用パターンに合わせた挙動（簡潔で安全な取り扱い）を優先しています。必要であればパーサの仕様を拡張してください。