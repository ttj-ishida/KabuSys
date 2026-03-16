# Changelog

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-03-16

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基本コンポーネントを実装。
  - パッケージメタ情報:
    - バージョン: 0.1.0
    - モジュール公開: data, strategy, execution, monitoring

- 設定/環境管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート判定: .git または pyproject.toml を基準に自動探索（CWD に依存しない）。
    - 自動ロードの優先順: OS 環境変数 > .env.local > .env。
    - テスト等で自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いを考慮）。
  - Settings クラスを公開（settings インスタンス）:
    - J-Quants: jquants_refresh_token
    - kabuステーション: kabu_api_password, kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - Slack: slack_bot_token, slack_channel_id
    - DB パス: duckdb_path（デフォルト data/kabusys.duckdb）、sqlite_path（デフォルト data/monitoring.db）
    - 環境/ログ設定: KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL の検証
    - ユーティリティプロパティ: is_live, is_paper, is_dev

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本設計:
    - API レート制限を厳守（120 req/min）する固定間隔スロットリング実装（内部 RateLimiter）。
    - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx に対する再試行。
    - 401 受信時はリフレッシュトークンで自動的に id_token を再取得して 1 回だけリトライ（無限再帰防止）。
    - ページネーション対応（pagination_key を利用）。
    - Look-ahead バイアス防止のため取得時刻（fetched_at）を UTC で記録。
    - 冪等性: DuckDB への保存は ON CONFLICT DO UPDATE を用いる。
  - 主要 API:
    - get_id_token(refresh_token: Optional[str]) -> str : リフレッシュトークンから id_token を取得
    - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...): データ取得（ページネーション対応）
    - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records):
      DuckDB への保存関数（PK 欠損行スキップ・保存件数を返す）
  - モジュールレベルの id_token キャッシュを実装（ページネーションや連続呼び出しで共有）。
  - HTTP レスポンスの JSON デコード失敗やネットワークエラー時の明瞭なエラーメッセージ化。
  - 型変換ユーティリティ: _to_float / _to_int（堅牢な変換ロジック、空値や不正値に対応）

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - データレイヤー（Raw / Processed / Feature / Execution）の DDL を網羅的に定義。
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリパターンを想定して複数インデックスを作成）
  - init_schema(db_path) 関数でディレクトリ自動作成、全テーブルとインデックスの冪等的作成を実装
  - get_connection(db_path) で既存 DB への接続を返すユーティリティ

- 監査ログ（tracing/audit）テーブルと初期化（kabusys.data.audit）
  - トレーサビリティ階層を意識したテーブル群を実装:
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求ログ、order_request_id を冪等キーとして扱う）
    - executions（約定ログ、broker_execution_id をユニークな冪等キーとして記録）
  - 各種制約（CHECK、外部キー）、created_at / updated_at 運用指針を組み込み
  - init_audit_schema(conn) は UTC タイムゾーン設定（SET TimeZone='UTC'）を行い、DDL とインデックスを冪等作成
  - init_audit_db(db_path) で監査専用 DB の初期化をサポート

- データ品質チェックモジュール（kabusys.data.quality）
  - DataPlatform に基づく品質チェックを実装:
    - 欠損データ検出: check_missing_data（raw_prices の OHLC 欠損）
    - 異常値（スパイク）検出: check_spike（前日比によるスパイク検出、デフォルト閾値 50%）
    - 重複チェック: check_duplicates（主キー重複検出）
    - 日付不整合検出: check_date_consistency（未来日付 / market_calendar と整合しないデータ）
    - run_all_checks で全チェックをまとめて実行
  - QualityIssue dataclass による検出結果の標準化（check_name, table, severity, detail, rows）
  - DuckDB に対して効率的な SQL を使ってサンプル行を取得（最大 10 件）し、エラー／警告を集計
  - 非営業日チェックは market_calendar テーブルが存在しない場合は安全にスキップ

### Changed
- 初期リリースのため該当なし

### Fixed
- 初期リリースのため該当なし

### Notes / マイグレーション
- 初回セットアップ手順（例）
  1. 必要な環境変数を設定 (.env をプロジェクトルートに配置、または環境変数で設定)
     - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など
  2. DuckDB スキーマの初期化:
     - from kabusys.data.schema import init_schema
     - conn = init_schema(settings.duckdb_path)
  3. 監査ログを初期化する場合:
     - from kabusys.data.audit import init_audit_schema
     - init_audit_schema(conn)
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
- 監査ログの TIMESTAMP は UTC で保存されます（init_audit_schema は接続に対して SET TimeZone='UTC' を発行します）。
- DuckDB への保存は ON CONFLICT DO UPDATE を利用しているため、通常の再実行で重複データの追記を防ぎます。ただし DB スキーマを手動で変更した場合は注意してください。

### Known issues
- まだユニットテストや外部統合テストの記録は含まれていません（将来追加予定）。
- strategy / execution / monitoring パッケージは初期化モジュールのみ（実装の追加が今後必要）。

---

（本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして公開する際は、実運用での変更点・責任者確認を行ってください。）