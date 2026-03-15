# CHANGELOG

すべての重要な変更履歴をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。  

現在のバージョンは 0.1.0 です（初期リリース）。

---

## [Unreleased]
（なし）

---

## [0.1.0] - 2026-03-15

初回公開リリース。

### Added
- パッケージ基盤を追加
  - パッケージ名: kabusys
  - __version__ = "0.1.0"
  - パッケージエクスポート: data, strategy, execution, monitoring のプレースホルダモジュールを作成

- 環境設定管理モジュールを追加 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルート検出: .git または pyproject.toml を基準に __file__ の親階層を探索（CWD に依存しない実装）
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - OS 環境変数の保護機構: .env の上書き時に既存 OS 環境変数を保護
  - .env パーサを独自実装
    - コメント行（#）や空行を無視
    - "export KEY=val" 形式をサポート
    - クォートされた値（シングル／ダブルクォート）に対応、バックスラッシュのエスケープ処理を考慮
    - クォートなし値におけるインラインコメントの扱い（# の直前が空白またはタブの場合のみコメントと認識）
    - 無効行のスキップ
    - .env ファイルの読み込み失敗時には warnings.warn で警告を出力
  - Settings クラスを提供（settings = Settings()）
    - J-Quants / kabu ステーション / Slack / DB パスなど主要設定をプロパティで取得
    - 必須設定は _require() で未設定時に ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - デフォルト値:
      - KABU_API_BASE_URL -> "http://localhost:18080/kabusapi"
      - DUCKDB_PATH -> "data/kabusys.duckdb"
      - SQLITE_PATH -> "data/monitoring.db"
      - KABUSYS_ENV -> "development"（ただし有効値は development, paper_trading, live）
      - LOG_LEVEL -> "INFO"（ただし有効値は DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - ユーティリティプロパティ: is_live, is_paper, is_dev

- DuckDB スキーマ定義と初期化モジュールを追加 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）および Execution 層を定義
  - Raw レイヤーのテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
  - Processed レイヤーのテーブル:
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature レイヤーのテーブル:
    - features, ai_scores
  - Execution レイヤーのテーブル:
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型、CHECK 制約、PRIMARY KEY、外部キー制約を定義
  - 頻出クエリを想定したインデックスを複数定義（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status など）
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定 DB を初期化しテーブルとインデックスを作成（冪等）
      - db_path の親ディレクトリがなければ自動作成
      - ":memory:" をサポート（インメモリ DB）
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない）
  - スキーマ作成順は外部キー依存を考慮して定義

### Documentation
- 各モジュールにドキュメンテーション文字列（docstring）を追加
  - パッケージ概要、各関数・クラスの用途や引数、戻り値を記載

### Other
- 型アノテーション（Python 3.10+ の union 型 | を使用）を多数導入
- ファイルの文字エンコーディングとして UTF-8 を使用

### Known notes / 使用上の注意
- Settings の必須環境変数が未設定の場合は例外が発生するため、運用前に .env を作成するか環境変数を設定してください。
- init_schema() は初回実行時にテーブルとインデックスを作成します。既に存在するスキーマがある場合は基本的に安全にスキップされますが、運用環境ではバックアップを推奨します。
- .env の自動読み込みはプロジェクトルートが特定できない場合はスキップされます（パッケージ配布後の利用を想定）。

---

（次回以降のリリースでは、追加機能、変更点、バグ修正、互換性に関する詳細をここに記載します。）