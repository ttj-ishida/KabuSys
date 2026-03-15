CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-15
--------------------

初回リリース。日本株自動売買システムの骨格とデータ層・設定管理・監査ログの初期実装を提供します。

Added
- パッケージ基本定義
  - pakage メタ: src/kabusys/__init__.py を追加。バージョン __version__ = "0.1.0"、公開モジュールとして data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (src/kabusys/config.py)
  - Settings クラスを実装し、環境変数から設定値を取得するプロパティ群を提供。
    - J-Quants: jquants_refresh_token (JQUANTS_REFRESH_TOKEN)
    - kabuステーション API: kabu_api_password (KABU_API_PASSWORD)、kabu_api_base_url (KABU_API_BASE_URL, デフォルト: http://localhost:18080/kabusapi)
    - Slack: slack_bot_token (SLACK_BOT_TOKEN)、slack_channel_id (SLACK_CHANNEL_ID)
    - データベース: duckdb_path (DUCKDB_PATH, デフォルト: data/kabusys.duckdb)、sqlite_path (SQLITE_PATH, デフォルト: data/monitoring.db)
    - システム: env (KABUSYS_ENV; 有効値: development, paper_trading, live)、log_level (LOG_LEVEL; DEBUG/INFO/WARNING/ERROR/CRITICAL)
    - 補助プロパティ: is_live / is_paper / is_dev
  - 必須環境変数未設定時は ValueError を送出する _require() を実装。
  - 自動 .env ロード機能を実装:
    - プロジェクトルートを .git または pyproject.toml から探索（.cwd に依存しない探索）。
    - 読み込み順: OS 環境 > .env.local (上書き) > .env（未設定のみセット）。
    - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をサポート。
    - OS 環境変数は保護（protected）され、.env による上書きを制御。
  - .env パーサーの実装:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート値をサポートし、バックスラッシュによるエスケープを処理。
    - クォートなし値のインラインコメント処理（'#' の直前に空白/タブがある場合のみコメントとして扱う）。
    - 無効行やコメント行をスキップ。
  - 不正な KABUSYS_ENV / LOG_LEVEL 値のバリデーションを追加。

- データスキーマ（DuckDB）初期化 (src/kabusys/data/schema.py)
  - データレイヤーを 3+1 層で定義（Raw / Processed / Feature / Execution）に基づく多数のテーブル DDL を用意。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY 等）を設定。
  - パフォーマンス向けのインデックスを定義（銘柄×日付スキャン、ステータス検索などのクエリパターンを想定）。
  - 公開 API:
    - init_schema(db_path): DuckDB データベースを初期化し、全テーブルとインデックスを作成。親ディレクトリがなければ自動作成。":memory:" 対応。
    - get_connection(db_path): 既存 DB へ接続（スキーマ初期化は行わない。初回は init_schema を使用）。
  - スキーマ作成は冪等（既存テーブルがあればスキップ）。

- 監査ログ（Audit）モジュール (src/kabusys/data/audit.py)
  - シグナルから約定までのトレーサビリティを保証する監査テーブル群を実装:
    - signal_events（戦略・シグナルの生成ログ、decision/理由やステータスを含む）
    - order_requests（発注要求ログ、order_request_id を冪等キーとして扱う。limit/stop のチェック制約を導入）
    - executions（約定ログ、broker_execution_id をユニークにし、注文との紐付けを保持）
  - 監査用インデックスを定義（signal 日付/銘柄、strategy/日付、status クエリ、broker_order_id での検索等）。
  - 公開 API:
    - init_audit_schema(conn): 既存の DuckDB 接続に監査テーブルを追加。すべての TIMESTAMP を UTC で保存するために SET TimeZone='UTC' を実行。
    - init_audit_db(db_path): 監査専用 DB を生成し、監査スキーマを初期化（親ディレクトリの自動作成、":memory:" 対応）。
  - 設計方針を反映: 監査ログは削除しない前提（FK は ON DELETE RESTRICT）、created_at/updated_at の取り扱いを明記。

- パッケージ構造のプレースホルダ
  - 空のパッケージ初期化ファイルを追加: src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py（将来的な機能拡張のための準備）。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- 環境変数の取り扱いに注意:
  - OS 環境変数を保護する仕組みを導入し、.env による誤った上書きを防止。
  - .env ファイルの読み込みに失敗した場合は警告を出力するが、プロセスは継続。

Notes / Implementation details
- DuckDB スキーマの多くは CHECK 制約や FOREIGN KEY、INDEX を使って整合性と検索性能を考慮して設計されています。初期化は冪等であり、既存データに対して安全に実行できます。
- 監査スキーマでは全ての TIMESTAMP を UTC に揃える設計（SET TimeZone='UTC'）を採用しています。アプリ側で updated_at の更新を確実に行う必要があります。
- .env のパースは POSIX シェルの簡易仕様を模した挙動（export、クォートとエスケープ、コメント）を持ち、実運用でよくあるケースに対応しています。

今後の予定
- strategy / execution / monitoring モジュールの具体実装（シグナル生成、ポートフォリオ最適化、ブローカ接続、監視／アラート）を追加予定。
- テストカバレッジの拡充（.env パーサーの各種境界ケース、スキーマ初期化のマイグレーション互換性等）。
- マイグレーション機構（スキーマ変更のためのバージョン管理）検討。