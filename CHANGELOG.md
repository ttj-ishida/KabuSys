# Changelog

すべての注目すべき変更履歴をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

## [Unreleased]


## [0.1.0] - 2026-03-16
初回リリース — 基本的な日本株自動売買システムのコア実装を追加。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョンを src/kabusys/__init__.py にて "0.1.0" として定義。
  - サブモジュールの公開: data, strategy, execution, monitoring。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env 読み込み:
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を読み込む。
    - OS 環境変数を保護する protected 機構を実装。
    - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env のパースは export 形式、クォート/エスケープ、行内コメント等に対応する堅牢な実装。
  - 必須環境変数チェック用の _require ユーティリティを提供。
  - 既定値とバリデーション:
    - KABUSYS_ENV: development|paper_trading|live の検証。
    - LOG_LEVEL の検証 (DEBUG/INFO/WARNING/ERROR/CRITICAL)。
    - デフォルトのパス設定: DUCKDB_PATH, SQLITE_PATH、KABU_API_BASE_URL の既定値。

  - 必須（例）環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - OHLCV（日足）、四半期財務（BS/PL）、JPX マーケットカレンダーを取得するクライアント実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - リトライロジック:
    - 最大リトライ回数 3 回、指数バックオフ (base=2.0)。
    - HTTP 408, 429 および 5xx 系をリトライ対象。
    - 429 の場合は Retry-After ヘッダを優先。
  - 認証:
    - refresh_token から ID トークンを取得する get_id_token (POST /token/auth_refresh)。
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰を防止）。
    - ページネーション間で共有されるモジュールレベルの id_token キャッシュ。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数（冪等に保存）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE により重複を排除。
    - fetched_at を UTC ISO フォーマットで記録して Look-ahead Bias を抑制。
  - 型変換ユーティリティ:
    - _to_float / _to_int: 空値・不正値処理、"1.0" のような float 文字列を安全に int に変換するロジック等を実装。

- DuckDB スキーマ & 初期化 (src/kabusys/data/schema.py)
  - DataPlatform の 3 層設計（Raw / Processed / Feature）および Execution 層のテーブル DDL を定義。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義: 検索パターンに基づく複数の INDEX を作成。
  - init_schema(db_path) により DB ファイルの親ディレクトリを自動作成し、DDL/INDEX を実行して初期化（冪等）。
  - get_connection(db_path) で既存 DB への接続を返す。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - DataPlatform に基づく差分 ETL の実装:
    - run_prices_etl, run_financials_etl, run_calendar_etl: 差分取得（バックフィル）、保存を個別に実行。
    - run_daily_etl: 市場カレンダー取得 → 営業日調整 → 株価 ETL → 財務 ETL → 品質チェック のフローを実行。
  - 差分ロジック:
    - DB の最終取得日から backfill_days（デフォルト 3 日）前を再取得することで API の後出し修正に対応。
    - カレンダーは先読み (lookahead_days, デフォルト 90 日) を行い、営業日判定に利用。
  - エラーハンドリング:
    - 各ステップを独立して try/except し、1 ステップ失敗でも残りを継続（Fail-Fast ではない）。
    - ETLResult 型に取得件数・保存件数・品質問題・エラーメッセージを格納して返却。
  - id_token を外部注入可能にしテスト容易性を確保。

- データ品質チェック (src/kabusys/data/quality.py)
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欄の欠損検出（severity=error）。
    - check_spike: 前日比スパイク（デフォルト閾値 50%）の検出（急騰・急落検出）。
  - チェックはサンプル行（最大 10 件）を返し、全件収集方式を採用（Fail-Fast ではない）。
  - DuckDB 上で SQL を用いて効率的に実行、パラメータバインドを利用してインジェクション対策。

- 監査ログ (src/kabusys/data/audit.py)
  - 戦略→シグナル→発注→約定のトレーサビリティを保証する監査テーブルを実装。
  - トレーサビリティ階層を明確化（business_date, strategy_id, signal_id, order_request_id, broker_order_id）。
  - 主なテーブル:
    - signal_events: 戦略が生成したすべてのシグナルを保存（棄却やエラー含む）。
    - order_requests: 発注要求（order_request_id を冪等キーとして制御）。limit/stop/market のチェック制約を実装。
    - executions: 実際の約定ログ（broker_execution_id をユニーク冪等キーとして扱う）。
  - 全テーブルで created_at を持ち、タイムゾーンを UTC に固定（init_audit_schema は SET TimeZone='UTC' を実行）。
  - init_audit_schema(conn) と init_audit_db(db_path) により監査スキーマを初期化。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

付記 / 運用上の注意
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト値:
  - KABU_API_BASE_URL: http://localhost:18080/kabusapi
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - KABUSYS_ENV: development（候補: development, paper_trading, live）
  - LOG_LEVEL: INFO
- 自動 .env 読み込みを無効化したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で便利）。
- DB 初期化:
  - data.schema.init_schema(db_path) を初回に実行してください（:memory: 指定でインメモリ DB）。
  - 監査ログは init_audit_schema(conn) または init_audit_db(db_path) で初期化可能。
- API 呼び出しに関する設計決定のメモ:
  - レート制限 120 req/min（固定間隔スロットリング）。
  - リトライは最大 3 回、429 の場合は Retry-After を尊重。
  - 401 受信時はトークンを自動リフレッシュして 1 回だけ再試行。
  - ページネーション中は id_token を共有して効率化。

この CHANGELOG はコードから推測して作成しています。実際のリリースノートとして公開する前に内容（日付・必須環境変数や挙動の詳細）をプロジェクト方針に合わせて確認・編集してください。