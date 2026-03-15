# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のパッケージバージョン: 0.1.0

## [Unreleased]
（未発表の変更はここに記載）

## [0.1.0] - 2026-03-15
初回公開

### Added
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポートモジュール: data, strategy, execution, monitoring

- 環境変数・設定管理モジュール（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を自動読み込み
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出に .git または pyproject.toml を使用（__file__ を基点に親ディレクトリを探索）
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - .env 行パーサーの実装
    - コメント行（#）の無視
    - export KEY=val 形式をサポート
    - シングル/ダブルクォートをサポートし、バックスラッシュによるエスケープに対応
    - クォートなし値に対するインラインコメント処理（'#' の直前が空白/タブの場合にコメントと判定）
  - .env ファイル読み込みの挙動
    - override フラグと protected キーセットにより既存 OS 環境変数の保護が可能
    - ファイル読み込み失敗時は警告を出力（例外は投げない）
  - Settings クラスを提供（プロパティ経由でアプリ設定を取得）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須設定は未設定時に ValueError を送出
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを提供（Path を返す）
    - KABUSYS_ENV の許容値: development, paper_trading, live（不正値は ValueError）
    - LOG_LEVEL の許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL（不正値は ValueError）
    - ユーティリティプロパティ: is_live / is_paper / is_dev

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 機能
    - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
    - ページネーション対応（pagination_key を用いた継続取得）
    - レスポンスの JSON デコードとエラーハンドリング
  - レート制御
    - 固定間隔スロットリング: 120 req/min（最小間隔を計算して待機する _RateLimiter 実装）
  - リトライ戦略
    - 最大 3 回のリトライ、指数バックオフ（base 2.0 秒）
    - ステータスコード 408, 429, および 5xx をリトライ対象
    - 429 の場合は Retry-After ヘッダを優先
    - ネットワークエラー（URLError, OSError）もリトライ
  - 認証トークン管理
    - get_id_token(refresh_token) でリフレッシュトークンから idToken を取得（POST /token/auth_refresh）
    - モジュールレベルのトークンキャッシュを保持し、ページネーション間で共有
    - 401 受信時は id_token を自動リフレッシュして 1 回だけリトライ（無限再帰を防止）
  - データ取得関数
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供
    - ログ出力で取得件数を報告
  - 永続化関数（DuckDB 連携）
    - save_daily_quotes, save_financial_statements, save_market_calendar を提供
    - 全て冪等（INSERT ... ON CONFLICT DO UPDATE）で既存レコードを更新
    - fetched_at を UTC ISO8601（秒精度、Z）で記録し Look-ahead bias を防止
    - PK 欠損行はスキップし、スキップ件数を警告ログ出力
  - 型変換ユーティリティ
    - _to_float / _to_int を実装。変換失敗は None を返す
    - _to_int は "1.0" のような float 文字列を int に変換するが、小数部が 0 でない場合は None を返す（意図しない切り捨て防止）

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - 3 層（Raw / Processed / Feature）および Execution 層のテーブル定義を実装
  - 代表的なテーブル
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型、CHECK 制約、PRIMARY KEY を付与
  - 頻出クエリのためのインデックス定義を追加（コード×日付、ステータス検索、FK 参照用など）
  - init_schema(db_path) を提供
    - db_path の親ディレクトリを自動作成
    - 全 DDL を実行してテーブルとインデックスを作成（冪等）
    - ":memory:" を使ってインメモリ DB を初期化可能
  - get_connection(db_path) を提供（既存 DB への接続。初期化は行わない）

- 監査ログ（トレーサビリティ）モジュール（kabusys.data.audit）
  - 監査用テーブルの定義と初期化を実装（DataPlatform.md に準拠）
  - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）をサポート
  - 主なテーブル
    - signal_events: 戦略が生成した全シグナルを保存（棄却/エラー含む）。decision と reason を記録
    - order_requests: 発注要求（order_request_id を冪等キーとして機能）。limit/stop のチェック制約を実装
    - executions: 証券会社からの約定情報（broker_execution_id を冪等キー）
  - init_audit_schema(conn) を提供
    - conn に対して SET TimeZone='UTC' を実行し、全 TIMESTAMP を UTC で保存
    - 監査用インデックスを作成（status・signal_id・broker_order_id 等での高速検索）
  - init_audit_db(db_path) を提供（監査専用 DB の初期化）

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- （初版のため該当なし）

---

注記:
- 上記はソースコードから推測した初版の機能と設計方針に基づく CHANGELOG です。実際の運用での細かな仕様や外部依存（例: J-Quants の API レスポンス形式・エラーハンドリングの挙動）については運用時に確認してください。