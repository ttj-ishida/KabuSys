CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。  
現在のバージョンはパッケージの __version__ に合わせて 0.1.0 としています。

Unreleased
----------

（なし）

0.1.0 - 2026-03-16
------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
  - パッケージ初期化:
    - src/kabusys/__init__.py: パッケージ名・バージョン定義（0.1.0）と公開サブパッケージ一覧。
  - 設定管理:
    - src/kabusys/config.py:
      - .env ファイルおよび環境変数を読み込む自動ローダを実装（プロジェクトルートを .git / pyproject.toml で検出）。
      - .env パースは export KEY=val、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
      - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
      - Settings クラスを公開（プロパティ経由で J-Quants / kabuAPI / Slack / DB パス / 環境 / ログレベル等を取得）。
      - 設定検証: KABUSYS_ENV と LOG_LEVEL の有効値検査、必須環境変数未設定時は ValueError。
      - 主要環境変数名の例:
        - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL,
        - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
  - データアクセス・DuckDB スキーマ:
    - src/kabusys/data/schema.py:
      - Raw / Processed / Feature / Execution の各レイヤを含む DuckDB DDL を定義。
      - テーブル群（raw_prices, raw_financials, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）を含む。
      - インデックス定義と作成順序を実装し、init_schema(db_path) で冪等に初期化。
      - get_connection(db_path) を提供（スキーマ初期化を行わない）。
  - J-Quants API クライアント:
    - src/kabusys/data/jquants_client.py:
      - API ベース実装（_BASE_URL）とレート制限（120 req/min）を守る固定間隔レートリミッタを実装。
      - リトライ戦略: 指数バックオフ（最大 3 回）、対象ステータス 408/429/5xx。429 の場合は Retry-After ヘッダ優先。
      - 401 Unauthorized 受信時は自動でリフレッシュ（get_id_token）して 1 回だけ再試行（無限再帰防止）。
      - ページネーション対応の取得関数:
        - fetch_daily_quotes(code?, date_from?, date_to?)
        - fetch_financial_statements(code?, date_from?, date_to?)
        - fetch_market_calendar(holiday_division?)
      - DuckDB へ冪等に保存する保存関数:
        - save_daily_quotes(conn, records)
        - save_financial_statements(conn, records)
        - save_market_calendar(conn, records)
      - 値変換ユーティリティ: _to_float, _to_int（文字列の "1.0" を扱う等の仕様）。
      - get_id_token(refresh_token?) を提供（POST /token/auth_refresh）。
      - データ取得時に fetched_at（UTC）を付与して Look-ahead バイアスを防止。
  - ETL パイプライン:
    - src/kabusys/data/pipeline.py:
      - 差分更新を行う ETL（run_daily_etl）を実装。処理順:
        1. 市場カレンダーの先読み（デフォルト lookahead 90 日）
        2. 株価日足の差分取得（backfill デフォルト 3 日）
        3. 財務データの差分取得（backfill デフォルト 3 日）
        4. 品質チェック（オプション）
      - 個別ジョブ:
        - run_calendar_etl, run_prices_etl, run_financials_etl を提供。
      - 差分判定用ユーティリティ:
        - get_last_price_date, get_last_financial_date, get_last_calendar_date。
      - 営業日調整: _adjust_to_trading_day（market_calendar を参照して非営業日を直近営業日に調整）。
      - ETL 実行結果を ETLResult dataclass に収集（取得数・保存数・品質問題・エラー一覧等）。
      - エラーハンドリング方針: 各ステップは独立して例外処理し、1 ステップ失敗でも他のステップは継続。品質チェックは全件収集（Fail-Fast ではない）。
  - データ品質チェック:
    - src/kabusys/data/quality.py:
      - QualityIssue dataclass を定義（check_name, table, severity, detail, rows）。
      - check_missing_data(conn, target_date?)：raw_prices の OHLC 欠損検出（volume は許容）。
      - check_spike(conn, target_date?, threshold?)：前日比のスパイク検出（デフォルト閾値 0.5 = 50%）。
      - 設計方針: SQL による効率的判定、パラメータバインド、全件検出とサンプル収集。
  - 監査ログ / トレーサビリティ:
    - src/kabusys/data/audit.py:
      - 信号→発注→約定のトレーサビリティ用テーブル群を定義（signal_events, order_requests, executions）。
      - order_request_id を冪等キーとして扱う設計、すべての TIMESTAMP は UTC で保存するように init_audit_schema で SET TimeZone='UTC' を実行。
      - init_audit_schema(conn) と init_audit_db(db_path) を提供（冪等初期化）。

Changed
- （初回リリースのため変更履歴はありません）

Fixed
- （初回リリースのため修正履歴はありません）

Notes / 実装上の注意
- 環境変数の自動ロードはプロジェクトルート検出に依存するため、配布環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御できます。
- J-Quants API クライアントはモジュールレベルで ID トークンをキャッシュし、ページネーション間で再利用します。必要に応じて get_id_token(force_refresh) を呼び出して強制更新してください。
- DuckDB の DDL は ON CONFLICT / CHECK 制約を用いて冪等性とデータ整合性を確保しています。初回は init_schema() を呼び出してスキーマを作成してください。
- デフォルトのスパイク閾値は 50%（_SPIKE_THRESHOLD = 0.5）。運用に応じて pipeline.run_daily_etl の引数や quality.check_spike の threshold を調整してください。

今後の予定（非網羅）
- 追加品質チェック（重複・日付不整合の詳細チェック等）の実装拡張。
- execution（ブローカー連携）層の実装: 発注送信、約定コールバック処理、ポジション更新の実装。
- 単体テスト・統合テスト、CI 設定の追加。
- ドキュメント（DataSchema.md, DataPlatform.md 等）に基づくユーザー向け導入手順の充実。