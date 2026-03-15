# Changelog

すべての重要な変更点を記録します。慣例に従い、変更はカテゴリ別（Added, Changed, Fixed, …）で整理しています。

なお、本CHANGELOGは与えられたコードベースの内容から推測して作成しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-15
初回公開リリース。

### Added
- パッケージ基盤を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - サブモジュール（空の __init__ を含む）: data, strategy, execution, monitoring

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルや環境変数から設定を読み込む自動ロード機構を実装
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートの自動検出: .git または pyproject.toml を基準に探索（__file__ を起点）
    - 自動ロード無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能
    - OS 環境変数を保護するための上書き制御（.env と .env.local の挙動を区別）
  - .env パーサを実装（堅牢な解析）
    - 空行・コメント行（#）の無視
    - export KEY=val 形式に対応
    - クォートされた値のサポート（シングル/ダブルクォート、バックスラッシュによるエスケープ処理）
    - クォートなしの値では「#」の直前がスペース/タブの場合にコメントとして扱う（インラインコメント処理）
  - Settings クラスによるアプリ設定の公開プロパティ
    - J-Quants / kabu ステーション / Slack / データベースパス等の必須/任意設定をプロパティで取得
    - 必須の環境変数が未設定の場合は ValueError を送出する（_require）
    - デフォルト値:
      - KABU_API_BASE_URL: "http://localhost:18080/kabusapi"
      - DUCKDB_PATH: "data/kabusys.duckdb"
      - SQLITE_PATH: "data/monitoring.db"
      - KABUSYS_ENV のデフォルト: "development"
      - LOG_LEVEL のデフォルト: "INFO"
    - env と log_level の検証:
      - KABUSYS_ENV は {development, paper_trading, live}
      - LOG_LEVEL は {DEBUG, INFO, WARNING, ERROR, CRITICAL}
    - 環境判定ヘルパー: is_live, is_paper, is_dev

- DuckDB スキーマ定義・初期化モジュール（src/kabusys/data/schema.py）
  - データレイヤ構成（Raw / Processed / Feature / Execution）に基づくテーブル定義を追加
    - Raw レイヤ: raw_prices, raw_financials, raw_news, raw_executions
    - Processed レイヤ: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature レイヤ: features, ai_scores
    - Execution レイヤ: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対する制約（PRIMARY KEY、CHECK、外部キー制約）を定義
    - 価格/数量に対する非負チェック、注文/取引サイズの正数チェック、列の存在性チェックなど
    - 外部キーにより news_symbols → news_articles、orders → signal_queue、trades → orders 等の連動を定義
  - 利用頻度を想定したインデックスを定義（銘柄×日付検索、ステータス検索、外部キー参照等）
  - スキーマ初期化 API を提供
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定先に DuckDB ファイルを作成（必要なら親ディレクトリを自動作成）
      - 定義済みの全テーブル・インデックスを作成（冪等）
      - ":memory:" の指定でインメモリ DB を使用可能
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB へ接続（スキーマ初期化は行わない）
  - スキーマは DataSchema.md（コメント）に準拠した 3 層構造（Raw / Processed / Feature）+ Execution 層を想定

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Notes / 注意事項
- Settings の必須プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定だと ValueError を投げます。実運用前に .env か OS 環境変数を用いて設定してください。
- .env の自動読み込みはプロジェクトルートの検出に依存します。パッケージを配布した環境やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して自動ロードを抑止できます。
- DuckDB スキーマは外部キー制約や CHECK 制約を含みます。初回セットアップ時は init_schema() を呼び出してスキーマを作成してください。
- このCHANGELOGはコードベースの内容から推測して作成しています。実際の公開履歴やリリースノートと差異がある可能性があります。