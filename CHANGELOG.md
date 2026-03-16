# Changelog

すべての注目すべき変更履歴をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-16
初回リリース

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - __all__ で主要モジュール（data, strategy, execution, monitoring）を公開。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml から探索して検出（CWD 非依存）。
    - .env と .env.local の読み込み順序（OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - protected 引数を使った読み込みオプション（既存 OS 環境変数を上書きしない保護機能）。
  - Settings クラスを提供し、以下の設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID
    - DUCKDB_PATH、SQLITE_PATH（デフォルトパスを設定）
    - KABUSYS_ENV（development|paper_trading|live の検証）および LOG_LEVEL（有効値検証）
    - is_live / is_paper / is_dev ヘルパー

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得 API クライアントを実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - リトライ/エラーハンドリング:
    - 指数バックオフによる最大 3 回リトライ（408/429/5xx 対応）。
    - 429 の場合は Retry-After ヘッダを優先。
    - 401 受信時は自動でリフレッシュして 1 回だけリトライ（無限再帰を防止）。
  - id_token キャッシュ（モジュールレベル、ページネーション間で共有）。
  - ページネーション対応（pagination_key を利用して全ページを取得）。
  - データ保存ユーティリティ:
    - DuckDB 用の save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - fetched_at を UTC ISO フォーマットで保存（Look-ahead Bias 対策）。
    - INSERT ... ON CONFLICT DO UPDATE による冪等保存（重複・更新の吸収）。
  - 型変換ユーティリティ: _to_float / _to_int（不正値の安全な取り扱い、"1.0" のような文字列処理を含む）。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataPlatform の 3 層（Raw / Processed / Feature）＋Execution 層を網羅するテーブル定義を追加。
    - Raw layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）と型付けを整備。
  - 頻出クエリ向けのインデックス群を作成。
  - init_schema(db_path) でディレクトリ自動作成とテーブル初期化（冪等）を行う API を提供。
  - get_connection(db_path) による既存 DB 接続取得。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新＆バックフィルを行う ETL（run_daily_etl）を実装。
    - 市場カレンダー、株価日足、財務データの順で差分取得・保存。
    - calender の先読み（デフォルト 90 日）、株価/財務のバックフィル（デフォルト 3 日）。
    - 各ステップは個別にエラーハンドリングされ、他ステップを妨げない設計（Fail-Fast ではない）。
    - ETL 実行後に品質チェックを実行するオプションを提供（spike_threshold デフォルト 0.5）。
  - run_prices_etl / run_financials_etl / run_calendar_etl を提供（差分判定、最終取得日の取得ヘルパーを利用）。
  - _adjust_to_trading_day：非営業日を直近の過去営業日に調整するヘルパー（market_calendar を利用、フォールバックあり）。
  - ETLResult dataclass を導入（取得数・保存数・品質問題・エラー一覧等を集約）。to_dict によるシリアライズ対応。

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - signal_events / order_requests / executions の監査テーブルを定義。
  - トレーサビリティの階層化（business_date → strategy_id → signal_id → order_request_id → broker_order_id）をサポート。
  - order_request_id を冪等キーとして扱う設計。発注種別ごとのチェック制約（limit/stop/market の必須/禁止価格カラム）を実装。
  - executions では broker_execution_id をユニークに保持（証券会社側の冪等性）。
  - タイムゾーンを UTC に固定（init_audit_schema は SET TimeZone='UTC' を実行）。
  - init_audit_schema(conn) と init_audit_db(db_path) により既存接続／専用 DB の初期化をサポート。
  - 監査向けのインデックスを多数追加（status, date, code, signal_id, broker_order_id 等を高速化）。

- データ品質チェック (src/kabusys/data/quality.py)
  - QualityIssue dataclass を導入（チェック名、テーブル、重大度、詳細、サンプル行）。
  - 実装されたチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は許容）。
    - check_spike: LAG を用いた前日比スパイク検出（閾値デフォルト 0.5）。
  - 各チェックは DuckDB 接続と SQL を使って効率的に実行し、最大 10 件のサンプル行を返す設計。
  - チェックは Fail-Fast ではなく全件収集し、呼び出し元が重大度で判断できるようにする。

### 変更 (Changed)
- 該当なし（初回リリースのため既存変更はなし）

### 修正 (Fixed)
- 該当なし（初回リリース）

### 破壊的変更 (Breaking Changes)
- 該当なし（初回リリース）

### セキュリティ (Security)
- 該当なし（今回のコミット範囲では特筆すべきセキュリティ修正は無し。ただし環境変数やトークン取扱いは Settings / get_id_token の使用に注意。）

注記・補足
- 多くの箇所で「冪等性」「UTC による時刻管理」「ロギング」「入力検証（CHECK）」を意識した実装が行われています。
- J-Quants API の実行はレート制御・リトライ・トークン自動更新を含む堅牢な実装になっていますが、実運用時は API キーやネットワークの監視、ログ設定（LOG_LEVEL）を適切に行ってください。
- DuckDB のスキーマ初期化は冪等です。既存の DB に影響を与えずに呼び出せますが、運用前にバックアップを取ることを推奨します。