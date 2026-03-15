# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog 準拠です。  

※ バージョン番号はパッケージ内の __version__ に準拠しています。

## [0.1.0] - 2026-03-15

### Added
- 初回リリース。パッケージ名: kabusys（src/kabusys）
  - パッケージ情報とエクスポートを定義
    - バージョン: 0.1.0（src/kabusys/__init__.py）
    - __all__ に data, strategy, execution, monitoring を登録

- 環境変数／設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動読み込み機能を実装
    - 自動読み込みの優先順位: OS環境変数 > .env.local > .env
    - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索する _find_project_root()
  - .env パーサーを実装（_parse_env_line）
    - export KEY=val 形式をサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応
    - クォートなし値の行内コメント（#）の扱いは直前が空白／タブの場合のみコメントとして扱う等の挙動
  - .env ファイル読み込み（_load_env_file）
    - override フラグと protected（OS環境変数等の上書き防止）パラメータをサポート
    - ファイル読み込み失敗時は警告を発行して処理を続行
  - 必須環境変数の取得ヘルパー（_require）を実装。未設定時は ValueError を送出
  - Settings クラスを提供（settings インスタンスを公開）
    - J-Quants / kabuステーション / Slack / データベース／システム設定のプロパティを提供
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（許容値: development, paper_trading, live）と判定補助 is_dev/is_paper/is_live
      - LOG_LEVEL（許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - 値検証（不正な env/log level の場合は例外を送出）

- DuckDB スキーマ定義・初期化モジュールを追加（src/kabusys/data/schema.py）
  - 3層構造（Raw / Processed / Feature）および Execution 層のテーブルを定義
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して型・CHECK 制約・主キー・外部キー制約を設定（入力整合性を確保）
    - 例: side フィールドの CHECK、価格/サイズに対する非負チェック、news_symbols の外部キー制約（ON DELETE CASCADE）など
  - よく使うクエリ向けのインデックス定義を追加（code/date 検索やステータス検索など）
  - init_schema(db_path) を提供
    - DuckDB ファイルの親ディレクトリを自動作成
    - DDL を順序に沿って実行（外部キー依存を考慮）
    - 冪等（既存テーブルはスキップ）
    - ":memory:" を指定してインメモリ DB を使用可能
    - 初期化後に duckdb 接続オブジェクトを返す
  - get_connection(db_path) を提供（スキーマ初期化は行わず接続だけ返す）

- パッケージ構成ファイルを追加（空のサブパッケージ初期化ファイル）
  - src/kabusys/data/__init__.py、src/kabusys/execution/__init__.py、src/kabusys/strategy/__init__.py、src/kabusys/monitoring/__init__.py（将来の拡張ポイント）

### Fixed
- （該当なし）初回リリースのため既知の修正はなし

### Changed
- （該当なし）初回リリースのため既存挙動の変更はなし

### Security
- .env 読み込み時に OS 環境変数を protected として上書きを防止する仕組みを導入（_load_env_file の protected）
- .env ファイル読み込み失敗時は例外を投げず警告に留める（意図しない例外による起動停止を防ぐ）

### Notes / 備考
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後やテスト時に挙動を変えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DB のデフォルトパスは相対パス（data/…）になっているため、本番運用では設定を明示的に上書きすることを推奨します。
- 今後のリリースで strategy / execution / monitoring の具体的実装やマイグレーション機能、より詳細なバリデーション等を追加予定です。