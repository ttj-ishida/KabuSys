# Changelog

すべての注目すべき変更点をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。  
安定版リリースや後方互換性の有無は各リリースノートのセクションを参照してください。

注意: 日付はこのコードベースの現状（ソースコードから推測）を基に付与しています。

## [Unreleased]
- (なし)

## [0.1.0] - 2026-03-15
初回公開リリース。日本株自動売買システムのコア基盤を提供します。主要な機能は設定管理、データ層（DuckDB スキーマ）、監査ログの初期化 API を含みます。

### Added
- パッケージの基本定義
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に設定。

- 環境変数／設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 使用例をドキュメントコメントに記載。
  - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
  - .env 解析機能:
    - export KEY=val 形式をサポート。
    - シングル／ダブルクォート内のエスケープシーケンスに対応。
    - クォートなしの値では '#' をインラインコメントとして扱うルールを実装（直前がスペース/タブの場合にコメントと判定）。
    - 無効行やコメント行をスキップ。
    - .env 読み込み時に OS 環境変数は保護（protected）され、override の挙動を制御。
  - 必須設定取得用の _require() と、以下のプロパティを持つ Settings:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb), SQLITE_PATH (デフォルト: data/monitoring.db)
    - KABUSYS_ENV（development / paper_trading / live の検証）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）およびユーティリティフラグ is_live / is_paper / is_dev。

- データ層（DuckDB スキーマ）を追加（src/kabusys/data/schema.py）
  - DataLake レイヤー設計に基づきテーブルを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム型、CHECK 制約、PRIMARY KEY、FOREIGN KEY を細かく定義（データ整合性を強化）。
  - 頻出クエリに備えたインデックス定義を多数追加（例: idx_prices_daily_code_date、idx_signal_queue_status、idx_orders_status など）。
  - db 初期化 API:
    - init_schema(db_path: str | Path) -> duckdb connection: 親ディレクトリの自動作成、DDL の冪等実行、インデックス作成。
    - get_connection(db_path: str | Path) -> duckdb connection: 既存 DB への接続（スキーマ初期化は行わない）。
  - ":memory:" モードに対応。

- 監査ログ／トレーサビリティ機能を追加（src/kabusys/data/audit.py）
  - シグナルから約定に至るフローを UUID で連鎖可能にする監査テーブル群を提供:
    - signal_events（戦略が生成したすべてのシグナルを保存、棄却やエラーも含む）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ。limit/stop の価格チェックを含む制約）
    - executions（証券会社からの約定ログ。broker_execution_id をユニークキーとして冪等に対応）
  - 監査用インデックスを多数定義（例: idx_signal_events_date_code、idx_order_requests_status、idx_executions_code_executed_at など）。
  - init_audit_schema(conn) により既存の DuckDB 接続に監査テーブルを追加可能（冪等）。
  - init_audit_db(db_path) により監査専用 DB を初期化して接続を返す。
  - すべての TIMESTAMP を UTC で保存する方針を実装（init_audit_schema 内で SET TimeZone='UTC' を実行）。
  - 監査データは削除しない前提、外部キーは ON DELETE RESTRICT を採用。

- パッケージ構成（プレースホルダ）
  - strategy, execution, monitoring のパッケージ初期化ファイルを追加（空の __init__.py を配置）。今後の拡張ポイント。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / マイグレーション / 使用上の注意
- DB 初期化:
  - 初回起動時は data.schema.init_schema(settings.duckdb_path) を呼んでスキーマを作成してください。
  - 監査テーブルを別 DB で管理する場合は data.audit.init_audit_db() を利用できます。既存接続へ追加する場合は init_audit_schema(conn) を使用してください。
- 環境変数:
  - 必須の環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は Settings のプロパティで _require() によりチェックされます。未設定の場合は ValueError が発生します。
  - .env の自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に探索します。パッケージ配布後でも CWD に依存せず動作するよう設計されています。
- トレーサビリティ:
  - order_request_id と broker_execution_id 等により発注-約定の冪等性と追跡性を確保しています。アプリケーション側で updated_at を更新する運用が必要です。
- 制約と検証:
  - 多数の CHECK 制約（サイズ>0、価格>=0、列の有無の組合せチェック等）を DDL レベルで設定しており、データ整合性に注意してください。これにより不正データの挿入は DB 側で拒否されます。

---

以上。今後のリリースでは戦略ロジック、実取引インタフェース、モニタリング機能の実装・改善点を記載してください。