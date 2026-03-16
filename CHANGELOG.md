# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  

注: 本リリースはソースコードから推測した初期リリースの変更点をまとめたものです。

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買システムのコアデータ基盤・ETL・監査ログ・設定管理・外部APIクライアントなどの基本機能を実装。

### 追加 (Added)
- パッケージ基礎
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に指定。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルートの判定は .git または pyproject.toml を基準に行い、CWD に依存しない探索を実装。
    - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
    - OS 環境変数を保護するための protected キーセットを考慮した .env 上書き制御を実装。
  - .env パーサを実装（export 句、シングル／ダブルクォート内のバックスラッシュエスケープ、行末コメントの扱いなどに対応）。
  - Settings クラスを提供: J-Quants / kabu ステーション API / Slack / DB パス / システム環境 (env、log_level) などのプロパティを環境変数から取得。
    - 必須項目 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID) は未設定時に ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装（許容値は定義済み）。
    - duckdb/sqlite のファイルパスはデフォルト値と expanduser をサポート。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出し基盤を実装（_request）。
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装（_RateLimiter）。
    - 冪等な ID トークンキャッシュ（モジュールレベル）を実装し、ページネーション間で共有。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。リトライ対象ステータスは 408, 429 と 5xx。
    - 429 の場合は Retry-After ヘッダを優先して待機時間を決定。
    - 401 受信時はトークンを自動リフレッシュして一度だけ再試行（無限再帰を防ぐ allow_refresh フラグ）。
    - JSON デコードエラー時の詳細メッセージを含む例外処理。
  - 認証関数 get_id_token(refresh_token) を提供（POST /token/auth_refresh）。
  - データ取得関数を提供（ページネーション対応、ページネーションキーの重複チェックを含む）。
    - fetch_daily_quotes: 株価日足（OHLCV）
    - fetch_financial_statements: 四半期財務データ（BS/PL）
    - fetch_market_calendar: JPX マーケットカレンダー（祝日・半日・SQ）
  - DuckDB への保存関数（冪等）を提供（ON CONFLICT DO UPDATE を使用）。
    - save_daily_quotes: raw_prices に保存。fetched_at は UTC ISO8601 で記録。
    - save_financial_statements: raw_financials に保存。
    - save_market_calendar: market_calendar に保存。HolidayDivision を解釈して is_trading_day / is_half_day / is_sq_day を設定。
  - 型変換ユーティリティを実装: _to_float, _to_int（"1.0" のような文字列を安全に int に変換するロジック等）。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - 3 層（Raw / Processed / Feature）＋Execution 層のテーブルを定義した DDL を実装。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK など）を付与。
  - 検索性能を考慮したインデックス群を用意（銘柄×日付スキャン、status 検索など）。
  - init_schema(db_path) を提供。DB ファイルの親ディレクトリ自動作成、":memory:" 対応、冪等なテーブル作成。
  - get_connection(db_path) を提供（既存 DB への接続を返す）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL の高水準 API を実装。
    - run_daily_etl(conn, target_date, ...): 市場カレンダー → 株価 → 財務 → 品質チェック の順で処理。各ステップは個別にエラーハンドリングし、1 ステップ失敗でも他を継続。
    - run_calendar_etl / run_prices_etl / run_financials_etl: 差分更新ロジック、backfill（デフォルト 3 日）、カレンダーの lookahead（デフォルト 90 日）を実装。
    - 差分更新のための最終取得日取得ユーティリティ: get_last_price_date, get_last_financial_date, get_last_calendar_date。
    - カレンダーに基づく営業日調整機能 _adjust_to_trading_day（最大 30 日遡る）。
  - ETLResult dataclass を実装（取得数・保存数・品質問題・エラー一覧を保持）。品質問題は要約辞書に変換可能。
  - テスト容易性のため id_token 注入可能。

- 監査ログ（Audit） (src/kabusys/data/audit.py)
  - シグナル→発注要求→約定までを UUID 連鎖でトレースする監査テーブルを実装。
    - signal_events: 戦略が生成したシグナルのログ（decision, reason, strategy_id 等）。
    - order_requests: 冪等キー order_request_id を持つ発注要求ログ。order_type 毎の価格チェック制約を実装。
    - executions: 証券会社からの約定ログ（broker_execution_id をユニーク冪等キーとして保持）。
  - すべての TIMESTAMP を UTC で保存するため init_audit_schema は SET TimeZone='UTC' を実行。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。
  - 監査系に特化したインデックス群を定義（status キュー検索、broker_order_id/ broker_execution_id 紐付け等）。

- データ品質チェック (src/kabusys/data/quality.py)
  - QualityIssue データクラスを実装（check_name, table, severity, detail, rows）。
  - チェック実装（DuckDB 接続を SQL で効率的に処理）。
    - check_missing_data: raw_prices の OHLC 欠損（open/high/low/close）検出。見つかった場合は severity="error"。
    - check_spike: 前日比のスパイク検出（デフォルト閾値 50%）。LAG を用いた実装でサンプル行を収集。
  - 各チェックは問題のサンプルを最大 10 件返却し、Fail-Fast ではなく全件収集の方針。

- パッケージ構成
  - data パッケージ: jquants_client, schema, pipeline, audit, quality を含む。
  - 空の __init__ を execution/strategy/data に配置（将来的な拡張準備）。

### 変更 (Changed)
- なし（初回リリースのため）。

### 修正 (Fixed)
- なし（初回リリースのため）。

### 既知の制約 / 注意点 (Known issues / Notes)
- J-Quants API リトライは最大 3 回。極端な負荷下ではスロットルされる可能性あり。
- .env パーシングは一般的ケースに対応するが、極端に複雑なシェル拡張構文はサポート外。
- DuckDB の制約・インデックスは初期設計に基づく。大規模データや高頻度クエリ時のチューニングが必要な場合がある。
- execution/strategy/monitoring の詳細実装はこのリリースでは含まれておらず、今後の拡張を想定。

### マイグレーション / 移行メモ
- 既存の DuckDB を使用する場合はスキーマ初期化の順序に注意（init_schema を一度実行してください）。監査ログを別 DB に分けたい場合は init_audit_db を利用可能。
- 環境変数の必須キーを .env.example を参考に設定してください（JQUANTS_REFRESH_TOKEN など）。

---

今後のリリース案内（例）
- 次版で予定する改善: execution 層（kabu ステーション連携）実装、strategy 実装例、監視/アラート（Slack 通知）の統合、より多様な品質チェックの追加、単体テストおよび CI ワークフローの整備。