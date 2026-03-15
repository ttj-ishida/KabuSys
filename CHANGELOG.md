# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※ 初回リリース (0.1.0) は、プロジェクトのコアコンポーネント（設定管理、J-Quants クライアント、DuckDB スキーマ、監査ログ等）を実装した内容に基づき推測して作成しています。

## [0.1.0] - 2026-03-15

### Added
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加。パッケージメタ情報として __version__ = "0.1.0" を設定。
  - パッケージ公開 API に data, strategy, execution, monitoring を含める（__all__）。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。読み込み順は OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用など）。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理をサポート）。
  - .env 読み込み時、OS の既存環境変数は保護（protected）され、.env.local の override オプションにより上書き制御が可能。
  - 必須環境変数取得用の _require() を実装（未設定時は ValueError）。
  - Settings に以下のプロパティを実装:
    - jquants_refresh_token (JQUANTS_REFRESH_TOKEN 必須)
    - kabu_api_password (KABU_API_PASSWORD 必須)
    - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
    - slack_bot_token (SLACK_BOT_TOKEN 必須)
    - slack_channel_id (SLACK_CHANNEL_ID 必須)
    - duckdb_path (デフォルト: data/kabusys.duckdb)
    - sqlite_path (デフォルト: data/monitoring.db)
    - env / log_level（値検証を行い、不正値は ValueError）
    - is_live / is_paper / is_dev のヘルパープロパティ

- J-Quants データクライアント (kabusys.data.jquants_client)
  - J-Quants API とのインタラクションをするクライアントを追加。
  - 基本設計:
    - API レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時はリフレッシュトークンから ID トークンを自動取得して 1 回リトライ（無限ループ回避のため allow_refresh フラグ制御）。
    - ページネーション対応（pagination_key を利用）。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を抑止するトレーサビリティを確保。
    - モジュールレベルで ID トークンをキャッシュ（ページネーション間で共有）。
  - 公開 API:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(...) -> list[dict]
    - fetch_financial_statements(...) -> list[dict]
    - fetch_market_calendar(...) -> list[dict]
    - save_daily_quotes(conn, records) -> int
    - save_financial_statements(conn, records) -> int
    - save_market_calendar(conn, records) -> int
  - データ保存は DuckDB を用い、INSERT ... ON CONFLICT DO UPDATE により冪等性を確保。
  - ヘルパー関数 _to_float / _to_int を実装し、入力値の型安全な変換を行う。

- DuckDB スキーマ (kabusys.data.schema)
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）＋Execution 層のテーブル群を定義。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な型チェック・制約（CHECK、PRIMARY KEY、FOREIGN KEY）を設定。
  - 頻出クエリ向けのインデックスも作成（コード・日付検索、ステータス検索、外部キー参照向けなど）。
  - init_schema(db_path) を実装:
    - db_path の親ディレクトリが存在しない場合は自動的に作成。
    - :memory: をサポート。
    - テーブル作成は冪等（既存テーブルを上書きしない）。
  - get_connection(db_path) を提供（既存 DB に接続、スキーマ初期化は行わない）。

- 監査ログ（Audit）モジュール (kabusys.data.audit)
  - シグナルから約定に至るトレーサビリティを担保する監査用テーブル群を追加。
  - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）を設計に反映。
  - 主なテーブル:
    - signal_events（戦略が生成したシグナルの記録、棄却やエラーも含む）
    - order_requests（発注要求: order_request_id を冪等キーとして扱う）
    - executions（約定ログ、broker_execution_id をユニークキーとして冪等性確保）
  - ステータス列と制約、更新履歴用の created_at / updated_at を含む設計。
  - init_audit_schema(conn) / init_audit_db(db_path) を追加。init_audit_schema は UTC タイムゾーンを強制（SET TimeZone='UTC'）。
  - 監査向けインデックス群（signal_events 日付/銘柄、order_requests.status、broker_order_id 連携等）を作成。

- その他
  - 空のパッケージ初期化ファイルを追加（kabusys.data.__init__, strategy.__init__, execution.__init__, monitoring.__init__）によりパッケージ構造を整備。

### Changed
- （初回リリースのため該当なし）設計段階の整備・ドキュメントコメントを多数追加（モジュール docstring に設計方針や注意点を記載）。

### Fixed
- （実装段階での堅牢性改善）
  - .env パーサのクォート・エスケープ・インラインコメント処理を実装して edge case に耐性を持たせた。
  - HTTP 429 の場合、Retry-After ヘッダーを優先して待機時間を設定。

### Security
- JWT/ID トークンの自動リフレッシュを行うが、get_id_token() 呼び出し時の無限再帰を allow_refresh フラグで防止している。
- OS 環境変数は .env による上書きから保護（protected set）され、意図しない上書きを防止。

### Migration / 注意事項
- 初回起動時は DuckDB スキーマの初期化が必要です:
  - data.schema.init_schema(settings.duckdb_path) を呼び出してテーブルを作成してください。
  - 監査ログを別 DB に分ける場合は data.audit.init_audit_db() を使用するか、既存接続へ data.audit.init_audit_schema(conn) を呼び出してください。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須です。未設定の場合、Settings 呼び出し時に ValueError が発生します。
- デフォルトパス:
  - DuckDB: data/kabusys.duckdb（Settings.duckdb_path）
  - SQLite (monitoring 用): data/monitoring.db（Settings.sqlite_path）
- 環境切替:
  - KABUSYS_ENV の有効値は development / paper_trading / live のみ。その他は ValueError。
  - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ有効。
- .env 自動ロード:
  - 自動ロードが不要な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - .env.local は .env の上書きを意図しており、override=True によって実行時の挙動を制御します（ただし OS 環境変数は常に保護されます）。

---

今後のリリースでは、strategy / execution / monitoring の具象実装（戦略アルゴリズム、発注エンジン、モニタリング/アラート機能）やテスト・CI の追加、より細かいエラー処理やメトリクス収集の実装を予定しています。必要であれば、この CHANGELOG を基にリリースノートの英訳やバージョン計画も作成します。