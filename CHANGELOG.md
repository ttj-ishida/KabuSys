# Changelog

すべての変更は Keep a Changelog のフォーマットに従います。  
このプロジェクトはセマンティックバージョニングを使用します。 — https://semver.org/

## [Unreleased]

## [0.1.0] - 2026-03-15
初期リリース

### Added
- パッケージ基盤を追加
  - kabusys パッケージ本体（src/kabusys/__init__.py）
    - __version__ = "0.1.0"
    - __all__ に "data", "strategy", "execution", "monitoring" を公開

- 環境設定モジュールを追加（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供
  - 自動 .env ロード機能（プロジェクトルートを .git または pyproject.toml で探索）
    - 読み込み順: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数をサポート
    - OS側で設定されている環境変数は protected として上書き不可
  - 高度な .env パーサ実装
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
    - コメント処理（クォート無しでは '#' の直前に空白がある場合のみコメントとみなす等）
    - 無効行をスキップする堅牢な実装
  - Settings が提供するプロパティ（取得必須のものは未設定時に ValueError）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABU_API_BASE_URL（デフォルト: "http://localhost:18080/kabusapi"）
    - DUCKDB_PATH（デフォルト: "data/kabusys.duckdb"）、SQLITE_PATH（デフォルト: "data/monitoring.db"）
    - KABUSYS_ENV（"development"/"paper_trading"/"live" の検証）
    - LOG_LEVEL（"DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL" の検証）
    - is_live / is_paper / is_dev の便宜プロパティ

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）
  - 主な機能
    - ID トークン取得（get_id_token）とキャッシュ
      - get_id_token: POST /token/auth_refresh を呼び出し idToken を取得
      - モジュールレベルでトークンをキャッシュし、ページネーション間で共有
    - 汎用リクエスト関数（_request）
      - レート制限（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）
      - リトライ戦略: 指数バックオフ（最大 3 回）、対象ステータス: 408, 429, 5xx、ネットワークエラー時もリトライ
      - 401 を受け取った場合はトークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止）
      - JSON デコード失敗時にわかりやすい例外を投げる
    - データ取得関数（ページネーション対応）
      - fetch_daily_quotes: 株価日足（OHLCV）
      - fetch_financial_statements: 四半期財務データ（BS/PL 等）
      - fetch_market_calendar: JPX マーケットカレンダー（祝日・半日・SQ）
    - DuckDB への保存関数（冪等）
      - save_daily_quotes: raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE
      - save_financial_statements: raw_financials テーブルへ同様の冪等保存
      - save_market_calendar: market_calendar テーブルへ保存（HolidayDivision を取引日/半日/SQ の真偽値に変換）
    - 取得メタ情報（fetched_at）を UTC で記録して Look-ahead Bias の追跡が可能
    - データ変換ユーティリティ
      - _to_float: None/空値/変換失敗時は None
      - _to_int: "1.0" のような小数表現を許容し、非整数となる場合は None を返す（意図しない切り捨て回避）
  - ロギング: 取得件数・保存件数・リトライや 401 リフレッシュなど重要イベントをログ出力

- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）＋Execution レイヤのテーブル定義を実装
  - 定義済みテーブル（主なもの）
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（CHECK、PRIMARY KEY、FOREIGN KEY）を多用したスキーマ設計
  - 頻出クエリ向けのインデックス定義を追加
  - init_schema(db_path) による初期化関数
    - db_path の親ディレクトリを自動作成
    - ":memory:" 対応
    - 冪等でテーブル作成・インデックス作成を行う
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）

- 監査（Audit）モジュールを追加（src/kabusys/data/audit.py）
  - 監査ログテーブル（signal_events, order_requests, executions）を導入
    - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）
    - order_request_id を冪等キーとして設計（再送で二重発注を防止）
    - すべての TIMESTAMP を UTC で保存する (init_audit_schema で SET TimeZone='UTC')
    - エラー／棄却されたイベントも必ず永続化し、削除しない前提（ON DELETE RESTRICT）
    - order_requests に対する複数の CHECK（limit/stop/market の価格必須/不要ルール）
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化関数
  - 監査用インデックス群を提供（signal_id, business_date, broker_order_id など）

- パッケージ構造（空の __init__ を含む）
  - src/kabusys/data/__init__.py
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/monitoring/__init__.py

### Notes / Migration
- 環境変数の必須キー:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env ロードをテスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 初期化は data.schema.init_schema(db_path) を使用してください。既存 DB へ接続するだけなら data.schema.get_connection(db_path) を使用します。
- J-Quants API を使う際は rate limit（120 req/min）とリトライ挙動に注意してください。クライアントは内部でこれらを尊重しますが、外部からの大量同時呼び出しは避けてください。
- 監査ログは削除しない前提の設計です。履歴を保持する運用を想定しています。

### Breaking Changes
- 初回リリースのため該当なし

### Fixed / Changed / Removed / Deprecated / Security
- 該当なし（初回リリース）

---

必要であれば、各関数 / クラスの短い使用例や環境変数のサンプル（.env.example 相当）を別途作成します。どの情報を優先して出力するか指定してください。