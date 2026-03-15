# CHANGELOG

すべての notable な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-03-15

初回リリース。

### 追加 (Added)
- パッケージ構成を追加
  - kabusys パッケージを作成。公開モジュール: data, strategy, execution, monitoring。
  - バージョン情報: __version__ = "0.1.0"。

- 環境変数/設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。
  - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサを実装:
    - コメント行と空行のスキップ。
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォート無しでのインラインコメント判別（'#' の直前が空白またはタブの場合にコメントとみなす）。
  - 環境変数の取得ラッパ Settings を提供:
    - 必須設定の取得時に未設定なら ValueError を発生。
    - サポートされる設定例:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（既定: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（既定: data/kabusys.duckdb）
      - SQLITE_PATH（既定: data/monitoring.db）
      - KABUSYS_ENV（既定: development; 有効値: development, paper_trading, live）
      - LOG_LEVEL（既定: INFO; 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - Helper プロパティ: is_live, is_paper, is_dev。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本機能:
    - 株価日足（OHLCV）取得: fetch_daily_quotes()
    - 財務データ（四半期 BS/PL）取得: fetch_financial_statements()
    - JPX マーケットカレンダー取得: fetch_market_calendar()
    - リフレッシュトークンからの ID トークン取得: get_id_token()
  - 設計特徴:
    - API レート制限の厳守: 固定間隔スロットリング実装（120 req/min -> min interval 計算）。
    - リトライロジック: 指数バックオフ、最大3回リトライ。対象はネットワーク系エラーおよび HTTP 408/429/5xx。
    - 401 Unauthorized 受信時には ID トークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止）。
    - ページネーション対応（pagination_key を追跡）。
    - JSON パース失敗時は意味のあるエラーを送出。
    - ID トークンはモジュールレベルでキャッシュし、ページネーション間で共有。
    - fetched_at を UTC で記録して Look-ahead Bias を防止。

  - DuckDB への保存機能（冪等性）:
    - save_daily_quotes(), save_financial_statements(), save_market_calendar() を提供。
    - INSERT .. ON CONFLICT DO UPDATE を用いて冪等性を確保。
    - PK 欠損行はスキップし、スキップ数をログ出力。
    - 日付/時刻は UTC（fetched_at）で記録。
    - 型変換ユーティリティ: _to_float(), _to_int()（不正な値は None を返す）。

- DuckDB スキーマと初期化 (kabusys.data.schema)
  - DataLayer を想定したスキーマを定義し、init_schema(db_path) による初期化を提供。
  - 層構造（Raw / Processed / Feature / Execution）に基づく幅広いテーブルを定義:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）を設定。
  - よく使われるクエリのためのインデックス群を作成（コード・日付、ステータス検索等）。
  - get_connection(db_path) を提供（既存 DB への接続、スキーマ初期化は行わない点に注意）。
  - init_schema は親ディレクトリ自動作成や ":memory:" のサポートを備える。

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - トランザクションの完全トレーサビリティを目的とした監査テーブル群を追加:
    - signal_events（戦略が生成したシグナルを記録）
    - order_requests（発注要求、order_request_id を冪等キーとして利用）
    - executions（証券会社からの約定情報）
  - 設計方針:
    - すべての TIMESTAMP を UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）。
    - エラーや棄却済みイベントも永続化（削除しない前提、ON DELETE RESTRICT）。
    - order_requests に複数のチェック制約（limit/stop/market の価格要件）を実装。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（既存の DuckDB 接続へ監査テーブルを追加可能）。

- プレースホルダーモジュール
  - kabusys.execution, kabusys.strategy, kabusys.monitoring のパッケージを用意（現時点では初期化ファイルのみ）。

### 変更 (Changed)
- （該当なし）初回リリースのため過去変更はなし。

### 修正 (Fixed)
- （該当なし）初回リリースのため修正履歴はなし。

### 削除 (Removed)
- （該当なし）

### 互換性および移行ノート (Notes)
- データベース初期化:
  - DuckDB を使用する場合は初回に init_schema(settings.duckdb_path) を呼び出してスキーマを作成してください。
  - 監査ログを利用する場合は init_audit_schema(conn) を呼んで監査テーブルを追加してください。
- 環境変数:
  - 必須の環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）が未設定の場合、Settings の該当プロパティ呼び出しで ValueError が発生します。
  - 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト環境等で利用）。
- J-Quants クライアント:
  - API レート制限・リトライは組み込み済みですが、外部からの大量並列呼び出しがある場合は別途調整が必要です（モジュールレベルの RateLimiter は単一プロセス内の制御を想定）。
  - get_id_token はリフレッシュトークンを引数に受け取れますが、省略時は Settings から読み込みます。テスト時等での無限再帰を防ぐため内部リフレッシュ呼び出しは allow_refresh=False で制御しています。

このリリースは基盤機能（構成管理、データ取得、永続化スキーマ、監査ログ）の整備を目的とした初版です。戦略・発注・モニタリングの実装は今後追加予定です。