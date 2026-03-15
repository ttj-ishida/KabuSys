Changelog
=========
すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

次のリリースで重要な変更がある場合は Unreleased に記載してください。

Unreleased
----------
（なし）

0.1.0 - 2026-03-15
------------------
初回リリース。以下の主要機能と実装を追加しました。

Added
- パッケージメタ
  - kabusys パッケージを追加。バージョンは 0.1.0（src/kabusys/__init__.py）。
  - __all__ に ["data", "strategy", "execution", "monitoring"] を定義。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env ファイルと環境変数を統一的に扱う Settings クラスを追加。
  - 自動ロードの仕組みを実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 環境変数自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env のパーサを実装:
    - コメント行と空行の無視。
    - "export KEY=val" 形式に対応。
    - シングル／ダブルクォート内のエスケープ処理（バックスラッシュ）に対応。
    - クォートなし値の行内コメント判定（'#' の直前が空白/タブの場合にコメントとみなす）。
  - .env 読み込み時の上書きルール:
    - override=False: 未設定のキーのみセット。
    - override=True: protected（読み込み時に取得した OS 環境変数のキーセット）を除いて上書き。
  - Settings が取得する主要プロパティ（必須キーは未設定時に ValueError を送出）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の便利プロパティ

- データスキーマ（DuckDB）初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の 4 層を想定したスキーマ定義を追加。
  - 追加した主なテーブル（DDL の抜粋）:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム制約（CHECK、PRIMARY KEY、FOREIGN KEY 等）を多数導入（整合性とデータ品質を確保）。
  - 頻出クエリ向けのインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) を追加:
    - DuckDB ファイルを作成（parent ディレクトリ自動作成）し、すべてのテーブルとインデックスを冪等に作成する。
    - ":memory:" によるインメモリ DB のサポート。
  - get_connection(db_path) を追加（既存 DB への接続のみ。スキーマ初期化は行わない）。

- 監査ログ（Audit）スキーマ（src/kabusys/data/audit.py）
  - シグナルから約定までのトレーサビリティを担保する監査テーブル群を追加。
  - トレーサビリティ構造: business_date → strategy_id → signal_id → order_request_id → broker_order_id
  - 追加した監査テーブル:
    - signal_events（シグナル生成ログ。棄却されたシグナルも保存）
    - order_requests（発注要求ログ。order_request_id を冪等キーとして扱う）
    - executions（約定ログ。broker_execution_id を冪等キーとして扱う）
  - order_requests における注文タイプ別の CHECK 制約（limit/stop/market の価格要件）を導入。
  - 監査用のインデックス定義を追加（例: idx_signal_events_date_code, idx_order_requests_status, idx_executions_broker_order_id 等）。
  - init_audit_schema(conn) を追加:
    - 与えた DuckDB 接続に監査用テーブルとインデックスを冪等に作成。
    - 実行前に "SET TimeZone='UTC'" を実行し、TIMESTAMP を UTC で保存する方針を明示。
  - init_audit_db(db_path) を追加（監査専用 DB の作成 + 初期化）。

- パッケージ構造
  - サブパッケージの __init__.py を配置（strategy, execution, monitoring, data） — 各サブパッケージのプレースホルダ。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated / Removed / Security
- （該当なし）

Migration / Usage Notes
- 環境変数
  - 必須の秘密情報（JQUANTS_REFRESH_TOKEN 等）は環境変数または .env(.local) に設定してください。未設定時は Settings のプロパティ参照で ValueError を送出します。
  - 自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で便利です）。
  - .env.local は .env より優先して読み込まれ、既存 OS 環境変数は上書きされません（保護）。

- DuckDB 初期化
  - 通常は以下のようにしてスキーマを初期化して接続を取得します:
    - from kabusys.data.schema import init_schema
      conn = init_schema("data/kabusys.duckdb")
  - 監査テーブルを既存の接続に追加する場合:
    - from kabusys.data.audit import init_audit_schema
      init_audit_schema(conn)
  - 監査専用 DB を個別に作成する場合:
    - from kabusys.data.audit import init_audit_db
      conn = init_audit_db("data/kabusys_audit.duckdb")

設計上の留意点（今後の改善候補）
- .env のパーシングはシェルとの完全互換を目指していません（現在は主要ケースに対応）。特殊ケースは userspace の .env 作成規約で回避することを推奨します。
- 現在のスキーマは DuckDB を想定して設計されています。将来的に別の RDB をサポートする場合は DDL と一部制約の見直しが必要です。
- 監査データは削除しない前提（FOREIGN KEY は ON DELETE RESTRICT を利用）。運用上の保守（アーカイブ等）方針を検討する必要があります。

お問い合わせ / 貢献
- バグ報告や機能提案は issue を作成してください。README / CONTRIBUTING は別途追加予定です。