# Changelog

すべての重要な変更点はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。

最新リリース
- 0.1.0 - 2026-03-15

### Added
- パッケージ初期リリース (kabusys v0.1.0)
  - src/kabusys/__init__.py
    - パッケージメタ情報を追加: __version__ = "0.1.0"
    - __all__ を定義し、公開サブパッケージとして data, strategy, execution, monitoring を明示
  - 環境変数・設定管理モジュールを追加 (src/kabusys/config.py)
    - Settings クラスを実装し、アプリケーション設定を環境変数から提供する単一インスタンス settings を公開
    - 必須環境変数取得のヘルパー _require を実装（未設定時は ValueError を送出）
    - 以下の主要プロパティを提供:
      - jquants_refresh_token (JQUANTS_REFRESH_TOKEN を必須)
      - kabu_api_password (KABU_API_PASSWORD を必須)
      - kabu_api_base_url (デフォルト: "http://localhost:18080/kabusapi")
      - slack_bot_token, slack_channel_id (それぞれ必須)
      - duckdb_path (デフォルト: data/kabusys.duckdb)、sqlite_path (デフォルト: data/monitoring.db)
      - env (KABUSYS_ENV; 有効値: development, paper_trading, live。デフォルト: development)
      - log_level (LOG_LEVEL; 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO)
      - is_live / is_paper / is_dev ブールプロパティ
    - .env 読み込み機能:
      - 自動ロードの仕組みを実装（パッケージルートを .git または pyproject.toml から検出して .env / .env.local を読み込む）
      - 読み込み優先順位: OS環境変数 > .env.local > .env
      - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
      - OS側の既存環境変数を保護する機構（protected set を利用して .env.local の上書きを制御）
      - .env パースの堅牢化:
        - export KEY=val 形式に対応
        - シングル/ダブルクォート対応、バックスラッシュによるエスケープ処理、内部の # を含む場合の取り扱い等
        - 無効行やコメント行 (# で始まる行) の無視
      - .env ファイル読み込み失敗時は警告を発する（例外は抑制）
  - DuckDB スキーマ定義と初期化モジュールを追加 (src/kabusys/data/schema.py)
    - データレイヤを想定したスキーマ設計（ドキュメント DataSchema.md 想定）
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに対して列型、チェック制約、主キー、外部キーなどを定義
    - パフォーマンスを考慮したインデックスを複数定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）
    - 公開 API:
      - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - 指定パスの DuckDB を初期化（親ディレクトリ自動作成、DDL を順番に実行、冪等）
        - ":memory:" をサポート
      - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
        - 既存 DB へ接続（初期化は行わない旨の明記）
  - パッケージ構成ファイル（空のパッケージ初期化ファイルを配置）
    - src/kabusys/data/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/strategy/__init__.py
    - src/kabusys/monitoring/__init__.py
    - これによりサブパッケージの拡張・実装が可能な骨組みを提供

### Changed
- 初版のため該当なし

### Fixed
- 初版のため該当なし

### Deprecated
- 初版のため該当なし

### Removed
- 初版のため該当なし

### Security
- 初版のため該当なし

注記
- .env の自動読み込みはプロジェクトルートの検出に基づくため、配布後やテスト時に挙動を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- settings の必須キーが未設定の場合、ValueError が発生します。デフォルト値は README/.env.example 等を参照して設定してください。