CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。
フォーマットや運用方法の詳細は https://keepachangelog.com/ を参照してください。

Unreleased
----------

（未リリースの変更はここに記載してください）

0.1.0 - 2026-03-16
-----------------

追加 (Added)
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報:
    - __version__ = "0.1.0"
    - 公開モジュール: data, strategy, execution, monitoring

- 環境設定モジュール (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み:
    - プロジェクトルート判定は __file__ から親ディレクトリを探索し、.git または pyproject.toml を基準に行うため CWD に依存しない。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - OS 環境変数は保護され、.env による上書きを制御可能。
  - .env パーサの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートの中のバックスラッシュエスケープ対応。
    - コメント処理: クォート外では '#' が直前にスペース/タブがある場合にコメントとして扱う。
  - Settings クラスを公開 (settings):
    - 必須プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は例外）。
    - オプション/デフォルト: KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)、DUCKDB_PATH (data/kabusys.duckdb)、SQLITE_PATH (data/monitoring.db)。
    - 環境モード検証: KABUSYS_ENV は development / paper_trading / live のいずれかであることを検証。
    - ログレベル検証: LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 取得対象:
    - 株価日足（OHLCV）
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー（祝日・半日・SQ）
  - 設計された挙動:
    - レート制限制御: 固定間隔スロットリングで 120 req/min（最小間隔 60/120 秒）を順守する _RateLimiter を実装。
    - リトライロジック: 指数バックオフ、最大試行回数 3 回。HTTP 408/429 と 5xx をリトライ対象。
    - 429 の場合は Retry-After ヘッダを優先。
    - 401 受信時は自動でリフレッシュトークンを用いて id_token を再取得して 1 回リトライ（無限再帰を防ぐため allow_refresh フラグあり）。
    - id_token はモジュールレベルでキャッシュ（ページネーション間で共有）。
    - JSON デコード失敗時は明示的なエラーを出力。
    - ページネーション対応: pagination_key を使った全件取得処理を提供。
  - 取得関数:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(id_token?, code?, date_from?, date_to?) -> list[dict]
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes(conn, records): raw_prices テーブルに INSERT ... ON CONFLICT DO UPDATE を使用して保存。
    - save_financial_statements(conn, records): raw_financials に冪等保存。
    - save_market_calendar(conn, records): market_calendar に冪等保存。
    - 保存時に fetched_at を UTC の ISO8601 (Z) で記録。
  - ユーティリティ:
    - _to_float / _to_int: 型変換ヘルパー。float 文字列や "1.0" のような float 整数表現を扱う際の安全処理あり。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - 3層データモデルを採用:
    - Raw Layer (raw_prices, raw_financials, raw_news, raw_executions)
    - Processed Layer (prices_daily, market_calendar, fundamentals, news_articles, news_symbols)
    - Feature Layer (features, ai_scores)
    - Execution Layer (signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance)
  - 各テーブルに制約と CHECK を設定しデータ整合性を担保。
  - インデックス定義を多数追加して、銘柄×日付スキャンやステータス検索などのクエリパターンを最適化。
  - 公開 API:
    - init_schema(db_path) -> duckdb connection: テーブル作成（冪等）と親ディレクトリの自動作成。
    - get_connection(db_path) -> duckdb connection: 既存 DB への接続（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL フロー:
    1. 差分更新: DB の最終取得日を確認し未取得範囲のみを取得。
    2. 保存: jquants_client の save_* 関数で冪等保存（ON CONFLICT）。
    3. 品質チェック: quality モジュールで欠損・スパイク・重複・日付不整合を検出。
  - デフォルト挙動:
    - 初回ロード開始日: 2017-01-01。
    - カレンダー先読み: デフォルト 90 日（_CALENDAR_LOOKAHEAD_DAYS）。
    - 株価・財務のバックフィル: デフォルト 3 日（_DEFAULT_BACKFILL_DAYS）。
    - 差分更新時の date_from 自動計算、backfill による後出し修正吸収。
  - 個別ジョブ:
    - run_prices_etl(conn, target_date, id_token?, date_from?, backfill_days?) -> (fetched, saved)
    - run_financials_etl(...)
    - run_calendar_etl(conn, target_date, id_token?, date_from?, lookahead_days?) -> (fetched, saved)
  - 日次統合エントリ:
    - run_daily_etl(conn, target_date?, id_token?, run_quality_checks=True, spike_threshold=0.5, backfill_days=3, calendar_lookahead_days=90) -> ETLResult
    - ETLResult オブジェクトに取得件数、保存件数、品質問題、エラー一覧を収集。各ステップは独立して例外処理し、1 ステップ失敗でも他は継続する（Fail-Fast ではない）。
    - 市場カレンダー取得後に対象日を営業日に調整するヘルパーを実装（最大 30 日遡るフェイルセーフあり）。
  - テスト容易性のため id_token を外から注入可能。

