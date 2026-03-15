# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に従います。  
現在のバージョンは 0.1.0 です。

履歴:
- 0.1.0 - 2026-03-15
  - Added
    - パッケージ初期リリース "KabuSys"。
      - パッケージ名: kabusys
      - 公開 API: __version__ = "0.1.0", __all__ = ["data", "strategy", "execution", "monitoring"]
    - 環境変数・設定管理モジュール (kabusys.config)
      - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
      - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト用途想定）。
      - .env パーサー実装:
        - コメント行・空行の無視、`export KEY=val` 形式のサポート。
        - シングル/ダブルクォートで囲まれた値のバックスラッシュによるエスケープ処理に対応。
        - クォートなし値のインラインコメント扱いは直前がスペース/タブの場合のみとする振る舞いを採用。
      - 環境変数読込時の上書き制御:
        - OS 環境変数を保護する protected set を用意し、.env.local は既存の OS 環境変数を上書きしない。
      - Settings クラスを公開（settings = Settings()）:
        - J-Quants / kabuステーション / Slack / データベースパス 等のプロパティを提供。
        - 必須値は _require() により未設定時に ValueError を送出。
        - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の値検証を実装。
        - is_live / is_paper / is_dev の便利プロパティを提供。
    - データ層スキーマ定義モジュール (kabusys.data.schema)
      - DuckDB 用スキーマを定義（Raw / Processed / Feature / Execution の多層構造）。
      - 主なテーブル（抜粋）:
        - Raw: raw_prices, raw_financials, raw_news, raw_executions
        - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
        - Feature: features, ai_scores
        - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
      - 列定義に対する制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY 等）を多用してデータ整合性を強化。
      - 頻出クエリ向けのインデックス定義を追加（例: prices_daily(code, date), signal_queue(status), orders(status) 等）。
      - init_schema(db_path) を提供:
        - 指定パスに対してディレクトリ自動作成、DDL とインデックスを順次実行して DB を初期化。
        - 冪等（既存テーブルがある場合はスキップ）。
        - ":memory:" サポート。
      - get_connection(db_path) を提供（スキーマ初期化は行わない）。
    - 監査ログ（トレーサビリティ）モジュール (kabusys.data.audit)
      - シグナルから約定に至るトレーサビリティを保証する監査テーブル群を定義。
      - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）設計方針に準拠。
      - 主な監査テーブル:
        - signal_events: 戦略が生成したシグナルを全件記録（棄却・エラー含む）。
        - order_requests: 冪等キー(order_request_id) を持つ発注要求ログ（limit/stop/market のチェック制約を実装）。
        - executions: 証券会社提供の約定ID（broker_execution_id）を冪等キーとして保持。
      - 監査テーブルは削除しない前提で設計（FOREIGN KEY は ON DELETE RESTRICT）。
      - 全ての TIMESTAMP を UTC で保存する（init_audit_schema は SET TimeZone='UTC' を実行）。
      - init_audit_schema(conn) と init_audit_db(db_path) を提供（既存接続に監査テーブルを追加、または監査専用 DB を初期化）。
      - 監査用インデックスを複数定義（signal_events の日付・銘柄検索、order_requests/status、executions の broker_order_id 等）。
  - Changed
    - （初回リリースのため変更履歴なし）
  - Fixed
    - （初回リリースのため修正履歴なし）
  - Deprecated
    - なし
  - Removed
    - なし
  - Security
    - なし

補足（開発者向けメモ）
- 使用例:
  - 設定取得: from kabusys.config import settings; settings.jquants_refresh_token
  - DB 初期化: from kabusys.data.schema import init_schema; conn = init_schema(settings.duckdb_path)
  - 監査テーブル追加: from kabusys.data.audit import init_audit_schema; init_audit_schema(conn)
- 設計上の注意:
  - .env の自動読み込みはプロジェクトルートを基準にするため、パッケージ配布後も CWD に依存せず動作する。
  - .env 読み込み時に OS 環境変数を保護するため、既存の OS 環境変数はデフォルトで上書きされない（ただし .env.local は override=True で適用）。
  - 監査ログは削除せず永続化することを前提としているため、データ削除操作は慎重に行ってください。