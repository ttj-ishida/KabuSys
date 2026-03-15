# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このプロジェクトの初期リリースである v0.1.0 の主な実装内容と設計上の注意点をまとめています。

全般的なルール:
- 版番号: semantic versioning を想定しています（現行バージョンは 0.1.0）。
- 日付はリリース日です。

## [Unreleased]

- （今後の変更をここに記載します）

## [0.1.0] - 2026-03-15

Added
- パッケージ初期構成を追加
  - src/kabusys/__init__.py にパッケージ名・バージョン（__version__ = "0.1.0"）および公開サブパッケージを定義（data, strategy, execution, monitoring）。
- 環境変数・設定管理モジュールを実装（src/kabusys/config.py）
  - .env/.env.local ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
  - .env の行解析を堅牢化（コメント、export プレフィックス、クォートとエスケープ処理、インラインコメントの扱いなど）。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - settings オブジェクトを公開し、主要設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV の検証（development, paper_trading, live のみ許可）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の利便性プロパティ
- J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）
  - データ取得機能:
    - fetch_daily_quotes: 日足（OHLCV）のページネーション対応取得
    - fetch_financial_statements: 四半期財務諸表のページネーション対応取得
    - fetch_market_calendar: JPX マーケットカレンダー取得
  - 認証:
    - get_id_token: リフレッシュトークンから id token を取得する POST 実装
    - モジュールレベルで id token をキャッシュし、ページネーション間で共有
    - 401 受信時に自動的にトークンをリフレッシュして 1 回だけ再試行
  - レート制限とリトライ:
    - デフォルトで 120 req/min（固定間隔スロットリング）を遵守する RateLimiter を実装
    - ネットワーク / サーバーエラーに対するリトライ（指数バックオフ、最大 3 回）
    - 429 の場合は Retry-After を優先
    - タイムアウトやネットワークエラーのログと再試行
  - データ保存（DuckDB への冪等な保存）:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装
    - INSERT ... ON CONFLICT DO UPDATE を用いて冪等性を担保
    - fetched_at を UTC タイムスタンプで記録（Look-ahead bias を防ぐために取得時刻を保存）
  - JSON パース、HTTP レスポンスのエラーハンドリングを堅牢化
  - 値変換ユーティリティ:
    - _to_float / _to_int: 不正値や空値を適切に None にする安全な変換
    - _to_int は "1.0" のような文字列を float 経由で変換し、小数部が非ゼロの場合は None を返すなどの細かい扱い
- DuckDB スキーマ定義と初期化モジュールを実装（src/kabusys/data/schema.py）
  - 3層データモデル（Raw / Processed / Feature）と Execution 層を含むテーブル群を DDL で定義
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な CHECK 制約、PRIMARY KEY、外部キーを付与
  - 頻出クエリを想定したインデックス群を作成（コード・日付・ステータス検索など）
  - init_schema(db_path) によりデータベースファイルの親ディレクトリ作成とテーブル初期化（冪等）を行う
  - get_connection(db_path) により既存 DB への接続を返す（スキーマ初期化はしない）
- 監査ログ（トレーサビリティ）モジュールを実装（src/kabusys/data/audit.py）
  - シグナル -> 発注 -> 約定 の完全トレースを目的とした監査テーブルを実装
  - 主なテーブル:
    - signal_events（戦略が生成したシグナルのログ）
    - order_requests（発注要求、order_request_id を冪等キーとして扱う）
    - executions（証券会社からの約定ログ、broker_execution_id を一意キーとして扱う）
  - 監査用インデックス群を作成（戦略別検索、status 列のスキャン、broker_order_id による紐付けなど）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供
  - すべての TIMESTAMP を UTC で保存するために conn.execute("SET TimeZone='UTC'") を実行
  - ステータス遷移や制約（limit/stop 注文に対する price の必須性など）をチェック制約で表現
- 空のモジュール・パッケージの雛形を追加
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py を追加（将来の拡張ポイント）

Changed
- （初期リリースのため変更履歴なし）

Fixed
- （初期リリースのため修正履歴なし）

Security
- 認証トークンの取り扱いに注意:
  - J-Quants のリフレッシュトークンは settings.jquants_refresh_token 経由で取得されるため、.env や環境変数の取り扱いに十分注意してください。
  - .env 自動ロードはデフォルト ON。CI/テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。

Notes / 注意点
- デフォルトのデータベースパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  必要に応じて環境変数で変更してください。
- J-Quants API のレート制限は 120 req/min を想定しているため、外部からの同時アクセスや追加クライアントの導入時は注意が必要です。
- save_* 系関数は DuckDB の接続（duckdb.DuckDBPyConnection）を受け取り、呼び出し側でトランザクション管理（conn context manager 等）を行えます。
- audit テーブルは原則として削除されない前提（ON DELETE RESTRICT）で設計されています。監査ログの取り扱い方針に沿って運用してください。

Breaking Changes
- なし（初回リリース）

References
- 内部ドキュメント（設計方針）への注記は各モジュールの docstring に記載済み（例: DataPlatform.md, DataSchema.md に対応した実装意図）。

--- 

今後のリリースでは、strategy / execution / monitoring 層の具体的な実装（戦略ロジック、発注ラッパー、Slack 通知、メトリクス収集など）やテストカバレッジの向上、エラー監視強化を予定しています。必要であればこの CHANGELOG を英文化した版や、リリースごとの差分をさらに詳細に分割して作成します。