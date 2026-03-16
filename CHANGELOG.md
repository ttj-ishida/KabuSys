# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

## [Unreleased]

## [0.1.0] - 2026-03-16

### 追加 (Added)
- 初期リリース: KabuSys 日本株自動売買システムの基盤機能を実装。
- パッケージ公開:
  - トップレベルパッケージ kabusys として data, strategy, execution, monitoring モジュールを公開（strategy / execution / monitoring は初期は空の __init__）。
  - バージョン情報: 0.1.0。
- 環境設定管理 (kabusys.config):
  - .env ファイルまたは環境変数から設定を自動読み込み。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - プロジェクトルート検出: .git または pyproject.toml を基準にファイルの親階層からプロジェクトルートを特定。
  - .env 行パーサ実装:
    - `export KEY=val` 構文対応、シングル/ダブルクォートのエスケープ考慮、行内コメント処理等に対応。
  - Settings クラス:
    - J-Quants / kabu API / Slack / DB パス / 環境モード（development/paper_trading/live）/ログレベルのプロパティを提供。
    - 必須環境変数のチェック（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
    - デフォルト値とバリデーション（env, log_level の有効値チェック）。
- J-Quants クライアント (kabusys.data.jquants_client):
  - API 呼び出しユーティリティを実装（JSON 取得、タイムアウト、エラーハンドリング）。
  - レート制限制御: 固定間隔スロットリングで 120 req/min を順守する _RateLimiter 実装。
  - 再試行戦略:
    - 指数バックオフ、最大試行回数 3、対象ステータス (408, 429, >=500)。
    - 429 の場合は Retry-After ヘッダを優先。
    - ネットワーク・URLError に対するリトライ。
  - トークン管理:
    - リフレッシュトークンから idToken を取得する get_id_token。
    - ページネーション間で共有するモジュールレベルの ID トークンキャッシュと 401 受信時の自動リフレッシュ（1 回のみ）。
  - データ取得関数:
    - fetch_daily_quotes（OHLCV, ページネーション対応）
    - fetch_financial_statements（四半期 BS/PL, ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
    - 取得時にログ出力・ページネーションキー重複回避
  - DuckDB への保存関数（冪等性を重視）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 各関数は fetched_at を UTC タイムスタンプで記録し、ON CONFLICT DO UPDATE により重複を排除。
    - PK 欠損行はスキップしてログ出力。
  - ユーティリティ関数: 型変換ヘルパー _to_float/_to_int（空値や不正値の扱いを明示）。
- スキーマ定義 (kabusys.data.schema):
  - DuckDB 用の包括的スキーマを定義（Raw / Processed / Feature / Execution レイヤー）。
  - 各種テーブル（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）と制約（PK, CHECK, FK）を定義。
  - クエリパターンを考慮したインデックスを作成（例: code×date、status 系）。
  - init_schema(db_path) によりディレクトリ作成 → テーブル/インデックス生成（冪等）。
  - get_connection(db_path) で既存 DB への接続を提供。
- ETL パイプライン (kabusys.data.pipeline):
  - 日次 ETL (run_daily_etl) の実装:
    - 市場カレンダー取得（先読み lookahead）、株価・財務データの差分取得（backfill を含む）、品質チェックの順で実行。
    - 各ステップは独立して例外を捕捉し、他ステップを継続（Fail-Fast ではない）。
    - トレーディングデイ調整（market_calendar に基づき非営業日は直近営業日に調整）。
    - 差分更新の算出 helper（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
    - run_prices_etl / run_financials_etl / run_calendar_etl の実装（差分ロジック、バックフィル、保存呼び出し）。
  - ETLResult データクラス: 実行結果・品質問題・エラーを集約して返却（to_dict で整形可能）。
- 監査ログ (kabusys.data.audit):
  - シグナル→発注→約定までを UUID 連鎖で追跡する監査用テーブルを定義:
    - signal_events（戦略が生成したシグナル全件を記録）
    - order_requests（冪等キー order_request_id、注文タイプ別チェック、更新用 updated_at）
    - executions（証券会社の約定を記録、broker_execution_id をユニーク冪等キーとして扱う）
  - 監査用インデックス群を定義（status / strategy_id / broker_order_id 等）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供し、UTC タイムゾーンを設定して初期化。
- データ品質チェック (kabusys.data.quality):
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - チェック実装（duckdb SQL ベース）:
    - 欠損データ検出（raw_prices の OHLC 欄）
    - スパイク検出（前日比の変動率が閾値を超えるレコード）
    - （設計に重複チェック、日付不整合検出も記載）
  - 各チェックは全件収集方式で問題を一覧化し、呼び出し元が重大度に応じて処理を判断可能。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### 注意事項 (Notes)
- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。これらが未設定の場合、Settings の該当プロパティ呼び出しで ValueError を送出。
- DuckDB のデフォルトパス:
  - DUCKDB_PATH デフォルト: data/kabusys.duckdb
  - SQLITE_PATH デフォルト: data/monitoring.db
- run_daily_etl は品質チェックでエラーが検出されても自動停止しない（結果に品質問題を集約して返す）。重大度の扱いは呼び出し元で判断すること。
- audit スキーマは削除前提を想定していない（FK は ON DELETE RESTRICT）。監査ログは原則削除しない設計。

### 既知の制限 (Known limitations)
- strategy / execution / monitoring モジュールは初期は空実装（将来的に戦略・発注実装を追加予定）。
- J-Quants API の rate limit は固定スロットリングで実装しているため、より高度なバースト対応が必要な場合は将来的な改善対象。

---

（以降はバージョン履歴をここに追加してください）