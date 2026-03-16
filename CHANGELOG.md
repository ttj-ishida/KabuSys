# Changelog

すべての変更は Keep a Changelog の慣例に従い、セマンティックバージョニング (SemVer) を使用しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買システムのコア機能を実装しました。以下の主要コンポーネントと機能を含みます。

### Added
- パッケージ初期化
  - `kabusys` パッケージを追加。パッケージバージョンを `0.1.0` として定義（src/kabusys/__init__.py）。
  - パブリックモジュール: `data`, `strategy`, `execution`, `monitoring` をエクスポート。

- 環境設定/ロード
  - `.env` / `.env.local` の自動読み込み機能を実装（プロジェクトルート検出ロジック: `.git` または `pyproject.toml` を探索）。CWD に依存しない実装（src/kabusys/config.py）。
  - `.env` パースの強化:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの取り扱い（クォート有無での挙動差異）
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 必須環境変数取得関数 `_require()` を提供。設定項目のプロパティ化:
    - J-Quants: `JQUANTS_REFRESH_TOKEN`
    - kabuステーション: `KABU_API_PASSWORD`, `KABU_API_BASE_URL`（デフォルト http://localhost:18080/kabusapi）
    - Slack: `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - DB パス: `DUCKDB_PATH`, `SQLITE_PATH`
  - 実行環境 / ログレベル検証（`KABUSYS_ENV` は `development|paper_trading|live`、`LOG_LEVEL` は `DEBUG|INFO|WARNING|ERROR|CRITICAL`）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）・財務データ（四半期 BS/PL）・JPX マーケットカレンダー取得機能を実装。
  - レート制限対策: 固定間隔スロットリングで 120 req/min を遵守（内部 RateLimiter）。
  - 再試行（リトライ）ロジック実装:
    - 指数バックオフ、最大 3 回リトライ（対象: 408, 429, >=500）
    - 429 時は `Retry-After` ヘッダを優先
  - 認証トークン自動リフレッシュ:
    - 401 受信時はリフレッシュを行い 1 回だけ再試行
    - id_token のモジュールキャッシュ共有（ページネーション間で再利用）
  - ページネーション対応（pagination_key）、ルックアヘッドバイアス対策として取得時刻（UTC の fetched_at）を記録。
  - DuckDB へ冪等に保存（INSERT ... ON CONFLICT DO UPDATE）する保存関数を提供:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 型変換ユーティリティ `_to_float`, `_to_int` を用意（変換失敗や空値は None を返す、整数変換は "1.0" のようなケースを考慮）。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - 3 層データモデルを定義:
    - Raw Layer（raw_prices/raw_financials/raw_news/raw_executions）
    - Processed Layer（prices_daily/market_calendar/fundamentals/news_*）
    - Feature Layer（features/ai_scores）
    - Execution Layer（signals/signal_queue/portfolio_targets/orders/trades/positions/portfolio_performance）
  - データ整合性を考慮した制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）と型を定義。
  - 頻出クエリ向けのインデックスを作成。
  - `init_schema(db_path)` による冪等的な初期化と `get_connection(db_path)` を提供。parent ディレクトリ自動作成、":memory:" のサポート。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新を行う日次 ETL: 市場カレンダー、株価日足、財務データの差分取得・保存。
  - デフォルトでバックフィル（backfill_days=3）を行い、API の後出し修正を吸収。
  - カレンダーは先読み（デフォルト 90 日）を取得して営業日調整に利用。
  - 各ステップは独立したエラーハンドリング（1 ステップ失敗でも他を継続）を採用し、結果を ETLResult で集約。
  - 品質チェック（quality モジュール）と連携可能。ETLResult に品質問題とエラー概要を格納。
  - 補助関数: テーブル存在チェック、最大日付取得、営業日調整など。

- 監査ログ（audit）テーブルと初期化（src/kabusys/data/audit.py）
  - シグナル→発注要求→約定までのトレーサビリティのための監査テーブルを実装:
    - signal_events, order_requests, executions
  - 冪等キー（order_request_id、broker_execution_id 等）やステータス管理、各種制約を定義。
  - `init_audit_schema(conn)` / `init_audit_db(db_path)` による初期化（すべての TIMESTAMP は UTC）。
  - 監査向けのインデックスを定義。

- データ品質チェック（src/kabusys/data/quality.py）
  - 以下のチェックを実装:
    - 欠損データ検出（raw_prices の OHLC 欠損）
    - 異常値（スパイク）検出（前日比の閾値、デフォルト 50%）
    - （将来的に追加想定の）重複・日付不整合チェックのインフラ
  - 各チェックは QualityIssue のリストを返却し、Fail-Fast ではなく全件収集する設計。
  - SQL ベースで DuckDB を効率的に照会（パラメータバインドを使用）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- 認証トークンの取り扱い:
  - J-Quants リフレッシュトークンは環境変数から取得し、API 呼び出し時に取得する id_token をキャッシュして再利用。401 時に自動リフレッシュを行うが、無限再帰防止のため内部トークン取得呼び出しはリフレッシュを許可しない設計。
- .env 自動ロードでは OS 環境変数を保護（`.env.local` の上書き時も保護可能）。

### Notes / Migration
- 初回利用時は DuckDB スキーマを初期化してください:
  - data/schema.init_schema(db_path)
  - 監査ログのみ別 DB にする場合: data/audit.init_audit_db(db_path)
- 必須環境変数（未設定時は ValueError）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env 読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- J-Quants API の利用はレート制限や認証に注意してください（内部で対策済みですが、利用側でも適切な運用を推奨）。
- 現状は DuckDB が必須（データストアとして）。SQLite は監視 DB 用に設定項目あり。

---

今後の予定（例）
- ETL のより詳細な品質チェック（重複検査、未来日検出など）の追加。
- execution 層（発注送信、ブローカーAPI連携）の実装。
- モニタリング・Slack 通知などの統合。