# Changelog

すべての変更点は Keep a Changelog のフォーマットに準拠します。  
初版リリースを記録しています。

## [0.1.0] - 2026-03-15

### Added
- 基本パッケージの初期実装を追加（kabusys 0.1.0）。
  - src/kabusys/__init__.py
    - パッケージ名とバージョンを定義（__version__ = "0.1.0"）。
    - 公開モジュール一覧を __all__ で指定（data, strategy, execution, monitoring）。

- 環境変数 / 設定管理モジュールを追加。
  - src/kabusys/config.py
    - .env ファイルおよび環境変数からの設定値自動読み込み機能を実装。
      - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を探すため、CWD に依存しない自動ロード。
      - 読み込み優先順位: OS環境変数 > .env.local > .env。
      - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
      - OS既存環境変数を保護するための上書き制御（protected set）。
    - .env パーサ実装（_parse_env_line）:
      - export KEY=val 形式対応、シングル／ダブルクォートのエスケープ処理対応、インラインコメントルール等を考慮した堅牢なパース。
    - Settings クラスを提供（settings インスタンス）
      - J-Quants / kabu ステーション / Slack / データベースパス等のプロパティを定義。
      - 必須環境変数取得時は未設定で ValueError を送出する _require を採用（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
      - デフォルト値:
        - KABU_API_BASE_URL: "http://localhost:18080/kabusapi"
        - DUCKDB_PATH: "data/kabusys.duckdb"
        - SQLITE_PATH: "data/monitoring.db"
        - KABUSYS_ENV: "development"
        - LOG_LEVEL: "INFO"
      - KABUSYS_ENV の検証（development / paper_trading / live のみ許可）と、LOG_LEVEL 値検証を追加。
      - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- J-Quants API クライアントを追加。
  - src/kabusys/data/jquants_client.py
    - API ベースURL、レート制限（120 req/min）に基づく固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大リトライ 3 回、対象ステータス: 408, 429, >=500）。429 の場合は Retry-After ヘッダを優先。
    - 401 受信時のトークン自動リフレッシュ（1 回だけ）およびトークンキャッシュ（モジュールレベル _ID_TOKEN_CACHE）。
    - JSON デコード失敗時の明示的エラー報告。
    - データ取得関数（ページネーション対応）:
      - fetch_daily_quotes: 日足（OHLCV）を取得
      - fetch_financial_statements: 四半期財務データを取得
      - fetch_market_calendar: JPX マーケットカレンダーを取得
    - DuckDB への保存関数（冪等、ON CONFLICT DO UPDATE を使用）:
      - save_daily_quotes: raw_prices テーブルへ保存（date, code を PK）
      - save_financial_statements: raw_financials テーブルへ保存（code, report_date, period_type を PK）
      - save_market_calendar: market_calendar テーブルへ保存（date を PK）
    - Look-ahead Bias 防止のため、fetched_at を UTC タイムスタンプで保存。
    - 型変換ユーティリティ:
      - _to_float: 安全に float に変換（失敗時は None）
      - _to_int: 整数に変換（"1.0" は許容するが "1.9" のような小数は None を返す）

- DuckDB スキーマ定義と初期化モジュールを追加。
  - src/kabusys/data/schema.py
    - DataSchema.md に基づく 3 層＋Execution 層のテーブル定義を実装:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - テーブルの整合性を考慮した作成順序、各種制約（CHECK / PRIMARY KEY / FOREIGN KEY）を含む DDL を提供。
    - よく使われるクエリパターンに対応するインデックスを定義。
    - init_schema(db_path) により DuckDB を初期化（親ディレクトリの自動作成、":memory:" 対応）。
    - get_connection(db_path) で既存 DB への接続を返す（初期化は行わないことを明記）。

- 監査ログ（トレーサビリティ）モジュールを追加。
  - src/kabusys/data/audit.py
    - 戦略から約定までの監査トレース用テーブルを定義:
      - signal_events: 戦略が生成したシグナルのログ（決定結果／棄却理由などを含む）
      - order_requests: 発注要求ログ（order_request_id を冪等キーとして扱う、limit/stop の価格チェックを含む）
      - executions: 実際の約定ログ（broker_execution_id をユニーク冪等キーとして扱う）
    - 監査用インデックス群を定義（戦略／日付検索、status スキャン、broker_order_id での紐付け等）。
    - init_audit_schema(conn) で既存の DuckDB 接続に監査テーブルを追加、UTC タイムスタンプ保存（SET TimeZone='UTC'）。
    - init_audit_db(db_path) で監査専用 DB を初期化して接続を返す。

- プレースホルダパッケージモジュールを追加（現在は空の __init__.py）。
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/monitoring/__init__.py
  - src/kabusys/data/__init__.py

### Changed
- （初版）該当なし

### Fixed
- （初版）該当なし

### Notes / 設計上の指針
- API 周り:
  - J-Quants API はレート制限を厳守する設計（_RateLimiter）。
  - 401 エラー時は自動でリフレッシュを試みる（1 回）ため、長時間実行でもトークン更新を透過的に扱える。
  - ページネーション用の pagination_key を追跡し、重複ループを防止。
- データ永続化:
  - DuckDB への保存は冪等性を重視（ON CONFLICT DO UPDATE を使用）。
  - fetched_at / created_at は UTC を基本とし、トレーサビリティを確保。
- 監査 / トレーサビリティ:
  - order_request_id や broker_execution_id を使って一意に追跡可能とし、二重発注や重複約定の管理を容易にする設計。
  - 監査ログは削除しない前提（外部キーは ON DELETE RESTRICT）。
- 環境設定:
  - .env パースはシェル風の表記（export を含む）やクォート、エスケープ、コメントを考慮する堅牢実装。
  - OS 環境変数をプロテクトして上書きを防止可能。

### Breaking Changes
- （初版）該当なし

---

以上が初期リリース（0.1.0）の変更点です。今後のリリースでは各層（戦略、実行、監視）の具体実装、テスト追加、ドキュメント整備（DataSchema.md, DataPlatform.md 等の参照実装）を予定しています。