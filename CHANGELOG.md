CHANGELOG
=========

すべての重要な変更履歴をこのファイルに記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。
リリースバージョンはソース内の kabusys.__version__ に同期しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-15
--------------------

初回公開リリース。主要な機能、データモデル、設定管理、および外部 API クライアントを実装しました。

Added
- パッケージ初期化
  - パッケージルート: src/kabusys/__init__.py にて __version__=0.1.0、公開サブパッケージを定義。
- 環境変数・設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（コメント・export プレフィックス・シングル/ダブルクォート・エスケープ対応）。
  - OS 環境変数を保護する protected オプション（.env.local は .env の上書きに使用）。
  - Settings クラスを導入し、主要設定をプロパティで取得：
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev ヘルパー
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - OHLCV（日足）、四半期財務データ、JPX マーケットカレンダー取得用 API クライアントを実装。
  - 設計上の特徴：
    - レート制限保護: 固定間隔スロットリングを用いた RateLimiter（120 req/min を想定）。
    - リトライロジック: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx にリトライ。
    - 401 応答時には自動でトークンをリフレッシュして 1 回リトライ（無限再帰回避済み）。
    - id_token のモジュールレベルキャッシュを保持（ページネーション間で共有）。
    - Look-ahead Bias 防止のため、取得データに fetched_at を UTC で付与する方針。
    - DuckDB への保存は冪等化（ON CONFLICT DO UPDATE）を採用。
  - 提供関数:
    - get_id_token(refresh_token=None)
    - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
    - save_daily_quotes(conn, records)
    - save_financial_statements(conn, records)
    - save_market_calendar(conn, records)
  - JSON デコードエラー、ネットワークエラー、HTTP エラーに関する明確な例外処理とログ出力を実装。
  - 型変換ユーティリティ: _to_float / _to_int（不正値や小数部切り捨てに対する安全処理）。
- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋Execution 層のテーブル定義を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム制約（NOT NULL, CHECK, PRIMARY KEY）を多数定義し、スキーマレベルでのデータ整合性を確保。
  - 検索パフォーマンスを考慮したインデックスを複数定義（銘柄×日付、ステータス検索等）。
  - 公開 API:
    - init_schema(db_path) — DB ファイルを作成（親ディレクトリの自動作成含む）し、全テーブルとインデックスを作成（冪等）。
    - get_connection(db_path) — 既存 DB への接続（スキーマ初期化は行わない）。
- 監査ログ（監査トレーサビリティ）モジュール (src/kabusys/data/audit.py)
  - シグナルから約定までを UUID 連鎖で完全トレースする監査テーブル群を実装。
  - 主なテーブル:
    - signal_events（戦略が生成したシグナルを記録、棄却等も含む）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社から得た約定ログ、broker_execution_id をユニークキーとして扱う）
  - ステータス列と遷移を設計（pending/sent/filled/... 等）。
  - すべての TIMESTAMP は UTC 保存を前提にし、init_audit_schema() 実行時に SET TimeZone='UTC' を呼ぶ。
  - インデックスを作成し検索を高速化。
  - 公開 API:
    - init_audit_schema(conn) — 既存接続に監査テーブルを追加（冪等）。
    - init_audit_db(db_path) — 監査専用 DB を初期化して返す。
- 空モジュール / パッケージプレースホルダ
  - src/kabusys/{execution,strategy,monitoring,data/__init__.py} を追加（将来拡張用プレースホルダ）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated / Removed / Security
- 該当なし。

Migration / 使用上の注意
- 初回セットアップ:
  - DuckDB スキーマを作成するには: from kabusys.data import schema; schema.init_schema(settings.duckdb_path)
  - 監査ログを別 DB で管理する場合は schema.init_audit_db(path) を使用、既存接続へ追加する場合は init_audit_schema(conn) を呼ぶ。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - .env.example を参考に .env を用意してください。
- 自動 .env 読み込みはプロジェクトルートが見つからない場合スキップされます（パッケージ配布後の挙動を考慮）。
- ネットワークや API レート制限に起因するリトライが組み込まれていますが、運用環境ではログを監視してください。
- get_id_token() は内部で _request を呼び出しますが、トークンリフレッシュ処理時の無限再帰を防ぐため allow_refresh を適切に制御しています（通常の運用では意識不要）。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装（実注文連携、ポジション管理、監視アラート等）。
- テストカバレッジと CI の整備。
- データ取り込みバッチ・スケジューラ統合の追加。

--- 
この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時はリリース方針や追加情報（既知の制限、互換性注意など）を追記してください。