- 品質チェックモジュール (kabusys.data.quality)
  - チェック項目:
    - 欠損データ検出 (raw_prices の open/high/low/close)
    - 異常値（スパイク）検出: 前日比の絶対変化率 > threshold（デフォルト 50%）
    - 重複チェック（主キー重複）
    - 日付不整合（将来日付や営業日外のデータ）
  - 各チェックは QualityIssue オブジェクトのリストを返し、呼び出し元が重大度に応じて対処を行える設計（Fail-Fast ではない）。
  - DuckDB の SQL を用いて高速に検査し、サンプル行（最大 10 件）を返す。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - 監査テーブルを別モジュールで定義・初期化:
    - signal_events: 戦略が生成したシグナルを記録（棄却・エラー含む）。
    - order_requests: 発注要求ログ（order_request_id を冪等キーとして採用）。limit/stop/market のチェック制約を実装。
    - executions: 証券会社からの約定を記録（broker_execution_id をユニークキーとして冪等性確保）。
  - 監査設計原則:
    - すべての TIMESTAMP は UTC で保存（init 時に SET TimeZone='UTC' を実行）。
    - トレーサビリティは business_date → strategy_id → signal_id → order_request_id → broker_order_id の階層で追跡可能。
    - order_requests は ON DELETE RESTRICT（ログは削除しない前提）。
    - created_at/updated_at を持ち、アプリ側で updated_at を更新することを想定。
  - 公開 API:
    - init_audit_schema(conn): 既存 DuckDB 接続に監査テーブルを追加（冪等）。
    - init_audit_db(db_path) -> conn: 監査ログ専用 DB を作成して初期化。

変更 (Changed)
- 初期リリースのため該当なし。

修正 (Fixed)
- 初期リリースのため該当なし。

注意・既知の制限 (Notes / Known limitations)
- J-Quants API のレート制限は固定間隔スロットリングで制御しているため、burst を許容する実装ではありません（安定して 120 req/min を守ることを優先）。
- get_id_token はリフレッシュトークンを必要とするため、環境変数 JQUANTS_REFRESH_TOKEN の設定が必須。
- DuckDB の ON CONFLICT 機能を使用して冪等保存を実現しているため、スキーマの主キー・制約に依存します。スキーマ変更時はマイグレーションが必要。
- quality.check_spike のデフォルト閾値は 50%（_SPIKE_THRESHOLD）。用途に応じて run_daily_etl の spike_threshold 引数で調整可能。
- .env のコメントパースは「直前がスペース/タブの場合のみ # をコメントとみなす」挙動になっている点に注意（意図しない切り出し防止）。

開発者向けメモ
- 自動 .env ロードを無効化したいテストでは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。
- データベースの初期化:
  - data.schema.init_schema(settings.duckdb_path) でメイン DB を初期化。
  - data.audit.init_audit_db(...) または data.audit.init_audit_schema(conn) で監査テーブルを追加。
- ETL を実行する典型例:
  - conn = init_schema(settings.duckdb_path)
  - result = run_daily_etl(conn)

以上。