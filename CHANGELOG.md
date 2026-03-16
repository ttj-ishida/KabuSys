KEEP A CHANGELOG（準拠）

すべての重要な変更はここに記録します。フォーマットは Keep a Changelog に準拠しています。

なお、本CHANGELOGは与えられたコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

Unreleased
---------
（なし）

0.1.0 - 2026-03-16
------------------
Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: __version__ = "0.1.0"、公開モジュールリスト __all__ を設定（data, strategy, execution, monitoring）。

- 環境変数・設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 自動読み込みの優先順位: OS環境変数 > .env.local > .env
    - 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
  - 強化された .env パーサー:
    - コメント行、export プレフィックス（export KEY=val）をサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
    - クォート無しの行でのインラインコメント判定の細かな取り扱い。
  - Settings クラスを提供し、以下の主要設定をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（allowed: development, paper_trading, live。デフォルト: development）
    - LOG_LEVEL（allowed: DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO）
    - is_live / is_paper / is_dev のブール判定プロパティ

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装（_request）。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）。対象: ネットワーク系エラー + 408/429/5xx。
    - 401 Unauthorized 受信時はリフレッシュを自動試行して 1 回リトライ（id_token の自動更新）。
    - ページネーション対応（pagination_key を扱う）。
    - JSON デコード失敗時の適切なエラーメッセージ。
  - id_token のキャッシュをモジュールレベルで保持し、ページネーション間で共有する実装（_ID_TOKEN_CACHE）。
  - API の高レベル関数を提供:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(...) -> list[dict]
    - fetch_financial_statements(...) -> list[dict]
    - fetch_market_calendar(...) -> list[dict]
  - DuckDB への保存関数（冪等: ON CONFLICT DO UPDATE）:
    - save_daily_quotes(conn, records) -> int
    - save_financial_statements(conn, records) -> int
    - save_market_calendar(conn, records) -> int
  - 取得時刻（fetched_at）を UTC で付与し、Look-ahead bias を防ぐ観点で「いつデータを取得したか」をトレース可能に。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層（厳密には Raw, Processed, Feature, Execution）のテーブル群を定義。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブルを定義。
  - features, ai_scores（Feature 層）を定義（特徴量管理・AIスコア用）。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等の Execution 層を定義。
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）を設置し、データ整合性を担保。
  - 頻出クエリ向けにインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) により DB ファイル親ディレクトリを自動作成して全テーブルを冪等に作成する関数を提供。
  - get_connection(db_path) で既存 DB への接続を取得可能（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL の流れを実装（run_daily_etl）:
    - 市場カレンダー ETL（先読み: デフォルト 90 日）
    - 株価日足 ETL（差分取得 + バックフィル。デフォルト backfill_days=3）
    - 財務データ ETL（差分取得 + バックフィル）
    - 品質チェック（オプションで実行）
  - 差分更新のヘルパーを提供:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - run_prices_etl / run_financials_etl / run_calendar_etl（各 ETL は差分のみ取得）
  - ETL の結果を ETLResult データクラスで集約（取得件数、保存件数、品質問題一覧、エラー一覧）。
  - ETL の各ステップは独立してエラーハンドリングされ、1 ステップ失敗でも他ステップは継続（Fail-Fast ではない設計）。

- 監査ログ（kabusys.data.audit）
  - シグナルから約定に至る監査用テーブル群を実装:
    - signal_events（戦略が生成したシグナル履歴）
    - order_requests（発注要求。order_request_id を冪等キーとして扱う）
    - executions（証券会社から返った約定ログ。broker_execution_id をユニーク制約）
  - 発注種別ごとのチェック制約（limit / stop / market の価格必須/非必須ルール）を実装。
  - ステータス遷移やエラーメッセージを格納するフィールドを用意。
  - UTC タイムゾーンでの TIMESTAMP 保存を強制（init_audit_schema は SET TimeZone='UTC' を実行）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。

- データ品質チェック（kabusys.data.quality）
  - 品質チェック用のフレームワークと QualityIssue データクラスを実装。
  - 実装済みチェック（少なくとも実装されているもの）:
    - check_missing_data(conn, target_date=None): raw_prices の OHLC 欄の欠損を検出（検出時は severity="error"）。
    - check_spike(conn, target_date=None, threshold=0.5): 前日比（LAG）によるスパイク（急騰・急落）検出（デフォルト閾値 50%）。
  - 各チェックは問題のサンプル（最大 10 件）と件数の集計を返し、呼び出し元は重大度に応じて取り扱いを決定可能。

Changed
- （初期リリースのため過去からの変更はなし）

Fixed
- （初期リリースのため修正履歴はなし）

Deprecated
- （なし）

Removed
- （なし）

Security
- トークンや機密情報は環境変数経由で管理する設計を採用（.env 自動読み込みあり）。
- ネットワーク呼び出しでの再試行やレート制御、トークン自動リフレッシュによりサービス拒否や認証失敗時の脆弱性・運用リスクを低減。

注記 / マイグレーション / 利用上のポイント
- 初回利用時:
  - settings.jquants_refresh_token 等の必須環境変数を .env または OS 環境で設定してください。
  - DuckDB の初期化は data.schema.init_schema(db_path) を使用してください。既存 DB があれば冪等でスキーマ確認／作成します。
  - 監査ログを別 DB に分けたい場合は init_audit_db() を利用してください（または既存接続に init_audit_schema を呼ぶ）。
- 自動 .env ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト目的等）。
- J-Quants API のリクエストは内部で 120 req/min に制限されています。大量取得を行う場合は注意してください。
- run_daily_etl はカレンダー取得 → 営業日調整 → 株価/財務の差分取得 → 品質チェックの順で実行します。品質チェックで問題が検出されても ETL は中断せず結果を返します（呼び出し元で対処）。

今後の想定改善点（コードから推測）
- 品質チェックの拡張（重複チェック、将来日付チェックなどの実装完了）。
- strategy / execution / monitoring パッケージの具体実装（現状 __init__.py のみ用意）。
- API 呼び出しにおける並列化やバックオフ戦略の微調整。
- より詳細なログ出力やメトリクス収集（Prometheus 等）への統合。

------------------
作成: 推測に基づく初期 CHANGELOG（コードベースの実装から生成）
