# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。初回公開リリースの変更点をコードベースから推測して記載しています。

全般な注意:
- 本リリースは初回（0.1.0）と想定しています。
- 日付は本回答作成日時です（2026-03-16）。
- 各項目はコード内 API / 挙動を基に要約しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-16

初期リリース。日本株自動売買プラットフォームの基礎モジュール群を追加。

### Added
- パッケージ基本情報
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - パッケージ公開 API: data, strategy, execution, monitoring をエクスポート。

- 環境設定モジュール（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から自動検出）。
  - .env パーサー: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、無効行（空行/コメント）の無視に対応。
  - 自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テストなどで利用可能）。
  - Settings クラスを追加し、環境変数から設定値を取得（必須トークン取得で未設定時は ValueError を送出）。
    - J-Quants, kabu ステーション, Slack, DB パス等の設定プロパティを提供。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）に対するバリデーションを実装（有効値を限定）。
  - デフォルトの DB パス: DuckDB は data/kabusys.duckdb、SQLite は data/monitoring.db。Path.expanduser を使用。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティを実装（_request）。
    - ベース URL: https://api.jquants.com/v1。
    - レート制限（120 req/min）を _RateLimiter で制御。
    - リトライロジック（指数バックオフ、最大 3 回、ネットワーク系 / 429 / 408 / 5xx を再試行対象）。
    - 401 Unauthorized 受信時はトークンを自動リフレッシュして 1 回だけ再試行（無限再帰回避）。
    - JSON デコード失敗時の明確なエラー。
  - get_id_token(): リフレッシュトークンから idToken を取得する POST 実装（テスト容易性のため refresh_token を注入可能）。
  - ページネーション対応のデータ取得関数を追加:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (四半期財務)
    - fetch_market_calendar (JPX マーケットカレンダー)
    - ページネーションキー共有のためのモジュールレベルのトークンキャッシュを実装。
  - DuckDB への保存関数（冪等 / upsert 実装）を追加:
    - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
    - 保存時に fetched_at を UTC タイムスタンプで付与し、PK 欠損はスキップして警告ログ出力。
  - 型変換ユーティリティ:
    - _to_float, _to_int（"1.0" 等のケースや不正値を安全に扱うロジックを含む）。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DataPlatform 設計に従った多層スキーマを定義（Raw / Processed / Feature / Execution 層）。
  - 主要テーブルを定義:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックスを多数定義し、頻出クエリを最適化（例: code×date、status 検索など）。
  - init_schema(db_path) を追加し、ディレクトリ自動作成・DDL 実行を行う（冪等）。
  - get_connection(db_path) により既存 DB への接続を返す（初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL 実装（run_daily_etl）:
    - 市場カレンダー ETL → 株価日足 ETL → 財務データ ETL → 品質チェック（オプション）の順序。
    - 各ステップは独立してエラーハンドリングされ、1 ステップ失敗でも他のステップは継続（エラーは result.errors に蓄積）。
    - 差分更新ロジック: DB の最終取得日から未取得レンジを自動算出。デフォルトのバックフィルは 3 日（_DEFAULT_BACKFILL_DAYS）。
    - カレンダー先読み: デフォルト 90 日（_CALENDAR_LOOKAHEAD_DAYS）。
    - ETLResult データクラスを導入し、取得件数・保存件数・品質問題・エラーの収集と to_dict() を提供。
  - 個別 ETL ジョブ:
    - run_prices_etl, run_financials_etl, run_calendar_etl（差分・バックフィル・ページネーション対応）。
    - 対象日が非営業日の場合、_adjust_to_trading_day により直近の営業日に調整。

- 監査ログ（トレーサビリティ）スキーマ（src/kabusys/data/audit.py）
  - シグナル→発注要求→約定の階層を UUID 連鎖でトレース可能にする監査テーブルを追加:
    - signal_events, order_requests, executions を定義。
  - order_request_id を冪等キーとして再送防止を考慮した制約とチェックを導入（limit/stop/market の価格チェック等）。
  - 全 TIMESTAMP を UTC 保存するため init_audit_schema() 内で SET TimeZone='UTC' を実行。
  - インデックス定義により日付・銘柄検索、status スキャン、broker_order_id による紐付けを効率化。
  - init_audit_schema(conn) / init_audit_db(db_path) により既存接続・専用 DB の初期化をサポート。

- データ品質チェックモジュール（src/kabusys/data/quality.py）
  - QualityIssue データクラスを追加（check_name, table, severity, detail, sample rows）。
  - チェック実装（少なくとも以下を提供）:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は対象外）。問題は severity="error" として報告。
    - check_spike: 前日比スパイク検出（LAG を使った SQL 実装）。デフォルト閾値 50%。
  - 設計方針として Fail-Fast ではなく全件収集し、呼び出し元で重大度に応じて判断するスタイル。

- パッケージ構成のプレースホルダ
  - strategy, execution, monitoring のパッケージ初期化ファイルを追加（現時点では実装なし / 将来的拡張の余地を残す）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 認証トークンは明示的に環境変数経由で取得される設計（Settings にて必須チェック）。
- .env の読み込み時に OS 環境変数を保護（.env.local は上書き可能だが、既存の OS 環境変数は protected される実装）。

### Notes / Migration / Usage
- 環境変数必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID が Settings により必須となるため、.env を準備してください。エラー時は ValueError が発生します。
- 自動 .env 読み込みはプロジェクトルート検出に依存するため、配布環境での利用時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定するか、環境変数を直接設定してください。
- DuckDB の初回セットアップは data.schema.init_schema(db_path) を使用。監査ログは init_audit_schema(conn) または init_audit_db(db_path) を用いて追加・初期化します。
- J-Quants API 呼び出しポリシー:
  - レート上限 120 req/min を守る実装。
  - リトライは最大 3 回（401 は自動リフレッシュを1回試行）。
- ETL 実行例:
  - run_daily_etl(conn) を呼ぶとカレンダー・株価・財務を差分取得して保存し、品質チェックを実行して ETLResult を返す。
- 監査テーブルは削除を前提としない運用（ON DELETE RESTRICT）で、すべての監査データを保持する設計。

---

今後の予定（コード構造より推測）
- strategy / execution / monitoring モジュールの実装（シグナル生成、発注連携、監視・通知）。
- quality モジュールの追加チェック（重複チェック、将来日付/営業日外データ検出、総合 run_all_checks 実装の確定）。
- テストケース整備と CI の導入（環境変数依存の分離、モック可能な id_token 注入等）。

(以上)