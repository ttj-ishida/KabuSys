CHANGELOG
=========
すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-03-16
-------------------

初回公開リリース（ベース実装）。日本株自動売買プラットフォームのコア部分を実装しています。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名・バージョンと公開サブパッケージ（data, strategy, execution, monitoring）を定義。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml から検出）。
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの扱い等）。
  - .env の読み込み順序: OS 環境 > .env.local > .env（既存 OS 環境は保護）。
  - 設定アクセス用 Settings クラスを提供（settings インスタンス）。
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティ（必須パラメータは未設定時に ValueError を送出）。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL 検証。
    - デフォルト DB パス（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - 認証: リフレッシュトークンから ID トークンを取得する get_id_token。
  - HTTP レイヤ:
    - レート制限: 固定間隔スロットリングで 120 req/min を遵守（_RateLimiter）。
    - 再試行（リトライ）ロジック: 指数バックオフ、最大 3 回、対象ステータス 408/429/5xx。429 の場合 Retry-After ヘッダ優先。
    - 401 発生時はトークンを自動リフレッシュして 1 回リトライ（無限再帰を防止）。
    - JSON デコードエラーハンドリング、タイムアウト等。
  - DuckDB へ冪等的に保存する save_* 関数:
    - raw_prices / raw_financials / market_calendar テーブル向けに ON CONFLICT DO UPDATE を使用して重複を排除。
    - fetched_at を UTC ISO8601 で記録（Look-ahead Bias防止のため取得時刻を保持）。
  - 入力変換ユーティリティ: _to_float / _to_int（堅牢な数値変換ロジック）。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DataPlatform の 3 層（Raw / Processed / Feature）＋Execution 層のテーブル DDL を定義。
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（主キー・型チェック・CHK）を明示的に付与。
  - 頻出クエリ向けのインデックス定義を追加。
  - init_schema(db_path) で DB ファイルの親ディレクトリ作成→テーブル・インデックス作成（冪等）。
  - get_connection(db_path) を提供（初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL の主要処理を実装:
    - run_calendar_etl / run_prices_etl / run_financials_etl（差分更新、ページネーション、backfill 対応）。
    - run_daily_etl: カレンダー取得 → 営業日調整 → 株価/財務差分取得 → 品質チェック、という順序で実行。各ステップは独立して例外処理され、1ステップ失敗でも他ステップは継続。
  - 差分更新ロジック:
    - 最終取得日の自動検出と backfill_days（デフォルト 3）に基づく再取得。
    - カレンダーは lookahead（デフォルト 90 日）で先読みして営業日調整に使用。
  - ETLResult データクラスを導入し、fetch/save件数、品質問題、エラーメッセージ等を集約。
  - id_token の注入可能化でテスト容易性を確保。

- 監査ログ（audit）スキーマ（src/kabusys/data/audit.py）
  - 戦略→シグナル→発注要求→約定 のトレーサビリティを保持する監査テーブルを実装:
    - signal_events, order_requests（冪等キー: order_request_id）, executions
  - 発注/約定のステータスやエラーメッセージ用カラムを用意。
  - 全 TIMESTAMP を UTC で保存するため init_audit_schema は "SET TimeZone='UTC'" を実行。
  - init_audit_db(db_path) により監査専用 DB の初期化が可能。
  - 監査向けインデックスを追加（検索・ジョイン性能を考慮）。

- データ品質チェック（src/kabusys/data/quality.py）
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は許容）。
    - check_spike: 前日比のスパイク検出（LAG ウィンドウを使用、デフォルト閾値 50%）。
  - 各チェックは問題を全件収集して QualityIssue のリストを返す（Fail-Fast しない）。
  - DuckDB を用いた効率的な SQL 実装、パラメータバインドを使用して注入リスクを低減。

### Changed
- （該当なし — 初回リリース）

### Fixed
- （該当なし — 初回リリース）

### Security
- 環境変数の保護機能（OS の環境変数はデフォルトで .env による上書きを防止）。
- SQL 実行時はパラメータバインド（?）を可能な限り使用。

Notes / 実装上のポイント
- API レート制限は固定間隔スロットリングで厳格に守る設計（_MIN_INTERVAL_SEC = 60 / 120）。
- HTTP リトライはネットワーク・サーバ障害に対してロバストに動作（指数バックオフ、Retry-After 優先）。
- DuckDB 側は ON CONFLICT DO UPDATE を用いることで冪等性を担保。
- 日時は基本的に UTC を採用（fetched_at, created_at 等）。
- ETL の品質チェックは警告とエラーの重大度を分け、呼び出し元での対応を想定。
- .env のパースは実運用で見られる様々な記法（export、クォート、エスケープ、行内コメント）に対応。

今後の予定（例）
- strategy / execution / monitoring 層の実装拡充（現在はパッケージ空の __init__）。
- Slack 通知や kabuステーション連携の具体的発注モジュール実装。
- 単体テスト、CI設定、型チェック・リントの追加。

以上。