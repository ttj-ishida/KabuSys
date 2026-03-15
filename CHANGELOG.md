CHANGELOG
=========

すべての注目すべき変更をこのファイルで記録します。  
フォーマットは Keep a Changelog に準拠します。

Unreleased
----------

（現在なし）

0.1.0 - 2026-03-15
-----------------

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 基本パッケージ構成を追加
  - kabusys/__init__.py に __version__ と公開モジュール一覧を定義。
  - 空のモジュール初期化ファイルを配置: execution, strategy, monitoring（後続実装のためのプレースホルダ）。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動的に読み込む自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml により検出）。
  - 読み込み順序:
    - OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト等で利用）。
  - .env パーサを実装:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - 非クォート値中のコメント認識（`#` の前が空白/タブの場合にコメントとみなす）。
    - 無効行（空行、コメント、= が無い行）は無視。
  - _load_env_file にてファイル読み込み時のエラーワーニングと上書き制御（override, protected）を実装。
  - Settings クラスを提供（環境変数から取得・バリデーションを実行）:
    - 必須トークン・ID: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を発生）。
    - データベースパスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"（Path に展開）。
    - KABUSYS_ENV の許容値検証: development / paper_trading / live。
    - LOG_LEVEL の許容値検証: DEBUG, INFO, WARNING, ERROR, CRITICAL。
    - ヘルパー: is_live / is_paper / is_dev を提供。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API ベース: https://api.jquants.com/v1 を利用するクライアント実装。
  - レート制御:
    - _RateLimiter による固定間隔スロットリング（120 req/min → 最小間隔 0.5 秒）。
  - リクエスト実装:
    - 最大リトライ回数 3、指数バックオフ（base=2 秒）。
    - リトライ対象ステータス: 408, 429 および 5xx。
    - 429 時は Retry-After ヘッダを優先。
    - ネットワークエラー（URLError/OSError）にもリトライを試行。
    - JSON デコード失敗時には詳細メッセージ付きで例外化。
    - 401 Unauthorized を受けた場合、トークン自動リフレッシュを 1 回だけ行い再試行（無限再帰を防止）。
  - トークン管理:
    - モジュールレベルの ID トークンキャッシュを導入（ページネーション間でトークン共有）。
    - get_id_token() によるリフレッシュトークン→IDトークン取得をサポート。
  - データ取得関数（ページネーション対応）を提供:
    - fetch_daily_quotes: 日足（OHLCV）。
    - fetch_financial_statements: 四半期財務（BS/PL 等）。
    - fetch_market_calendar: JPX マーケットカレンダー（祝日・半日・SQ）。
  - 取得時の設計原則を明示:
    - API レート制限の順守、リトライ、トークン自動リフレッシュ、Look-ahead Bias 防止のため fetched_at を UTC で記録。
  
- DuckDB 連携保存機能（kabusys.data.jquants_client）
  - save_* 系関数を実装し、取得データを DuckDB のテーブルへ冪等的に保存:
    - save_daily_quotes → raw_prices（ON CONFLICT DO UPDATE を使用）。
    - save_financial_statements → raw_financials（ON CONFLICT DO UPDATE を使用）。
    - save_market_calendar → market_calendar（ON CONFLICT DO UPDATE を使用）。
  - PK 欠損行はスキップし、スキップ件数を警告ログ出力。
  - fetched_at は UTC タイムスタンプで保存（ISO8601 Z 表記）。
  - 型変換ユーティリティ: _to_float, _to_int（安全な変換・不正値は None）。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataSchema に基づき、以下のレイヤ別テーブルを定義・初期化する DDL を追加:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（PRIMARY KEY, CHECK 等）を付与し、データ整合性を重視。
  - 頻出クエリに備えた複数のインデックスを作成（コード×日付スキャン、ステータス検索、JOIN 支援等）。
  - init_schema(db_path) を提供:
    - db_path の親ディレクトリが無ければ自動作成。
    - ":memory:" サポート。
    - 冪等にテーブルとインデックスを作成して DuckDB 接続を返す。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- 監査ログ（トレーサビリティ）モジュール (kabusys.data.audit)
  - 戦略→シグナル→発注→約定の完全なトレーサビリティを目的とした監査テーブルを定義:
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求ログ、order_request_id を冪等キーとして利用）
    - executions（約定ログ）
  - 設計方針:
    - UUID 連鎖による追跡性、全イベントの永続化（削除しない前提）、すべての TIMESTAMP を UTC 保存。
    - order_requests の CHECK 制約により order_type に応じた価格フィールドの必須/禁止を明示。
    - 発注/約定のステータス列を持ち監査に必要な状態遷移を表現。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（監査用テーブルとインデックスを冪等に作成）。

Changed
- （初版のため、過去バージョンからの変更なし）

Fixed
- （初版のため、修正なし）

Security
- J-Quants の id_token はモジュール内でキャッシュし、必要に応じて明示的にリフレッシュする設計。自動ロードされる .env には OS 環境変数の上書きを防止する protected ロジックを導入（環境の誤上書きを軽減）。

Notes / Migration
- 初回利用時は必ず init_schema() または init_audit_db()/init_audit_schema() を呼び、DuckDB のテーブルを作成してください。
- 環境変数が必須なキーは未設定だと ValueError を送出します。.env.example 等を参考に設定してください。
- 自動 .env ロードが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Acknowledgements / TODO
- strategy, execution, monitoring 各モジュールはプレースホルダを配置済み。今後これらに戦略実装、発注実行連携、監視機能を追加予定。
- 今後のリリースで、より詳細なエラーハンドリング、テスト、ドキュメント（DataSchema.md, DataPlatform.md 参照）を追加予定。