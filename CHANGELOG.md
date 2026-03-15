# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の方針に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-15

初期リリース

### Added
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - __all__ に data, strategy, execution, monitoring を公開

- 環境変数・設定管理モジュールを追加 (src/kabusys/config.py)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートの探索は __file__ を起点に行い、.git または pyproject.toml を検出してルートを特定（CWD に依存しない挙動）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途想定）
    - OS 側に既に存在する環境変数は保護され、.env の読み込み時に上書きされない（.env.local は override=true だが protected に含まれるキーは上書きされない）
  - .env パーサ実装（_parse_env_line）
    - 空行・コメント行（# で始まる行）を無視
    - "export KEY=val" 形式に対応
    - クォートされた値に対してバックスラッシュによるエスケープを処理し、対応する閉じクォートまでを値として扱う（インラインコメントは無視）
    - クォートなし値では、'#' が先頭または直前がスペース/タブの場合に以降をコメントとして扱う
  - Settings クラスを提供（settings = Settings() によりインスタンス化）
    - J-Quants / kabu ステーション / Slack / データベース / システム設定用プロパティを公開
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は未設定時に ValueError を送出（必須）
      - KABU_API_BASE_URL のデフォルトは "http://localhost:18080/kabusapi"
      - データベースパスのデフォルト:
        - DUCKDB_PATH: data/kabusys.duckdb
        - SQLITE_PATH: data/monitoring.db
      - KABUSYS_ENV の検証（許容値: development, paper_trading, live）
      - LOG_LEVEL の検証（許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
      - is_live / is_paper / is_dev のユーティリティプロパティ

- DuckDB スキーマ定義と初期化モジュールを追加 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋ Execution 層を想定したテーブル群の DDL を定義
  - 主なテーブル（抜粋）
    - Raw Layer:
      - raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at) — 主キー (date, code)
      - raw_financials (code, report_date, period_type, revenue, ...) — 主キー (code, report_date, period_type)
      - raw_news (id, datetime, source, title, content, url, fetched_at)
      - raw_executions (execution_id, order_id, datetime, code, side, price, size, fetched_at)
    - Processed Layer:
      - prices_daily (date, code, open, high, low, close, volume, turnover) — 主キー (date, code)
      - market_calendar (date, is_trading_day, is_half_day, is_sq_day, holiday_name)
      - fundamentals (code, report_date, period_type, ...)
      - news_articles / news_symbols（news_symbols は news_articles.id を外部キーに持ち ON DELETE CASCADE）
    - Feature Layer:
      - features (date, code, momentum_20, momentum_60, volatility_20, ...)
      - ai_scores (date, code, sentiment_score, regime_score, ai_score, ...)
    - Execution Layer:
      - signals (date, code, side, score, signal_rank) — side は ('buy','sell') の CHECK 制約
      - signal_queue (signal_id, date, code, side, size, order_type, price, status, created_at, processed_at)
        - order_type は ('market','limit','stop')
        - status は ('pending','processing','filled','cancelled','error')
      - portfolio_targets, orders, trades, positions, portfolio_performance
      - orders.signal_id -> signal_queue(signal_id) は ON DELETE SET NULL、trades.order_id -> orders(order_id) は ON DELETE CASCADE
  - 各カラムに対する CHECK 制約（負の値禁止、サイズ正数等）を多く盛り込んでいる
  - インデックス定義を追加（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status など）
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定したパスに対してディレクトリを自動作成（":memory:" 指定時はインメモリ DB）
      - 全テーブルとインデックスを作成（冪等）
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB に接続（スキーマ初期化は行わない。初回は init_schema を推奨）

- モジュールプレースホルダを追加
  - src/kabusys/data/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/monitoring/__init__.py
  - （将来的な機能拡張のためのパッケージ構成を用意）

### Changed
- なし

### Fixed
- なし

### Removed
- なし

---

補足・利用例
- 簡単な初期化例:
  - settings を使って duckdb を初期化:
    - from kabusys.config import settings
    - from kabusys.data.schema import init_schema
    - conn = init_schema(settings.duckdb_path)
- .env ロードの挙動に注意:
  - OS 環境変数はデフォルトで保護され、.env / .env.local で上書きされない（ただし .env.local の方が .env より優先）
  - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定

このリリースは基盤構造（設定管理、データベーススキーマ、パッケージ骨格）を提供するものです。今後は各レイヤー（データ取得、特徴量作成、戦略実装、発注実行、監視）の実装を順次追加していく予定です。