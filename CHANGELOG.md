# CHANGELOG

すべての重要な変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠します。

最新更新: 2026-03-16

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-03-16

初回リリース — KabuSys 日本株自動売買システムのコア実装を追加。

### 追加 (Added)

- パッケージ構成
  - パッケージ初期化: kabusys.__init__ にてバージョン番号と公開サブパッケージ（data, strategy, execution, monitoring）を定義。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの検出は __file__ を基点に親ディレクトリから `.git` または `pyproject.toml` を探索。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロード無効化可能（テスト用途）。
  - .env パーサーの強化:
    - export KEY=val 形式対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの取り扱い（クォートあり/なしでの挙動を区別）。
  - OS 環境変数を保護する protected 機能（override=True 時も保護されたキーは上書きしない）。
  - Settings クラスを提供し、プロパティ経由で必須設定を取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須値として検証。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等にデフォルトを提供。
    - KABUSYS_ENV の値検証（development / paper_trading / live）。
    - LOG_LEVEL の値検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - is_live/is_paper/is_dev のヘルパー。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - ベース実装:
    - レートリミッタ（固定間隔スロットリング）で 120 req/min を遵守。
    - 冪等性と品質のため各取得で fetched_at を UTC ISO8601 形式で付与。
    - リトライロジック: 最大 3 回、指数バックオフ、ネットワーク/サーバーエラー (408, 429, 5xx) を考慮。
    - 401 受信時はトークンを自動リフレッシュして 1 回再試行（無限再帰防止）。
    - ID トークンキャッシュをモジュールレベルで保持（ページネーション間で共有）。
  - API 呼び出し関数（ページネーション対応）:
    - fetch_daily_quotes (株価日足 / OHLCV)
    - fetch_financial_statements (四半期 BS/PL 等)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 各関数は ON CONFLICT DO UPDATE を使って重複を排除・上書き（冪等性確保）。
  - ユーティリティ: 型変換ヘルパー _to_float, _to_int（不正値や小数切り捨て回避の考慮あり）。

- データベーススキーマ (src/kabusys/data/schema.py)
  - DataPlatform に基づく 3 層（Raw / Processed / Feature）＋Execution 層の DDL を定義:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 運用上の頻出クエリ向けインデックス定義を追加。
  - init_schema(db_path) により DuckDB を初期化して全テーブル/インデックスを作成（冪等）。
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は実行しない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - run_daily_etl を中心とした日次 ETL 実装:
    - 処理順: カレンダー ETL → 株価 ETL（差分＋backfill）→ 財務 ETL → 品質チェック（任意）
    - 差分更新ロジック: DB の最終取得日から backfill_days（デフォルト 3 日）前を再取得して API の後出し修正を吸収。
    - calendar は先読み（デフォルト 90 日）して営業日調整に利用。
    - ETLResult データクラスで取得数／保存数／品質問題／エラー情報を集約。
    - 各ステップはエラーハンドリングして独立稼働（あるステップの失敗で他ステップ継続）。
    - get_last_* ヘルパー（raw_prices/raw_financials/market_calendar の最終取得日取得）。
    - _adjust_to_trading_day で非営業日→直近営業日へ調整（最大 30 日遡り、カレンダー未取得時はフォールバックでそのまま）。

- 監査ログ（トレーサビリティ）モジュール (src/kabusys/data/audit.py)
  - 監査テーブル群と初期化関数を実装:
    - signal_events（シグナル発生ログ）、order_requests（発注要求：order_request_id を冪等キー）、executions（約定ログ）
    - 全テーブルに created_at/updated_at を付与し、UTC タイムゾーンで保存されることを明示（init_audit_schema は SET TimeZone='UTC' を実行）。
    - 外部キーは ON DELETE RESTRICT（監査ログを削除しない方針）。
    - init_audit_schema(conn) と init_audit_db(db_path) を提供。
    - インデックス定義: 日付・銘柄検索、status ベースのキュー検索、broker_order_id / broker_execution_id による紐付け等を想定。

- 品質チェックモジュール (src/kabusys/data/quality.py)
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損（open/high/low/close）を検出（severity=error）。
    - check_spike: 前日比スパイク検出（デフォルト閾値 50%）。LAG ウィンドウ関数を使用して変動率を判定。
  - 設計方針: Fail-Fast ではなく全問題を収集して呼び出し元で重大度に応じた判断を行う。

- ロギング・品質設計
  - 各主要処理で logger を用いた情報・警告・例外ログ出力を実装。
  - ETL・API クライアント・保存処理で取得件数やスキップ件数を明示的にログ出力。

### 変更 (Changed)

- 初回リリースのため該当なし。

### 修正 (Fixed)

- 初回リリースのため該当なし。

### 既知の注意点 / マイグレーションノート

- 初回起動時または新規環境では、DuckDB スキーマを明示的に初期化してください:
  - data.schema.init_schema(settings.duckdb_path)
- 監査ログを別 DB に分けたい場合は init_audit_db() を利用できます。
- 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（主にテスト用途）。
- J-Quants リフレッシュトークンなど必須環境変数が未設定の場合 Settings のプロパティは ValueError を送出します。`.env.example` を参照して設定してください。

---

貢献者: 初期実装（自動生成された変更履歴のため個別クレジットは省略）

（この CHANGELOG はソースコードから推測して作成されています。実際のリリースノートには運用上の詳細や bugfix、貢献者情報を追記してください。）