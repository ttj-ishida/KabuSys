CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  
安定したリリースはセマンティックバージョニングに従います。

Unreleased
----------

（なし）

0.1.0 - 2026-03-15
------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージ公開情報:
    - __version__ = "0.1.0"
    - __all__ = ["data", "strategy", "execution", "monitoring"]
- 環境設定管理モジュール (kabusys.config)
  - .env / .env.local からの自動読み込み機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索する _find_project_root() を採用し、CWD に依存しない仕様。
    - 自動読み込みの無効化フラグ: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードをスキップ可能。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - .env パーサーの実装 (_parse_env_line):
    - 空行・コメント行（先頭に #）を無視。
    - export KEY=val 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープを処理し、対応する閉じクォートまでを値として扱う。
    - クォート無しの値では、'#' が直前にスペースまたはタブある場合をコメント開始とみなす（インラインコメント処理）。
  - .env 読み込みロジック (_load_env_file):
    - override / protected オプションにより OS 環境変数保護や上書き制御が可能。
    - ファイル読み込み失敗時に警告を出力。
  - 設定抽象 (Settings クラス, settings シングルトン)
    - 必須環境変数取得のヘルパー _require()。
    - J-Quants / kabu ステーション / Slack / データベース 等のプロパティを提供:
      - jquants_refresh_token, kabu_api_password, kabu_api_base_url (デフォルト値あり),
      - slack_bot_token, slack_channel_id,
      - duckdb_path (デフォルト data/kabusys.duckdb), sqlite_path (デフォルト data/monitoring.db)
    - KABUSYS_ENV 値検証（development, paper_trading, live のみ許容）。
    - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev の利便性プロパティ。
- DuckDB ベースのスキーマ定義・初期化 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層／Execution 層を含むテーブル群を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して型チェック、CHECK 制約、主キー、外部キー（必要箇所）を付与。
  - 頻出クエリを想定したインデックスを作成（銘柄×日付、ステータス検索等）。
  - 初期化関数 init_schema(db_path) を提供:
    - テーブル作成は冪等（存在する場合はスキップ）。
    - db_path の親ディレクトリを自動作成。
    - ":memory:" を使用したインメモリ DB をサポート。
  - 既存 DB への接続取得用に get_connection(db_path) を提供（初期化は行わない）。
- 監査ログ（トレーサビリティ）モジュール (kabusys.data.audit)
  - DataPlatform.md に基づく監査テーブル群を実装し、シグナル→発注→約定までの UUID 連鎖でのトレースを可能にする設計。
  - テーブル:
    - signal_events: 戦略が生成したシグナルの全記録（リスクで棄却されたものも含む）。decision フィールドにより詳細な理由を保持。
    - order_requests: 発注要求ログ（order_request_id を冪等キーとして扱う）。order_type ごとの価格チェック（limit/stop の必須制約）を含む。
    - executions: 証券会社からの約定ログ。broker_execution_id をユニークにして約定の冪等性を担保。
  - 監査用インデックス群を用意（シグナル日付/銘柄、戦略別検索、status によるキュー検索、broker_order_id/broker_execution_id での紐付け等）。
  - 初期化 API:
    - init_audit_schema(conn): 既存の DuckDB 接続に監査テーブルを追加（SET TimeZone='UTC' を実行し TIMESTAMP を UTC で保存）。
    - init_audit_db(db_path): 監査専用 DB を作成して初期化（親ディレクトリ自動作成、":memory:" 対応）。
- ドキュメント文字列（モジュール内 docstring）により設計意図・利用上の注意を明記（DataSchema.md / DataPlatform.md を参照する旨）。

Changed
- （該当なし: 初回リリース）

Fixed
- （該当なし: 初回リリース）

Removed
- （該当なし: 初回リリース）

Security
- （該当なし）

Notes / Limitations
- strategy, execution, monitoring パッケージは __init__.py が存在するものの具体的な実装は含まれておらず、今後の実装が想定されます。
- DuckDB の制約やインデックスの挙動は DuckDB の仕様（例: UNIQUE における NULL 扱い）に依存します。README/設計文書の参照を推奨します。

Upgrade notes
- なし（初回リリース）

References
- 各モジュール内 docstring（DataSchema.md / DataPlatform.md に準拠）を参照してください。