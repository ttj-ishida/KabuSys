# Changelog

すべての重要な変更点はこのファイルに記録します。
このプロジェクトは Keep a Changelog の形式に従います。
バージョニングは SemVer を使用します。

[未リリース]

## [0.1.0] - 2026-03-16
初回リリース。

概要:
このリリースでは日本株自動売買システム「KabuSys」の基盤となるコアモジュールを実装しました。
主に環境設定管理、J-Quants データ取得クライアント、DuckDB スキーマ/初期化、監査ログ（audit）、およびデータ品質チェックの機能を提供します。

追加（Added）
- パッケージ基底
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - モジュールの公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数の自動読み込み機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用途）。
  - .env 行パーサを実装（export プレフィックス、クォート、エスケープ、インラインコメント処理をサポート）。
  - Settings クラスで必要設定をプロパティとして提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - デフォルトや検証:
    - KABUSYS_ENV の許容値: development / paper_trading / live（不正値は ValueError）。
    - LOG_LEVEL の許容値: DEBUG / INFO / WARNING / ERROR / CRITICAL（不正値は ValueError）。
    - データベースパスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
  - settings = Settings() をモジュールレベルで提供。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 基本設計:
    - API レート制限（120 req/min）を固定間隔スロットリングで守る RateLimiter を実装。
    - 再試行（指数バックオフ）ロジックを実装（最大 3 回、408/429/5xx を対象）。
    - 401 受信時に自動でリフレッシュトークンから id_token を取得して 1 回リトライする機能を実装（無限再帰防止）。
    - ページネーション対応（pagination_key を利用して全ページを取得）。
    - 取得時刻（fetched_at）を UTC タイムスタンプで記録し、look-ahead bias のトレースを可能に。
  - 提供 API:
    - get_id_token(refresh_token: Optional[str]) -> str: リフレッシュトークンから id_token を取得。
    - fetch_daily_quotes(...): 日足（OHLCV）をページネーション対応で取得。
    - fetch_financial_statements(...): 財務（四半期 BS/PL）をページネーション対応で取得。
    - fetch_market_calendar(...): JPX マーケットカレンダーを取得。
    - save_daily_quotes(conn, records): DuckDB の raw_prices へ冪等に保存（ON CONFLICT DO UPDATE）。
    - save_financial_statements(conn, records): raw_financials へ冪等保存。
    - save_market_calendar(conn, records): market_calendar へ冪等保存。
  - ユーティリティ:
    - JSON デコード失敗時の明確なエラー、ネットワーク/HTTP エラーのログ、429 の Retry-After ヘッダ考慮。
    - 型変換ヘルパ: _to_float, _to_int（安全な変換ロジック、"1.0" のような float 文字列の扱いなど）。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - 3 層データレイヤ（Raw / Processed / Feature）および Execution 層のテーブル定義を実装。
    - Raw テーブル例: raw_prices, raw_financials, raw_news, raw_executions
    - Processed テーブル例: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature テーブル例: features, ai_scores
    - Execution テーブル例: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）とインデックスを定義し、頻出クエリを考慮。
  - init_schema(db_path) を実装: DB ファイルの親ディレクトリを自動作成し、全テーブルとインデックスを作成（冪等）。
  - get_connection(db_path) を実装: 既存 DB への接続を返す（スキーマ初期化は行わない）。

- 監査ログ（Audit）（src/kabusys/data/audit.py）
  - 戦略→シグナル→発注→約定までのトレーサビリティを保証する監査用テーブル群を実装。
    - signal_events（シグナル生成ログ）: 戦略 ID、decision、reason、created_at 等を保存。
    - order_requests（発注要求ログ）: order_request_id を冪等キーとして扱い、limit/stop/market の制約を表現。status, error_message, created_at, updated_at を保持。
    - executions（約定ログ）: broker_execution_id をユニーク冪等キーとして保存、commission, executed_at 等。
  - init_audit_schema(conn) と init_audit_db(db_path) を実装。タイムゾーンを UTC に固定（SET TimeZone='UTC'）。
  - 監査用のインデックスも作成（status 検索、signal_id / broker_order_id による検索等）。

- データ品質チェック（src/kabusys/data/quality.py）
  - DataPlatform に基づく品質チェックを実装。各チェックは QualityIssue dataclass を返す（複数検出を全収集）。
    - check_missing_data(conn, target_date): raw_prices の OHLC 欠損（open/high/low/close）を検出（severity=error）。
    - check_spike(conn, target_date, threshold): 前日比スパイク（デフォルト 50%）を検出（severity=warning）。
    - check_duplicates(conn, target_date): 主キー重複（date, code）を検出（severity=error）。
    - check_date_consistency(conn, reference_date): 将来日付レコードと market_calendar による非営業日レコードを検出（将来日付=error, 非営業日=warning）。market_calendar 未存在時はスキップ。
    - run_all_checks(...) を提供し、全チェックをまとめて実行して結果を返す。
  - SQL はパラメータバインドを使用し、最大 10 件のサンプル行を返す設計。

変更（Changed）
- （初回リリースのため該当なし）

修正（Fixed）
- （初回リリースのため該当なし）

既知の注意点（Known issues / Notes）
- J-Quants クライアントは urllib を使用した同期 HTTP 実装。大量リクエストや並列処理を行う場合は上位で調整が必要（スレッド/プロセス安全性、共有 RateLimiter の扱いに注意）。
- DuckDB の UNIQUE / INDEX の挙動や NULL 扱いの違いに依存した設計箇所あり（コメント参照）。
- .env パーサは一般的なケースをサポートしているが、極端に複雑なシェル式のパーシングは想定していません。
- audit テーブルは「削除しない前提」で設計（ON DELETE RESTRICT）。運用時に取り扱い方針を検討してください。

開発者向けメモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- データベース初期化:
  - from kabusys.data import schema
  - conn = schema.init_schema(settings.duckdb_path)
  - audit 用追加: from kabusys.data import audit; audit.init_audit_schema(conn)

ライセンスや著者情報はソースツリーの別ファイルを参照してください。

---

署名: KabuSys 開発チーム (自動生成 CHANGELOG)