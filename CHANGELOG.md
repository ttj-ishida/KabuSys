# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-15

初回リリース。

### 追加 (Added)
- パッケージ基盤を追加（kabusys v0.1.0）。
  - パッケージのトップレベルでバージョンを定義: __version__ = "0.1.0"。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境変数・設定管理モジュールを追加（kabusys.config）。
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダを実装。
    - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して判定（CWD に依存しない挙動）。
    - 読み込み順序: OS 環境変数 > .env.local（上書き） > .env（未設定キーのみ設定）。
    - OS 環境変数が保護されるよう protected キーセットを使用して誤上書きを防止。
  - .env パーサを実装（_parse_env_line）。
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮して正しくパース。
    - クォート無し値では「#」がインラインコメントとして扱われる場合の判定（直前がスペース/タブの場合）を実装。
    - 無効行（空行やコメント、キーなし行など）は無視。
  - 設定取得用の Settings クラスを提供（settings インスタンスを公開）。
    - J-Quants（JQUANTS_REFRESH_TOKEN）、kabuステーション API（KABU_API_PASSWORD, KABU_API_BASE_URL）、
      Slack（SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）、データベースパス（DUCKDB_PATH, SQLITE_PATH）等のプロパティを提供。
    - KABUSYS_ENV（development / paper_trading / live）の検証を実施。無効値は ValueError を送出。
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）を検証。
    - is_live / is_paper / is_dev のブールプロパティを提供。
    - 必須環境変数未設定時は _require() により ValueError を送出。

- DuckDB ベースのデータスキーマ定義を追加（kabusys.data.schema）。
  - Data Lake / Data Platform を想定した 4 層（Raw / Processed / Feature / Execution）のテーブル定義を含む DDL を実装。
    - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
    - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature レイヤー: features, ai_scores
    - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・制約（CHECK、PRIMARY KEY、FOREIGN KEY 等）を定義。
  - 頻出クエリを想定したインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status 等）。
  - init_schema(db_path) を提供:
    - DuckDB データベースを初期化し全テーブル・インデックスを作成（冪等）。
    - db_path の親ディレクトリが存在しない場合は自動作成。
    - ":memory:" をサポートすることでインメモリ DB を利用可能。
  - get_connection(db_path) を提供（既存 DB への接続。初回は init_schema を推奨）。

- 監査ログ（Audit）モジュールを追加（kabusys.data.audit）。
  - シグナルから約定に至るトレーサビリティを確保する監査テーブル群を実装。
    - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）を想定。
  - 監査用テーブル:
    - signal_events: 戦略が生成したシグナルを全て記録（リスクで棄却されたものも含む）。decision フィールドによる詳細な理由列挙を持つ。
    - order_requests: 発注要求ログ。order_request_id を冪等キーとして扱い、limit/stop/market のチェック制約を付与。status と error_message を保持。
    - executions: 証券会社からの約定ログ。broker_execution_id をユニークな冪等キーとして保存。
  - すべての TIMESTAMP を UTC で保存する設定（init_audit_schema は "SET TimeZone='UTC'" を実行）。
  - 監査用のインデックス群を作成（例: idx_signal_events_date_code, idx_order_requests_status, idx_executions_code_executed_at 等）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供（既存接続へのテーブル追加、専用 DB 初期化の両対応）。

- パッケージの空モジュールプレースホルダを追加:
  - kabusys.execution.__init__、kabusys.strategy.__init__、kabusys.data.__init__、kabusys.monitoring.__init__（将来の拡張用）。

### 変更 (Changed)
- 該当なし（初回リリースのため）。

### 修正 (Fixed)
- 該当なし（初回リリースのため）。

### 非推奨 (Deprecated)
- 該当なし。

### 削除 (Removed)
- 該当なし。

### セキュリティ (Security)
- 該当なし。

注記:
- データベーススキーマは冪等に作成されるため、何度でも安全に init_schema / init_audit_schema を実行可能です。
- 環境変数の自動ロードはテスト環境などで無効化できるため、CI での確定的な挙動を確保できます。
- audit テーブルは削除しない方針（FK は ON DELETE RESTRICT）で監査証跡を保持する設計です。