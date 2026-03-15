# Changelog

すべての重要な変更をここに記録します。フォーマットは Keep a Changelog に準拠します。

現在のバージョン: 0.1.0 (初回リリース)
リリース日: 2026-03-15

## [Unreleased]
- 

## [0.1.0] - 2026-03-15

Added
- パッケージの初回公開（kabusys 0.1.0）。
- 基本パッケージ構成:
  - src/kabusys/__init__.py に __version__ = "0.1.0" として公開エントリ。
  - 空のパッケージモジュール: execution, strategy, monitoring を配置（将来の拡張用）。
- 環境設定管理モジュール (src/kabusys/config.py):
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
  - 自動ロードはプロジェクトルート検出（.git または pyproject.toml）に基づいて行うため、CWD に依存しない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - .env のパースを強化:
    - "export KEY=val" 形式をサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォート無し値のインラインコメント処理（# の前がスペース／タブの場合のみコメントと判断）。
    - 無効行やキー無し行のスキップ。
  - .env の読み込み順序と上書き制御:
    - OS環境 > .env.local (override=True) > .env (override=False)。
    - OS 環境変数は protected として上書き禁止。
  - Settings クラスで主要設定をプロパティとして提供:
    - 必須値のチェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - データベースパス既定値（DUCKDB_PATH, SQLITE_PATH）。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の値検証。is_live / is_paper / is_dev 判定ヘルパー。
- データ層: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API クライアントで以下を実装:
    - レート制御 (120 req/min) を行う固定間隔スロットリング (_RateLimiter)。
    - リトライ機構（指数バックオフ, 最大 3 回）。対象ステータス 408/429 および 5xx、ネットワークエラーにも対応。
    - 401 受信時はリフレッシュトークンを自動で更新して 1 回だけリトライ（無限再帰防止）。
    - ID トークンのモジュールレベルキャッシュを導入（ページネーション間で共有可能）。
    - JSON デコード失敗時の明確なエラー報告。
  - API データ取得関数（ページネーション対応）:
    - fetch_daily_quotes (日足 OHLCV)
    - fetch_financial_statements (四半期財務)
    - fetch_market_calendar (JPX マーケットカレンダー)
    - 取得レコードに対してログ出力（取得件数）。
    - pagination_key を使った重複防止。
  - DuckDB への保存関数（冪等設計）:
    - save_daily_quotes → raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE。
    - save_financial_statements → raw_financials テーブルへ冪等保存。
    - save_market_calendar → market_calendar テーブルへ冪等保存。HolidayDivision から is_trading_day / is_half_day / is_sq_day を判定。
    - 保存時に fetched_at (UTC ISO8601) を付与し、Look-ahead Bias のトレーサビリティを確保。
  - 型変換ユーティリティ:
    - _to_float: None/空文字や変換失敗時に None を返す。
    - _to_int: 文字列→int の頑健な変換。小数部がある値（"1.9" 等）は None を返す（意図しない切り捨て防止）。
- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）+ Execution 層の DDL を実装:
    - Raw テーブル: raw_prices, raw_financials, raw_news, raw_executions
    - Processed テーブル: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature テーブル: features, ai_scores
    - Execution テーブル: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェック制約（CHECK, PRIMARY KEY, FOREIGN KEY 等）を付与。
  - 頻出クエリ向けのインデックスを作成（銘柄×日付、ステータス検索など）。
  - init_schema(db_path) でディレクトリ自動作成、全テーブルとインデックスを冪等的に作成して接続を返す。
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）。
- 監査ログ（Audit）モジュール (src/kabusys/data/audit.py)
  - シグナル→発注→約定のトレーサビリティを担保する監査テーブルを実装:
    - signal_events: 戦略が生成したシグナルを記録（戦略ID、decision、reason、created_at 等）。
    - order_requests: 発注要求（order_request_id を冪等キーとして扱う）。order_type による価格必須チェックなどの整合性制約を導入。
    - executions: 証券会社からの約定ログ（broker_execution_id を冪等キーとして保存）。
  - 監査テーブルは削除しない方針（FK は ON DELETE RESTRICT）、全 TIMESTAMP を UTC で保存するため init_audit_schema は SET TimeZone='UTC' を実行。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供し、既存の DuckDB 接続へ監査スキーマを追加可能。
  - 監査向けのインデックスを追加（signal_events の日付/戦略検索、order_requests.status スキャン等）。
- パッケージ公開エントリ (src/kabusys/data/__init__.py, src/kabusys/monitoring/__init__.py, ...)

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の取り扱いで OS 環境を保護するため .env の上書き制御機構を導入。

Notes / Implementation details
- J-Quants API のレート制限（120 req/min）に合わせた固定間隔スロットリングを採用。バーストを想定する場合や高精度のスループットが必要な場合は将来的にトークンバケット等の採用を検討してください。
- DuckDB への挿入は ON CONFLICT DO UPDATE による冪等化を行っています。既存データの上書きポリシーはテーブル毎に異なるため、必要に応じて整合性ポリシーを調整してください。
- audit.order_requests の broker_order_id に対する UNIQUE インデックスは NULL を複数許容する DuckDB の挙動に留意してください。

既知の制約・今後の改善案
- 現在 strategy / execution / monitoring モジュールは雛形のみ。発注ロジック・リスク管理・監視機能は今後追加予定。
- J-Quants クライアントは urllib を用いており、より高機能な HTTP クライアント（requests / httpx）への差し替え検討余地あり（タイムアウト・セッション管理・接続プーリング等の改善）。
- テスト用のモックやインテグレーションテストセットアップ（DuckDB のファイル分離、API モックなど）は今後整備予定。

--- 

（改定履歴はここに追記してください）