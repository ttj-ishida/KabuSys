# CHANGELOG

すべての注目すべき変更点をここに記録します。  
形式は「Keep a Changelog」に準拠しています。  

※初期リリース（v0.1.0）はパッケージ内の実装から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買プラットフォームの基本コンポーネント群を追加。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは `0.1.0`。
  - 公開モジュール: data, strategy, execution, monitoring（骨組みを含む）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env 行パーサを実装（export 形式、クォート内のエスケープ、インラインコメント処理に対応）。
  - 必須環境変数取得ヘルパ (`_require`) とアプリ設定ラッパ `Settings` を提供。
  - 既定の設定項目:
    - J-Quants: JQUANTS_REFRESH_TOKEN
    - kabuステーション API: KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - 環境: KABUSYS_ENV（development/paper_trading/live）
    - ログレベル: LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - リトライロジックを実装（指数バックオフ、最大 3 回。対象: 408/429/5xx、ネットワークエラー）。
  - 401 受信時はリフレッシュトークンで ID トークンを自動更新して 1 回リトライする仕組みを実装（トークンキャッシュ共有）。
  - ページネーション対応のフェッチ関数:
    - fetch_daily_quotes: 株価日足（OHLCV）取得（ページネーション対応）
    - fetch_financial_statements: 財務データ（四半期 BS/PL）取得（ページネーション対応）
    - fetch_market_calendar: JPX マーケットカレンダー取得
  - DuckDB へ冪等に保存する save_* 関数を提供（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes -> raw_prices
    - save_financial_statements -> raw_financials
    - save_market_calendar -> market_calendar
  - 取得日時（fetched_at）を UTC で記録して Look-ahead バイアス追跡を可能にするユニフォームな設計。
  - 値変換ユーティリティ (_to_float, _to_int) を実装（安全な型変換ルールを適用）。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を追加。
  - 代表的なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - データ整合性を考慮した CHECK 制約・PRIMARY KEY を多数定義。
  - 性能を考慮したインデックスを複数定義（銘柄×日付、ステータス検索など）。
  - init_schema(db_path) でデータベースファイルの親ディレクトリ自動作成とテーブル作成を行い、DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL のメインエントリ run_daily_etl を実装。
    - ワークフロー: カレンダー取得 → 株価差分取得（backfill）→ 財務差分取得（backfill）→ 品質チェック
    - 各ステップは独立してエラーハンドリングされ、1 ステップの失敗が他に波及しない設計（全件収集型エラーハンドリング）。
  - 差分更新ロジック:
    - raw_* の最終取得日から backfill_days（日）分を再取得することで後出し修正を吸収（デフォルト backfill_days=3）。
    - 市場カレンダーは lookahead（デフォルト 90 日）分先読みして当日の営業日判定に利用。
  - 個別ジョブ実装:
    - run_prices_etl, run_financials_etl, run_calendar_etl（それぞれ取得・保存を行い取得数・保存数を返す）。
  - ETL 実行結果を表す ETLResult データクラスを提供（品質問題とエラーの収集・シリアライズをサポート）。

- 監査ログ（トレーサビリティ）(kabusys.data.audit)
  - シグナルから約定までを UUID 連鎖でトレースする監査テーブルを追加。
  - テーブル:
    - signal_events（戦略が生成したシグナルを保存）
    - order_requests（発注要求。order_request_id を冪等キーとして利用）
    - executions（証券会社から返された約定ログ）
  - すべての TIMESTAMP を UTC で保存するよう設定（init_audit_schema 内で SET TimeZone='UTC' を実行）。
  - ステータス遷移や CHECK 制約、参照整合性（ON DELETE RESTRICT）を定義。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供。インデックスも定義。

- データ品質チェック (kabusys.data.quality)
  - DataPlatform.md に基づく品質チェック処理を実装。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（必須カラムの NULL を検出）
    - check_spike: 前日比スパイク検出（LAG を使った SQL 実装。デフォルト閾値 50%）
    - （設計として重複チェック・日付不整合検出も想定。品質問題は QualityIssue 型で返却）
  - QualityIssue データクラスを提供（check_name, table, severity, detail, rows）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 注意事項 / マイグレーション
- DuckDB 初期化:
  - データ保存を行う前に schema.init_schema(db_path) を呼び出してスキーマを作成してください。
  - 監査テーブルのみを別 DB に作る場合は init_audit_db を使用できます。
- 環境変数:
  - J-Quants の API 利用には JQUANTS_REFRESH_TOKEN が必須です。欠如時は例外が発生します。
  - 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ETL 動作:
  - run_daily_etl は内部で market_calendar を先に更新してから価格・財務を差分取得します（営業日の調整を行うため）。
  - 保存処理は冪等（ON CONFLICT DO UPDATE）なので再実行耐性があります。
- レート制限と再試行:
  - J-Quants API は 120 req/min に合わせた固定間隔スロットリングを実装しています。大量取得時は遅延が発生します。
  - 401 の場合は自動リフレッシュを試行しますが、get_id_token 自身の呼び出しは無限再帰防止のため allow_refresh=False が設定されています。

今後の予定（想定）
- strategy / execution / monitoring 各層の具象実装（戦略ロジック、ブローカー連携、監視・アラート）を追加。
- 品質チェックの追加強化（重複検出、将来日付検出、より詳細なサンプル出力）。
- テストカバレッジと CI の追加。

--- 
（この CHANGELOG は現在のコードベースから推測して作成しています。実際のリリースノート作成時はコミットログやリリース方針に基づいて更新してください。）