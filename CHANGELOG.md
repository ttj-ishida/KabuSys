# Changelog

すべての重要な変更はこのファイルに記録します。
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

## [Unreleased]


## [0.1.0] - 2026-03-15
初回リリース。

### 追加
- パッケージの骨組みを追加（kabusys）。
  - パッケージバージョン: 0.1.0
  - __all__ に data, strategy, execution, monitoring を公開

- 環境変数・設定管理モジュールを追加（kabusys.config）。
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）を起点に自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env 読み取り時の堅牢なパーサを実装：
    - 空行・コメント（#）をスキップ
    - export プレフィックス対応
    - シングル/ダブルクォート内のエスケープ処理対応
    - インラインコメントの扱い（クォートの有無に応じた扱い）
  - 環境変数の上書き制御（.env と .env.local の優先度）と OS 環境変数保護機能を実装
  - Settings クラスを公開（settings インスタンス経由で利用）
    - J-Quants / kabu API / Slack / DB パスなどのプロパティを提供
    - デフォルト値: KABUSYS_ENV=development, LOG_LEVEL=INFO, KABU_API_BASE_URL=http://localhost:18080/kabusapi
    - duckdb と sqlite のデフォルトパスを提供（expanduser 対応）
    - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値以外は ValueError）

- J-Quants API クライアントを追加（kabusys.data.jquants_client）。
  - 取得対象: 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー
  - 設計上の特徴:
    - API レート制限（120 req/min）を固定間隔スロットリングで遵守（内部 RateLimiter）
    - リトライロジック（最大 3 回、指数バックオフ、対象: 408/429/5xx、429 の場合は Retry-After を優先）
    - 401 (Unauthorized) 受信時はリフレッシュトークンで自動的に ID トークンを更新して 1 回リトライ（無限再帰回避）
    - ID トークンのモジュールレベルキャッシュを実装（ページネーション間で共有）
    - ページネーション対応（pagination_key を用いた繰り返し取得）
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead Bias 防止を支援
  - 公開 API:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
    - save_* 系関数で DuckDB への保存を提供（save_daily_quotes, save_financial_statements, save_market_calendar）
      - 保存は冪等性を保つ（INSERT ... ON CONFLICT DO UPDATE）
      - PK 欠損行はスキップしログ出力
      - 型変換ユーティリティ (_to_float, _to_int) を用意

- DuckDB スキーマ定義・初期化モジュールを追加（kabusys.data.schema）。
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を実装
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 厳格な制約（CHECK・PRIMARY KEY・FOREIGN KEY）を付与
  - 頻出クエリ向けのインデックスを作成
  - init_schema(db_path) によりディレクトリ作成を行い DB を初期化（:memory: 対応）
  - get_connection(db_path) で既存 DB に接続（スキーマ初期化は行わない）

- 監査ログ（トレーサビリティ）モジュールを追加（kabusys.data.audit）。
  - シグナル → 発注 → 約定を UUID 連鎖でトレース可能にする監査テーブル群を定義
  - 主なテーブル:
    - signal_events（戦略が生成したシグナルを全記録、棄却やエラーも保持）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ、order_type に応じた制約を付与）
    - executions（証券会社からの約定を記録、broker_execution_id を冪等キーとして扱う）
  - すべての TIMESTAMP は UTC に固定（init_audit_schema は SET TimeZone='UTC' を実行）
  - インデックス群を定義し検索を高速化
  - init_audit_schema(conn) と init_audit_db(db_path) を公開（既存接続への追加初期化や専用 DB の初期化をサポート）

- 空のパッケージモジュールを作成（kabusys.data.__init__, kabusys.execution, kabusys.strategy, kabusys.monitoring の __init__）。将来的な拡張点を確保。

### 変更
- —（初回リリースのため該当なし）

### 修正
- —（初回リリースのため該当なし）

### 既知の注意点 / マイグレーション
- init_schema は指定された DuckDB ファイルの親ディレクトリを自動作成しますが、既存 DB へスキーマ追加が必要な場合は get_connection の後に適切な DDL を実行してください。
- .env 自動ロードはプロジェクトルート探索に依存するため、配布後や CWD が異なる環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にして手動で設定を読み込むことを検討してください。
- J-Quants API のトークン自動リフレッシュは 401 発生時に 1 回のみ行います。失敗時は例外となります。

### セキュリティ
- —（初回リリースのため該当なし）

---

今後のバージョンでは、strategy / execution / monitoring 層の実装、Slack や kabu ステーションとの連携ロジック、より詳細なテストやドキュメントの追加を予定しています。