# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを採用しています。
リリース日付はパッケージ内のバージョンに基づき記載しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-16

初回公開リリース。日本株自動売買システム「KabuSys」の基盤モジュール群を実装。

### Added
- パッケージメタ情報
  - kabusys.__version__ = "0.1.0"
  - 公開サブパッケージ: data, strategy, execution, monitoring（strategy/execution/monitoring はプレースホルダ）

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索するため、CWD 非依存で動作。
  - .env/.env.local の自動ロード（優先度: OS 環境 > .env.local > .env）。自動ロードを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ実装: コメント行、export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応。
  - Settings クラスを提供（プロパティ経由で必須設定を取得、未設定時は ValueError を送出）。
  - サポートする設定例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV (development / paper_trading / live), LOG_LEVEL

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得 API 実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を順守する RateLimiter 実装。
  - リトライ: 指数バックオフ（最大 3 回）、対象ステータス 408/429 および 5xx、429 の場合は Retry-After を優先。
  - 認証: refresh_token から id_token を取得する get_id_token()、401 受信時の自動リフレッシュ（1 回のみ）と id_token キャッシュ共有（ページネーション対応）。
  - ページネーション処理対応: fetch_* 関数は pagination_key を使った継続取得をサポート。
  - Look-ahead bias 防止のため取得時刻（fetched_at）を UTC 形式で記録。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性を担保。
  - 値変換ユーティリティ: _to_float / _to_int（厳密な int 変換ルールを含む）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を実装:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 監査系や実行系に必要な制約（PK / FK / CHECK）を細かく定義。
  - 頻出クエリ向けのインデックス定義を実装。
  - init_schema(db_path) によりディレクトリ自動作成を行い、DDL を冪等に適用して接続を返す。get_connection() で既存 DB へ接続可能。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL run_daily_etl() を実装。処理フロー:
    1. 市場カレンダー ETL（先読み lookahead）
    2. 株価日足 ETL（差分 + backfill）
    3. 財務データ ETL（差分 + backfill）
    4. 品質チェック（オプション）
  - 差分更新ロジック: DB の最終取得日から未取得分のみ取得。バックフィル日数（デフォルト 3 日）により後出し修正を吸収。
  - 市場カレンダーはデフォルトで target_date より先に一定日数（デフォルト 90 日）を取得。
  - 品質チェック実行フローとの統合（quality モジュール呼び出し）。
  - ETLResult データクラス: 各ステップの取得数/保存数、品質問題、エラー一覧などを収集。has_errors / has_quality_errors 等のユーティリティを提供。

- 監査ログ（kabusys.data.audit）
  - 監査（トレーサビリティ）用テーブルを別モジュールで分離して実装:
    - signal_events（戦略が生成したシグナルの記録）
    - order_requests（発注要求、order_request_id を冪等キーとして定義）
    - executions（証券会社からの約定ログ、broker_execution_id をユニークな冪等キーとして記録）
  - ステータス列、作成時刻（created_at）、updated_at の運用方針を明記。すべての TIMESTAMP は UTC に統一（init_audit_schema は SET TimeZone='UTC' を実行）。
  - 監査用インデックス群を定義。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。

- データ品質チェック（kabusys.data.quality）
  - QualityIssue データクラスを提供（チェック名、テーブル、severity、detail、サンプル行）。
  - 実装済みチェック:
    - 欠損データ検出（raw_prices の OHLC 欄の NULL を検出）→ check_missing_data()
    - スパイク検出（前日比変動率が閾値を超えるものを検出）→ check_spike()
    - （設計で重複チェック・日付不整合の検出が想定されているが、初期実装での個別関数は上記参照）
  - 各チェックは問題を全件収集し、重大度に応じて呼び出し元で停止判断を行う設計（Fail-Fast ではない）。
  - DuckDB の SQL をパラメータバインドで実行し、効率と安全性を確保。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 認証トークンの取り扱い:
  - J-Quants のリフレッシュトークンは settings.jquants_refresh_token 経由で取得。get_id_token() 呼び出し時に明示的なトークン注入も可能で、テスト容易性を確保。
  - id_token の自動リフレッシュは 401 の場合のみ 1 回に制限し、無限再帰を防止。

### Notes / Migration / Usage
- 初回セットアップ:
  1. .env を用意（.env.example を参照）。
  2. init_schema(settings.duckdb_path) で DuckDB スキーマを初期化。
  3. （監査専用 DB を使用する場合は）init_audit_db(path) を実行。
- 自動 .env ロードを無効化したいテスト等の環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- strategy, execution, monitoring パッケージは名称として公開されているものの、現時点ではモジュール本体は空（プレースホルダ）です。実運用の戦略ロジック・発注実行ロジックは別途実装が必要です。
- DuckDB スキーマの CHECK 制約や FK は厳密に定義しているため、外部システムから書き込む場合はデータ整合性に注意してください。

---

今後の予定（未実装・予定機能の例）
- execution 層の証券会社 API アダプタ（kabuステーション等）と監査ログ連携の実装
- リアルタイム監視・アラート（monitoring）の実装
- 重複チェック・日付不整合チェック等の quality モジュール強化
- ユニットテスト・統合テストの充実

【補足】
上記はコードベースの実装内容から推測して作成した CHANGELOG です。各項目の細部は実際の運用・ドキュメントに合わせて調整してください。