CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-16
------------------

Added
- 初回リリース。
- パッケージ構成:
  - kabusys: メインパッケージ（__version__ = 0.1.0）。
  - サブパッケージ: data, strategy, execution, monitoring の骨組みを追加。
- 設定/環境変数管理 (kabusys.config):
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - .env のパース機能を実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント取り扱いなどに対応）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / データベースパス / 実行環境 / ログレベルなどの設定取得を提供。必須値は未設定時に明示的な例外を送出。
  - デフォルトの DB パス（DuckDB/SQLite）やログレベル、環境（development, paper_trading, live）等の既定値と妥当性チェックを実装。
- J-Quants API クライアント (kabusys.data.jquants_client):
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得の API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）を実装。
  - リトライロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）を実装。429 の場合は Retry-After を優先。
  - 401 受信時にリフレッシュトークンで自動的に id_token を再取得して 1 回リトライする仕組みを実装（無限再帰を防止するフラグ付き）。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を実装し、pagination_key を追跡。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性を確保し、PK 欠損レコードはスキップ（警告ログ）。
  - 型変換ユーティリティ（_to_float, _to_int）を実装。float 文字列 -> int の変換時に小数部が残る場合は None を返す等の安全策を導入。
  - モジュールレベルの id_token キャッシュを実装（ページネーション間で共有）。
- DuckDB スキーマと初期化 (kabusys.data.schema):
  - Raw / Processed / Feature / Execution の 3 層＋監査用テーブル群を DDL で定義。
  - raw_prices, raw_financials, raw_news, raw_executions、prices_daily, market_calendar, fundamentals, news_*、features, ai_scores、signals, signal_queue, orders, trades, positions, portfolio_performance など主要テーブルを含む。
  - 各テーブルに適切な制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）を付与。
  - パフォーマンスを考慮したインデックス群を作成。
  - init_schema(db_path) による初期化を実装（親ディレクトリ自動作成、:memory: サポート）。get_connection で接続のみ取得可能。
- ETL パイプライン (kabusys.data.pipeline):
  - 日次 ETL パイプラインを実装（run_daily_etl）。処理順は市場カレンダー取得 → 株価日足差分取得 → 財務データ差分取得 → 品質チェック。
  - 差分更新ロジック: DB の最終取得日から backfill_days を考慮して再取得（デフォルト backfill_days = 3）。初回ロード時は最小データ日（2017-01-01）を使用。
  - カレンダーは target_date に対して先読み（デフォルト 90 日）して営業日調整に用いる。
  - 各処理は独立して例外を捕捉し、失敗しても他ステップを継続する（全体で ETLResult を返し、発生したエラーや品質問題を集約）。
  - テスト容易性のため id_token を注入可能。
  - run_prices_etl/run_financials_etl/run_calendar_etl の個別ジョブ API を提供。
- 品質チェック (kabusys.data.quality):
  - 欠損データ検出（OHLC 欄の NULL を検出）、スパイク検出（前日比の絶対変動 > threshold）、重複チェック、日付不整合検出などの骨組みを実装。
  - QualityIssue データクラスを導入し、チェック名・対象テーブル・重大度（error/warning）・詳細・サンプル行を返す設計。
  - check_missing_data と check_spike の実装（SQL ベース、パラメータバインド使用）。スパイクのデフォルト閾値は 50%。
  - 全チェックは Fail-Fast ではなくすべての問題を収集して返す設計。
- 監査/トレーサビリティ (kabusys.data.audit):
  - シグナル→発注→約定の流れを UUID 連鎖でトレースする監査テーブル群を追加（signal_events, order_requests, executions）。
  - 発注要求に対する冪等キー(order_request_id)、証券会社側の約定 ID を扱うためのユニーク制約、全テーブルで UTC タイムスタンプを使用する方針を採用。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供して監査用スキーマを初期化可能。
  - ステータス遷移や CHECK 制約を明文化（例: order_requests の order_type による price フィールド制約等）。
- ロギング/メッセージ:
  - 各主要処理で情報ログ／警告ログ／エラーログを出力。API レスポンス件数、保存件数、スキップ件数等を記録。

Changed
- （初回リリースのため無し）

Fixed
- （初回リリースのため無し）

Deprecated
- （初回リリースのため無し）

Removed
- （初回リリースのため無し）

Security
- 環境変数に機密トークン（J-Quants refresh token、Slack トークン、kabu API パスワード等）を利用する設計のため、.env の取り扱いに注意。（自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を提供）
- すべての TIMESTAMP は UTC で扱うことを明記（監査ログ初期化で SET TimeZone='UTC' を実行）。

Notes / Implementation Details
- DuckDB の初期化は冪等（CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS）で安全。既存データの上書きは行わない。
- 保存処理は ON CONFLICT DO UPDATE を用いて冪等性を確保。PK 欠損行はスキップして警告ログを出す。
- J-Quants クライアント: rate limiting、リトライ、トークンリフレッシュ、ページネーション、JSON デコードエラーハンドリングなど堅牢性を重視。
- テスト向け設計: id_token の注入や KABUSYS_DISABLE_AUTO_ENV_LOAD による .env 自動読込抑止など、外部依存の分離を考慮。
- デフォルトのデータベースパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視用): data/monitoring.db
  - いずれも環境変数で上書き可能。":memory:" を渡すことでインメモリ DB を使用可能。

Breaking Changes
- 初回リリースのため既存 API 破壊はなし。

Acknowledgements / Future
- 今後のリリースでは strategy / execution / monitoring の具象実装、より多くの品質チェック、運用向けコマンドラインツールや CI/CD での DB 初期化ワークフロー、テストカバレッジの追加を予定。

README やドキュメント（DataPlatform.md, DataSchema.md 等）を参照してデータモデル・ETL の詳しい仕様を確認してください。