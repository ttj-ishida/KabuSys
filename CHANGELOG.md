CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

Unreleased
----------

（現在のリリースなし）

[0.1.0] - 2026-03-15
-------------------

Added
- 基本パッケージとモジュールを追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - プロジェクトルートの自動検出関数を実装
    - .git または pyproject.toml を基準に探索するため、CWD に依存しない自動 .env ロードを可能に。
    - ルートが見つからない場合は自動ロードをスキップ。
  - .env ファイル自動読み込みを実装
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途向け）。
    - OS の既存環境変数は保護（protected）され、.env.local の override フラグがあっても上書きされない。
  - .env パーサを実装（_parse_env_line）
    - 空行・コメント（#）を無視。
    - export KEY=val 形式をサポート。
    - シングル・ダブルクォート対応。クォート内のバックスラッシュエスケープを解釈。
    - クォートなしの場合、直前がスペース/タブの '#' をインラインコメントとみなして削除。
  - Settings クラスを提供（settings インスタンスを公開）
    - 必須環境変数取得時に未設定なら ValueError を送出する _require() を用意。
    - 必須キー（例）:
      - JQUANTS_REFRESH_TOKEN（J-Quants 用）
      - KABU_API_PASSWORD（kabu ステーション API）
      - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知）
    - デフォルト値の提供:
      - KABUS_API_BASE_URL のデフォルト: http://localhost:18080/kabusapi
      - DUCKDB_PATH のデフォルト: data/kabusys.duckdb
      - SQLITE_PATH のデフォルト: data/monitoring.db
      - KABUSYS_ENV のデフォルト: development
      - LOG_LEVEL のデフォルト: INFO
    - バリデーション:
      - KABUSYS_ENV は {development, paper_trading, live} のみ許可（不正値は ValueError）
      - LOG_LEVEL は {DEBUG, INFO, WARNING, ERROR, CRITICAL} のみ許可（不正値は ValueError）
    - 補助プロパティ:
      - is_live, is_paper, is_dev

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - 3〜4層のデータレイヤ構成に基づくテーブル定義を追加
    - Raw Layer:
      - raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer:
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer:
      - features, ai_scores
    - Execution Layer:
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して PRIMARY KEY、CHECK 制約、外部キー制約を設計
    - 例: raw_prices の PRIMARY KEY (date, code)、orders->signal_queue の外部キー参照（ON DELETE SET NULL) など
  - 頻出クエリに備えたインデックス定義を追加
    - 例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status 等
  - DB 初期化関数を提供
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定したパスで DuckDB を開き、全テーブルとインデックスを作成（冪等）。
      - db_path の親ディレクトリが存在しない場合、自動作成。
      - ":memory:" を指定してインメモリ DB を利用可能。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ作成は行わない — 初回は init_schema を使用）。

Other
- モジュールの __init__.py を整備（各サブパッケージの準備。現時点では実装は空の初期化ファイル）
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定

Fixed
- 初回リリースのため該当なし

Changed
- 初回リリースのため該当なし

Removed
- 初回リリースのため該当なし

Security
- 初回リリースのため該当なし

使用上の注意 / マイグレーションノート
- DB 初期化:
  - 初回は init_schema() を実行してスキーマを作成してください。既存 DB に対しては冪等なので繰り返し実行しても安全です。
- 環境変数:
  - 必須環境変数（JQUANTS_REFRESH_TOKEN 等）は未設定だと ValueError が発生します。CI/本番環境では適切に設定してください。
  - 自動 .env ロードはプロジェクトルートが検出できる場合にのみ行われます。パッケージ配布後に CWD に依存せず動作することを意図しています。
  - テストなどで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env の記法:
  - export プレフィックス、クォート、バックスラッシュによるエスケープ、インラインコメントの扱い（クォート外かつ直前がスペース/タブの '#' をコメントとする）に注意してください。