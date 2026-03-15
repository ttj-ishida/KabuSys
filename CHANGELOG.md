# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

※ この CHANGELOG はソースコードから推測して作成した初期リリース記録です。

## [Unreleased]

## [0.1.0] - 2026-03-15
最初の公開リリース。日本株自動売買システムのコア設定・スキーマ・初期化ロジックを含みます。

### Added
- パッケージ初期化
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - パブリックサブパッケージ: data, strategy, execution, monitoring を __all__ に定義。

- 環境変数・設定管理モジュール（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を追加。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行うため、CWD に依存しない。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - OS 環境変数は保護され（上書き禁止）、.env.local は .env の上書きを許可。
  - .env パーサーを実装
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート対応（バックスラッシュエスケープを考慮）。クォートが閉じられた以降のインラインコメントは無視。
    - クォートなしの場合、 '#' がスペースまたはタブ直前にある場合のみコメントと認識する細かな挙動。
    - 無効行（空行、コメント行、= がない行）を無視する。
  - 設定取得用 Settings クラスを提供（単一インスタンス settings をエクスポート）
    - J-Quants / kabu ステーション / Slack / DB / システム設定用プロパティを定義:
      - jquants_refresh_token (必須: JQUANTS_REFRESH_TOKEN)
      - kabu_api_password (必須: KABU_API_PASSWORD)
      - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
      - slack_bot_token (必須: SLACK_BOT_TOKEN)
      - slack_channel_id (必須: SLACK_CHANNEL_ID)
      - duckdb_path (デフォルト: data/kabusys.duckdb)
      - sqlite_path (デフォルト: data/monitoring.db)
      - env (KABUSYS_ENV: development | paper_trading | live。値チェック有り)
      - log_level (LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL。値チェック有り)
      - 補助プロパティ: is_live / is_paper / is_dev
    - 必須環境変数が未設定の場合法的に ValueError を送出する _require 実装。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - 3層構造（Raw / Processed / Feature）＋ Execution 層のテーブル定義を追加。
  - 主なテーブル（代表例、詳細はソース参照）:
    - Raw Layer:
      - raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer:
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer:
      - features, ai_scores
    - Execution Layer:
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェック制約（NULL制約、CHECK 制約、主キー、外部キー）を付与。
  - 典型的なクエリパターンを想定したインデックスを作成:
    - 例: idx_prices_daily_code_date, idx_features_code_date, idx_signal_queue_status, idx_orders_status など。
  - スキーマ初期化 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - DB ファイルの親ディレクトリを自動作成（:memory: をサポート）。
      - 全テーブル・インデックスを作成（冪等）。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化はしない。初回は init_schema を推奨）。

- サブパッケージプレースホルダ
  - src/kabusys/execution/__init__.py、src/kabusys/strategy/__init__.py、src/kabusys/data/__init__.py、src/kabusys/monitoring/__init__.py を追加（パッケージ構造の準備）。

### Security
- .env の自動読み込み時に OS 環境変数を上書きしない既定の挙動により、CI/本番環境の環境変数を保護。
- 必須トークン類（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）は明示的に必須として ValueError を発生させ、未設定での誤動作を防止。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

今後のリリースでは、strategy / execution / monitoring の具体実装、マイグレーション、テストカバレッジ、ドキュメント補完を追加していく予定です。