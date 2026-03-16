# Changelog

すべての注目すべき変更点はここに記載します。  
フォーマットは "Keep a Changelog" に準拠します。

v0.1.0 - 2026-03-16
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのコア機能を実装。
- パッケージ情報
  - パッケージバージョン: 0.1.0
  - パッケージトップ: kabusys.__all__ に data, strategy, execution, monitoring を公開。
- 環境設定（kabusys.config）
  - .env/.env.local の自動ロード機構を実装（プロジェクトルートの検出: .git または pyproject.toml を起点）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサ実装: export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントを考慮した堅牢なパース。
  - Settings クラスを提供（J-Quants トークン、kabu API、Slack トークン/チャンネル、DB パス、環境・ログレベル検証等）。
  - 必須環境変数未設定時の明示的エラー（_require）。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、四半期財務、JPX マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - レートリミッタ実装（120 req/min 固定間隔スロットリング）。
  - リトライロジック（指数バックオフ、最大 3 回、対象: 408, 429, 5xx、ネットワークエラー扱いの URLError/OSError 対応）。
  - 401 受信時はリフレッシュトークンで id_token を自動リフレッシュして 1 回だけ再試行（無限再帰対策あり）。
  - id_token モジュールレベルキャッシュを保持し、ページネーション間で共有。
  - レスポンスの JSON デコードエラーは明示的に例外化。
  - 取得データ保存前に fetched_at を UTC ISO8601（Z）で記録（Look-ahead bias のトレース対応）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等化（ON CONFLICT DO UPDATE）を採用。
  - 型変換ユーティリティ（_to_float, _to_int）：不整合値は None を返す。_to_int は "1.0" を許容し "1.9" のような小数部がある数は None を返す仕様。
- DuckDB スキーマ（kabusys.data.schema）
  - DataPlatform の三層（Raw / Processed / Feature） + Execution レイヤーに対応した DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed テーブル。
  - features, ai_scores などの Feature テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution テーブル。
  - 頻出クエリ向けにインデックスを定義。
  - init_schema(db_path) によりディレクトリ作成→DDL/INDEX 実行→DuckDB 接続を返す（冪等）。
  - get_connection(db_path) で既存 DB への接続を取得（初期化は行わない）。
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL のエントリ run_daily_etl を実装（市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）。
  - 差分更新の自動算出: DB の最終取得日を基に date_from を決定、デフォルト backfill_days=3 により後出し修正を吸収。
  - calendar は先読み lookahead_days=90（日）で未来のカレンダーを事前取得。
  - 各ステップは独立して例外を捕捉し、1ステップ失敗でも他ステップは継続（エラーは ETLResult.errors に記録）。
  - ETLResult クラス（target_date、取得件数/保存件数、quality_issues、errors、派生プロパティ等）を提供。
  - 個別ジョブ run_prices_etl / run_financials_etl / run_calendar_etl を公開。
  - jquants_client の save_* を使った冪等保存。
- 監査ログ（kabusys.data.audit）
  - トレーサビリティ用の監査テーブルを実装（signal_events, order_requests, executions）。
  - order_request_id を冪等キーとして扱う設計、全てのテーブルに created_at を持たせる方針。
  - DuckDB で UTC タイムゾーンを設定する init_audit_schema / init_audit_db を提供。
  - 発注ステータス遷移や制約（limit/stop の価格チェック等）を DDL レベルで表現。
  - 監査検索向けのインデックスを多数定義。
- データ品質チェック（kabusys.data.quality）
  - QualityIssue データクラスを実装（check_name, table, severity, detail, rows）。
  - check_missing_data（raw_prices の OHLC 欠損検出）を実装（サンプル出力・件数集計）。
  - check_spike（前日比スパイク検出）を実装（LAG ウィンドウを使い変動率で検出。デフォルト閾値 50%）。
  - 複数のチェックを集約して呼び出す想定（pipeline 側から run_all_checks を呼ぶ設計）。各チェックは Fail-Fast ではなく問題を収集して返す設計。

Notes / Documentation
- 環境変数（代表例）:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - SLACK_BOT_TOKEN（必須）
  - SLACK_CHANNEL_ID（必須）
  - DUCKDB_PATH / SQLITE_PATH（省略時は data/ ディレクトリ配下を使用）
  - KABUSYS_ENV（development | paper_trading | live、無効値は例外）
  - LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- ETL の挙動:
  - run_daily_etl は市場カレンダー取得後に対象日を営業日に調整してから株価/財務 ETL を実行。
  - 品質チェックはデフォルトで実行され、重大な品質問題は ETLResult.has_quality_errors で判定可能。
- 保存はすべて冪等性（INSERT ... ON CONFLICT DO UPDATE）を意識しているため、再実行での重複を避ける設計。

Known issues / 注意点
- pipeline.run_calendar_etl から jquants_client.fetch_market_calendar を呼ぶ箇所で渡す引数名（date_from, date_to）と jquants_client.fetch_market_calendar のドキュメント/引数（holiday_division を受け取る実装）に不一致が見受けられます。実運用前に API クライアント側とパイプライン側の引数整合性を確認してください。
- strategy/execution/monitoring パッケージの __init__ は存在するが、戦略ロジック・発注実行・監視機能の具体実装はこのリリースでは限定的（もしくは未実装）です。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

---

今後の予定（例）
- J-Quants クライアントの calendar API 引数の整合性確認とテスト追加
- quality モジュールの重複・日付整合性チェックの実装補完とユニットテスト
- strategy / execution 層の実装充実（ブローカ接続・発注実行の実装）
- CI / テストカバレッジの拡充

（以上）