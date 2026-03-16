CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しており、重要な変更点のみを記載します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-16
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ公開情報: __version__ = "0.1.0"
  - サブパッケージ公開: data, strategy, execution, monitoring

- 環境設定管理機能を追加 (kabusys.config)
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 読み込みの優先順位: OS 環境 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env パーサ実装: export 形式、単一/二重クォート、バックスラッシュエスケープ、インラインコメント処理に対応
  - 環境変数取得ユーティリティ Settings を提供（必須チェックを含む）
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パスのデフォルト値: DUCKDB_PATH = data/kabusys.duckdb, SQLITE_PATH = data/monitoring.db
    - KABUSYS_ENV の妥当性チェック（development / paper_trading / live）
    - LOG_LEVEL の妥当性チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のヘルパー

- J-Quants API クライアントを追加 (kabusys.data.jquants_client)
  - API レート制御（120 req/min）を守る固定間隔スロットリング実装 (_RateLimiter)
  - HTTP リトライロジック（指数バックオフ、最大 3 回）および Retry-After/429 の考慮
  - 401 受信時の自動トークンリフレッシュ（1 回まで）とモジュールレベルの ID トークンキャッシュ
  - ページネーション対応の取得関数:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (財務データ)
    - fetch_market_calendar (JPX カレンダー)
  - JSON デコードエラーやネットワーク例外の扱い、30 秒タイムアウト設定
  - データ保存関数（DuckDB 向け、冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - fetched_at を UTC ISO 8601 で記録し、ON CONFLICT DO UPDATE による上書き
  - ユーティリティ関数: _to_float, _to_int（堅牢な型変換）

- DuckDB スキーマ定義と初期化を追加 (kabusys.data.schema)
  - 3層データレイヤ設計に基づく DDL 実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PK / CHECK / FOREIGN KEY）とパフォーマンス向けインデックスを定義
  - init_schema(db_path) によりディレクトリ自動作成＋テーブル作成（冪等）
  - get_connection(db_path) で既存 DB へ接続

- ETL パイプラインを追加 (kabusys.data.pipeline)
  - 差分更新（最終取得日ベース） + backfill（デフォルト 3 日）による取り直し機能
  - 市場カレンダーの先読み（デフォルト 90 日）による営業日調整
  - run_prices_etl / run_financials_etl / run_calendar_etl による個別ジョブ
  - 総合エントリ run_daily_etl:
    - カレンダー取得 → 株価取得 → 財務取得 → 品質チェック（オプション）の順で実行
    - 各ステップは個別に例外を捕捉し、他ステップに影響を与えない（全件収集方針）
  - ETLResult データクラス（取得数、保存数、品質問題、エラー一覧など）を提供
  - _adjust_to_trading_day 等の補助関数とテーブル存在チェック、最終取得日取得関数を実装

- 監査ログ（トレーサビリティ）スキーマを追加 (kabusys.data.audit)
  - シグナル / 発注要求 / 約定 を UUID 連鎖でトレースするテーブル群:
    - signal_events, order_requests (冪等キー order_request_id), executions
  - すべての TIMESTAMP を UTC で保存する仕様（init_audit_schema で SET TimeZone='UTC' を実行）
  - 発注・約定系に適した制約とインデックスを定義
  - init_audit_schema(conn) / init_audit_db(db_path) を提供

- データ品質チェックを追加 (kabusys.data.quality)
  - QualityIssue データクラス
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（必須列の欠損はエラー）
    - check_spike: LAG を用いた前日比スパイク検出（デフォルト閾値 50%）
  - 各チェックはサンプル行を返し、Fail-Fast ではなく問題を全件収集する設計
  - DuckDB 上での効率的な SQL 実装（パラメータバインド使用）

- パッケージ構成および空の __init__ を各サブモジュールに用意 (strategy, execution, data 等)

Notes / Usage
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API 用パスワード
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知用 Slack 設定
- デフォルトファイルパス:
  - DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH で上書き可)
  - SQLite (監視用): data/monitoring.db (環境変数 SQLITE_PATH で上書き可)
- J-Quants API に対する制約:
  - レート制限 120 req/min を内部で守る（モジュールレベルの RateLimiter）
  - リトライ対象は 408/429/5xx／ネットワークエラー。401 は自動リフレッシュを試行
- DuckDB スキーマ初期化は init_schema() を推奨（既存テーブルは上書きせずスキップ）

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし（初回リリース）

References
- DataSchema.md, DataPlatform.md 等の内部設計に基づく実装想定（コードコメント参照）