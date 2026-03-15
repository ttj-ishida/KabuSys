Keep a Changelog
=================

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のフォーマットに従います。

0.1.0 - 2026-03-15
------------------

Added
- 初期リリース。基本パッケージ構成とコア機能を追加。
  - パッケージエントリポイント
    - kabusys/__init__.py を追加。バージョン情報 (__version__ = "0.1.0") と公開モジュール一覧 (__all__ = ["data", "strategy", "execution", "monitoring"]) を定義。
  - 環境変数・設定管理 (kabusys.config)
    - .env ファイルまたは既存の OS 環境変数から設定値を読み込む自動ロード機能を実装。
      - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - プロジェクトルートの検出は、パッケージ内の __file__ を基準に親ディレクトリを探索し、.git または pyproject.toml を基準に判定。作業ディレクトリ (CWD) に依存しない設計。
      - 読み込み順序: OS 環境変数 > .env.local (上書き) > .env（既存未設定のみ）。OS 環境変数は protected として扱われ、.env/.env.local で上書きされない。
      - .env のパースで以下に対応:
        - 空行・コメント行（# で始まる行）の無視。
        - export KEY=val 形式のサポート。
        - クォートされた値のバックスラッシュエスケープと対応する閉じクォートまでの正しい抽出。
        - 非クォート値におけるコメント扱いは、'#' の直前が空白またはタブの場合のみコメントとみなす（'#' を含む値を許容）。
      - .env ファイルの読み込みに失敗した場合は警告を発する（読み込み継続）。
    - Settings クラスにより、アプリケーション設定をプロパティで提供。
      - J-Quants、kabuステーション API、Slack、DB パスなど主要設定をプロパティとして露出:
        - jquants_refresh_token (必須: JQUANTS_REFRESH_TOKEN)
        - kabu_api_password (必須: KABU_API_PASSWORD)
        - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
        - slack_bot_token (必須: SLACK_BOT_TOKEN)
        - slack_channel_id (必須: SLACK_CHANNEL_ID)
        - duckdb_path (デフォルト: data/kabusys.duckdb)
        - sqlite_path (デフォルト: data/monitoring.db)
      - env (KABUSYS_ENV) のバリデーション: 有効値は "development", "paper_trading", "live"。不正値は ValueError。
      - log_level (LOG_LEVEL) のバリデーション: 有効値は "DEBUG","INFO","WARNING","ERROR","CRITICAL"。不正値は ValueError。
      - is_live / is_paper / is_dev の補助プロパティ。
      - _require 関数により必須環境変数未設定時は ValueError を返し、.env.example を参照するようメッセージを提示。
  - DuckDB スキーマ定義と初期化 (kabusys.data.schema)
    - DataSchema.md に基づく想定の多層テーブル定義を実装（Raw / Processed / Feature / Execution レイヤー）。
    - Raw Layer:
      - raw_prices, raw_financials, raw_news, raw_executions を定義（主キー・型・CHECK 制約あり）。
    - Processed Layer:
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols を定義。news_symbols は news_articles への外部キー (ON DELETE CASCADE) を設定。
    - Feature Layer:
      - features, ai_scores を定義（特徴量・AI スコア領域）。
    - Execution Layer:
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance を定義。
      - 外部キー制約と CHECK（side, order_type, status 等の許容値）を多数採用。
    - インデックス定義:
      - 銘柄×日付スキャンやステータス検索のためのインデックス群を用意（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
    - スキーマ初期化 API:
      - init_schema(db_path) を提供。DuckDB を接続し、全テーブルとインデックスを作成する（冪等）。db_path の親ディレクトリが存在しなければ自動作成。":memory:" を指定してインメモリ DB を使用可能。
      - get_connection(db_path) を提供。スキーマ初期化は行わず既存 DB へ接続のみ行う（初回は init_schema を推奨）。
    - テーブル作成順を外部キー依存を考慮して管理。
    - DDL 定義によりデータ整合性を確保するための詳細な CHECK 制約を採用（負数禁止、サイズ > 0 など）。
  - モジュール雛形
    - execution, strategy, monitoring のパッケージ雛形を追加（各 __init__.py は存在）。

Changed
- （初版のため変更なし）

Fixed
- （初版のため修正なし）

Security
- （初版のためセキュリティ項目なし）

Notes / 備考
- .env の詳細なパース挙動（クォート内のエスケープ処理やコメント判定）により、実運用での .env 設定の柔軟性を高めていますが、期待どおりの動作にならないケースがあれば .env の書式を見直してください。
- init_schema は既存テーブルがある場合でも冪等に実行されるため、起動時の初期化処理として安全に利用できます。get_connection はスキーマを保証しないため、初回起動時には init_schema を呼ぶことを推奨します。