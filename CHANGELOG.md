CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。
リリース日付はリポジトリの __version__（src/kabusys/__init__.py）に基づく初回リリースを記載しています。

[0.1.0] - 2026-03-16
--------------------

Added
- パッケージ初回リリース。
- 基本パッケージ情報:
  - パッケージ名: KabuSys
  - バージョン: 0.1.0
  - モジュール公開: data, strategy, execution, monitoring

- 環境変数・設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト等を想定）。
  - .env パーサーの実装: コメント、export 文、シングル/ダブルクォート、エスケープシーケンス、インラインコメントの扱いを考慮。
  - 環境設定ラッパー Settings を導入。以下のプロパティを提供:
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - slack_bot_token, slack_channel_id
    - duckdb_path, sqlite_path
    - env (development/paper_trading/live の検証), log_level（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev の簡易判定
  - 必須環境変数未設定時に ValueError を投げる _require() を実装。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API からのデータ取得:
    - 株価日足 (fetch_daily_quotes)
    - 財務データ（四半期 BS/PL）(fetch_financial_statements)
    - JPX マーケットカレンダー (fetch_market_calendar)
  - 設計上の特徴:
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）。対象は 408/429/5xx とネットワークエラー。
    - 401 受信時は自動でリフレッシュを試行して最大 1 回リトライ（トークン取得時の再帰を防止）。
    - id_token のモジュールレベルキャッシュ（ページネーション間で共有）。
    - ページネーション対応（pagination_key を利用してすべてのページを取得）。
    - データ取得時に取得時刻（fetched_at）を UTC ISO8601 で付与して Look-ahead Bias を防止。
  - DuckDB への保存関数（冪等化）:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。いずれも ON CONFLICT DO UPDATE を使用して重複を排除。
    - PK 欠損行はスキップしログに警告出力。
  - 入力変換ユーティリティ (_to_float / _to_int) を実装し、非数値や不正フォーマットに安全に対処。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層＋Execution 層（Raw / Processed / Feature / Execution）のテーブル群を定義。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を豊富に定義。
  - 頻出クエリに対するインデックスを作成（コード×日付、ステータス検索等）。
  - init_schema(db_path) によりディレクトリ自動作成、DDL の順序を考慮した冪等な初期化を提供。
  - get_connection(db_path) により既存 DB への接続を取得（スキーマ初期化は行わない）。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - シグナル→発注→約定の監査トレーサビリティ用テーブルを定義:
    - signal_events, order_requests (冪等キー: order_request_id), executions
  - 監査向け制約とステータス管理（order_requests.status の遷移群）を定義。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。UTC タイムゾーンの強制（SET TimeZone='UTC'）。
  - インデックスを用意して監査用検索を効率化（signal_id・broker_order_id・status 等）。

- データ品質チェックモジュール (kabusys.data.quality)
  - DataPlatform.md に基づく品質チェック群を実装:
    - 欠損検出: check_missing_data (raw_prices の OHLC 欠損)
    - 異常値検出: check_spike (前日比スパイク検出、デフォルト閾値 50%)
    - 重複チェック: check_duplicates (主キー重複検出)
    - 日付不整合: check_date_consistency (未来日付・market_calendar による非営業日判定)
    - run_all_checks で全チェックをまとめて実行可能
  - 各チェックは QualityIssue のリストを返し、複数問題を収集する設計（Fail-fast ではない）。
  - DuckDB に対する SQL をパラメータバインドで実行し、サンプル行（最大 10 件）を返却。
  - ログ出力（error / warning）を適宜実施。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 認証トークン（id_token）取得/リフレッシュ処理を備え、401 発生時に自動リフレッシュを行うことでトークン期限切れによる失敗を軽減。
- .env の自動読み込みは環境変数によって無効化可能（テスト環境での誤読防止）。

Notes / 補足
- DuckDB の初期化関数は冪等であり、既存テーブルがあれば上書きしません。初回利用時は init_schema() を呼び出してください。
- J-Quants API のレート制限やリトライはクライアント内で管理しますが、大量取得時は呼び出し頻度に注意してください。
- 現時点では strategy / execution / monitoring のパッケージ初期化ファイル（__init__）のみを提供しており、各層の具体的なアルゴリズムや外部ブローカー連携の実装は今後のリリースで追加予定です。