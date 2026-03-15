# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
特になし。

## [0.1.0] - 2026-03-15

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージ公開 API: __all__ = ["data", "strategy", "execution", "monitoring"]

- 環境設定/読み込み機能（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索するため、実行カレントディレクトリに依存しない。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - OS側の既存環境変数は保護され、.env.local は既存値を上書きできる（ただし保護中のキーは上書きされない）。
    - 自動ロード無効フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって自動読み込みを無効化可能（テスト用途を想定）。
  - .env パーサーの実装:
    - 空行・コメント行（先頭が#）を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクオートで囲まれた値のエスケープ処理に対応（バックスラッシュによるエスケープを解釈）。
    - クォートなし値では inline コメント認識のルールを細かく扱う（'#' の直前がスペース/タブの場合のみコメントとみなす）。
  - Settings クラスによる環境値アクセス:
    - 必須環境変数を取得するメソッド（未設定時は ValueError を送出）
    - サポートする設定項目（例）:
      - JQUANTS_REFRESH_TOKEN (必須)
      - KABU_API_PASSWORD (必須)
      - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
      - SLACK_BOT_TOKEN (必須)
      - SLACK_CHANNEL_ID (必須)
      - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
      - SQLITE_PATH (デフォルト: data/monitoring.db)
      - KABUSYS_ENV: 有効値は development / paper_trading / live（不正値は例外）
      - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（不正値は例外）
    - ユーティリティプロパティ: is_live, is_paper, is_dev

- データベーススキーマ定義（kabusys.data.schema）
  - DuckDB 用のスキーマを層構造（Raw / Processed / Feature / Execution）で定義。
  - 生データ（Raw Layer）テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions（各列制約・主キーを定義）
  - 整形済み（Processed Layer）テーブル:
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - 特徴量（Feature Layer）テーブル:
    - features, ai_scores
  - 実行関連（Execution Layer）テーブル:
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - テーブル設計上の特徴:
    - 各種 CHECK 制約、主キー、外部キーを設定してデータ整合性を担保
    - 頻出クエリに対するインデックス群を定義（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status など）
    - 外部キー依存を考慮した作成順を明示
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定パスに DuckDB ファイルを作成（必要なら親ディレクトリを自動作成）
      - 全テーブル・インデックスを冪等に作成
      - ":memory:" を指定してインメモリ DB を利用可能
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続（スキーマ初期化は行わない。初回は init_schema を推奨）

- 監査ログ（トレーサビリティ）スキーマ（kabusys.data.audit）
  - シグナルから約定までの追跡を目的とした監査テーブル群を定義。
  - 主なテーブル:
    - signal_events: 戦略が生成した全シグナルを記録（棄却やエラーも含む）
    - order_requests: 発注要求ログ（order_request_id を冪等キーとして扱う）
      - order_type に応じた制約 (limit / stop / market) を実装
      - status 管理（pending → sent → filled / partially_filled / cancelled / rejected / error）
    - executions: 実際の約定ログ（broker_execution_id をユニーク・冪等キーとして扱う）
  - 設計原則:
    - すべての TIMESTAMP を UTC で保存（init_audit_schema 実行時に TimeZone='UTC' を設定）
    - 監査ログは削除しない前提（ON DELETE RESTRICT）
    - created_at / updated_at による時系列トレース
  - インデックス:
    - 日付・銘柄検索、戦略別検索、status ベースのキュー検索、broker_order_id / broker_execution_id 紐付け用インデックス等を定義
  - 公開 API:
    - init_audit_schema(conn: duckdb.DuckDBPyConnection) -> None
      - 既存の DuckDB 接続に監査テーブルを追加（冪等）
      - UTC タイムゾーン設定を適用
    - init_audit_db(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 監査ログ用の新規 DuckDB を初期化して接続を返す（親ディレクトリ自動作成、UTC 適用、":memory:" 対応）

- プレースホルダーパッケージ
  - execution, strategy, monitoring 各パッケージの __init__.py を配置（将来的な実装用に構造を確立）

Notes
- DuckDB に依存するため、実行環境に duckdb パッケージが必要。
- デフォルトのデータベースファイルパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視用データベース設定用): data/monitoring.db

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- なし

----

参照: コードに定義された仕様・制約・デフォルト値は CHANGELOG の説明に基づきます。実際の運用では .env.example を参照し、必須環境変数を設定してください。