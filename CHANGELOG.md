# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
タグ付けやリリースはセマンティックバージョニングに従います。

現在のバージョン: 0.1.0 — 初回公開リリース

## [Unreleased]
（現時点のコードベースでは未リリースの変更はありません）

## [0.1.0] - 2026-03-16
初回リリース。本リポジトリは日本株向け自動売買プラットフォームの基盤モジュールを提供します。主にデータ取得・保存（DuckDB）・ETLパイプライン・品質チェック・監査ログの初期実装を含みます。

### Added
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" に設定し、公開サブパッケージとして data, strategy, execution, monitoring を定義。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。読み込み順序は OS 環境変数 > .env.local > .env。
  - プロジェクトルートを .git または pyproject.toml を基準に検出するロジックを追加（__file__ を基準とするため CWD に依存しない）。
  - .env パーサーを実装：
    - 空行・コメント行を無視、`export KEY=val` 形式対応。
    - シングル／ダブルクォート内のエスケープ処理を考慮して値を抽出。
    - クォートなし値のインラインコメント判定（'#' の直前がスペース/タブの場合にコメントと認識）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途など）。
  - Settings クラスを導入し、J-Quants / kabu API / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）の参照およびバリデーションを提供。
    - 必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定時に ValueError を送出。
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL（DEBUG/INFO/...）の値検証。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する API クライアントを実装。
  - レート制御（_RateLimiter）を実装して J-Quants の 120 req/min 制限に準拠する固定間隔スロットリングを導入。
  - リトライロジック（最大 3 回、指数バックオフ）、およびネットワーク/HTTP エラーコード（408/429/5xx）に対する再試行処理を実装。
  - 401 Unauthorized を検知した場合、自動でリフレッシュトークンから id_token を更新して 1 回リトライする機能を追加（無限再帰防止のため get_id_token 呼び出し時には allow_refresh=False）。
  - ページネーション対応（pagination_key）およびページ間で共有するモジュールレベルの id_token キャッシュを実装。
  - データ取得時に「fetched_at」を UTC で記録する方針（look-ahead bias 回避、いつデータを知ったかのトレーサビリティ）。
  - DuckDB への保存用関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。いずれも冪等性を担保するため ON CONFLICT DO UPDATE を使用。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正値や空値の安全な扱いを確保。

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層（＋監査向け別層）のテーブルを定義する DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw レイヤー、
    prices_daily, market_calendar, fundamentals, news_articles, news_symbols の Processed レイヤー、
    features, ai_scores の Feature レイヤー、
    signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance の Execution レイヤーを定義。
  - 各テーブルに適切な型チェック制約、PRIMARY KEY、FOREIGN KEY を付与。
  - よく使うクエリ用のインデックス群を定義してパフォーマンスを考慮。
  - init_schema(db_path) で DB の親ディレクトリ自動作成、テーブル作成（冪等）および接続返却。get_connection() で既存 DB へ接続可能。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL の実装（run_daily_etl）：
    - 市場カレンダー取得（先読み lookahead_days）、株価日足差分取得（backfill_days による再取得）、財務データ差分取得、品質チェックの順で実行。
    - 各ステップは独立してエラーをハンドリングし、1 ステップ失敗でも他ステップは継続（Fail-Fast ではない）。
    - 差分取得ヘルパー（最終取得日の判定、営業日調整 _adjust_to_trading_day）を実装。
    - run_prices_etl / run_financials_etl / run_calendar_etl を分離して単体で呼び出し可能。
    - ETLResult データクラスを導入し取得件数、保存件数、品質問題、エラーを集約して返却。
    - デフォルトのバックフィルは 3 日、カレンダー先読みは 90 日、初回ロード用の最小開始日を 2017-01-01 に設定。

- 監査ログ（kabusys.data.audit）
  - シグナルから約定までのトレーサビリティを保つ監査テーブル群を実装（signal_events, order_requests, executions）。
  - UUID ベースのトレーサビリティ階層を採用（business_date -> strategy_id -> signal_id -> order_request_id -> broker_order_id）。
  - 発注要求（order_requests）は冪等キー order_request_id を持ち、limit/stop/market のチェックや制約を定義。
  - executions テーブルは証券会社側の約定 ID を一意に保持し、ON DELETE RESTRICT により監査証跡を保護。
  - すべての TIMESTAMP を UTC で保存する方針を採用（init_audit_schema で SET TimeZone='UTC' を実行）。
  - 監査用インデックス群（処理待ち検索、signal_id/日付検索、broker_order_id 検索など）を定義。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供し、既存の DuckDB に監査テーブルを追加可能。

- データ品質チェック（kabusys.data.quality）
  - 欠損データ検出（raw_prices の OHLC 欄）、スパイク検出（前日比絶対変化率が閾値超）、重複（主キー重複）、日付不整合（将来日付・非営業日）などのチェック設計を実装。
  - QualityIssue データクラスを導入し、check_name / table / severity / detail / rows（サンプル）を返却。
  - check_missing_data(), check_spike() 等の関数を実装し、ETL 後に run_all_checks から利用可能な設計（ETL 側で run_all_checks を呼び出して結果を集約できる）。
  - SQL を用いた効率的な実装、パラメータバインド（?）を使用してインジェクションを防止。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の保護:
  - .env 自動ロード時に既存の OS 環境変数を protected として上書きを防止する仕組みを導入（.env と .env.local の読み込みロジック）。
- API トークンの取り扱い:
  - id_token の自動リフレッシュを実装する際に allow_refresh フラグで無限再帰を防止。

### Notes / Migration / 使用上の注意
- 初回セットアップ:
  - DuckDB スキーマ作成は data.schema.init_schema(db_path) を呼び出してください。監査テーブルは init_audit_schema(conn) で追加可能です。
- タイムゾーン:
  - 監査ログ周りは UTC 固定で保存されます。監査用の接続初期化時に TimeZone='UTC' が設定されます。
- 環境変数自動読み込みの無効化:
  - テスト等で .env の自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ETL の挙動:
  - run_daily_etl は品質チェックで重大な問題（severity="error"）が検出されても ETL 自体を中断せず、結果オブジェクト内に問題を集約します。呼び出し元で措置を判断してください。
- API レート制限:
  - jquants_client は J-Quants のレート制限に合わせた固定間隔スロットリングを行いますが、複数プロセス・複数ホストから同一 API を叩く場合は注意が必要です（グローバル共有のレートリミッタはプロセス内スコープのみ）。

フィードバックや改善要求があれば issue を作成してください。今後は strategy / execution / monitoring 層の実装強化、テストカバレッジ追加、各種エラーハンドリングの堅牢化、CI/CD での DB マイグレーション運用などを予定しています。