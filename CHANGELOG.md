# Changelog

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-03-15
最初のリリース。日本株自動売買システムの基礎的なモジュール群とデータ基盤スキーマ、環境設定周りの実装を追加。

### 追加 (Added)
- パッケージ基礎
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。エクスポート: data, strategy, execution, monitoring。
  - 空のパッケージモジュールを配置（src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py, src/kabusys/monitoring/__init__.py）によりモジュール構成を確立。

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env ファイルまたは既存の OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を探索）して、CWD に依存しない自動読み込みを実現。
  - .env パーサー実装（クォート、エスケープ、コメント、export プレフィックス対応）。無効行のスキップ処理を実装。
  - .env と .env.local の優先度を考慮した読み込み（OS 環境変数 > .env.local > .env）。.env.local は上書き (override) が有効。
  - OS 側の既存環境変数を保護する protected キーセット機能を実装。
  - 自動ロードを無効化する環境変数を導入: KABUSYS_DISABLE_AUTO_ENV_LOAD（テスト用途を想定）。
  - Settings クラスを実装し、アプリケーションで使用する主要設定値をプロパティ経由で提供:
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション API: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN（必須）、SLACK_CHANNEL_ID（必須）
    - DB パス: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - システム設定: KABUSYS_ENV（development/paper_trading/live のバリデーション）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - ヘルパー: is_live / is_paper / is_dev のブール判定プロパティ
  - 必須環境変数が未設定の場合は ValueError を送出する _require() を実装。

- データベーススキーマ（DuckDB）基盤（src/kabusys/data/schema.py）
  - 三層データレイヤーに対応するテーブル定義を実装（冪等な CREATE TABLE IF NOT EXISTS を使用）:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラムの型・CHECK 制約・PRIMARY KEY・FOREIGN KEY を含めたスキーマを定義（データ整合性を重視）。
  - 頻出クエリを想定したインデックスを多数追加（例: 銘柄×日付、status 系の検索、orders/trades の結合用インデックス 等）。
  - init_schema(db_path) を実装:
    - DuckDB ファイルの親ディレクトリ自動作成（":memory:" はそのまま）。
    - すべての DDL とインデックスを順に実行してスキーマを初期化し、DuckDB 接続を返す。
  - get_connection(db_path) を実装（既存 DB への接続。初回は init_schema() を使用するようドキュメント化）。

- 監査ログ（Audit）スキーマ（src/kabusys/data/audit.py）
  - シグナル → 発注 → 約定 のトレーサビリティを保証する監査テーブル群を実装:
    - signal_events（戦略が生成したシグナルログ。棄却/エラー含む）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社からの約定ログ。broker_execution_id を冪等キーとして確保）
  - 発注周りの状態遷移を想定した status 列・error_message・updated_at 等を定義。
  - すべての TIMESTAMP を UTC で保存するために init_audit_schema() で SET TimeZone='UTC' を実行。
  - init_audit_schema(conn) と init_audit_db(db_path) により既存接続へ追加、または監査専用 DB の初期化をサポート。
  - 監査用インデックスを追加（signal_events の検索や order_requests.status のスキャン、broker_order_id/broker_execution_id での紐付け等）。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 注意事項 (Notes)
- DuckDB のスキーマは冪等に作成されるため、既存データベースへの再初期化は安全に実行できます（ただしスキーマ変更があった場合は移行が必要）。
- audit スキーマでは監査ログを削除しない設計（FK は ON DELETE RESTRICT）。運用時にはディスク容量と永続化ポリシーに注意してください。
- .env の自動ロードはプロジェクトルートの検出に依存します。パッケージ配布後やテスト時に自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

（将来的な変更はここに追記してください）