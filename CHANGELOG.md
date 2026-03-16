# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-16

### Added
- パッケージ初期リリース "KabuSys"（src/kabusys）
  - パッケージメタ情報と公開モジュールを定義（src/kabusys/__init__.py）。
  - モジュール構成: data, strategy, execution, monitoring（現時点で一部はプレースホルダ）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env/.env.local の読み込み順・上書きルール実装（OS 環境変数は保護）。
  - .env のパース機能: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープをサポート。
  - Settings クラスによる型付きプロパティ:
    - J-Quants / kabu station / Slack / DB パス（DuckDB / SQLite）などの必須/省略可能設定取得。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
  - 必須環境変数未設定時は ValueError を送出する _require ロジック。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しの汎用リクエスト実装（JSON デコード、タイムアウト、ヘッダ設定）。
  - レート制限実装: 固定間隔スロットリングで 120 req/min を尊重（_RateLimiter）。
  - リトライ実装: 指数バックオフ、最大 3 回、408/429/5xx を対象。429 の場合は Retry-After ヘッダ優先。
  - 401 エラー時の自動トークンリフレッシュ（1 回まで）と再試行処理。
  - id_token のキャッシュ共有と強制リフレッシュ機構。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB 保存関数（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - すべて ON CONFLICT DO UPDATE を使用して重複を排除し更新を許容
    - fetched_at を UTC タイムスタンプ（ISO 8601, "Z"）で記録
  - 値変換ユーティリティ: _to_float, _to_int（厳格な int 変換ルールを含む）

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - 3 層データモデル（Raw / Processed / Feature）と Execution 層を含む包括的な DDL を実装。
  - Raw テーブル: raw_prices, raw_financials, raw_news, raw_executions 等。
  - Processed テーブル: prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等。
  - Feature テーブル: features, ai_scores。
  - Execution テーブル: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - パフォーマンスを考慮したインデックス定義群。
  - init_schema(db_path) による冪等な初期化（親ディレクトリ自動作成、:memory: サポート）。
  - get_connection(db_path) による既存 DB への接続取得（スキーマ初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL のワークフローを実装（差分取得 → 保存 → 品質チェック）。
  - 差分更新ロジック:
    - 最終取得日からの自動算出（初回は J-Quants の最小データ日付を使用）
    - backfill_days による再取得（デフォルト 3 日）で API の後出しを吸収
  - 市場カレンダーの先読み（デフォルト 90 日）を実装し、営業日調整に利用
  - ETLResult データクラスによる実行結果（取得件数、保存件数、品質問題、エラー等）の集約
  - 個別ジョブ:
    - run_prices_etl, run_financials_etl, run_calendar_etl（各々差分取得＋保存）
  - run_daily_etl: カレンダー → 価格 → 財務 → 品質チェック の順で実行。各ステップは独立してエラー処理（1 ステップ失敗でも他は継続）する設計。
  - 品質チェックの注入（run_quality_checks 引数）と spike_threshold の可変化。

- 監査ログ（Audit）スキーマ（src/kabusys/data/audit.py）
  - シグナル→発注要求→約定までトレース可能な監査テーブルを定義:
    - signal_events, order_requests, executions
  - 冪等キー（order_request_id / broker_execution_id 等）と厳密なチェック制約、FK（ON DELETE RESTRICT）を採用。
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化（UTC タイムゾーン固定）。
  - 発注ロジックへ適用可能なステータス列と更新タイムスタンプ仕様。

- データ品質チェックモジュール（src/kabusys/data/quality.py）
  - QualityIssue データクラスで品質問題を表現（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - 欠損データ検出（raw_prices の OHLC 欄）
    - スパイク検出（前日比の変動率が閾値を超える場合、デフォルト閾値 50%）
    - （設計に重複チェック、日付不整合検出も記載。現コードは主要チェックを実装中）
  - DuckDB 上で効率的に SQL による検査を行い、サンプル行を返却。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

Notes / 補足
- J-Quants API 呼び出しに関する詳細（レート制限、リトライ、トークンリフレッシュ）は jquants_client に実装されており、運用時の安定性を重視しています。
- DuckDB スキーマは冪等に作成されるため、既存データベースへの追加入力が容易です。監査ログは削除しない設計（トレーサビリティ重視）です。
- .env の自動読み込みはプロジェクトルート検出に依存します。パッケージ配布後の環境やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化してください。

今後の予定（例）
- strategy / execution 層の具体実装（発注ロジックとブローカー連携）
- 追加品質チェック（重複・未来日付など）の実装完了
- CI/テスト用の ID トークンモックや API モックの整備
- ドキュメント（DataSchema.md, DataPlatform.md 参照）の公開（現コードに設計意図を多数コメントとして含む）