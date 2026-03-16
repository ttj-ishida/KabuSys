# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載します。  
現在のバージョンは src/kabusys/__init__.py に定義された v0.1.0 です。

## [Unreleased]
- 次回リリースに向けた作業中。

## [0.1.0] - 2026-03-16
初回公開リリース。

### Added
- パッケージ初期構成を追加
  - kabusys パッケージのエントリポイントおよび __version__ を追加。
  - モジュール公開: data, strategy, execution, monitoring。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を自動読み込み（プロジェクトルートを .git または pyproject.toml を基準に検出）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - コメント処理（クォート外での # を適切に無視）
  - OS 環境変数（既存の env）を保護する protected 機能（.env.local により上書き可）。
  - Settings クラスを追加し、主要設定値をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev ヘルパー

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX 市場カレンダー取得関数を実装:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - API ページネーション対応（pagination_key）
  - 認証機能: refresh_token から id_token を取得する get_id_token（POST）。
  - HTTP レイヤー:
    - 固定間隔スロットリングによるレート制御（120 req/min を実装した RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対応）。
    - 401 受信時の id_token 自動リフレッシュ（1 回のみ再試行、無限再帰回避）。
    - JSON デコードエラーの明示的なハンドリング。
  - ID トークンのモジュールレベルキャッシュ（ページネーション間で共有）。
  - データ保存関数（DuckDB 用）の実装（冪等性を意識）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 各 save_* は fetched_at を UTC で付与し、ON CONFLICT DO UPDATE を利用して重複を排除。
  - 型変換ユーティリティ: _to_float, _to_int（安全な変換と不正値の扱い）。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - 3 層（Raw / Processed / Feature / Execution）に対応するテーブルDDLを定義:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 有用なインデックス定義を追加（頻出クエリ向け）。
  - init_schema(db_path) でディレクトリ作成→テーブル/インデックス作成（冪等）。
  - get_connection(db_path) を提供（既存 DB への接続）。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL のエントリポイント run_daily_etl を実装:
    - 市場カレンダー取得 → 株価差分取得（backfill）→ 財務差分取得 → 品質チェック の順で実行。
    - 各ステップは独立してエラーハンドリング（1ステップ失敗でも他は継続）。
    - カレンダー先読み（デフォルト 90 日）やバックフィル（デフォルト 3 日）をサポート。
  - 個別ジョブ実装: run_calendar_etl, run_prices_etl, run_financials_etl（差分更新ロジックを含む）。
  - ETLResult データクラスを追加（取得数・保存数・品質問題・エラー一覧・シリアライズ機能）。
  - 市場営業日調整ヘルパー _adjust_to_trading_day を提供（市場カレンダーに基づく調整）。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - 監査用テーブルを定義・初期化するモジュールを追加:
    - signal_events（戦略シグナル履歴）
    - order_requests（発注要求・冪等キー order_request_id）
    - executions（約定ログ、broker_execution_id をユニークキーとして冪等化）
  - UTC タイムゾーン強制（init_audit_schema で SET TimeZone='UTC'）。
  - 適切な制約・チェック・外部キーを付与して監査性を確保。
  - 監査用インデックス群を追加（検索・キュー処理・コールバックの紐付けを容易化）。
  - init_audit_db(db_path) による専用 DB 初期化ヘルパーを提供。

- データ品質チェック (kabusys.data.quality)
  - 品質チェックフレームワークとチェック実装を追加:
    - QualityIssue データクラス（check_name, table, severity, detail, rows）。
    - check_missing_data: raw_prices の OHLC 欠損検出（サンプル行取得、件数集計）。
    - check_spike: 前日比スパイク（LAG を使った差分計算）検出（閾値デフォルト 50%）。
  - 各チェックは全問題を収集して返却し、呼び出し元が重大度に基づき対処可能。

### Changed
- （初回リリースのため変更履歴はありません）

### Fixed
- （初回リリースのため修正履歴はありません）

### Security
- 認証トークンや API 呼び出しに関するエラーハンドリングを強化（トークンリフレッシュ・リトライ制御）。
- .env 読み込み時に既存の OS 環境変数を保護する仕組みを導入。

### Notes / Usage
- J-Quants API を利用するために JQUANTS_REFRESH_TOKEN の設定が必須。
- DuckDB を利用するローカルパスは Settings.duckdb_path（デフォルト data/kabusys.duckdb）。
- ETL 実行時は run_daily_etl に既に初期化済みの DuckDB 接続を渡して実行してください。
- .env 自動ロードはプロジェクトルートの検出に依存するため、パッケージ配布後は必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を利用ください。

---

（今後のリリースでは各モジュールの追加機能、品質チェックの拡張、実行層のブローカー連携などを追記予定です）