Keep a Changelog 準拠 — CHANGELOG.md

すべての変更は SemVer に従います。  
フォーマットやラベルは https://keepachangelog.com/ja/ に準拠しています。

Unreleased
- なし

0.1.0 - 2026-03-16
-----------------
Added
- パッケージ初期リリースとして以下の主要機能を実装。
  - パッケージメタ情報
    - kabusys.__version__ = "0.1.0"
    - パッケージ公開モジュール: data, strategy, execution, monitoring
  - 環境設定管理 (kabusys.config)
    - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env のパースは export 形式やクォート、エスケープ、インラインコメント等に対応。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途等）。
    - 必須環境変数未設定時は明確な例外を発生させる Settings クラスを提供。
    - 主な環境変数:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development, paper_trading, live のいずれか）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - J-Quants クライアント (kabusys.data.jquants_client)
    - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得する API クライアントを実装。
    - レート制限保護: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
    - リトライ戦略: 指数バックオフ、最大 3 回、対象は 408/429/5xx、およびネットワークエラーに対するリトライ。
    - 401 受信時はリフレッシュトークンを使って ID トークンを自動更新し 1 回リトライして再試行（無限再帰防止）。
    - ページネーション対応およびページ間でのトークンキャッシュ（モジュールレベル）。
    - データ取得関数:
      - fetch_daily_quotes(...)
      - fetch_financial_statements(...)
      - fetch_market_calendar(...)
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes(conn, records): raw_prices テーブルへ ON CONFLICT DO UPDATE。
      - save_financial_statements(conn, records): raw_financials テーブルへ ON CONFLICT DO UPDATE。
      - save_market_calendar(conn, records): market_calendar テーブルへ ON CONFLICT DO UPDATE。
    - 取得時刻（fetched_at）は UTC ISO8601 で記録し、Look-ahead Bias の追跡を容易にする。
    - 数値変換ユーティリティ（_to_float, _to_int）で不正値を安全に扱う。
  - DuckDB スキーマ定義・初期化 (kabusys.data.schema)
    - 3 層（Raw, Processed, Feature）+ Execution 層を含む包括的なスキーマを DDL で定義。
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw 層テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層。
    - features, ai_scores 等の Feature 層。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層。
    - 性能最適化のためのインデックスを複数定義（code/date 検索やステータス検索に対応）。
    - init_schema(db_path) で DB ファイルの親ディレクトリを自動作成し、テーブル・インデックスを冪等に作成。
    - get_connection(db_path) で既存 DB へ接続（初期化は行わない）。
  - ETL パイプライン (kabusys.data.pipeline)
    - 日次 ETL のエントリポイント run_daily_etl(conn, ...) を実装。
    - 個別ジョブ:
      - run_calendar_etl: カレンダーを先読み（デフォルト lookahead 90 日）。
      - run_prices_etl: 株価日足の差分更新（バックフィルデフォルト 3 日）。
      - run_financials_etl: 財務データの差分更新（バックフィルデフォルト 3 日）。
    - 差分更新ロジック: DB の最終取得日を参照して未取得分のみ取得、バックフィルで後出し修正を吸収。
    - ETL 結果は ETLResult dataclass で詳細なメタ情報（取得数・保存数・品質問題・エラー等）を返却。
    - ETL は各ステップ独立して例外処理を行い、1 ステップ失敗でも他ステップは継続（Fail-Fast ではない）。
  - 監査ログ（トレーサビリティ） (kabusys.data.audit)
    - signal_events, order_requests, executions の監査テーブルを定義。
    - UUID ベースのトレーサビリティ階層を想定（戦略→シグナル→発注要求→証券会社ID→約定）。
    - すべての TIMESTAMP を UTC で保存する（init_audit_schema は SET TimeZone='UTC' を実行）。
    - order_requests は冪等キー（order_request_id）を持ち、CHECK 制約で limit/stop/market の価格要件を表現。
    - init_audit_schema(conn) / init_audit_db(path) を提供。
  - 品質チェックモジュール (kabusys.data.quality)
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損を検出（sample 最大 10 件）。
    - 異常値検出 (check_spike): 前日比でのスパイク検出（デフォルト閾値 50%）。
    - 重複チェック、日付不整合チェック（将来日付・営業日外）を設計に含む（いくつかはクエリベースで実装の想定）。
    - QualityIssue dataclass を用いて、check_name, table, severity, detail, rows を返却。
    - 各チェックは全件収集を行い、呼び出し側で重大度に応じたハンドリングを行う設計。

Changed
- 新規パッケージの初期実装のため該当なし。

Fixed
- 新規パッケージの初期実装のため該当なし。

Deprecated
- なし

Removed
- なし

Security
- HTTP タイムアウト（30 秒）やリトライ制御を実装し、外部 API 呼び出し時の堅牢性を向上。
- 環境変数保護: .env のロード時、既存 OS 環境変数は protected として上書きを制御（override フラグあり）。

注意事項（Migration / Usage Notes）
- データベース初期化:
  - 初回は kabusys.data.schema.init_schema(settings.duckdb_path) を呼んでスキーマを作成してください。
  - 監査ログを使う場合は init_audit_schema(conn) を呼んで監査テーブルを追加してください（既存接続を再利用可）。
- 環境変数:
  - 必須の値（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）が未設定だと Settings プロパティで ValueError を投げます。
  - 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API:
  - API レート上限 120 req/min を守るために内部でスロットリングを行います。大量リクエスト時は注意してください。
  - 401 による自動トークン更新を行いますが、refresh に失敗すると例外となります。
- ETL のデフォルト設定:
  - backfill_days=3（後出し修正吸収のため最終取得日の数日前から再取得）
  - calendar_lookahead_days=90（市場カレンダーを先読み）
  - run_daily_etl はデフォルトで品質チェックを実行します（run_quality_checks=True）。
- DuckDB の挙動:
  - init_schema は親ディレクトリが存在しない場合自動作成します。
  - get_connection はスキーマ初期化を行わないため、初回は必ず init_schema を使用してください。

今後の予定（想定）
- strategy / execution / monitoring の具体的実装（現在はパッケージ骨子のみ）。
- 追加の品質チェックやアラート連携（Slack 通知等）。
- 単体テスト・統合テストの整備と CI パイプラインの導入。

その他
- 本リリースは初期段階の機能群を含むため、外部 API・DB 設計に依存する部分があります。運用開始前に必須環境変数や DB 初期化を適切に行ってください。