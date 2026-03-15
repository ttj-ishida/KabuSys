# Changelog

すべての変更は Keep a Changelog のフォーマットに従い、セマンティックバージョニングを使用します。
リリース日はリポジトリ内の現在の状態（バージョン __version__ = 0.1.0）に合わせて記載しています。

## [0.1.0] - 2026-03-15

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（各サブパッケージの __init__ を用意）

- 環境設定管理モジュール (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装
    - 読み込み優先度: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途を想定）
    - プロジェクトルート判定は __file__ を起点に `.git` または `pyproject.toml` を探索して行う（CWD に依存しない）
  - .env パーサの実装:
    - `export KEY=val` 形式をサポート
    - シングル/ダブルクォートのエスケープ処理対応（バックスラッシュエスケープを処理）
    - インラインコメントの扱い（未クォート値では '#' の直前が空白/タブのときコメントと判定）
    - 無効行（空行・コメント・パース失敗）をスキップ
  - Settings クラスを追加（環境変数から各種値を取得）
    - J-Quants / kabuステーション / Slack / DB パスなどのプロパティを提供
    - バリデーション: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の許容値チェック
    - 便利プロパティ: is_live, is_paper, is_dev
    - デフォルト DB パス: DuckDB → `data/kabusys.duckdb`, SQLite → `data/monitoring.db`

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API ベース実装
    - レート制御: 固定間隔スロットリングで 120 req/min（_RateLimiter）
    - リトライ: 指数バックオフ（最大 3 回）。対象ステータス: 408, 429, 5xx およびネットワークエラー
    - 429 の場合は `Retry-After` ヘッダを優先して待機
    - 401 応答時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰防止フラグを備える）
    - ID トークンのモジュールレベルキャッシュ（ページング間で共有）
    - ページネーション対応（pagination_key を利用）
    - JSON デコードエラー時に詳細を含むエラーを発生
  - データ取得関数:
    - fetch_daily_quotes: 株価日足 (OHLCV) をページング取得
    - fetch_financial_statements: 四半期 BS/PL をページング取得
    - fetch_market_calendar: JPX マーケットカレンダーを取得
    - 取得後のログに取得件数を出力
    - 「いつシステムがそのデータを知り得たか」をトレースするため fetched_at を UTC ISO 形式で付与（Look-ahead Bias 防止）
  - DuckDB への保存関数（冪等: ON CONFLICT DO UPDATE）
    - save_daily_quotes: raw_prices テーブルへ保存（PK: date, code）
    - save_financial_statements: raw_financials テーブルへ保存（PK: code, report_date, period_type）
    - save_market_calendar: market_calendar テーブルへ保存（PK: date）
    - PK 欠損レコードはスキップし、スキップ件数を警告ログ出力
  - ユーティリティ:
    - _to_float / _to_int: 型変換ユーティリティ（安全に None を返す仕様、"1.0" 等の処理に配慮）

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataPlatform の 3 層（Raw / Processed / Feature）および Execution レイヤーに対応した DDL を定義
  - 主なテーブル（抜粋）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義を含む（頻出のクエリパターンを想定したインデックス群）
  - init_schema(db_path) を提供:
    - 指定パスの親ディレクトリがなければ自動作成
    - ":memory:" を指定するとインメモリ DB を使用可能
    - 冪等でテーブル・インデックスを作成
  - get_connection(db_path) を提供（スキーマ初期化は行わない）

- 監査ログ・トレーサビリティモジュール (kabusys.data.audit)
  - 監査用 DDL を定義（signal_events, order_requests, executions）
  - トレーサビリティ設計（UUID ベースの階層、order_request_id は冪等キー）
  - created_at / updated_at を用いる運用前提、タイムゾーンは UTC 固定（init_audit_schema 内で SET TimeZone='UTC' を実行）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供（いずれも冪等）
  - インデックス定義を含み、監査用途での検索性能を考慮

### Changed
- 初期リリースのため該当なし

### Fixed
- 初期リリースのため該当なし

### Security
- 初期リリースのため該当なし

### Notes / 使用上の注意
- 自動で .env をプロジェクトルートから読み込む設計のため、CI やテストで明示的に環境変数を差し替える場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API へのリクエストは内部でレート制限・リトライ・トークンリフレッシュを行いますが、外部要因（大規模なバーストリクエストなど）に対しては適切に待ち時間を設けるなどの追加制御が必要な場合があります。
- DuckDB の初期化時に親ディレクトリが自動作成されるため、書き込み権限のないパスを指定すると失敗します。
- audit テーブルは削除を前提としない設計（ON DELETE RESTRICT 等）になっているため、運用ではデータ retention ポリシーを別途検討してください。

もしリリースノートに追記したい点（例: 使い方サンプル、マイグレーション手順、将来追加予定の機能など）があれば教えてください。必要に応じて追記・修正を行います。