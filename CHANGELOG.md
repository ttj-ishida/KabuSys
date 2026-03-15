CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。

[Unreleased]
------------

(なし)

[0.1.0] - 2026-03-15
--------------------

Added
- 初回リリース。パッケージ全体の基本機能を実装。
- パッケージ定義
  - kabusys パッケージ初期化とバージョン宣言を追加（__version__ = "0.1.0"）。
  - サブパッケージ構成: data, strategy, execution, monitoring（strategy/execution/monitoring は初期は __init__ のみ）。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定自動読み込みを実装。
  - プロジェクトルートの検出ロジックを実装（.git または pyproject.toml を基準）。
  - .env パーサを実装:
    - 空行・コメント行のスキップ、"export KEY=val" 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなし値のインラインコメント取り扱い（直前が空白/タブの場合に # をコメントとして認識）。
  - .env 読み込み順序: OS環境 > .env.local > .env、および .env.local は override=True で上書き可能。
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - settings オブジェクトを提供（必須変数未設定時は ValueError を送出する _require を使用）。
  - 各種設定プロパティ:
    - J-Quants / kabu ステーション / Slack / DB パス（DuckDB/SQLite）等の取得。
    - KABUSYS_ENV 値検証（development, paper_trading, live のみ許容）。
    - LOG_LEVEL 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev ヘルパー。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティを実装（_request）。
    - レート制限（120 req/min）を厳守する固定間隔スロットリングの RateLimiter を実装。
    - リトライロジック（最大 3 回、指数バックオフ、408/429/5xx をリトライ対象）。
    - 429 の場合は Retry-After ヘッダを優先。
    - 401 受信時の自動 ID トークンリフレッシュ（1 回のみ）と再試行の実装（無限再帰防止フラグ）。
    - ページネーション対応（pagination_key を利用）。
    - JSON デコード失敗や最大リトライ超過時に明示的な例外を発生。
  - get_id_token: リフレッシュトークンから ID トークンを取得（POST）。settings.jquants_refresh_token を利用。
  - fetch_ 系関数を実装:
    - fetch_daily_quotes: 日足（OHLCV）をページネーション込みで取得。
    - fetch_financial_statements: 四半期財務データをページネーション込みで取得。
    - fetch_market_calendar: JPX マーケットカレンダー取得。
  - 検索結果の取得日時（fetched_at）を UTC で記録して Look-ahead Bias を抑制する方針を明記。
  - モジュールレベルの ID トークンキャッシュを実装（ページネーション間でトークン共有）。
  - データ保存関数（DuckDB 用、冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - INSERT ... ON CONFLICT DO UPDATE による冪等性確保（主キー重複は更新）。
    - PK 欠損行はスキップしログ出力。
  - ユーティリティ関数:
    - _to_float / _to_int: 型変換の厳密化（空値や変換失敗時は None、"1.0" 的扱い、float 小数部有りは int 変換を抑制など）。
  - 実装に関する設計原則（レート制限、リトライ、トークン管理、fetched_at によるトレーサビリティ等）をコード内コメントで明文化。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）および Execution 層を含むスキーマを実装。
  - 多数のテーブルDDLを定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各テーブルに対して型チェック・CHECK 制約・PRIMARY KEY を設定し整合性を担保。
  - 頻出クエリ向けのインデックス定義を用意（コード×日付、status 検索、JOIN 最適化等）。
  - init_schema(db_path) によるデータベース初期化関数を提供（親ディレクトリ自動作成、冪等にテーブル作成）。
  - get_connection(db_path) による既存 DB への接続取得関数を提供（初期化は行わない）。

- 監査ログ（トレーサビリティ）モジュール (src/kabusys/data/audit.py)
  - 戦略→シグナル→発注→約定のトレースを可能にする監査テーブルを定義。
  - テーブル: signal_events, order_requests, executions を実装。各テーブルは UUID をキーとして監査連鎖を確立。
  - order_requests は冪等キー (order_request_id) を持ち、制約チェック（limit/stop/market の値整合）を組み込み。
  - executions は broker_execution_id を一意キーとして扱い冪等性を担保。
  - すべての TIMESTAMP を UTC で保存する方針を適用（init_audit_schema は "SET TimeZone='UTC'" を実行）。
  - init_audit_schema(conn) と init_audit_db(db_path) の公開 API を提供。
  - 監査索引群を定義して検索/結合性能を向上。

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）

Deprecated
- （なし）

Removed
- （なし）

Security
- （なし）

Notes / 開発者向けメモ
- settings._require は必須環境変数がない場合に ValueError を投げます。CI/デプロイでは .env や環境変数の設定を忘れないでください。
- .env 自動読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後に挙動が想定と異なる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い手動で設定することを推奨します。
- J-Quants クライアントはネットワークエラーや HTTP エラーを扱うため、呼び出し元での例外ハンドリングが必要です。ログにリトライ情報が出力されます。
- strategy / execution / monitoring サブパッケージは初期スタブのみのため、実際の戦略実装や発注ロジックは別途実装が必要です。