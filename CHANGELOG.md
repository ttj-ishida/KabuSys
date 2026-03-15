CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

[0.1.0] - 2026-03-15
--------------------

Added
- パッケージ初版を追加 (kabusys 0.1.0)
  - パッケージメタ:
    - src/kabusys/__init__.py: __version__ = "0.1.0", __all__ に主要モジュールを公開 (data, strategy, execution, monitoring)

- 環境変数・設定管理
  - src/kabusys/config.py を追加:
    - .env ファイルまたは既存の OS 環境変数から設定を自動読み込みする仕組みを実装。
      - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を探す（CWD に依存しない）。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
      - .env の読み込み失敗時は警告を出力して続行（例外を投げない）。
    - .env パーサは以下をサポート/考慮:
      - 空行や # で始まるコメント行を無視
      - export KEY=val 形式に対応
      - シングル/ダブルクォートされた値内のバックスラッシュエスケープを解釈し、インラインコメントを無視
      - クォートなし値の '#' は、その直前がスペースまたはタブの場合にコメントとみなす（それ以外は値の一部）
    - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得:
      - 必須値は _require() で検証し、未設定時は ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
      - デフォルト値:
        - KABUSYS_API_BASE_URL -> "http://localhost:18080/kabusapi"（kabuステーション用）
        - DUCKDB_PATH -> "data/kabusys.duckdb"
        - SQLITE_PATH -> "data/monitoring.db"
        - KABUSYS_ENV -> "development"（有効値: development, paper_trading, live。無効値は ValueError）
        - LOG_LEVEL -> "INFO"（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL。無効値は ValueError）
      - ヘルパー: is_live / is_paper / is_dev

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py を追加:
    - 基本設計:
      - API ベース URL: https://api.jquants.com/v1
      - レート制限遵守: 120 req/min を固定間隔スロットリングで実装（_RateLimiter, 最小間隔 60/120 = 0.5 秒）。
      - リトライロジック: 最大 3 回の再試行、指数バックオフ（基数 2.0 秒）、対象ステータス 408/429 と 5xx、ネットワークエラーも再試行。
      - 429 の場合は Retry-After ヘッダを優先して待機時間を決定。
      - 401 Unauthorized 受信時はトークン自動リフレッシュを一度だけ行い再試行（無限再帰を防ぐため allow_refresh フラグを使用）。
      - モジュールレベルの ID トークンキャッシュを保持し、ページネーション間で同一トークンを共有。
      - HTTP タイムアウト 30 秒。
    - 認証:
      - get_id_token(refresh_token=None): /token/auth_refresh に POST して idToken を取得（refresh_token は settings.jquants_refresh_token を使用可能）。
    - データ取得関数（ページネーション対応）:
      - fetch_daily_quotes(code/date_from/date_to): 日足（OHLCV）を取得。pagination_key によるページネーション処理。
      - fetch_financial_statements(code/date_from/date_to): 四半期 BS/PL を取得。pagination_key によるページネーション処理。
      - fetch_market_calendar(holiday_division): JPX マーケットカレンダーを取得。
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes(conn, records): raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE を用いて保存。fetched_at は UTC タイムスタンプ（ISO8601 Z 表記）で保存。PK 欠損行はスキップして警告。
      - save_financial_statements(conn, records): raw_financials テーブルへ同様に保存。
      - save_market_calendar(conn, records): market_calendar テーブルへ同様に保存。HolidayDivision を is_trading_day / is_half_day / is_sq_day に変換。
    - ユーティリティ:
      - _to_float/_to_int: 値変換ユーティリティ。空値や変換失敗時は None を返す。_to_int は "1.0" のような文字列を float 経由で許容するが、小数部が 0 以外の場合は None を返し誤った切り捨てを防止。

- DuckDB スキーマ定義と初期化
  - src/kabusys/data/schema.py を追加:
    - DataSchema.md 設計に基づく 3 層（Raw / Processed / Feature）＋Execution 層のテーブル群を定義:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに適切なデータ型・NOT NULL チェック・CHECK 制約・PRIMARY KEY を付与。
    - 頻出クエリ用のインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status 等）。
    - init_schema(db_path): 指定したパスに対してディレクトリ自動作成・テーブル作成を行う冪等初期化関数を提供（":memory:" でインメモリ DB をサポート）。
    - get_connection(db_path): 既存 DB への接続を返す（初期化は行わないことを明記）。

- 監査ログ（トレーサビリティ）
  - src/kabusys/data/audit.py を追加:
    - DataPlatform.md に基づく監査ログテーブル群を追加:
      - signal_events: 戦略が生成したシグナル（全てを記録、棄却やエラーも含む）。decision/理由/created_at 等を保存。
      - order_requests: 発注要求ログ。order_request_id を冪等キーとし、order_type ごとの価格必須チェック（limit/stop のチェック）を実装。status と updated_at を持つ。
      - executions: 証券会社からの約定ログ。broker_execution_id を一意な冪等キーとして保持。
    - すべての TIMESTAMP を UTC で保存するため、init_audit_schema は "SET TimeZone='UTC'" を実行。
    - インデックス群を定義し、検索/ジョイン/キュー処理を高速化。
    - init_audit_schema(conn): 既存の DuckDB 接続に監査テーブルとインデックスを追加（冪等）。
    - init_audit_db(db_path): 監査ログ専用 DB を作成して初期化するヘルパーを提供。

- パッケージ構成（空のパッケージイニシャライザ）
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を追加（モジュール化のためのプレースホルダ）。

Changed
- なし（初版）

Fixed
- なし（初版）

Notes / 実装上の注意
- .env の自動読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後やテスト環境での挙動に注意。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを抑止可能。
- J-Quants クライアントはレート制限・リトライ・トークン自動リフレッシュ等を実装しているが、実動作確認（API レートやエラーレスポンスの差異）により調整が必要な場合がある。
- DuckDB のスキーマは多くの制約・外部キー・インデックスを持つ設計になっているため、既存データをマイグレーションする場合は注意が必要。
- 監査ログは削除しない前提（外部キーは ON DELETE RESTRICT）で設計されている。削除や更新を行う運用はトレーサビリティ上の影響を考慮すること。

Acknowledgements
- 本リリースはシステム設計（DataSchema.md, DataPlatform.md）に基づいた初期実装です。今後の利用状況に応じて API、スキーマ、エラーハンドリング等を改善していきます。