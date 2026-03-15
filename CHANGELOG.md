Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは、https://keepachangelog.com/ja/ の慣例に従います。

フォーマット
----------
バージョン番号はセマンティックバージョニングに従います。

Unreleased
----------

0.1.0 - 2026-03-15
------------------

Added
- 初期リリース。日本株自動売買システム「KabuSys」の基礎モジュールを追加。
  - パッケージ構成
    - kabusys (パッケージルート)
      - data: データ関連（schema 等）
      - strategy: 戦略モジュール（初期はパッケージ空）
      - execution: 発注等の実行モジュール（初期はパッケージ空）
      - monitoring: 監視関連モジュール（初期はパッケージ空）
  - バージョン情報
    - __version__ = "0.1.0"
  - 環境変数・設定管理（kabusys.config）
    - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
      - 読み込み順序: OS 環境変数 > .env.local > .env
      - OS 環境変数は保護され、.env.local の override 設定でも上書きされない。
      - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用可能。
      - プロジェクトルート検出: 現在ファイルを起点に上位ディレクトリを探索し、.git または pyproject.toml が見つかればルートと認識（配布後の動作を考慮）。
    - .env パーサーの実装（_parse_env_line）
      - 空行・コメント行（# で始まる）を無視
      - export KEY=val 形式に対応
      - シングル/ダブルクォートを考慮した値のパース（バックスラッシュエスケープ対応）
      - クォートなし値の場合、インラインコメント判断は '#' の直前が空白またはタブの場合に限る（より自然なコメント扱い）
    - .env ファイル読み込み関数（_load_env_file）
      - ファイル読み込みエラー時に warnings.warn で警告を発する
      - override フラグと protected キー集合により上書きルールを制御
    - Settings クラスを公開（settings = Settings()）
      - J-Quants / kabuステーション / Slack / データベース / システム設定などのプロパティを提供
      - 必須環境変数未設定時は ValueError を送出（_require）
      - デフォルト値:
        - KABUSYS_API_BASE_URL のデフォルト: "http://localhost:18080/kabusapi"
        - DUCKDB_PATH のデフォルト: "data/kabusys.duckdb"
        - SQLITE_PATH のデフォルト: "data/monitoring.db"
        - KABUSYS_ENV のデフォルト: "development"（有効値: development, paper_trading, live）
        - LOG_LEVEL のデフォルト: "INFO"（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
      - ユーティリティプロパティ: is_live, is_paper, is_dev
  - DuckDB スキーマ定義（kabusys.data.schema）
    - 3層（Raw / Processed / Feature）＋ Execution レイヤーのテーブル定義を追加
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに適切な型チェック制約・PRIMARY KEY・FOREIGN KEY を設定（例: price>=0, size>0, side の CHECK 等）
    - インデックスを複数定義し、典型的なクエリパターン（銘柄×日付検索、ステータス検索等）に最適化
    - 公開 API:
      - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - 指定したパスに対してスキーマを作成（冪等）。":memory:" に対応。
        - db_path の親ディレクトリが存在しない場合は自動作成。
      - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - 既存 DB への接続を返す（スキーマ初期化は行わない）。初回は init_schema を呼ぶことを推奨。
  - その他
    - .env 読み込みで存在しないファイルは静かにスキップ
    - エラー発生時に詳細なメッセージを出す設計（環境変数未設定や不正値時の ValueError 等）

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

注記 / マイグレーション
- 初回起動時は init_schema() を呼んで DuckDB スキーマを作成してください。
- 環境変数の取り扱いに注意:
  - 機密情報（API トークン等）は OS 環境変数で設定しておくことを推奨（.env ファイルより優先され、.env.local の上書きから保護されます）。
  - 自動ロードを無効化したいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。