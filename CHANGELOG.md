KEEP A CHANGELOG
すべての変更は Keep a Changelog のフォーマットに従って記録しています。
このプロジェクトでは SemVer を採用しています。

[0.1.0] - 2026-03-15
====================

Added
-----
- 初回リリース: kabusys パッケージの基本機能を追加。
  - パッケージメタデータ
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
    - パッケージ公開対象として data, strategy, execution, monitoring を __all__ に追加。

  - 設定 / 環境変数管理 (src/kabusys/config.py)
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
      - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索（CWD 非依存）。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - 環境変数自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
      - OS 環境変数は保護され、.env の override 時に保護される仕組みを実装。
    - .env の詳細なパーサ実装:
      - コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理、行内コメントの扱いに対応。
    - Settings クラスを公開 (settings):
      - J-Quants / kabuステーション / Slack / データベース / システム設定用プロパティを提供。
      - 必須変数取得時の検査を実装（未設定で ValueError を送出）。
      - KABUSYS_ENV、LOG_LEVEL の値検証（有効な値セットを定義）。
      - デフォルトパス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。

  - J-Quants クライアント (src/kabusys/data/jquants_client.py)
    - API の呼び出しユーティリティを実装:
      - ベース URL、レート制限（120 req/min）に基づく固定間隔スロットリングを実装（_RateLimiter）。
      - リトライロジック（指数バックオフ, 最大 3 回）。リトライ対象ステータス: 408, 429, 5xx。
      - 429 の場合は Retry-After ヘッダを優先して待機。
      - 401 レスポンス受信時は自動で ID トークンをリフレッシュして 1 回だけ再試行（無限再帰防止）。
      - ページネーション対応（pagination_key の取り扱い）とモジュールレベルの ID トークンキャッシュ。
      - JSON デコードエラーやネットワークエラーの適切なラップとログ出力。
    - 認証ヘルパー: get_id_token(refresh_token: Optional[str]) を実装（POST /token/auth_refresh）。
    - データ取得関数:
      - fetch_daily_quotes: 株価日足（OHLCV）をページングで取得。
      - fetch_financial_statements: 四半期財務データをページングで取得。
      - fetch_market_calendar: JPX マーケットカレンダーを取得。
      - 各 fetch は取得件数をログ出力し、id_token を省略した場合はキャッシュを利用して自動リフレッシュを行う。
    - DuckDB への保存関数（冪等性を重視）:
      - save_daily_quotes, save_financial_statements, save_market_calendar を実装。
      - 保存時に fetched_at を UTC タイムスタンプで付与。
      - INSERT ... ON CONFLICT DO UPDATE を使い重複を排除（冪等）。
      - 主キー欠損レコードはスキップし、スキップ件数をログに警告出力。
    - データ変換ユーティリティ:
      - _to_float / _to_int: 安全な型変換ロジック（空値や変換失敗は None、"1.0" 等の扱いに注意）。

  - DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
    - DataLayer を想定したスキーマ定義を実装（Raw / Processed / Feature / Execution 層）。
    - 主なテーブル:
      - Raw: raw_prices, raw_financials, raw_news, raw_executions
      - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature: features, ai_scores
      - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各種 CHECK 制約・主キー・外部キーを定義（データ整合性を重視）。
    - 検索パフォーマンスを想定した索引群を定義。
    - init_schema(db_path) を実装:
      - DB ファイルの親ディレクトリ自動作成、DDL 実行、インデックス作成。冪等性を保証。
      - ":memory:" によるインメモリ DB に対応。
    - get_connection(db_path) を提供（スキーマ初期化は行わない点に注意）。

  - 監査ログ（トレーサビリティ）モジュール (src/kabusys/data/audit.py)
    - 監査テーブル群を定義し、監査用スキーマ初期化機能を提供。
    - 監査対象テーブル:
      - signal_events: 戦略が生成した全シグナルを記録（棄却/エラー含む）。
      - order_requests: 発注要求ログ（order_request_id を冪等キーとして採用）。limit/stop のチェック制約を追加。
      - executions: ブローカーからの約定情報を記録（broker_execution_id をユニーク／冪等扱い）。
    - 監査テーブル用インデックス群を定義（status や日付/銘柄での高速検索を想定）。
    - init_audit_schema(conn) を実装:
      - 既存の DuckDB 接続に監査テーブルを追加。UTC タイムゾーン設定（SET TimeZone='UTC'）。
    - init_audit_db(db_path) を実装: 監査専用 DB を初期化して接続を返す。

  - パッケージ構造
    - data, strategy, execution, monitoring パッケージの空 __init__.py を配置して名前空間を準備。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Security
--------
- （初回リリースのため該当なし）

Notes / 備考
--------------
- 設定に関する必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - これらは settings のプロパティ取得時に存在チェックを行い、未設定時は ValueError を送出します。
- J-Quants クライアントはレート制限やリトライ挙動を明示的に実装しており、運用環境での安定性を考慮しています。
- DuckDB スキーマは冪等的に作成されるため、既存 DB に対して繰り返し初期化を行っても安全です。
- 監査ログは削除しない前提（FOREIGN KEY は ON DELETE RESTRICT）で設計されています。すべての TIMESTAMP は UTC で保存します。
- 自動ロードの挙動やデフォルトパスなどは運用環境に合わせて .env/.env.local や OS 環境変数で上書きしてください。

今後の予定（例）
-----------------
- strategy / execution 層の具体的実装（アルゴリズム、リスク管理、ブローカー連携）。
- monitoring と Slack 通報の実装。
- 単体テスト / CI 環境の整備とテストカバレッジの拡充。