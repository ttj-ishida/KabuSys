CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
[Semantic Versioning](https://semver.org/).

[Unreleased]
------------

- （現時点では未リリースの変更はありません）

0.1.0 - 2026-03-15
-----------------

Added
- 初期リリースとしてパッケージを追加。
- パッケージメタ:
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポートモジュール: data, strategy, execution, monitoring
- 環境設定管理モジュール (kabusys.config):
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードを無効にするためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索（CWD 非依存）。
  - .env パーサを実装:
    - 空行・コメント行の無視、export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォート無しでのインラインコメント取り扱い（直前が空白/タブの場合のみ）。
  - .env 読み込み時の保護機能:
    - OS の既存環境変数を protected として上書き防止（一部ファイルは override が可能）。
  - Settings クラスでアプリ設定をプロパティで提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須取得（未設定時は ValueError）。
    - KABU_API_BASE_URL のデフォルト: http://localhost:18080/kabusapi
    - データベースパスのデフォルト:
      - DUCKDB_PATH: data/kabusys.duckdb
      - SQLITE_PATH: data/monitoring.db
    - 環境種別検証: KABUSYS_ENV は development / paper_trading / live のみ許容。is_live/is_paper/is_dev ヘルパー。
    - ログレベル検証: LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容。
- J-Quants API クライアント (kabusys.data.jquants_client):
  - 基本設計:
    - API レート制限（デフォルト 120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
    - リトライ（最大 3 回）、指数バックオフ、対象ステータス: 408, 429, 5xx。
    - 429 の場合は Retry-After ヘッダを優先。
    - 401 受信時はリフレッシュトークンで id_token を自動リフレッシュして 1 回再試行（無限再帰防止）。
    - ページネーション対応（pagination_key の追跡でループ脱出、ページ間で id_token を共有するキャッシュ）。
    - データ取得日時（fetched_at）を UTC ISO8601 で記録し、Look-ahead bias を抑制。
    - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を排除。
  - 提供関数:
    - get_id_token(refresh_token: Optional[str]) -> str
      - /token/auth_refresh に POST して idToken を取得。
    - fetch_daily_quotes(id_token, code, date_from, date_to) -> list[dict]
      - 株価日足（OHLCV）、ページネーション対応。
    - fetch_financial_statements(id_token, code, date_from, date_to) -> list[dict]
      - 四半期財務データ（BS/PL）、ページネーション対応。
    - fetch_market_calendar(id_token, holiday_division) -> list[dict]
      - JPX マーケットカレンダー（祝日・半日・SQ）。
    - save_daily_quotes(conn, records) -> int
      - raw_prices テーブルへ保存。PK 欠損行はスキップして警告ログ出力。挿入・更新件数を返す。
    - save_financial_statements(conn, records) -> int
      - raw_financials テーブルへ保存（冪等）。
    - save_market_calendar(conn, records) -> int
      - market_calendar テーブルへ保存（冪等）。HolidayDivision に応じて is_trading_day / is_half_day / is_sq_day を設定。
  - ユーティリティ:
    - _to_float / _to_int: 安全な型変換。int 変換は "1.0" などの小数表現を許容するが、小数部が 0 以外の場合は None。
- DuckDB スキーマ管理 (kabusys.data.schema):
  - DataSchema.md に基づく 3 層＋実行層のテーブル定義を実装（Raw / Processed / Feature / Execution）。
  - 定義済みテーブル（抜粋）:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な CHECK 制約・PRIMARY KEY・FOREIGN KEY を付与。
  - 頻出クエリに対応するインデックス群を定義。
  - init_schema(db_path) -> DuckDB 接続:
    - db_path の親ディレクトリがなければ自動作成。
    - 各 DDL を実行してテーブル・インデックスを作成（冪等）。
    - ":memory:" サポートあり。
  - get_connection(db_path) -> DuckDB 接続（スキーマ初期化は行わない）。
- 監査（Audit）モジュール (kabusys.data.audit):
  - 戦略→シグナル→発注→約定に至るトレーサビリティを UUID 連鎖で保存する監査用テーブルを追加。
  - DDL（抜粋）:
    - signal_events: 戦略が生成した全てのシグナル（拒否されたもの含む）を保存。
    - order_requests: 発注要求（order_request_id を冪等キーとして機能）。
      - limit/stop/market の価格チェックを CHECK 制約で厳密に検査。
    - executions: 証券会社からの約定情報（broker_execution_id をユニークな冪等キーとして想定）。
  - インデックス群を定義（status ベースのキュー検索、signal_id 関連、broker_order_id 関連 等）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供:
    - 全ての TIMESTAMP を UTC で保存するために conn.execute("SET TimeZone='UTC'") を実行。
    - 既存接続へ冪等に監査テーブルを追加可能。
- パッケージ構造:
  - strategy/, execution/, monitoring/ の初期化ファイルを追加（現時点では空の __init__.py を含む）。

Changed
- 初回リリースのため、過去バージョンからの変更はなし。

Fixed
- 初回リリースのため、修正履歴はなし。

Security
- J-Quants id_token の自動リフレッシュとキャッシュを導入し、認証エラー (401) 発生時の一貫した復旧を実装。
- .env 読み込み時に OS 環境変数を上書きしない保護機能を追加（意図しない環境上書きを防止）。

Deprecated
- なし

Removed
- なし

Notes / マイグレーション
- 初回リリースのためマイグレーションは不要。init_schema / init_audit_db を使用して DuckDB を初期化してください。
- .env 自動ロードはプロジェクトルートの検出に依存するため、パッケージを配布後に動作させる際はプロジェクトルート（.git または pyproject.toml）をパッケージ内に含めない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化するか、環境変数を明示的に設定してください。

問い合わせ / 貢献
- バグ報告・機能要望はリポジトリの Issue を使用してください。 Contributions は歓迎します。