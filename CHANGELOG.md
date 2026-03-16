# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システムのコアライブラリ基盤を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- 全体
  - パッケージ `kabusys` を追加。パッケージバージョンを `0.1.0` に設定。
  - 主要サブパッケージを公開: data, strategy, execution, monitoring（strategy/execution の __init__ はプレースホルダとして存在）。

- 設定 / 環境変数管理 (kabusys.config)
  - 環境変数読み込みモジュールを実装。
  - プロジェクトルート自動検出機能を追加（.git または pyproject.toml を探索）。
  - .env / .env.local ファイル自動読み込み（優先順位: OS 環境 > .env.local > .env）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト等で利用可能）。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等）。
  - Settings クラスを実装し、主要設定をプロパティ経由で取得可能に：
    - J-Quants トークン: JQUANTS_REFRESH_TOKEN（必須）
    - kabu API: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト localhost）
    - Slack: SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DB パス: DUCKDB_PATH / SQLITE_PATH（デフォルト値あり）
    - 環境種別: KABUSYS_ENV (development/paper_trading/live)、値検証
    - ログレベル: LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)、値検証
    - ラッパーで is_live / is_paper / is_dev を提供

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装（価格日足、財務データ、JPX カレンダー取得）。
  - レート制限制御 (120 req/min) の固定間隔スロットリング実装（_RateLimiter）。
  - リトライロジックを実装（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）。
  - 429 の場合は Retry-After ヘッダを優先して待機。
  - 401 受信時はリフレッシュトークンから id_token を自動リフレッシュして 1 回だけ再試行（無限再帰を避ける設計）。
  - id_token のモジュールレベルキャッシュ（ページネーション中で共有）。
  - ページネーション対応の fetch_* 関数実装:
    - fetch_daily_quotes
    - fetch_financial_statements
    - fetch_market_calendar
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE
  - データ整形ユーティリティ _to_float / _to_int を用意。
  - 各保存関数は fetched_at を UTC ISO フォーマットで記録し、PK 欠損行はスキップして警告を出力。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層に分けた包括的なテーブル群を定義。
  - 主なテーブル群:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 型チェック、チェック制約（CHECK）、主キー、外部キーを含むスキーマを実装。
  - 検索高速化のためのインデックス群を定義。
  - init_schema(db_path) でディレクトリ自動作成とテーブル作成（冪等）を行う API を提供。
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL パイプラインを実装（差分取得・保存・品質チェックの流れ）。
  - 設計方針: 差分更新、バックフィル、品質チェックは Fail-Fast ではなく問題を収集して呼び出し元に委ねる。
  - 主な機能:
    - 差分更新ユーティリティ（テーブルの最終取得日を取得する関数）
    - 市場カレンダーの先読み（デフォルト 90 日）
    - バックフィルのデフォルト値 3 日（_DEFAULT_BACKFILL_DAYS）
    - ETLResult データクラスを追加（取得数・保存数・品質問題・エラー一覧を格納）
    - run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL ジョブ（fetch + save）
    - run_daily_etl: 全体実行エントリポイント（カレンダー → 株価 → 財務 → 品質チェック）
    - 営業日調整ヘルパー (_adjust_to_trading_day) を実装（market_calendar に基づき過去方向で調整）

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - 監査用スキーマを追加（signal_events, order_requests, executions）。
  - 監査設計:
    - UUID 連鎖によるトレーサビリティ（signal_id, order_request_id, broker_order_id, broker_execution_id 等）
    - 発注要求は冪等キー（order_request_id）として動作
    - すべての TIMESTAMP を UTC で保存する方針（init_audit_schema は SET TimeZone='UTC' を実行）
    - エラーや棄却されたイベントも永続化
  - init_audit_schema(conn) / init_audit_db(db_path) API を提供。

- データ品質チェック (kabusys.data.quality)
  - QualityIssue データクラスを追加（check_name, table, severity, detail, rows）。
  - チェック実装:
    - check_missing_data: raw_prices の OHLC 欠損検出（必須カラムの NULL を error として報告）
    - check_spike: 前日比によるスパイク検出（デフォルト閾値 50%）
  - 各チェックはサンプル行を返し、Fail-Fast ではなく問題を収集して返す設計。

### 変更 (Changed)
- 初回リリースのため変更履歴はありません（新規追加のみ）。

### 修正 (Fixed)
- 初回リリースのため修正履歴はありません（新規追加のみ）。

### 注意事項 / マイグレーション
- 設定:
  - 必須な環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を設定しないとプロパティアクセスで ValueError が発生します。`.env.example` を参考に .env を配置してください。
  - 自動 .env 読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください（テスト時に便利です）。
- DuckDB:
  - 初回は data.schema.init_schema(db_path) を呼び出してスキーマを作成してください。以降は get_connection を用いて接続を取得できます。
  - 監査ログは別途 init_audit_schema() / init_audit_db() で初期化してください（UTC でのタイムゾーン保存を保証します）。
- J-Quants クライアント:
  - API レート制限と自動リトライ・トークンリフレッシュの仕組みは組み込まれていますが、実運用では API キーや接続先の確認、ログ監視を行ってください。

---

今後の予定（例）
- strategy / execution の具体的実装（戦略ロジック・発注実行ハンドラ）
- モニタリング / アラート機能の追加
- より包括的なテストケースと CI ワークフローの整備

（以上）