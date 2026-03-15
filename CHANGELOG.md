# CHANGELOG

すべての変更は Keep a Changelog に準拠して記載します。  
このファイルはプロジェクトの公開 API・データベーススキーマ・設定読み込み・外部 API クライアント等の導入を中心に、コードベースから推測して作成しています。

どのバージョンでも、重大な後方互換破壊（Breaking changes）は明記します。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システムの基盤となる設定管理、データ取得・永続化、監査ログ、スキーマ定義を含むコア実装を追加。

### Added
- パッケージ基礎
  - kabusys パッケージを追加。__version__ = "0.1.0" を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの判定に .git または pyproject.toml を利用し、CWD に依存しない堅牢な探索を実装。
    - 読み込み優先順：OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト用途を想定）。
  - .env パーサーを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント処理など）。
  - .env 読み込み時の上書き制御（override）と protected キー保護（OS 環境変数の保護）をサポート。
  - Settings クラスを追加し、以下の必須設定をプロパティで取得：
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを持つ、Path 型で取得）
    - KABUSYS_ENV の検証（development / paper_trading / live のみ有効）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - 環境判定ユーティリティ: is_live / is_paper / is_dev

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API クライアントを実装。取得可能なデータ：
    - 株価日足（OHLCV）
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー（祝日・半日・SQ）
  - 設計上の特徴：
    - レート制限遵守のための固定間隔スロットリング（デフォルト 120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回）。408/429/5xx をリトライ対象に含む。
    - 429 への対応で Retry-After ヘッダを優先して待機。
    - 401 発生時はリフレッシュトークンで id_token を自動更新して 1 回のみリトライ（無限再帰防止）。
    - id_token のモジュールレベルキャッシュを実装し、ページネーション間で共有。
    - ページネーション対応の fetch_* API（fetch_daily_quotes、fetch_financial_statements）を実装（pagination_key の追跡で重複防止）。
    - fetch_* は取得日時（fetched_at）を UTC で記録する方針で設計（Look-ahead Bias 防止）。
  - HTTP ユーティリティ _request を提供し、JSON デコードエラーやネットワークエラー時の扱いを明示。
  - get_id_token(refresh_token=None) を提供（settings.jquants_refresh_token をデフォルトで使用可能）。

- DuckDB 永続化ユーティリティ（kabusys.data.jquants_client の保存関数）
  - raw_prices, raw_financials, market_calendar に対する冪等な保存関数を追加（save_daily_quotes, save_financial_statements, save_market_calendar）。
  - INSERT ... ON CONFLICT DO UPDATE による上書き（アップサート）を実装し、重複を排除。
  - PK 欠損行はスキップして警告ログを出力。
  - 数値変換ユーティリティ _to_float / _to_int を実装し、空値・不正値を安全に None に変換。_to_int は "1.0" のような float 文字列を許容するが小数部がある場合は None を返す等の細かな振る舞いを定義。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataLayer の 3 層（Raw / Processed / Feature）および Execution レイヤーのテーブル DDL を定義。
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス（頻出クエリ向け）を定義。
  - init_schema(db_path) を実装：親ディレクトリの自動作成、DDL の順序実行（外部キーを考慮）、冪等（既存テーブルはスキップ）。
  - get_connection(db_path) を提供（スキーマ初期化を行わないため初回は init_schema を推奨）。

- 監査ログ（kabusys.data.audit）
  - シグナル〜発注〜約定までをトレース可能な監査テーブル群を実装（signal_events, order_requests, executions）。
  - 設計上の特徴：
    - order_request_id を冪等キーとして扱い、同一キーでの再送でも二重発注を防止する仕様。
    - すべてのテーブルに created_at（および必要に応じて updated_at）を持ち、監査痕跡を保証。
    - 監査テーブルは削除しない前提（外部キーは ON DELETE RESTRICT）。
    - init_audit_schema(conn) において TimeZone を UTC に設定してからテーブル作成。
    - init_audit_db(db_path) で監査専用 DB を作成するユーティリティを提供。
  - 監査向けのインデックスを複数追加（status／signal_id／broker_order_id 等の検索高速化）。

- パッケージ構成
  - strategy/, execution/, monitoring/ の __init__.py を配置（将来の拡張用のプレースホルダ）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Migration
- 必須環境変数：
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必ず設定してください。未設定の場合 Settings の該当プロパティアクセスで ValueError が発生します。
- デフォルト DuckDB パスは settings.duckdb_path = data/kabusys.duckdb。init_schema は親ディレクトリを自動作成します。
- J-Quants API のレート制限はデフォルトで 120 req/min に固定されています。必要に応じて _MIN_INTERVAL_SEC を調整してください。
- .env の自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト実行時の隔離に便利です）。
- API リトライの挙動：
  - 401 の場合は一度だけトークンをリフレッシュして再試行します（リフレッシュ失敗時は例外）。
  - 429 の際は Retry-After ヘッダを優先して待機します。その他のリトライは指数バックオフを使用します。

---

将来的に、戦略実装（strategy/）、発注実行ロジック（execution/）、モニタリング（monitoring/）を実装・拡充していく予定です。変更履歴は以降のリリースで詳細に記載します。