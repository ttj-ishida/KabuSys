# Changelog

すべての注記は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠します。

現在のバージョン: 0.1.0 — 初期リリース

## [Unreleased]

- （今後の変更をここに記載）

## [0.1.0] - 2026-03-15

初回公開リリース。日本株自動売買システムの基盤モジュール群を追加しました。主な内容は次のとおりです。

### 追加（Added）

- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__version__ = "0.1.0"）。__all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを特定（CWD に依存しない動作）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装:
    - コメント行/空行スキップ。
    - export KEY=val 形式に対応。
    - シングル／ダブルクォートで囲まれた値を想定し、バックスラッシュによるエスケープを正しく処理。
    - クォートなし値の末尾コメント処理（直前がスペース/タブの場合のみ '#...' をコメントとして扱う）。
  - .env ファイル読み込み時の上書き制御:
    - override=False の場合は未設定のキーのみセット。
    - override=True の場合は protected（既存 OS 環境変数）を上書きしない挙動。
    - 読み込み失敗時には警告を出力。
  - Settings クラスを提供（プロパティ経由で設定値を取得）:
    - 必須値のチェックを行う _require()（未設定時に ValueError）。
    - J-Quants、kabu API、Slack、DBパス等のプロパティを提供。
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH をデフォルト指定。
    - 環境（KABUSYS_ENV）の検証（development / paper_trading / live のみ許容）。
    - ログレベル（LOG_LEVEL）の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - ベース URL: https://api.jquants.com/v1。
    - API レート制限を尊重する固定間隔スロットリング（120 req/min、モジュール内 RateLimiter 実装）。
    - 自動リトライ（最大 3 回）と指数バックオフ（base=2.0 秒）。再試行対象は 408 / 429 / 5xx。
    - 429 の場合は Retry-After ヘッダを優先して待機。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回だけリトライ（再帰を防止する allow_refresh フラグ）。
    - JSON デコード失敗時に詳細メッセージを含む例外を発生。
    - ページネーション対応（pagination_key を用いてページを列挙、重複防止）。
    - fetch_* 系関数を提供:
      - fetch_daily_quotes: 日足（OHLCV）を取得（code / date 範囲対応）。
      - fetch_financial_statements: 四半期財務データを取得。
      - fetch_market_calendar: JPX マーケットカレンダーを取得（holidayDivision フィルタ対応）。
    - get_id_token(refresh_token=None) を提供（refresh token から id token を取得、POST /token/auth_refresh）。
    - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有し、必要時に force_refresh）。

  - DuckDB への保存処理（冪等処理）:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 保存時に fetched_at を UTC ISO8601（Z 付）で記録して Look-ahead Bias のトレースを可能に。
    - PK 欠損行をスキップし、スキップ数をログで警告。
    - INSERT ... ON CONFLICT DO UPDATE による冪等性実現（重複時は更新）。
    - market_calendar の HolidayDivision を解釈して is_trading_day / is_half_day / is_sq_day を算出。

  - ユーティリティ:
    - _to_float / _to_int を実装。空値や変換失敗時は None。_to_int は "1.0" のような数値文字列を許容するが小数部が残る場合は None を返して意図しない丸めを防止。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋Execution 層のテーブル定義を実装。
    - Raw テーブル: raw_prices, raw_financials, raw_news, raw_executions
    - Processed テーブル: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature テーブル: features, ai_scores
    - Execution テーブル: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - カラム定義に CHECK 制約や適切な型を付与し、主キー・外部キー制約を定義。
  - 典型的なクエリパターンに基づくインデックスを作成（銘柄・日付スキャンやステータス検索など）。
  - init_schema(db_path) を提供:
    - DuckDB ファイルの親ディレクトリを自動作成（":memory:" はそのまま）。
    - 全テーブル・インデックスを冪等に作成し、接続オブジェクトを返す。
  - get_connection(db_path) を提供（既存 DB への接続。初回は init_schema を推奨）。

- 監査ログ（kabusys.data.audit）
  - シグナルから約定までの完全なトレーサビリティを実現する監査テーブル群を実装。
    - signal_events: 戦略が生成した全シグナル（棄却やエラーも含む）。
    - order_requests: 発注要求（order_request_id を冪等キーとして利用）。order_type ごとのチェック制約（limit/stop/market の必須/不要フィールド）を実装。
    - executions: 証券会社からの約定ログ（broker_execution_id をユニーク冪等キーとして扱う）。
  - すべての TIMESTAMP を UTC で保存する方針（init_audit_schema は SET TimeZone='UTC' を実行）。
  - 監査用のインデックス群を作成（シグナル検索、status でのキュー検索、broker_order_id/broker_execution_id による紐付けなど）。
  - init_audit_schema(conn) を提供（既存の DuckDB 接続に監査テーブルを追加）。
  - init_audit_db(db_path) を提供（監査ログ専用 DB の初期化）。

- ロギング / エラー報告
  - 各種操作（API 取得件数、保存件数、スキップ件数、リトライ警告など）で logger を用いた情報・警告ログを出力。

### 変更（Changed）

- 初回リリースのため該当なし。

### 修正（Fixed）

- 初回リリースのため該当なし。

### 非推奨（Deprecated）

- 初回リリースのため該当なし。

### 削除（Removed）

- 初回リリースのため該当なし。

### 追加注記（Notes / Migration）

- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings にて必須とされています。未設定時は ValueError が発生します。
- デフォルト値:
  - KABUSYS_ENV のデフォルトは "development"。許容値は "development", "paper_trading", "live" のみ。
  - LOG_LEVEL のデフォルトは "INFO"（大文字での指定を想定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env の読み込みをスキップします（ユニットテスト等で有用）。
- DB 初期化:
  - 初回は必ず data.schema.init_schema() を実行してスキーマを作成してください。監査ログを別途初期化する場合は init_audit_schema()/init_audit_db() を利用してください。
- J-Quants API 制約:
  - クライアントは 120 req/min のレート制限を守る仕様になっています。大量取得処理ではこの制約に注意してください。
- トークンリフレッシュ:
  - get_id_token はモジュール内のキャッシュを利用します。401 に対する自動リフレッシュは 1 回のみ行われます。

---

今後のリリースでは strategy / execution / monitoring 層の実装やユニットテスト、外部 API コネクションの mock、より細かなエラーハンドリングやメトリクス計測の追加を予定しています。