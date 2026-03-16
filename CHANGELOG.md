CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。
リリース日や変更はコードベースの内容から推測して記載しています。

0.1.0 - 2026-03-16
-----------------

Added
- パッケージ初期リリース。
  - パッケージメタ情報: kabusys/__init__.py にて __version__ = "0.1.0"、公開モジュールとして data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を自動読み込みする仕組みを実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用）。
  - .env パーサ実装: export プレフィックスの処理、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い、無効行（空行・#で始まる行）の無視に対応。
  - Settings クラスを提供し、以下の設定値をプロパティ経由で取得可能：
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - 補助プロパティ: is_live / is_paper / is_dev

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する API クライアントを実装。
  - レート制限制御: 固定間隔スロットリングで 120 req/min を守る _RateLimiter 実装。
  - リトライロジック: 指数バックオフ（最大 3 回）、対象ステータス 408, 429, および 5xx を再試行。429 の場合は Retry-After ヘッダを優先。
  - 認証トークン処理:
    - get_id_token(refresh_token=None) でリフレッシュトークンから idToken を取得。
    - 401 受信時は自動でトークンをリフレッシュして 1 回リトライ（無限再帰を防ぐ allow_refresh オプション）。
    - モジュールレベルの ID トークンキャッシュ（ページネーション間で共有）。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
    - 各 fetch 関数は pagination_key を追跡して全ページ取得。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes(conn, records): raw_prices テーブルに ON CONFLICT DO UPDATE で保存。fetched_at を UTC ISO8601 で保存。PK 欠損行はスキップしてログ出力。
    - save_financial_statements(conn, records): raw_financials に保存（ON CONFLICT DO UPDATE）。PK 欠損行スキップ。
    - save_market_calendar(conn, records): market_calendar に保存（ON CONFLICT DO UPDATE）。HolidayDivision を is_trading_day/is_half_day/is_sq_day に安全に変換。
  - ユーティリティ: _to_float/_to_int により安全な型変換を提供（空値・不正値は None、float 形式の整数処理に注意）。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層を想定した広範なスキーマ定義を実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 各テーブルに制約（NOT NULL、CHECK、PRIMARY KEY、外部キー等）を付与。
  - 検索パフォーマンス向上のため複数インデックスを作成。
  - init_schema(db_path) でディレクトリ自動作成後に DDL を実行して初期化（冪等）。":memory:" のサポートあり。
  - get_connection(db_path) で接続取得（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL の実装 run_daily_etl(conn, target_date=None, ...) を提供。実行フロー:
    1. 市場カレンダー ETL（デフォルトで target + 90 日先を先読み）
    2. 株価日足 ETL（差分更新、デフォルトバックフィル 3 日）
    3. 財務データ ETL（差分更新、デフォルトバックフィル 3 日）
    4. 品質チェック（オプション）
  - 差分更新ロジック: DB の最終取得日を確認し、未取得範囲のみを自動算出。最小取得開始日は 2017-01-01。
  - 市場カレンダー先読みデフォルト: 90 日。
  - バックフィルデフォルト: 3 日（API の後出し修正を吸収）。
  - 個別 ETL ジョブ:
    - run_prices_etl(...)
    - run_financials_etl(...)
    - run_calendar_etl(...)
  - ETLResult データクラスを導入し、取得件数・保存件数・品質問題・エラーを集約。品質問題の重大度判定ヘルパーを含む。
  - 各ステップは独立して例外をキャッチし、1ステップの失敗でも他ステップは継続する設計（Fail-Fast ではない）。

- 監査ログ／トレーサビリティ (kabusys.data.audit)
  - シグナルから約定に至るトレーサビリティを残す監査スキーマを実装。
  - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）を想定。
  - テーブル: signal_events, order_requests（冪等キー order_request_id）, executions（broker_execution_id はユニーク）等。
  - すべての TIMESTAMP を UTC で保存するため init_audit_schema(conn) は "SET TimeZone='UTC'" を実行。
  - init_audit_db(db_path) で専用 DB の初期化と接続取得が可能。
  - ステータス列や CHECK 制約で発注ライフサイクル管理をサポート。

- データ品質チェック (kabusys.data.quality)
  - 品質チェック群を実装（関数: check_missing_data, check_spike, 他）。
  - QualityIssue データクラスでチェック名・テーブル・重大度・詳細・問題サンプル行を返却。
  - check_missing_data: raw_prices の OHLC 欄の欠損検出（欠損は error として報告）。
  - check_spike: LAG ウィンドウで前日比を計算し、デフォルト閾値 50%（0.5）を超えるスパイクを検出。
  - SQL を用いた実装で DuckDB 接続を受け取り効率的に実行。全件収集ポリシー（Fail-Fast ではない）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- HTTP レスポンスの JSON デコード失敗時に明示的に例外化し、エラーメッセージにレスポンス先頭を含めることでデバッグを支援（ただし本番ログ出力時は機密情報に注意）。

注意事項（実装から推測）
- HTTP クライアントは標準ライブラリの urllib を使用。より高度なタイムアウト/接続制御が必要な場合は将来的に HTTP クライアントの入れ替えを検討してください。
- トークンはモジュールレベルでキャッシュされる（プロセスローカル）。マルチプロセス環境では各プロセスで再取得されます。
- DuckDBの制約や CHECK により、不正なデータは挿入時に拒絶される可能性があります。ETL 実行前にスキーマが初期化されていることを確認してください（init_schema を推奨）。
- .env の自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後や CWD が異なる環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的に環境変数を設定することを推奨します。

今後の予定（未実装だが想定される拡張）
- strategy / execution / monitoring モジュールの具象実装（現在パッケージレイアウトは用意済み）。
- 非同期 HTTP クライアント対応やより柔軟なレートリミット制御。
- より詳細な品質チェック（重複検出、日付不整合検出の追加チェック等）。
- テストカバレッジ・CI の整備。

--- 

（この CHANGELOG はコードベースの内容から推測して作成しています。記載内容に誤りや追記希望があれば教えてください。）