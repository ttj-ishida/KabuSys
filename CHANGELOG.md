# CHANGELOG

すべての重要な変更を記録します。本プロジェクトは Keep a Changelog の形式に準拠します。

なお、本ファイルはコードベースの内容から推測して作成しています（実装された機能・設計に基づく初期リリースの記録）。

## [0.1.0] - 2026-03-16

### 追加 (Added)
- 初期リリースを公開。
- パッケージ構成:
  - kabusys パッケージ本体（__init__.py、バージョン 0.1.0）。
  - サブパッケージ: data, strategy, execution, monitoring（外部公開名を __all__ で定義）。
- 環境設定管理 (src/kabusys/config.py):
  - .env / .env.local の自動読み込み機能（デフォルトで有効）。読み込みの無効化は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - OS 環境変数を保護する読み込みロジック（.env.local は .env を上書き可能だが OS 環境変数は保護）。
  - .env パースの強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート対応（バックスラッシュエスケープ考慮）
    - インラインコメントの扱い（スペース/タブ前の # をコメントとみなす）
  - Settings クラスによる設定プロパティ:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID を必須取得（未設定時は ValueError）。
    - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH のデフォルト値サポート。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証。
    - is_live / is_paper / is_dev ヘルパー。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py):
  - daily quotes（OHLCV）、financial statements（四半期 BS/PL）、market calendar の取得関数を実装（ページネーション対応）。
  - API レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - 冪等な保存処理: DuckDB への INSERT は ON CONFLICT DO UPDATE を用いて重複を排除。
  - リトライロジック:
    - 最大 3 回のリトライ（指数バックオフ、base=2.0 秒）
    - 対象ステータス: 408, 429, その他 5xx
    - 429 の場合は Retry-After ヘッダを優先
  - 認証トークン処理:
    - refresh token から id_token を取得する get_id_token()
    - 401 発生時は id_token を自動リフレッシュして 1 回リトライ（無限再帰防止のため allow_refresh 制御）
    - モジュールレベルの id_token キャッシュを共有（ページネーション間で利用）
  - レスポンスの JSON デコード失敗時に詳細メッセージを出力。
  - save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）で fetched_at を UTC ISO8601（Z 表記）で記録。
  - 値変換ユーティリティ (_to_float, _to_int) を実装（空値・不正値は None、_to_int は小数部が非ゼロの場合は None）。
- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py):
  - DataSchema.md に準拠した 3 層（Raw / Processed / Feature）+ Execution 層のテーブル定義を実装。
  - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など。
  - 制約（PRIMARY KEY / CHECK / FOREIGN KEY）を多く設置してデータ整合性を担保。
  - クエリ性能を考慮したインデックス定義（頻出アクセスパターン向け）。
  - init_schema(db_path) でディレクトリ作成→スキーマ作成（冪等）および DuckDB 接続を返すユーティリティを提供。get_connection() により既存 DB に接続可能。
- ETL パイプライン (src/kabusys/data/pipeline.py):
  - 日次 ETL のエントリポイント run_daily_etl() を実装。処理順:
    1. 市場カレンダー ETL（先読み; デフォルト 90 日）
    2. 株価日足 ETL（差分 + backfill; デフォルト backfill_days=3）
    3. 財務データ ETL（差分 + backfill）
    4. 品質チェック（オプション）
  - 差分更新ロジック: DB の最終取得日から backfill_days 前を再取得することで API の後出し修正を吸収。
  - 取得対象日の営業日補正 (_adjust_to_trading_day) を実装（market_calendar を元に最大 30 日遡るフォールバック含む）。
  - fetch/save を組み合わせた個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl（それぞれ取得数と保存数を返す）。
  - ETLResult データクラスを導入し、各種結果（取得数／保存数／品質問題／エラー）を集約。to_dict() により品質問題をシリアライズ可能。
  - デフォルト最小データ開始日を _MIN_DATA_DATE = 2017-01-01 に設定。
  - 市場カレンダー先読み日数は _CALENDAR_LOOKAHEAD_DAYS = 90。
  - ETL 実行時は各ステップが独立して例外を捕捉し、1 ステップ失敗でも他を継続（Fail-Fast ではない）。
- 品質チェックモジュール (src/kabusys/data/quality.py):
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の open/high/low/close 欠損検出（サンプル最大 10 件を返却）。
    - check_spike: 前日比でのスパイク検出（LAG による前日 close 取得、閾値はデフォルト 50%）。
  - 設計方針: SQL を用いた効率的なチェック、Fail-Fast ではなく全件収集、パラメータバインド利用で注入リスクを低減。
  - pipeline.run_daily_etl() から quality.run_all_checks(...) を呼び出して統合的な品質検査を実行（ETL の一部として収集）。
- 監査ログ（トレーサビリティ）モジュール (src/kabusys/data/audit.py):
  - 監査テーブルを定義（signal_events, order_requests, executions）。
  - 設計原則を反映:
    - UUID を利用したトレーサビリティ階層（signal_id, order_request_id, broker_order_id 等）。
    - order_request_id は冪等キー。
    - すべての TIMESTAMP を UTC で記録（init_audit_schema() は SET TimeZone='UTC' を実行）。
    - 発注・約定のステータス管理、制約とインデックスを整備。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供（いずれも冪等で初期化）。
- 追加の実装上の注意点（ドキュメント・設計反映）:
  - J-Quants クライアントは Look-ahead Bias 防止のため fetched_at を UTC で保存し、いつシステムがデータを取得したかをトレース可能にしている。
  - 各種 INSERT は冪等性を担保（ON CONFLICT DO UPDATE）して重複挿入を防止。
  - ネットワーク/HTTP エラーへの堅牢なハンドリング（リトライ・指数バックオフ・Retry-After 考慮・401 の自動リフレッシュ）。
  - DuckDB のスキーマは外部キー依存順に作成されるようになっている。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注: 本 CHANGELOG は現状のコードベースを元に推測して作成した初版のリリースノートです。実際のリリース日や追加・修正項目はリポジトリの運用ルールに従って更新してください。