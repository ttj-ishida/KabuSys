# CHANGELOG

すべての注目すべき変更点を記録します。本プロジェクトは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-03-16
初期リリース。日本株自動売買システムのコアライブラリを追加。

### 追加 (Added)
- パッケージ基本情報
  - パッケージ名: kabusys、バージョン 0.1.0
  - __all__ に data, strategy, execution, monitoring を公開

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定自動読み込みを実装
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml から検出（CWD に依存しない）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - OS 環境変数を保護する protected 機構
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env の行パーサ実装（export 形式、クォートとバックスラッシュエスケープ、インラインコメントの扱いを考慮）
  - Settings クラスを提供（プロパティで必須/任意設定を取得）
    - 必須環境変数（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値: KABUSYS_ENV=development, LOG_LEVEL=INFO, DB パスのデフォルト（DUCKDB_PATH/SQLITE_PATH）
    - env と log_level の妥当性チェック（有効値セット検証）
    - ヘルパー is_live / is_paper / is_dev

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API ベース実装（_BASE_URL = https://api.jquants.com/v1）
  - レート制限 (120 req/min) を守る固定間隔スロットリング（_RateLimiter）
  - 汎用 HTTP リクエストラッパ (_request)
    - リトライロジック（指数バックオフ、最大 3 回）
    - 再試行対象: HTTP 408, 429 と 5xx 系。429 の場合は Retry-After ヘッダを優先
    - ネットワークエラー（URLError/OSError）に対するリトライ
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰を防止）
    - JSON デコード失敗時の明示的エラー
  - トークン管理
    - get_id_token(refresh_token=None)（POST /token/auth_refresh）
    - モジュールレベルの ID トークンキャッシュを共有（ページネーション間でトークン再利用）
  - データ取得関数（ページネーション対応）
    - fetch_daily_quotes: 日次株価（OHLCV）
    - fetch_financial_statements: 四半期財務（BS/PL）
    - fetch_market_calendar: JPX マーケットカレンダー
  - DuckDB 保存関数（冪等性を担保: ON CONFLICT DO UPDATE）
    - save_daily_quotes → raw_prices テーブルへ保存
    - save_financial_statements → raw_financials テーブルへ保存
    - save_market_calendar → market_calendar テーブルへ保存
  - ユーティリティ関数 _to_float / _to_int（安全な型変換）

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層 + 実行層のテーブル定義を実装
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY, CHECK 句等）を豊富に定義してデータ整合性を保つ
  - インデックス定義（頻出クエリ向け）
  - init_schema(db_path) でディレクトリ自動作成・テーブル作成を行い DuckDB 接続を返す
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計方針と差分更新ロジックを実装
    - run_prices_etl / run_financials_etl / run_calendar_etl：差分取得 + 保存
    - run_daily_etl：市場カレンダー → 株価 → 財務 → 品質チェック の順で実行
  - デフォルト挙動
    - 株価データの最小開始日: 2017-01-01
    - カレンダー先読み: 90 日（_CALENDAR_LOOKAHEAD_DAYS）
    - デフォルトバックフィル: 3 日（_DEFAULT_BACKFILL_DAYS）
  - ETLResult dataclass により実行結果（各取得件数、保存件数、品質問題、エラー）を集約
  - 各ステップは独立したエラーハンドリング（1 ステップ失敗でも他を続行）
  - 品質チェックは run_quality_checks=True で実行し、重大度に応じた判定を可能にする

- 監査ログ（Audit）モジュール (kabusys.data.audit)
  - シグナル → 発注要求 → 約定 のトレーサビリティを記録する DDL を実装
    - signal_events, order_requests, executions テーブル
    - order_request_id を冪等キーとして設計
    - すべての TIMESTAMP を UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）
    - 外部キーは ON DELETE RESTRICT（監査ログは削除しない前提）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供
  - 監査用インデックス群を定義（検索性能を想定）

- データ品質チェック (kabusys.data.quality)
  - QualityIssue dataclass を定義（check_name, table, severity, detail, rows）
  - 実装済みチェック（例）
    - check_missing_data: raw_prices の OHLC 欠損検出（重大度: error）
    - check_spike: 前日比スパイク検出（LAG を用いた SQL で検出、デフォルト閾値 50%）
  - すべてのチェックは問題を全件収集する設計（Fail-Fast ではない）
  - DuckDB 上で SQL により効率的に検査し、パラメータバインドを使用

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### 既知の制限 / 注意事項 (Known issues / Notes)
- run_calendar_etl と jquants_client.fetch_market_calendar のパラメータ不一致
  - pipeline.run_calendar_etl は jq.fetch_market_calendar(id_token=id_token, date_from=date_from, date_to=date_to) を呼び出していますが、現状の jquants_client.fetch_market_calendar のシグネチャは (id_token: str | None = None, holiday_division: str | None = None) となっており、date_from/date_to を受け取りません。このままでは呼び出し時に TypeError になる可能性があります。実装の整合（fetch_market_calendar の引数拡張または pipeline の呼び出し修正）が必要です。
- quality.run_all_checks の実装参照
  - pipeline.run_daily_etl は quality.run_all_checks を呼び出しますが、該当の関数実装がソースに含まれていない場合は呼び出し側で例外となるため、品質チェック統合の確認が必要です。
- fetch_market_calendar のページネーションや date_from/date_to サポート
  - 現時点の実装では市場カレンダーの取得 API 引数のサポート範囲に注意が必要（API の仕様に合わせたパラメータ伝搬確認を推奨）。
- 型変換の設計上の制約
  - _to_int は "1.9" のような小数文字列を意図せず切り捨てないため None を返す仕様。呼び出し側での取り扱いに注意。

### セキュリティ (Security)
- 環境変数の自動読み込み時に OS 環境変数を保護（上書き除外）する仕組みを導入
- HTTP Authorization トークンはモジュール内でキャッシュするが、トークンの取り扱いはアプリ側で適切に保護すること

### マイグレーション / 使用時の注意 (Migration / Usage Notes)
- 初回は data.schema.init_schema(db_path) を呼び出して DuckDB スキーマを初期化してください。
- 自動 .env 読み込みはプロジェクトルート判定に依存するため、配布後も正しく動作させるには .git または pyproject.toml を配置するか、KABUSYS_DISABLE_AUTO_ENV_LOAD をセットして外部から設定を注入してください。
- 必須環境変数が欠けると Settings のプロパティで ValueError が発生します。実行前に以下を設定してください（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- ETL のバックフィルやカレンダー先読み日数は run_daily_etl の引数で調整可能（backfill_days, calendar_lookahead_days）。

---

将来的なリリースでは上記の既知の不整合（カレンダー API 周り、品質チェック統合）を修正し、追加の機能（戦略層、発注実行ラッパ、モニタリング連携など）を追記していきます。