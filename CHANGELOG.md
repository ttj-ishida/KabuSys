# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システム「kabusys」のコア機能を実装しました。以下はコードベースから推測してまとめた主要な追加点と設計上の特徴です。

### Added
- パッケージ骨格
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を定義。
  - サブパッケージ表現: data, strategy, execution, monitoring を __all__ に公開。

- 環境設定管理 (src/kabusys/config.py)
  - .env / 環境変数の自動ロード機能（プロジェクトルートは .git または pyproject.toml を探索して判定）。
  - .env のパース実装（export プレフィックス対応、シングル/ダブルクォート、インラインコメントの扱い、エスケープ処理）。
  - .env と .env.local の読み込み優先度（OS環境変数 > .env.local > .env）、既存環境変数保護機構（protected set）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラス: J-Quants / kabu API / Slack / DB パス等のプロパティ取得、必須キー未設定時に ValueError を送出する _require()、KABUSYS_ENV と LOG_LEVEL の検証、is_live/is_paper/is_dev の便利プロパティ。
  - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH など。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 基本機能: 日足・財務（四半期）・マーケットカレンダー取得の fetch_* 関数を実装（ページネーション対応）。
  - 認証: refresh_token から id_token を取得する get_id_token() を実装。id_token のモジュールレベルキャッシュを保持。
  - レート制御: 固定間隔スロットリングによるレートリミッタ実装（120 req/min を遵守）。
  - リトライ/バックオフ: 指数バックオフによる最大 3 回リトライ、HTTP 408/429/5xx を再試行対象に含める。429 の場合は Retry-After を優先。
  - 401 応答時の自動トークンリフレッシュ（allow_refresh フラグで無限再帰を防止、1 回だけリフレッシュして再試行）。
  - DuckDB への保存関数 save_daily_quotes/save_financial_statements/save_market_calendar：ON CONFLICT DO UPDATE による冪等性を担保。fetched_at を UTC で記録。
  - 型変換ユーティリティ: _to_float / _to_int（堅牢な変換と不正値ハンドリング）。
  - ロギングによる取得件数やスキップ件数の報告。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - 3 層構造（Raw / Processed / Feature）と Execution 層を含む多くのテーブル定義を実装:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PK, CHECK 等）を付与。
  - 頻出クエリに備えたインデックス定義群。
  - init_schema(db_path) によるディレクトリ作成、DDL 実行、冪等な初期化。
  - get_connection(db_path) の提供（スキーマ初期化を行わない接続取得）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL の実装（run_daily_etl）: 市場カレンダー取得 → 株価差分取得（バックフィル） → 財務差分取得 → 品質チェック。
  - 差分更新ロジック: DB の最終取得日を基準に date_from を自動計算。デフォルトのバックフィル日数は 3 日。
  - カレンダーは先読み（デフォルト 90 日）して当日の営業日調整に利用。
  - ページネーション対応の fetch 関数を用いて取得、save_* による冪等保存。
  - ETLResult dataclass により処理結果・品質問題・エラーメッセージを集約。
  - 各ステップは独立して例外を捕捉し、1 ステップ失敗でも残りを続行（Fail-Fast ではない）。
  - ヘルパー: _table_exists, _get_max_date, _adjust_to_trading_day, get_last_* 関数。

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - シグナル → 発注要求（冪等キー付き）→ 約定 までを追跡するための監査テーブル定義:
    - signal_events, order_requests, executions
  - order_request_id を冪等キーとして二重発注を防止する設計。
  - 全ての TIMESTAMP を UTC で保存するため init_audit_schema は TimeZone='UTC' をセット。
  - ステータス遷移や CHECK 制約を含む堅牢なデータ整合性設計。
  - init_audit_db(db_path) による監査専用 DB 初期化の提供。
  - 監査系の検索用インデックスを作成。

- データ品質チェック (src/kabusys/data/quality.py)
  - QualityIssue dataclass により品質問題を構造化。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欄欠損を検出（必須カラムの NULL）。
    - check_spike: 前日比スパイク（デフォルト閾値 50%）を LAG ウィンドウで検出。
  - 各チェックは SQL（パラメータバインド）で実行し、サンプル行（最大 10 件）と件数を返す設計。
  - チェックは Fail-Fast ではなく全件収集し、呼び出し側で重大度に応じた判断を行えるようにしている。

### Design / Behavior highlights
- 冪等性（Idempotency）
  - DuckDB への書き込みは ON CONFLICT DO UPDATE を用いて重複を回避。
  - order_request_id / broker_execution_id など冪等キーを監査系で採用。

- トレーサビリティ
  - fetched_at や created_at を UTC で記録し、いつデータを知り得たかを追跡可能にしている。

- レート・リトライ
  - J-Quants API のレート制限（120 req/min）を守るための RateLimiter。
  - 408/429/5xx を対象とした指数バックオフリトライ。429 の Retry-After を尊重。
  - 401 発生時はトークンを自動的にリフレッシュして 1 回だけ再試行。

- テーブル設計
  - Raw → Processed → Feature → Execution の多層設計でデータプラットフォームの典型的パターンに沿う。
  - 各層に対して適切な PK / CHECK 制約とインデックスを用意。

### Fixed
- 初回リリースのため該当なし。

### Changed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし（ただし環境変数の保護ロジックやトークン取扱いに配慮した設計がされていることを注記）。

---

注意:
- 上記はソースコードの実装から推測して作成した CHANGELOG です。実際のリリースノートや追加ドキュメント（例: DataPlatform.md, DataSchema.md）がある場合はそれらも統合して最終版を作成してください。