Changelog
=========

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog のガイドラインに準拠しています。  

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 削除 (Removed)
- 破壊的変更 (Breaking Changes)

[Unreleased]
------------

- 現在未リリースの変更はありません。

[0.1.0] - 2026-03-15
-------------------

初期リリース — 日本株自動売買システム "KabuSys" の基盤機能を追加しました。

Added
- パッケージ初期化
  - パッケージメタデータと公開モジュールを追加 (kabusys.__init__: __version__ = 0.1.0, __all__ に data/strategy/execution/monitoring を含む)。

- 環境変数 / 設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みするロジックを実装。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - プロジェクトルート検出は __file__ から親ディレクトリを探索し、.git または pyproject.toml を基準に判定（CWD 非依存）。
  - .env パーサーで以下をサポート・堅牢化:
    - コメント行（#）と export プレフィックス（export KEY=val）対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォート無しの値におけるインラインコメントの扱い（直前が空白/タブの場合のみ）
  - .env 読み込み時の上書きポリシー:
    - .env は OS 環境変数を保護して未設定キーのみセット
    - .env.local は上書き（ただし OS 環境変数で保護されたキーは上書きしない）
  - Settings クラスを提供し、各種必須設定をプロパティとして取得:
    - J-Quants / kabu API / Slack トークン類（必須チェック）
    - DB パス（DuckDB, SQLite）の既定値と Path 変換
    - 環境 (development / paper_trading / live) とログレベルの検証
    - is_live / is_paper / is_dev のユーティリティプロパティ

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本設計:
    - API レート制限（120 req/min）を遵守する固定間隔スロットリング実装（_RateLimiter）
    - HTTP リクエスト共通関数 _request を提供（JSON デコード、最大リトライ、指数バックオフ）
    - リトライ対象のステータス (408, 429, 5xx) と Retry-After ヘッダ優先処理
    - 401 受信時は ID トークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止）
    - モジュールレベルの ID トークンキャッシュ (_ID_TOKEN_CACHE) と取得関数 get_id_token
    - ページネーション対応（pagination_key の検出とループ）、ページネーション間でトークンを共有
    - fetch_* 系関数で取得時刻のトレーサビリティを確保（save 側で fetched_at を付与）
  - データ取得 API:
    - fetch_daily_quotes: 日足 (OHLCV) をページネーション対応で取得
    - fetch_financial_statements: 四半期財務データをページネーション対応で取得
    - fetch_market_calendar: JPX マーケットカレンダー（祝日/半日/SQ）取得
  - DuckDB への保存関数（冪等性確保）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - INSERT … ON CONFLICT DO UPDATE による冪等保存
    - fetched_at を UTC ISO 形式で記録（Look-ahead bias 対策）
    - PK 欠損レコードはスキップし、警告ログ出力
  - 型変換ユーティリティ:
    - _to_float / _to_int: 空値や不正値に対する安全な変換ロジック（"1.0" などの文字列を許容、切り捨てに注意）

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataSchema.md に沿った 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を追加:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）と型を明示
  - 頻出クエリ向けのインデックス定義を追加（コード×日付やステータス検索など）
  - init_schema(db_path) により DB ファイルの親ディレクトリを自動作成し、全 DDL とインデックスを作成（冪等）
  - get_connection(db_path) を提供（既存 DB への接続、スキーマ初期化は行わない）

- 監査ログ（トレーサビリティ）モジュール (kabusys.data.audit)
  - 監査テーブル設計（signal_events, order_requests, executions）を追加
    - UUID ベースのトレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）
    - order_request_id を冪等キーとして扱う設計
    - 発注要求テーブルに複数の整合性 CHECK（limit/stop/market の価格条件）を追加
    - executions テーブルは broker_execution_id をユニーク（証券会社側の冪等キー）
  - すべての TIMESTAMP を UTC で扱う（init_audit_schema は SET TimeZone='UTC' を実行）
  - 監査用インデックスを多数追加（シグナル検索、status スキャン、broker id 紐付け等）
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（既存接続への追加初期化や専用 DB の初期化をサポート）

- モジュール構成
  - data / strategy / execution / monitoring のパッケージを準備（__init__.py を追加）

Changed
- 該当なし（初期リリースのため）

Fixed
- 該当なし（初期リリースのため）

Breaking Changes
- 該当なし

Notes / 今後の方針
- strategy, execution, monitoring パッケージは雛形を整備。具体的な戦略ロジック・発注ドライバ・監視機能は今後追加予定。
- J-Quants クライアントは基本機能（取得・保存・レート制御・認証）を提供。実運用では API レートやエラー挙動を実際の負荷下で検証してください。
- 監査ログは削除しない前提の設計（ON DELETE RESTRICT）。更新時は updated_at をアプリ側で更新すること。

Authors
- KabuSys 開発チーム

ライセンス
- プロジェクトに付与されるライセンスに従います（リポジトリに記載の LICENSE を参照してください）。