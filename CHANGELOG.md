# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載します。
このプロジェクトではセマンティックバージョニングを採用しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムのコア基盤を実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ初期化
  - kabusys パッケージの基本情報を追加（バージョン: 0.1.0、__all__ に主要サブパッケージを公開）。
- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化をサポート（テスト等向け）。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を検索（CWD に依存しない）。
  - 柔軟で堅牢な .env パーサを実装:
    - コメント行・空行の無視、export プレフィックス対応。
    - シングル/ダブルクォート、バックスラッシュエスケープの処理。
    - インラインコメントの判定（クォート無し時の '#' の扱い）。
  - _load_env_file による保護付き上書きロジック（OS 環境変数を protected として保護）を実装。
  - Settings クラスを実装し、アプリ設定をプロパティ経由で取得可能に:
    - J-Quants / kabu API / Slack / DB パス等の必須・既定値を定義。
    - env（development/paper_trading/live）や log_level の値検証、利便性プロパティ（is_live 等）を提供。
    - 必須変数未設定時は明示的に ValueError を送出。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する API クライアントを実装。
  - レート制御: 固定間隔スロットリングによる 120 req/min（_RateLimiter）。
  - 再試行ロジック: 指数バックオフ（base=2.0）、最大リトライ回数=3、対象ステータス(408,429,5xx) を想定。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1回のみ）を実装。get_id_token の無限再帰対策あり。
  - ページネーション対応（pagination_key を利用）およびモジュールレベルの ID トークンキャッシュ（ページング間共有）。
  - fetch_* 系関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供。
  - 保存用関数: DuckDB に対して冪等に保存する save_daily_quotes, save_financial_statements, save_market_calendar を実装。
    - fetched_at を UTC ISO8601 で記録して Look-ahead Bias を防止。
    - 不完全な PK を持つレコードはスキップしログ警告を出力。
    - INSERT ... ON CONFLICT DO UPDATE により冪等性を確保。
  - 型変換ユーティリティ: _to_float / _to_int（float 文字列からの安全な int 変換ロジックを含む）。
- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - DataLayer 構造（Raw / Processed / Feature / Execution）に基づく詳細な DDL を実装。
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw 層テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層テーブル。
    - features, ai_scores 等の Feature 層テーブル（特徴量格納）。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層テーブル。
  - 各テーブルに CHECK 制約・PRIMARY KEY を付与し、スキーマ整合性を担保。
  - 頻出クエリ向けのインデックス定義を追加（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) によりディレクトリ作成→全テーブル・インデックスの冪等作成を行うユーティリティを提供。
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない）。
- 監査ログ（トレーサビリティ）モジュール（kabusys.data.audit）
  - signal_events / order_requests / executions を持つ監査用スキーマを実装。
    - UUID ベースのトレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）。
    - order_request_id を冪等キーとして二重発注を防止する設計。
    - status 遷移・エラーメッセージ等を記録する仕組みを提供。
    - すべての TIMESTAMP を UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）。
    - FK は ON DELETE RESTRICT を用い、監査ログの削除を防止する方針。
  - init_audit_schema(conn) で既存接続に監査テーブルを追加可能。
  - init_audit_db(db_path) で監査用専用 DB の初期化と接続取得をサポート。
  - 監査系に適したインデックス群を追加（例: idx_order_requests_status, idx_executions_code_executed_at 等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

補足:
- ログ出力（logger）を各モジュールに導入し、取得件数やスキップ件数、リトライ情報などを通知するようにしています。
- 設計文書（DataSchema.md, DataPlatform.md 相当）の要件に沿う形で実装を行っています（コード内コメントに設計意図を明記）。

今後の予定（例）
- 実際の kabu ステーション（kabu API）との接続・発注実装。
- 戦略層および実運用用監視/通知（Slack 連携）の実装。
- 単体テスト・統合テストの追加と CI の整備。