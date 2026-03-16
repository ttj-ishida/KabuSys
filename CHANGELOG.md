CHANGELOG
=========

フォーマットは "Keep a Changelog" に準拠しています。
タグ付けは semver に従います。

Unreleased
----------

- なし

0.1.0 - 2026-03-16
------------------

Added
- 全体
  - 初回リリース。パッケージ名: kabusys、バージョン 0.1.0。
  - パッケージ公開インターフェース: data, strategy, execution, monitoring を __all__ で公開（strategy と execution は現時点では初期化ファイルのみのスタブ）。

- 環境設定 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートの検出は __file__ を基点に親ディレクトリを探索し、.git または pyproject.toml を基準として行うため CWD に依存しない。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途を想定）。
    - OS 環境変数は保護され、.env の上書きから除外される仕組みを導入。
  - .env パーサ実装の強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート対応、バックスラッシュによるエスケープ処理を考慮した値解析。
    - インラインコメント処理: クォート無しの場合は '#' の直前が空白／タブのときのみコメントと認識する等の細かい挙動。
  - Settings クラスを提供。主な設定項目（必須・デフォルト値を含む）:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を送出）
    - 任意 / デフォルト:
      - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
      - DUCKDB_PATH: デフォルト data/kabusys.duckdb
      - SQLITE_PATH: デフォルト data/monitoring.db
      - KABUSYS_ENV: 有効値 {development, paper_trading, live}（不正値は ValueError）
      - LOG_LEVEL: 有効値 {DEBUG, INFO, WARNING, ERROR, CRITICAL}（不正値は ValueError）
    - is_live / is_paper / is_dev のヘルパープロパティを提供。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - ベース URL: https://api.jquants.com/v1
    - レート制御: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
    - 再試行ロジック:
      - 最大 3 回のリトライ（指数バックオフ）。
      - 再試行対象ステータス: 408, 429, 5xx 系。
      - 429 の場合は Retry-After ヘッダを優先的に使用。
      - ネットワーク系エラー（URLError / OSError）の場合もリトライ。
    - 認証トークン (id_token) の自動リフレッシュ:
      - 401 を受けた場合はリフレッシュトークンで id_token を再取得して 1 回だけリトライ。
      - get_id_token は refresh_token を受け取り POST で /token/auth_refresh を呼ぶ。
      - モジュールレベルで id_token をキャッシュし、ページネーション間で共有。
  - データ取得 API（ページネーション対応）:
    - fetch_daily_quotes: 株価日足（OHLCV）取得。pagination_key を用いたページネーション処理。
    - fetch_financial_statements: 財務データ（四半期 BS/PL）取得。ページネーション対応。
    - fetch_market_calendar: JPX マーケットカレンダー取得。
  - DuckDB への保存関数（冪等: ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes: raw_prices テーブルへ保存、PK 欠損行はスキップ。fetched_at を UTC ISO 形式で記録。
    - save_financial_statements: raw_financials テーブルへ保存（code, report_date, period_type を PK とする）。
    - save_market_calendar: market_calendar テーブルへ保存。HolidayDivision を解釈して is_trading_day / is_half_day / is_sq_day を設定。
  - ユーティリティ変換:
    - _to_float / _to_int: 空値や不正値を None にする堅牢な変換ロジック。_to_int は "1.0" 等を float 経由で変換するが、小数部が非ゼロの場合は None を返す。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用の包括的スキーマを定義（Raw / Processed / Feature / Execution 層）。
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature 層: features, ai_scores
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種インデックスを定義（典型的なクエリパターンを想定）。
  - init_schema(db_path) を提供:
    - db_path の親ディレクトリを自動作成（":memory:" を除く）。
    - 全DDL とインデックスを実行してテーブルを冪等に作成。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL 設計に基づく日次パイプラインを実装。
    - 処理フロー: カレンダーETL → 株価ETL（差分＋バックフィル）→ 財務ETL（差分＋バックフィル）→ 品質チェック（任意）
    - 差分更新ロジック:
      - raw テーブルの最終取得日を参照して未取得分のみ取得。
      - 初回ロードは _MIN_DATA_DATE = 2017-01-01 を使用。
      - デフォルトの backfill_days = 3（最終取得日の数日前から再取得して API の後出し修正を吸収）。
    - カレンダー先読み: デフォルト lookahead_days = 90（日付の調整に使用）。
  - run_prices_etl / run_financials_etl / run_calendar_etl を個別に実行可能。
  - run_daily_etl を提供（結果は ETLResult オブジェクトで返却）。
    - ETLResult は取得件数・保存件数・品質問題・エラー一覧等を保持。
    - 各ステップは独立して例外処理され、1 ステップの失敗が全体を停止させない設計（Fail-Fast ではない）。
    - 品質チェックはデフォルトで有効（spike_threshold の調整可能）。

- データ品質チェック (kabusys.data.quality)
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欄の欠損検出（サンプル最大 10 件を返す）。欠損は重大度 "error" として扱う。
    - check_spike: 前日比のスパイク検出（デフォルト閾値 50%）。
      - LAG ウィンドウ関数で前日 close を取得し、閾値超の変動を検出。
  - 各チェックは問題のリストを返し、呼び出し元が重大度に応じて処理を判断できる（ETL 停止/ログ等）。

- 監査ログ・トレーサビリティ (kabusys.data.audit)
  - 戦略→シグナル→発注要求→約定 のトレーサビリティを確保する監査用テーブル群を実装。
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求ログ、order_request_id を冪等キーとして利用）
    - executions（約定ログ、broker_execution_id をユニークな外部冪等キーとして扱う）
  - init_audit_schema(conn) で監査テーブルとインデックスを追加。UTC タイムゾーンを強制 (SET TimeZone='UTC')。
  - init_audit_db(db_path) で監査専用 DB を初期化して接続を返す。

Changed
- 初回リリースにつき該当なし。

Fixed
- 初回リリースにつき該当なし。

Notes / 備考
- strategy および execution パッケージは初期化モジュールが存在するのみで、実際の戦略実装や発注ロジックはまだ実装されていません。監査や ETL、データ基盤は整備済みのため、これらを利用して戦略・実行ロジックを組み込むことを想定しています。
- DuckDB のテーブル定義や制約は厳格に設定してあり、データ品質チェックや ETL の冪等性（ON CONFLICT DO UPDATE）を前提とした設計です。
- J-Quants API の利用には有効なリフレッシュトークン (JQUANTS_REFRESH_TOKEN) が必要です。トークンの管理は settings を通じて行ってください。
- .env のパース挙動（コメントやクォートの扱いなど）は一般的な shell 形式に近い挙動を目指していますが、特殊なエッジケースは注意が必要です。

今後の予定（例）
- strategy 層に標準的な戦略テンプレート・バックテスト用ユーティリティを追加。
- execution 層（ブローカー連携）の具体的実装（kabu API など）の追加。
- 品質チェックの拡張（重複チェック・将来日付チェック等の追加）。
- 監査ログの可視化／集計ツールの提供。