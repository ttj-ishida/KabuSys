# CHANGELOG

すべての重要な変更を記録します。本プロジェクトでは「Keep a Changelog」の慣習に従い、後方互換性のある API 変更・追加・バグ修正等をカテゴリ別にまとめています。

フォーマット:
- すべての変更はリリース単位で時系列に記載します。
- 各リリースは Added / Changed / Fixed / Security 等に分類します。

## [0.1.0] - 2026-03-16

初回公開。日本株自動売買プラットフォームのコアライブラリを追加。

### Added
- パッケージの基本
  - パッケージ名: kabusys。トップレベルで data, strategy, execution, monitoring をエクスポートする __init__ を追加。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルートの探索は __file__ を起点に親ディレクトリを辿り、.git または pyproject.toml を基準に判定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
    - OS 環境変数を保護するため protected セットを利用し、.env.local での上書きも制御。
  - .env パーサを実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理を実施し、インラインコメントを無視。
    - クォートなし値では、'#' が直前に空白またはタブがある場合のみコメントとして扱う。
  - Settings クラスを提供し、以下の必須/デフォルト設定にアクセス可能:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を送出）
    - DB パスのデフォルト: DUCKDB_PATH = data/kabusys.duckdb、SQLITE_PATH = data/monitoring.db
    - KABUSYS_ENV のバリデーション（development/paper_trading/live）
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパープロパティ

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants API から株価日足、四半期財務データ、JPX マーケットカレンダーを取得するクライアントを実装。
  - 機能:
    - レート制限対応（120 req/min）: 固定間隔スロットリングを行う _RateLimiter を実装。
    - ページネーション対応: fetch_* 関数は pagination_key を追跡して全ページを取得。
    - 冪等保存サポートを想定した保存関数（save_*）を実装（後述の DuckDB 側 ON CONFLICT を利用）。
    - リトライロジック: 指数バックオフで最大 3 回リトライ（対象: 408/429/5xx、429 では Retry-After を考慮）。
    - 401 エラー時の自動トークンリフレッシュ（1 回まで）を実装。id_token キャッシュをモジュールレベルで共有（ページネーション間で再利用）。
    - JSON レスポンスのデコードエラーハンドリングと適切な例外化。
    - fetched_at（UTC）を付与して Look-ahead Bias を防止できる設計。
  - 公開 API:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
    - save_daily_quotes(conn, records) -> int
    - save_financial_statements(conn, records) -> int
    - save_market_calendar(conn, records) -> int
  - 型安全／データクリーニング用ユーティリティ: _to_float, _to_int（特に "1.0" 形式や小数部がある数値の扱いに注意）。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）+ Execution Layer のテーブル定義を実装。
  - 代表的なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・制約（CHECK / PRIMARY KEY / FOREIGN KEY）を設置。
  - 冪等性を前提とした初期化（CREATE TABLE IF NOT EXISTS）。
  - 頻出クエリに対するインデックス定義を追加（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - 公開 API:
    - init_schema(db_path) -> DuckDB 接続（必要に応じて親ディレクトリを自動作成）
    - get_connection(db_path) -> DuckDB 接続（スキーマ初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL パイプラインを実装（DataPlatform.md の設計に準拠）。
  - 処理フロー:
    1. 市場カレンダー ETL（先読み: デフォルト 90 日）
    2. 株価日足 ETL（差分 + デフォルトバックフィル 3 日）
    3. 財務データ ETL（差分 + バックフィル）
    4. 品質チェック（オプション）
  - 差分更新ヘルパー:
    - DB の最終取得日を参照して自動で date_from を算出（初回は 2017-01-01 から取得）。
    - backfill_days により過去数日を再取得して API の後出し修正を吸収。
    - 市場営業日の調整: market_calendar 取得後に target_date を直近営業日に調整する _adjust_to_trading_day。
  - ETLResult dataclass を追加し、実行結果（取得数・保存数・品質問題リスト・エラー）をまとめて返却。
  - 個別 ETL ジョブ API:
    - run_prices_etl(conn, target_date, ...)
    - run_financials_etl(conn, target_date, ...)
    - run_calendar_etl(conn, target_date, ...)
    - run_daily_etl(conn, target_date=None, run_quality_checks=True, ...)
  - 各ステップは独立して例外処理し、1 ステップ失敗でも他を継続する（全件収集型のエラーハンドリング）。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - シグナル→発注→約定までを UUID ベースで完全にトレース可能な監査スキーマを追加。
  - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）を想定。
  - 主なテーブル:
    - signal_events（シグナル生成ログ。戦略で棄却されたものも含む）
    - order_requests（発注要求。order_request_id を冪等キーとして扱う。limit/stop のチェック制約を追加）
    - executions（証券会社からの約定ログ。broker_execution_id をユニーク冪等キーとして扱う）
  - すべての TIMESTAMP は UTC で保存するため init_audit_schema() で SET TimeZone='UTC' を実行。
  - インデックスを用意して運用上の検索を高速化。
  - 公開 API:
    - init_audit_schema(conn)
    - init_audit_db(db_path) -> DuckDB 接続

- データ品質チェック (kabusys.data.quality)
  - DataPlatform.md に基づく品質チェックを実装。
  - チェック項目:
    - 欠損データ検出 (raw_prices の OHLC 欄)
    - 異常値（スパイク）検出（前日比絶対値 > 閾値、デフォルト 50%）
    - 重複チェック（主キー重複） — 実装方針あり（クエリベース）
    - 日付不整合検出（将来日付や営業日外）
  - QualityIssue dataclass を定義し、check_name / table / severity / detail / rows を返す。
  - 個別チェック関数を DuckDB 接続に対して SQL で実行し、問題があればサンプル行を最大 10 件返却。
  - run_all_checks を通じて pipeline から呼び出し可能（ETL の品質判定に利用）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- 機密情報取り扱いに関する注意点を実装レベルで考慮:
  - 環境変数の自動読み込みで OS 環境変数を保護する protected セットを利用。
  - 認証トークンは環境変数経由で取得し、取得時に ValueError を発することで明示的な設定を要求。

---

注:
- 各 save_* 関数は DuckDB 側の ON CONFLICT DO UPDATE を前提とした設計になっており、冪等性が確保されています。
- 実運用では J-Quants の API レート制限（120 req/min）や証券会社 API の実装ルールに従って運用してください。
- 既知の未実装点（将来的な追加項目の例）:
  - strategy/.execution/.monitoring パッケージの具体的な戦略・発注実装は現時点では空の __init__ のみ（今後の拡張を予定）。

この CHANGELOG はコードベースからの推定に基づいて作成しています。追加のリリースや修正が発生した場合はこのファイルを更新してください。