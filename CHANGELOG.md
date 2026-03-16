Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

[0.1.0] - 2026-03-16
--------------------

Added
- 初回リリース: 基本的な日本株自動売買システムのコアモジュールを追加。
  - パッケージ名: kabusys、バージョン: 0.1.0
  - モジュール公開: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring（__all__ に登録）

- 環境設定管理 (kabusys.config)
  - .env ファイル（.env, .env.local）や OS 環境変数からの自動ロード機能を実装。
  - 自動ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサーは次をサポート:
    - コメント行、export プレフィックス、シングル/ダブルクォート付き値、エスケープシーケンス、インラインコメントの取り扱い。
  - Settings クラスでアプリ設定を提供（プロパティ経由）
    - 必須環境変数チェック: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - オプション/デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH, LOG_LEVEL (デフォルト INFO)
    - env 値検証: KABUSYS_ENV は development/paper_trading/live のみ、有効でない場合は例外
    - ヘルパー: is_live/is_paper/is_dev

- J-Quants API クライアント (kabusys.data.jquants_client)
  - fetch / save 機能:
    - fetch_daily_quotes: 日足 (OHLCV) のページネーション取得
    - fetch_financial_statements: 四半期 BS/PL のページネーション取得
    - fetch_market_calendar: JPX マーケットカレンダー取得
    - save_daily_quotes / save_financial_statements / save_market_calendar: DuckDB への冪等保存 (ON CONFLICT DO UPDATE)
  - HTTP ヘルパーと堅牢性:
    - 固定間隔のレートリミッタ実装（120 req/min、_MIN_INTERVAL_SEC = 60/120）
    - 自動リトライ（指数バックオフ、最大 3 回）、対象ステータスコード (408, 429, >=500)、429 の Retry-After を考慮
    - 401 を受けた場合はリフレッシュトークンで id_token を自動再取得して 1 回リトライ（無限再帰回避）
    - id_token のモジュールレベルキャッシュを共有（ページネーション間で使い回し）
    - JSON デコードエラーの明示的なハンドリング
  - 型変換ユーティリティ:
    - _to_float/_to_int: 空値や不正値を安全に None に変換。_to_int は "1.0" のような文字列を float 経由で int に変換、非整数小数は None を返す。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataPlatform 設計に基づく 3 層＋実行層のスキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・型・チェック (CHECK/PRIMARY KEY/FOREIGN KEY) を付与してデータ整合性を確保
  - 頻出クエリ向けのインデックスを複数定義
  - init_schema(db_path) によりディレクトリ自動作成とテーブル初期化（冪等）

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新とバックフィル戦略:
    - run_prices_etl / run_financials_etl: DB の最終取得日を基に差分を取得、backfill_days により過去数日を再取得して API の後出し修正を吸収（デフォルト backfill_days=3）
    - run_calendar_etl: カレンダーは target_date から先読み（デフォルト 90 日）
    - get_last_price_date / get_last_financial_date / get_last_calendar_date で最終取得日を取得
    - _adjust_to_trading_day: 非営業日は直近の営業日に調整（market_calendar を参照）
  - メイン集約: run_daily_etl
    - 1) カレンダー取得（先に取得して営業日調整に使用）
    - 2) 株価日足 ETL
    - 3) 財務データ ETL
    - 4) 品質チェック（オプション）
    - ステップ単位で例外を局所ハンドリングして、1 ステップ失敗でも他は継続（Fail-Fast ではない）
    - ETLResult データクラスで取得数/保存数/品質問題/エラー概要を返却

- 品質チェック (kabusys.data.quality)
  - QualityIssue データクラスで問題を集約（check_name, table, severity, detail, rows）
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欄の欠損検出（volume は除外）
    - check_spike: LAG を用いた前日比スパイク検出（デフォルト閾値 50%）
  - 各チェックは Fail-Fast にせず全問題を収集して呼び出し元へ返す

- 監査ログ (kabusys.data.audit)
  - 戦略→シグナル→発注→約定を UUID の連鎖で完全トレースする監査スキーマを提供
    - signal_events, order_requests, executions テーブル（厳密なチェック・制約とステータス管理）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供
  - すべての TIMESTAMP を UTC で扱うように SET TimeZone='UTC' を実行
  - 発注の冪等性をサポート（order_request_id を冪等キー、broker_execution_id もユニーク）

Other notes / defaults
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb（Settings.duckdb_path）
  - SQLite（監視用）: data/monitoring.db（Settings.sqlite_path）
- J-Quants API のレート制限は 120 req/min を想定（内部でスロットリング）
- リトライ上限は 3 回、指数バックオフ係数は 2.0 秒（内部設定）
- カレンダー先読み: 90 日（pipeline のデフォルト）
- バックフィル: 3 日（pipeline のデフォルト）
- ロギングレベル: LOG_LEVEL 環境変数で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Notes for users / migration
- 初回セットアップ:
  - データベースの初期化は kabusys.data.schema.init_schema(path) を呼び出してください（:memory: も可）。
  - 監査ログ専用 DB を使う場合は kabusys.data.audit.init_audit_db(path) を利用できます。
- 環境変数:
  - 必須変数を .env などで設定してください（.env.example を参考）。
  - 自動 env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- テスト/CI:
  - pipeline 関数は id_token を引数で注入できるため、外部 API をモックしてユニットテストが可能です。
- 注意:
  - 現時点では戦略層・実行層（kabusys.strategy / kabusys.execution）の具体的な戦略・ブローカー連携実装は骨格が中心です。実運用前に発注・ブローカー連携の実装・テストが必要です。