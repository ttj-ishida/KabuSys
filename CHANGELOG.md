# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-15

Added
- 初回リリース v0.1.0 を追加。
- パッケージ初期化:
  - src/kabusys/__init__.py にパッケージ名・バージョン (`__version__ = "0.1.0"`) と公開サブパッケージ一覧 (`__all__ = ["data", "strategy", "execution", "monitoring"]`) を追加。
- 環境設定管理:
  - src/kabusys/config.py を追加。
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索して自動で .env / .env.local を読み込む。
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって自動ロードを無効化可能。
    - .env → .env.local の優先度により .env.local が上書き（ただし既存の OS 環境変数は保護される）。
    - .env ファイル読み込み失敗時は例外を投げず warnings.warn による警告で処理。
  - .env パーサーの強化:
    - 空行・コメント行や `export KEY=val` 形式に対応。
    - シングル／ダブルクォート内のエスケープ（バックスラッシュ）を考慮した値抽出。
    - クォートなしの行におけるインラインコメントの扱い（直前が空白/タブの場合のみコメントとして扱う）。
  - Settings のプロパティとして主要設定を提供（要求時に環境変数が未設定だと ValueError を送出）:
    - J-Quants / kabuステーション / Slack の必須トークン設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）。
    - KABU_API_BASE_URL のデフォルト値 ("http://localhost:18080/kabusapi")。
    - データベースパスのデフォルト（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）を Path 型で取得可能。
    - KABUSYS_ENV（development / paper_trading / live） と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証。
    - 環境判定ユーティリティ（is_live / is_paper / is_dev）。
- DuckDB スキーマ定義・初期化:
  - src/kabusys/data/schema.py を追加。
  - データレイヤ設計（Raw / Processed / Feature / Execution）に基づくテーブル群を定義：
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な制約を付与（PRIMARY KEY、FOREIGN KEY、チェック制約 CHECK など）し、データ整合性を強化。
  - 各テーブルの作成DDLを列挙し、依存関係を考慮した作成順を保持。
  - 頻出のクエリパターンに対するインデックスを作成（例: prices_daily(code, date)、features(code, date)、signal_queue(status) 等）。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定した DuckDB ファイルを初期化（冪等）。親ディレクトリがなければ自動作成。
      - ":memory:" を指定するとインメモリ DB を使用可能。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への単純接続を返す（スキーマ初期化は行わない）。
- パッケージ構造:
  - 空のパッケージ初期化ファイルを追加（execution, strategy, data, monitoring の __init__.py）。将来の機能拡張のための基盤を用意。
- 実装上の配慮:
  - .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。
  - .env パースの堅牢化（エスケープ、クォート、コメントルール）。
  - DuckDB 初期化は接続コンテキスト内で DDL とインデックスを実行し、エラー発生時も副作用を最小にする設計。

Changed
- （初回リリースにつき変更なし）

Fixed
- （初回リリースにつき修正なし）

Removed
- （初回リリースにつき削除なし）

注記
- DuckDB を利用するため duckdb パッケージが必要です。
- .env の仕様は一般的な shell 形式に近いものの、すべての corner case を網羅するものではありません。必要に応じて .env の書式を .env.example などで明示してください。