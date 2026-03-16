# Changelog

すべての注目すべき変更点はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-16
最初の公開リリース。日本株向け自動売買プラットフォームのコア基盤を実装しました。主な追加内容は以下の通りです。

### Added
- パッケージ基本情報
  - kabusys パッケージの初期化（src/kabusys/__init__.py）。バージョン: 0.1.0。公開モジュールを data, strategy, execution, monitoring としてエクスポート。

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動ロード（プロジェクトルートを .git または pyproject.toml で検出）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト用途）。
  - .env パーサ実装（export プレフィックス、クォート、エスケープ、インラインコメント対応）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベル等の設定値取得をラップ。必須変数未設定時は ValueError を送出。
  - 環境名（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（許可値チェック）。
  - デフォルトの DB パス（duckdb, sqlite）などを提供。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出し共通処理（_request）を実装。JSON デコードエラー、タイムアウト、HTTP エラーに対するリトライ（指数バックオフ）を組み込み。最大リトライ回数は 3 回。
  - レート制限を固定間隔スロットリングで実装（_RateLimiter、120 req/min を尊重）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）と id_token キャッシュ管理（モジュールレベル）。
  - ページネーション対応で fetch_daily_quotes / fetch_financial_statements を提供（pagination_key を扱う）。
  - fetch_market_calendar（JPX カレンダー）を提供。
  - DuckDB への冪等保存関数を提供（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE による上書きで重複排除。
  - 取得時刻（fetched_at）を UTC ISO 形式で付与して Look-ahead Bias 対策。
  - 型変換ユーティリティ (_to_float, _to_int) を実装（不正値や小数切り捨ての回避ロジックを含む）。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層を含む包括的なスキーマ DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores 等の Feature テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
  - 頻出クエリ向けのインデックス定義を用意（銘柄×日付、ステータス検索等）。
  - init_schema(db_path) によりディレクトリ自動作成 -> テーブル・インデックス作成（冪等）。get_connection() を提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL のエントリ（run_daily_etl）を実装。処理フロー: 市場カレンダー取得 → 株価差分取得（backfill 対応）→ 財務差分取得 → 品質チェック。
  - 差分更新ロジック: DB の最終取得日を参照し、backfill_days により数日前から再取得して API の後出し修正を吸収（デフォルト backfill_days=3）。
  - calendar の先読み（lookahead_days=90 日）により営業日調整が可能。
  - 個別ジョブ関数 run_prices_etl, run_financials_etl, run_calendar_etl を実装。各ステップは独立して例外処理され、1ステップ失敗でも他は継続。
  - ETLResult データクラスを導入し、取得数・保存数・品質問題・エラー一覧を返却。品質問題は上位で集約。
  - quality モジュールとの連携ポイント（引数で id_token を注入可能、テスト容易性を考慮）。

- 監査ログ（トレーサビリティ）スキーマ（src/kabusys/data/audit.py）
  - 信号 → 発注要求 → 約定 のトレーサビリティを担保する監査テーブルを実装（signal_events, order_requests, executions）。
  - order_request_id を冪等キーとする発注要求テーブル。制約（limit/stop/market の price 条件チェック）と外部キー制約（ON DELETE RESTRICT）。
  - executions は証券会社の broker_execution_id をユニーク（冪等性）として保持。
  - 監査用インデックス群を定義（戦略別・日付検索、status 検索、broker_order_id 参照など）。
  - init_audit_schema および init_audit_db を提供。全 TIMESTAMP を UTC で保存するために接続時に SET TimeZone='UTC' を実行。

- データ品質チェック（src/kabusys/data/quality.py）
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - 欠損データ検出（check_missing_data）：raw_prices の OHLC 欠損を検出（volume は除外）。サンプル行を最大 10 件返却。
  - スパイク検出（check_spike）：前日比での急騰・急落を LAG ウィンドウで検出。デフォルト閾値 50%（_SPIKE_THRESHOLD = 0.5）。
  - 各チェックは fail-fast ではなく問題を全件収集して QualityIssue のリストを返す設計。DuckDB のパラメータバインドを使用。

### Security
- なし（このリリースでは特にセキュリティ修正は含まれません）。ただし、認証トークンの取り扱い（環境変数・キャッシュ）や API リトライ処理に注意する設計としています。

### Breaking Changes
- なし（初版リリースのため互換性問題はありません）。

### Notes / Migration
- DuckDB の初期化は init_schema() を一度実行してから利用してください（初回のみテーブル作成が必要）。
- 自動 .env ロードはデフォルトで有効です。CI やユニットテスト等で自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants の呼び出しはレート制限（120 req/min）とリトライロジックを組み込んでいますが、実運用での呼び出し頻度・トークン管理は運用ポリシーに合わせて監視してください。

---

参考: この CHANGELOG はソースコード（src/kabusys/**）の実装内容から作成しています。必要であれば、各モジュールの使い方や環境変数例（.env.example 相当）の追記、リリースノートの英語版作成なども対応できます。