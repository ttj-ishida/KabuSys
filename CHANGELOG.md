CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このプロジェクトは Keep a Changelog の慣習に概ね準拠しています。

[未リリース]
------------

- なし

[0.1.0] - 2026-03-16
--------------------

Added
- パッケージ初版をリリース。
- 基本パッケージ構成を追加
  - kabusys パッケージ、サブパッケージ: data, strategy, execution, monitoring（/__init__.py に __version__=0.1.0 を設定）。
- 環境変数・設定管理モジュール (kabusys.config)
  - .env/.env.local 自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env の行パーサ実装（コメント・export プレフィックス・シングル/ダブルクォート・エスケープ対応）。
  - 環境変数の必須チェック用 Settings クラスを提供（settings インスタンス）。
  - 各種設定プロパティを実装（J-Quants / kabu API / Slack / DB パス / 環境 / ログレベル判定 等）。
  - 有効値検証（KABUSYS_ENV, LOG_LEVEL）とユーティリティプロパティ（is_live / is_paper / is_dev）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - get_id_token(): リフレッシュトークンから idToken を取得（POST /token/auth_refresh）。
  - fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar(): ページネーション対応でのデータ取得。
  - サーバー/ネットワークエラーに対するリトライ（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダ優先。
  - 401 受信時はトークンを自動リフレッシュして 1 回のみリトライ（無限再帰防止）。
  - API レート制限 (120 req/min) を固定間隔スロットリングで遵守する RateLimiter 実装。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias のトレーサビリティを確保。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性確保。
  - 数値変換ユーティリティ（_to_float, _to_int）を実装。空値/不正値を安全に None に変換。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - 3 層＋実行層に対応したスキーマ DDL を定義（Raw / Processed / Feature / Execution）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル群を定義。
  - prices_daily, market_calendar, fundamentals, news_articles 等の Processed テーブルを定義。
  - features, ai_scores 等の Feature テーブルを定義。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブルを定義。
  - 実運用を想定したインデックス定義を追加（頻繁に使われるクエリパターン向け）。
  - init_schema(db_path) でディレクトリの自動作成とテーブル初期化（冪等）を実行。get_connection() も提供。

- 監査ログ（トレーサビリティ）(kabusys.data.audit)
  - シグナル→発注→約定の監査テーブルを定義（signal_events, order_requests, executions）。
  - order_request_id を冪等キーとして扱う設計、すべてのテーブルに created_at/updated_at 等を付与。
  - 監査用インデックス群を追加（status 検索・signal_id 関連検索・broker_order_id 検索等）。
  - init_audit_schema(conn) / init_audit_db(db_path) により既存接続への監査スキーマ追加や専用 DB 初期化を実行。
  - 監査スキーマは TIMESTAMP を UTC で保存するために SET TimeZone='UTC' を実行。

- データ品質チェック (kabusys.data.quality)
  - QualityIssue データクラスで問題を表現（check_name, table, severity, detail, rows）。
  - check_missing_data(): raw_prices の OHLC 欠損検出（サンプル行の収集と総件数カウント）。
  - check_spike(): LAG を使った前日比スパイク検出（閾値デフォルト 50%）。
  - check_duplicates(): 主キー重複（date, code）の検出。
  - check_date_consistency(): 未来日付・market_calendar と矛盾する非営業日データの検出（テーブル未存在時は安全にスキップ）。
  - run_all_checks(conn, ...) で全チェックをまとめて実行し、検出した QualityIssue のリストを返す。
  - 各チェックは Fail-fast とせず問題を全件収集する方針（呼び出し元で重大度に応じた処理を行う）。

Changed
- （初版のため無し）

Fixed
- （初版のため無し）

Security
- 認証トークンの自動リフレッシュとキャッシュによる取り扱いに注意。refresh_token は環境変数 JQUANTS_REFRESH_TOKEN にて管理する想定。

Notes / Usage
- 必要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - SLACK_BOT_TOKEN（必須）
  - SLACK_CHANNEL_ID（必須）
  - DUCKDB_PATH / SQLITE_PATH（デフォルトを使用可能）
  - KABUSYS_ENV（development / paper_trading / live）
  - LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- .env 自動ロードはプロジェクトルートを基準に行われ、OS 環境変数は保護されます（.env.local は上書き許可）。
- DuckDB の初期化は init_schema() を用いること（get_connection() は既存 DB 接続用）。

今後の予定（非確定）
- strategy / execution / monitoring サブパッケージの具体的実装追加。
- API クライアントのユニットテストと統合テストの追加。
- ETL パイプラインやスケジューリング向け CLI / サービス化。

--- 

署名:
この CHANGELOG はソースコードからの仕様・機能推測に基づいて作成されています。実際の変更履歴やリリースノートと差異がある場合があります。