CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。
このプロジェクトはセマンティックバージョニングを採用しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-16
--------------------

Added
- 初回リリース。
- パッケージ構成を追加:
  - kabusys: パッケージメタ情報（__version__ = 0.1.0）。
  - サブパッケージ: data, strategy, execution, monitoring（__all__で公開）。
- 環境設定（kabusys.config）を実装:
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み制御: KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサ実装: export 形式、クォート（シングル/ダブル）、エスケープ、コメント対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等のプロパティを取得可能。
  - 必須環境変数未設定時に明確な ValueError を送出する _require() 実装。
- J-Quants API クライアントを実装（kabusys.data.jquants_client）:
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得機能を提供（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - 認証トークン取得（get_id_token）とモジュールレベルの ID トークンキャッシュ実装（ページネーション間でトークン共有）。
  - レート制御（_RateLimiter）を実装し、デフォルトで 120 req/min を守る固定間隔スロットリングを採用。
  - 再試行ロジックを実装（指数バックオフ、最大 3 回、HTTP 408/429/5xx 対象）。429 の場合は Retry-After を優先。
  - 401 受信時はトークンを自動リフレッシュして1回だけリトライ。無限再帰を防ぐ allow_refresh フラグ。
  - レスポンス JSON のパースとエラーハンドリング。ページネーションキー対応。
  - データ保存用ユーティリティ: fetched_at を UTC ISO8601 で記録（Look-ahead Bias 対策）。
  - 型変換ユーティリティ (_to_float, _to_int) を提供。
- DuckDB スキーマ管理（kabusys.data.schema）を実装:
  - 3 層（Raw / Processed / Feature）および Execution / Audit を含む包括的なテーブル定義を提供。
  - raw_prices / raw_financials / raw_news / raw_executions、prices_daily / market_calendar / fundamentals、features / ai_scores、signals / signal_queue / orders / trades / positions / portfolio_performance などを定義。
  - 頻出クエリに合わせたインデックスの作成。
  - init_schema(db_path) により DB ファイル親ディレクトリの自動作成とテーブル初期化（冪等）を実行。get_connection() で既存 DB に接続可能。
- ETL パイプライン（kabusys.data.pipeline）を実装:
  - 日次 ETL のワークフロー（run_daily_etl）を提供。処理順はカレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック。
  - 差分更新ロジック: DB の最終取得日を基に未取得範囲のみを取得。デフォルトのバックフィルは過去 3 日（backfill_days）。
  - カレンダーは target_date から先読み（デフォルト 90 日）して営業日調整に利用。
  - ETLResult データクラスで結果／品質問題／エラーを集約。各ステップは独立して例外ハンドリングされる（1 ステップ失敗でも他は継続）。
  - 個別 ETL ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl を公開。
- 監査ログ（kabusys.data.audit）を実装:
  - signal_events, order_requests, executions テーブルを定義し、監査トレーサビリティを確保。
  - order_request_id を冪等キーとして扱い、発注の二重送信を防止する設計。
  - すべての TIMESTAMP を UTC で保存するため init_audit_schema() は SET TimeZone='UTC' を実行。
  - init_audit_db(db_path) で監査専用 DB を初期化できる。
  - 監査用途に必要なインデックスを用意（status / date / code / broker_order_id 等）。
- データ品質チェック（kabusys.data.quality）を実装:
  - 欠損データ検出（open/high/low/close の NULL 検出）。
  - スパイク検出（前日比の絶対変化率が閾値を超えるレコードを検出、デフォルト閾値 50%）。
  - QualityIssue データクラスで問題情報（check_name, table, severity, detail, sample rows）を返す。Fail-Fast ではなく全件収集する方針。
  - DuckDB 上で効率的に実行する SQL ベースの実装（パラメータバインドを使用）。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Notes / 使用上の注意
- DB の初期化:
  - 通常: from kabusys.data.schema import init_schema; conn = init_schema(settings.duckdb_path)
  - 監査ログを追加する場合: from kabusys.data.audit import init_audit_schema; init_audit_schema(conn) または init_audit_db()
- 環境変数ロード:
  - OS 環境変数が優先され、.env は OS に存在しないキーのみセットされます。.env.local は override=True で OS キー以外を上書きします。
  - テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制限やリトライはクライアント実装側で制御していますが、API 側の制約やネットワーク状況に依存します。ログを確認して監視してください。
- fetched_at は UTC タイムスタンプで保存されます（Look-ahead Bias のトレースに利用可能）。
- ETL の品質チェックで重大（severity="error"）な問題が見つかっても、run_daily_etl はデフォルトで処理を継続し、結果の ETLResult に問題一覧を返します。呼び出し側で停止やアラートの判断を行ってください。

今後の予定 (例)
- strategy / execution / monitoring サブパッケージの具象実装（注文送信、リスク管理、Slack 通知等）。
- さらなる品質チェック（重複・日付不整合検出の具象実装の拡充）。
- テストカバレッジと CI の整備、ドキュメントの拡充。

---