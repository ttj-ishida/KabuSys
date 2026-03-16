# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングに従います。

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-03-16

### Added
- 基本パッケージ初回リリース。
  - パッケージ名: `kabusys`（バージョン 0.1.0）
  - 公開モジュール: `kabusys.data`, `kabusys.strategy`, `kabusys.execution`, `kabusys.monitoring`

- 環境変数・設定管理 (`kabusys.config`)
  - `.env` / `.env.local` の自動読み込み機能を追加（優先順位: OS 環境変数 > .env.local > .env）。
  - 自動ロードを環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途）。
  - プロジェクトルート判定: `.git` または `pyproject.toml` を基準に探索するため、CWD に依存しない。
  - `.env` パーサー強化:
    - `export KEY=val` 形式に対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理対応
    - インラインコメントの扱い（クォートなしでは直前が空白/タブの場合にコメントとして扱う）
  - 設定参照用 `Settings` クラスを提供（必須キー取得 `_require`、パスの Path 変換、値検証）。
    - 必須設定例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - 環境種別 (`KABUSYS_ENV`) とログレベル (`LOG_LEVEL`) の検証ロジックを実装
    - DB ファイルパスのデフォルト: `data/kabusys.duckdb`（DuckDB）、`data/monitoring.db`（SQLite）

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 基本的なデータ取得機能を実装:
    - 日次株価（OHLCV）取得: `fetch_daily_quotes`
    - 財務データ（四半期 BS/PL）取得: `fetch_financial_statements`
    - JPX マーケットカレンダー取得: `fetch_market_calendar`
  - 認証: リフレッシュトークンから ID トークンを取得する `get_id_token` を実装。モジュールレベルのトークンキャッシュを保持（ページネーション間で共有）。
  - HTTP 層の堅牢化:
    - 固定レートのスロットリングで API レート制限（120 req/min）を順守（`_RateLimiter`）。
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）。
    - `401` 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰を防止）。
    - ページネーション対応（`pagination_key` を利用）。
  - DuckDB への保存関数（冪等設計）:
    - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`
    - 各関数は `ON CONFLICT DO UPDATE` を使って重複を排除し、`fetched_at` を UTC タイムスタンプで記録。
  - ユーティリティ関数:
    - 型変換安全化: `_to_float`, `_to_int`（不正値や空文字を None とする、浮動小数を伴う整数文字列の扱いに注意）

- DuckDB スキーマ定義・初期化 (`kabusys.data.schema`)
  - 3 層データレイヤ（Raw / Processed / Feature）および Execution 層の DDL を定義。
  - 主なテーブル:
    - Raw: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature: `features`, `ai_scores`
    - Execution: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - インデックスを多数定義（銘柄×日付スキャンやステータス検索向け）。
  - 初期化 API:
    - `init_schema(db_path)` — DB ファイルの親ディレクトリを自動作成してテーブルを冪等的に作成し接続を返す。
    - `get_connection(db_path)` — 既存 DB への接続（スキーマ初期化は行わない）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - 日次 ETL のフローを実装:
    - 市場カレンダー ETL → 株価 (差分 + backfill) → 財務データ (差分 + backfill) → 品質チェック
  - 差分更新ロジック:
    - DB の最終取得日から未取得範囲を自動算出
    - デフォルトのバックフィル日数は 3 日（`backfill_days` で変更可能）
  - 市場カレンダーはデフォルトで 90 日先まで先読み（`calendar_lookahead_days`）。
  - 品質チェックとの統合（`quality` モジュールを呼び出し、エラーは収集して呼び出し元に委ねる）。
  - 結果を格納する `ETLResult` データクラスを提供（取得数・保存数・品質問題・エラー等を含む）およびログ出力。
  - 各 ETL ステップは例外を捕捉して継続する設計（Fail-Fast にしない）。

- 監査ログ（トレーサビリティ）機能 (`kabusys.data.audit`)
  - シグナルから約定までを UUID 連鎖でトレース可能にする監査テーブル群を実装。
  - テーブル:
    - `signal_events`（シグナル生成ログ。戦略 ID、decision、理由等を記録）
    - `order_requests`（冪等キーとしての `order_request_id` を持つ発注要求ログ。制約で limit/stop/market の価格必須条件を表現）
    - `executions`（証券会社からの約定ログ。`broker_execution_id` をユニークな冪等キーとして保存）
  - インデックスを付与して検索性を確保（status クエリや日付/銘柄検索など）。
  - 初期化 API:
    - `init_audit_schema(conn)` — 既存 DuckDB 接続に監査ログテーブルを追加（UTC タイムゾーン設定を実行）。
    - `init_audit_db(db_path)` — 監査専用 DB の初期化と接続返却。

- データ品質チェックモジュール (`kabusys.data.quality`)
  - 複数の品質チェックを提供（DuckDB 上の SQL を用いて効率的に検出）。
  - 実装済みチェック:
    - 欠損データ検出（`check_missing_data`）: `raw_prices` の OHLC 欠損を検出（未取得・NULL）
    - スパイク検出（`check_spike`）: 前日比の絶対変動率が閾値（デフォルト 50%）を超える場合に検出
    - （設計上）重複チェック、日付不整合検出も想定（モジュール全体での実装方針に基づく）
  - 各問題は `QualityIssue` データクラスで返却（check 名、テーブル、severity、詳細、サンプル行）。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Deprecated
- 初期リリースのため該当なし。

### Removed
- 初期リリースのため該当なし。

### Security
- API トークンの扱いに関する考慮:
  - ID トークンはモジュールキャッシュに保持し、必要時のみリフレッシュして再試行する実装。`get_id_token` はリフレッシュトークンを settings から取得する。
  - `.env` 自動読み込み時に OS 環境変数は上書きされない（保護セット）。上書きさせたい場合は `.env.local` を使用。

## Upgrade / Migration notes
- 初回利用前に DuckDB スキーマの初期化を行ってください:
  - 例: `conn = init_schema(settings.duckdb_path)`
- 監査ログを別 DB として管理する場合は `init_audit_db()` を使用してください。既存の DB に追加する場合は `init_audit_schema(conn)`。
- 環境変数の読み込みはプロジェクトルート（`.git` または `pyproject.toml`）を基準に行われます。自動ロードを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

この CHANGELOG はソースコードから推測して作成しています。実際のリリースノートには用途・互換性・既知の問題などを追記してください。