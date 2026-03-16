# Changelog

すべての注目すべき変更はここに記載します。
このファイルは「Keep a Changelog」仕様に従っています。  

注: この変更履歴はソースコードから推測して作成した初期リリースノートです。

## [Unreleased]

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システム「KabuSys」のコア基盤を実装しています。
以下は主要な追加点・設計上の重要事項の要約です。

### Added
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - 主要サブパッケージを公開 (`data`, `strategy`, `execution`, `monitoring`)。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env 読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - export 形式やクォート、インラインコメントの扱いを考慮した .env パーサを実装。
  - 自動読み込みを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` に対応。
  - 必須設定取得時に未設定なら例外を投げる `_require()` を提供。
  - デフォルト値や検証付きプロパティ:
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
    - DB パス: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - 環境: KABUSYS_ENV（development/paper_trading/live の検証あり）
    - ログレベル: LOG_LEVEL（DEBUG/INFO/... の検証あり）

- J-Quants クライアント (`kabusys.data.jquants_client`)
  - API 呼び出しの共通処理 `_request` を実装。機能:
    - レート制御（120 req/min 固定間隔スロットリング）を内部 RateLimiter で実装。
    - リトライロジック（指数バックオフ、最大3回、ネットワーク系や 408/429/5xx を対象）。
    - 401 受信時はリフレッシュトークンで自動的に id_token を更新して 1 回リトライ。
    - JSON デコードエラーやタイムアウトに対する適切な例外処理。
    - ページネーション対応（pagination_key の追跡）。
    - fetched_at を UTC タイムスタンプで付与する方針（Look-ahead Bias 対策）。
  - 認証ヘルパー `get_id_token`（リフレッシュトークンから idToken を取得）。
  - データ取得関数:
    - fetch_daily_quotes（株価日足: OHLCV）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等設計、ON CONFLICT DO UPDATE）:
    - save_daily_quotes -> raw_prices テーブルへ保存（PK 欠損行のスキップと警告）
    - save_financial_statements -> raw_financials テーブルへ保存
    - save_market_calendar -> market_calendar テーブルへ保存（is_trading_day/is_half_day/is_sq_day を型安全に格納）

- DuckDB スキーマ定義と初期化 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution の 3 層＋監査を意識した広範なテーブル群を定義。
  - 主要テーブル例:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 型チェックや CHECK 制約、外部キーを含む DDL を用意。
  - 頻出クエリに対するインデックスを定義（コード×日付やステータス検索など）。
  - init_schema(db_path) で DB ファイルの親ディレクトリ作成 → テーブル作成（冪等） → DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わないことに注意）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - 日次 ETL のエントリ `run_daily_etl` を実装。処理フロー:
    1. 市場カレンダー ETL（デフォルト先読み 90 日）
    2. 株価日足 ETL（差分更新 + バックフィル、デフォルト backfill_days=3）
    3. 財務データ ETL（差分更新 + バックフィル）
    4. 品質チェック（オプション）
  - 差分更新のための補助:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - _adjust_to_trading_day（非営業日の場合の調整、最大30日遡る）
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl（それぞれ差分ロジックと保存を行い取得数/保存数を返す）
  - ETLResult データクラスを定義（取得数・保存数・品質問題・エラーメッセージを集約）。
  - 各ステップは独立したエラーハンドリング（1 ステップ失敗でも他ステップは継続）。

- 監査ログ（トレーサビリティ）モジュール (`kabusys.data.audit`)
  - シグナルから約定までを UUID 連鎖で追跡する監査テーブルを提供。
  - テーブル:
    - signal_events（戦略が生成したシグナル、棄却やエラーも記録）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社からの約定ログ、broker_execution_id をユニークキーとして扱う）
  - 全 TIMESTAMP を UTC 保存にするため init_audit_schema で `SET TimeZone='UTC'` を実行。
  - init_audit_db(db_path) で専用監査 DB を初期化して接続を返す。
  - インデックス群を定義（status 検索、signal→order、broker_order_id 紐付け等）。

- データ品質チェックモジュール (`kabusys.data.quality`)
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - チェック実装（SQL ベース、DuckDB 接続を受け取り効率的に処理）:
    - check_missing_data: raw_prices の OHLC 欠損行を検出（volume は対象外）。検出時は severity="error" を返す。
    - check_spike: 前日比でのスパイク検出（デフォルト閾値 = 50%）。LAG ウィンドウ関数を用いた実装。
  - 各チェックは最大サンプル 10 行を返し、呼び出し側で重大度に応じて処理を決定できる（Fail-Fast ではない）。

### Notes / 使用上の重要なポイント
- 環境変数の自動読み込み
  - プロジェクトルート検出に失敗すると自動読み込みはスキップされる。
  - テスト等で自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は Settings プロパティで参照時に検証・例外を投げます。

- J-Quants API 呼び出し
  - レート制限（120 req/min）を守るため内部でスロットリングを行います。大量同時リクエストの際は待ちが発生します。
  - 401 発生時は id_token を自動更新して 1 回まで再試行します（無限再帰防止のため get_id_token 呼び出しでは allow_refresh=False）。
  - リトライは最大 3 回（指数バックオフ、429 の Retry-After を尊重）。

- DuckDB スキーマ & 初期化
  - 初回は必ず init_schema(db_path) を実行してテーブルを作成してください（既存テーブルがあればスキップされます）。
  - 監査ログを利用する場合は init_audit_schema(conn) を呼ぶか、init_audit_db を利用してください。
  - デフォルトの DuckDB パスは data/kabusys.duckdb（Settings.duckdb_path）です。":memory:" を渡すことでインメモリ DB を利用可能。

- ETL
  - run_daily_etl はデフォルトで品質チェックを実行します（品質チェックがエラーを返しても ETL 自体は可能な限り継続し、結果を ETLResult に集約します）。
  - バックフィル日数やスパイク閾値などは引数で調整可能です。

### Fixed
- 初回リリースのため該当なし

### Changed
- 初回リリースのため該当なし

### Removed
- 初回リリースのため該当なし

---

開発者向け補足（簡易手順）
- DB 初期化:
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)
- 監査 DB 初期化（別 DB を使う場合）:
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
- 日次 ETL 実行:
  - from kabusys.data.pipeline import run_daily_etl
  - res = run_daily_etl(conn)
  - res.to_dict() で結果の辞書化が可能

詳しい API 仕様や追加のユーティリティは今後のリリースで追記予定です。