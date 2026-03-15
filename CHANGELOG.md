CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

（現在差分はありません）

[0.1.0] - 2026-03-15
-------------------

初回リリース。

Added
- パッケージの初期化
  - src/kabusys/__init__.py にパッケージメタ情報を追加
    - バージョン: 0.1.0
    - __all__ に "data", "strategy", "execution", "monitoring" を公開

- 環境変数／設定管理モジュール（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を取得する Settings クラスを実装
    - 必須キーを取得する _require()（未設定時は ValueError を送出し .env.example を参照する旨のメッセージを含む）
    - プロパティ群（例）
      - jquants_refresh_token (JQUANTS_REFRESH_TOKEN)
      - kabu_api_password (KABU_API_PASSWORD)
      - kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
      - slack_bot_token (SLACK_BOT_TOKEN)
      - slack_channel_id (SLACK_CHANNEL_ID)
      - duckdb_path（デフォルト: data/kabusys.duckdb）
      - sqlite_path（デフォルト: data/monitoring.db）
      - env（KABUSYS_ENV、許容値: development, paper_trading, live）
      - log_level（LOG_LEVEL、許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
      - is_live / is_paper / is_dev のヘルパープロパティ
  - 自動 .env ロード機能
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD 非依存）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - OS 環境変数は保護され、.env の上書きを防ぐ（.env.local は override=True で上書き可能。ただし保護されたキーは上書きされない）
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ実装（_parse_env_line）
    - export KEY=val 形式をサポート
    - シングル/ダブルクォートに対応し、バックスラッシュによるエスケープを処理
    - クォートなし値に対するコメント処理: '#' は前がスペースまたはタブの場合にコメントとして扱う

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Data Lake/Analytics 用の三層構造テーブル群を定義・初期化する DDL を実装
    - Raw Layer
      - raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer
      - features, ai_scores
    - Execution Layer
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切なデータ型・制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）を設定
    - 例: prices_daily の low <= high 制約、raw_executions の side 制約 (buy/sell)、signal_queue の status 制約 等
  - インデックス定義（頻出クエリ向け）
    - idx_prices_daily_code_date, idx_features_code_date, idx_ai_scores_code_date, idx_signal_queue_status, idx_orders_status など
  - 初期化 API
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定したパスの親ディレクトリを自動作成
      - ":memory:" を指定するとインメモリ DB を利用
      - 全テーブルとインデックスを冪等に作成
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB へ接続（スキーマ初期化は行わない）

- パッケージ構造のプレースホルダ
  - src/kabusys/execution/__init__.py、src/kabusys/strategy/__init__.py、src/kabusys/data/__init__.py、src/kabusys/monitoring/__init__.py を配置（将来的な実装領域）

Changed
- （該当なし：初回リリース）

Fixed
- （該当なし：初回リリース）

Deprecated
- （該当なし：初回リリース）

Removed
- （該当なし：初回リリース）

Security
- 環境変数の自動上書きを防ぐため、OS の環境変数を保護する仕組みを実装

Notes / 今後の改善候補
- .env パーサの追加ユースケース（複雑なネストや複数行クォート等）への対応や、既存実装の単体テスト整備
- 機密情報（トークン等）の取り扱い向上（キー暗号化やシークレットマネージャ連携）
- データベースマイグレーション管理（バージョン管理ツール）を導入してスキーマ変更を安全に行う仕組みの追加
- strategy / execution / monitoring サブパッケージの実装（注文発注ロジック、戦略エンジン、モニタリング機能）

参考
- 必須環境変数の例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 無効な KABUSYS_ENV や LOG_LEVEL は ValueError を発生させ、使用可能な値を示します。