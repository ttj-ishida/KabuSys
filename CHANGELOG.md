# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを採用します。

## [0.1.0] - 2026-03-15

初回公開リリース。日本株自動売買システム「KabuSys」の基盤モジュールを実装しました。主な追加内容は以下の通りです。

### Added
- パッケージ基礎
  - パッケージエントリポイントを追加（kabusys.__init__）。バージョンは 0.1.0。
  - モジュール構成: data, strategy, execution, monitoring の名前空間を用意。

- 環境設定 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 環境自動ロード:
    - プロジェクトルート（.git または pyproject.toml を基準）を検出して .env と .env.local を自動で読み込む。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
    - OS 環境変数を保護するための protected キーセットを考慮した上書きロジック。
  - .env パーサーの実装:
    - コメント、export 形式、シングル/ダブルクォート、エスケープシーケンス、インラインコメントの扱いなどに対応。
  - 必須変数取得ヘルパー _require を提供（未設定時は ValueError）。
  - 代表的な設定プロパティ:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを含む Path 型で返却）
    - KABUSYS_ENV（development / paper_trading / live を検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL を検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API ベース機能:
    - トークン取得 (get_id_token) と ID トークンのモジュールキャッシュ。
    - 固定間隔のスロットリングによるレート制御（120 req/min を遵守する RateLimiter）。
    - リトライ/バックオフ:
      - ネットワークエラーや HTTP 408/429/5xx に対する指数バックオフ（最大 3 回）。
      - 429 レスポンスの Retry-After ヘッダを優先。
      - 401 を受信した場合はトークンを自動リフレッシュして 1 回だけ再試行（無限再帰を防止）。
    - ページネーション対応（pagination_key の処理、ページ間でトークンを共有）。
    - JSON デコードエラー時の明示的な例外。
  - データ取得関数:
    - fetch_daily_quotes: 株価日足（OHLCV）をページネーション対応で取得。
    - fetch_financial_statements: 四半期財務データをページネーション対応で取得。
    - fetch_market_calendar: JPX 市場カレンダー（祝日・半日・SQ）を取得。
    - 取得時にログ出力（取得レコード数）および Look-ahead Bias を防ぐため fetched_at を UTC で記録する設計方針を採用。
  - DuckDB 保存支援:
    - save_daily_quotes / save_financial_statements / save_market_calendar を追加。
    - 各保存関数は冪等（ON CONFLICT DO UPDATE）で重複を排除。
    - PK 欠損行のスキップと警告ログ出力。
    - 型変換ユーティリティ _to_float / _to_int を実装（不正値に対して安全に None を返す）。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataLayer に基づくスキーマを定義（Raw / Processed / Feature / Execution 層）。
  - テーブル群の DDL を網羅的に定義:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリパターンを想定した複数の CREATE INDEX）。
  - init_schema(db_path)：データベースの作成（親ディレクトリ自動生成）と全テーブル/インデックスの初期化（冪等）。
  - get_connection(db_path)：既存 DB への接続（スキーマ初期化は行わない）。

- 監査ログ（トレーサビリティ）モジュール (kabusys.data.audit)
  - トレーサビリティを目的とした監査テーブル群を追加:
    - signal_events（戦略が生成した全シグナルログ、棄却やエラーも保存）
    - order_requests（発注要求、order_request_id を冪等キーとする）
    - executions（証券会社から返された約定情報、broker_execution_id をユニーク鍵として冪等化）
  - 設計方針の実装:
    - すべての TIMESTAMP を UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）。
    - ON DELETE RESTRICT を用いた監査ログの非削除前提。
    - order_requests に対する入力チェック（limit/stop/market による価格カラムの必須/非必須制約）。
    - ステータス列と遷移を考慮したステータス列（pending/sent/filled 等）。
  - インデックス群の定義（シグナル／日付／銘柄検索や broker_order_id による検索など）。
  - init_audit_schema(conn)：既存接続に監査用テーブルとインデックスを追記（冪等）。
  - init_audit_db(db_path)：監査用専用 DB の初期化ユーティリティ（親ディレクトリ自動生成、UTC 設定）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

注記:
- DuckDB の初期化は init_schema() を初回に必ず実行してください（get_connection() は既存 DB へ接続するのみです）。
- J-Quants トークン周りは自動リフレッシュとキャッシュ機構を持ちますが、refresh token は安全に管理してください（環境変数経由で設定することを想定）。
- .env の自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後や異なる配置での挙動に注意してください。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。