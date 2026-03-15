CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン履歴はコードベースから推測して作成しています。

Unreleased
----------

なし

0.1.0 - 2026-03-15
------------------

Added
- 初回リリース: パッケージ kabusys を追加。パッケージバージョンは 0.1.0（src/kabusys/__init__.py）。
- パッケージ公開 API を定義（__all__ に data, strategy, execution, monitoring を含む）。

- 環境設定モジュールを追加（src/kabusys/config.py）
  - Settings クラスを提供し、環境変数からアプリ設定を取得するプロパティを実装。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須値の取得（未設定時は ValueError を送出）。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の値検証。
    - duckdb/sqlite のデフォルトパス設定（DUCKDB_PATH, SQLITE_PATH）。
    - is_live / is_paper / is_dev の判定ヘルパー。
  - .env 自動読み込み機能:
    - プロジェクトルートを .git または pyproject.toml から探索して決定（CWD に依存しない実装）。
    - 読み込み順は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export プレフィックス、クォート（バックスラッシュエスケープ含む）、行内コメントの取り扱いなどを考慮してパース。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）
  - 取得可能データ: 日足（OHLCV）、四半期財務データ（BS/PL）、JPX マーケットカレンダー。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する _RateLimiter を実装。
  - リトライ: 指数バックオフ（最大 3 回）、対象ステータス 408/429/5xx を再試行。429 の場合は Retry-After ヘッダを考慮。
  - 認証: refresh token から id_token を取得する get_id_token。モジュールレベルで id_token をキャッシュし、401 受信時には自動リフレッシュして 1 回リトライする動作を実装。
  - ページネーション対応: fetch_daily_quotes / fetch_financial_statements は pagination_key を扱い複数ページを取得。
  - fetched_at を UTC タイムスタンプで記録し、Look-ahead bias 防止とトレーサビリティを確保。
  - JSON デコードエラーやネットワークエラーのハンドリングとログ出力。
  - DuckDB への保存関数を提供（save_daily_quotes, save_financial_statements, save_market_calendar）
    - INSERT は ON CONFLICT DO UPDATE を用いて冪等性を担保。
    - PK 欠損行はスキップして警告ログを出力。
    - 値変換ユーティリティ（_to_float, _to_int）を実装。_to_int は "1.0" などの float 文字列を許容するが、小数が残る場合は None を返す等のルールを持つ。

- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）
  - 3 層構造を想定したテーブル定義を実装：
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェック・制約（CHECK, PRIMARY KEY, FOREIGN KEY）を付与。
  - 検索性能を考慮したインデックス定義（頻出クエリパターン向け）。
  - init_schema(db_path) で DB ファイルの親ディレクトリ自動作成 → DDL とインデックスを実行（冪等）。:memory: もサポート。
  - get_connection(db_path) により既存 DB への接続を取得可能（初期化は行わない）。

- 監査ログ（トレーサビリティ）モジュールを追加（src/kabusys/data/audit.py）
  - signal_events, order_requests, executions テーブルを定義し、戦略から約定に至る一連のトレーサビリティを確保（UUID 連鎖の設計思想）。
  - order_request_id を冪等キーとして扱う設計（同一キーでの再送で二重発注防止）。
  - 全 TIMESTAMP を UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）。
  - 各種制約（CHECK）と FK（ON DELETE RESTRICT）により監査ログの不変性を保証。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供（冪等）。

- パッケージ構成に空のモジュールプレースホルダを追加
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py, src/kabusys/data/__init__.py（将来拡張用）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- .env の自動読み込み時に OS 環境変数を保護するため protected セットを導入（override=True でも OS 環境変数を上書きしない実装）。
- ID トークンの自動リフレッシュは allow_refresh フラグで制御し、無限再帰を防止。

Notes / Design decisions
- J-Quants クライアントは API レート制限とリトライを重視し、ログや警告を適切に出力する設計。
- DuckDB スキーマはデータレイヤー分離（Raw / Processed / Feature / Execution）に基づき、データパイプラインの各段階を明確化。
- 監査ログは削除せず一貫して保存する前提で設計（ON DELETE RESTRICT などの制約）。
- 全体的に冪等性（ON CONFLICT / 冪等キー）と UTC タイムスタンプによるトレーサビリティを重視。

開発者向けメモ
- テスト環境などで .env 自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を初回利用する際は schema.init_schema() を呼んでから使用してください。get_connection() は既存 DB の接続時に利用します。