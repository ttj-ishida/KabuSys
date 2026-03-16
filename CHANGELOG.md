# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
安定版リリース前の初期公開バージョンとして以下の内容を記載します。

## [Unreleased]
- （今後の変更をここに記載）

## [0.1.0] - 2026-03-16
初期リリース。日本株自動売買プラットフォームの基礎機能を実装しました。以下の主要機能・設計方針が含まれます。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化とバージョン情報を追加 (`kabusys.__version__ = "0.1.0"`)。
  - モジュール構成: data, strategy, execution, monitoring のエクスポートを定義。

- 設定・環境変数管理 (`kabusys.config`)
  - .env / .env.local / OS 環境変数からの自動読み込み機能を実装（読み込み順: OS > .env.local > .env）。
  - プロジェクトルート検出: __file__ を基点に `.git` または `pyproject.toml` を探索してルートを特定（配布後も動作）。
  - .env パーサの実装:
    - export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメントへの対応。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack / DB パス等の設定。
    - デフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）。
    - 入力検証: KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の検証、必須キー未設定時は ValueError を送出。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API エンドポイント実装:
    - 株価日足取得: fetch_daily_quotes
    - 財務データ取得（四半期 BS/PL）: fetch_financial_statements
    - JPX マーケットカレンダー取得: fetch_market_calendar
    - リフレッシュトークンからの id_token 取得: get_id_token
  - HTTP 層の設計:
    - レート制限対応（固定間隔スロットリング、120 req/min）。
    - 冪等性のためモジュールレベルの id_token キャッシュ（ページネーション間で再利用）。
    - リトライロジック（指数バックオフ、最大 3 回）。リトライ対象: 408, 429 および 5xx。
    - 401 受信時はトークン自動リフレッシュを 1 回試行して再試行（無限再帰を防止）。
    - ページネーション対応（pagination_key を使った継続取得）。
    - JSON デコード失敗時の明確なエラーメッセージ。

  - DuckDB 保存ユーティリティ:
    - 株価 / 財務 / カレンダーの保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - 挿入は ON CONFLICT DO UPDATE による冪等性を確保。
    - PK 欠損行のスキップとログ警告、fetched_at に UTC タイムスタンプを記録。

  - 型変換ユーティリティ:
    - 安全な _to_float / _to_int 実装（空値・不正値を None に変換、float 文字列の int 変換時の切り捨て防止等）。

- DuckDB スキーマ定義・初期化 (`kabusys.data.schema`)
  - DataPlatform の 3 層（Raw / Processed / Feature）と Execution レイヤーに基づくテーブル定義を実装。
  - 多数のテーブルを定義（例: raw_prices, raw_financials, raw_news, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 各テーブルに適切な型制約・CHECK 制約・主キーを付与。
  - 実行パターンに合わせたインデックスを作成（頻出クエリのための複数インデックス）。
  - init_schema(db_path) でディレクトリ自動作成＋全DDLを実行して接続を返す（冪等）。
  - get_connection(db_path) により既存 DB への接続を取得（スキーマ初期化は行わない）。

- ETL パイプライン (`kabusys.data.pipeline`)
  - 日次 ETL のエントリ: run_daily_etl
    - ワークフロー: カレンダー取得 → 株価ETL（差分＋バックフィル） → 財務ETL（差分＋バックフィル） → 品質チェック（任意）。
    - 各ステップは独立したエラーハンドリング（1ステップ失敗でも他ステップを継続）。
    - 差分更新ロジック: DB の最終取得日を元に未取得範囲を自動算出。
    - バックフィル機能: 最終取得日の N 日前から再取得して API 後出し修正を吸収（デフォルト backfill_days=3）。
    - カレンダー先読み（デフォルト 90 日）により営業日判定を安定化。
    - ETLResult dataclass に処理結果・品質問題・エラー概要を集約し返却。
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl を提供（各々 idempotent に動作）。

- 品質チェック (`kabusys.data.quality`)
  - データ品質チェックフレームワークと QualityIssue データクラスを実装。
  - 実装済みチェック:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欄の欠損検出（サンプル最大 10 件を返す）。
    - スパイク検出 (check_spike): LAG ウィンドウで前日比を算出し、閾値（デフォルト 50%）を超える急騰・急落を検出。
  - 各チェックは全件収集方式で重大度（error/warning）を付与、呼び出し元が判断可能。
  - DuckDB 上でパラメータバインドされた SQL により効率的に実行。

- 監査ログ・トレーサビリティ (`kabusys.data.audit`)
  - シグナル → 発注要求 → 約定までを UUID 連鎖で追跡する監査スキーマを実装。
  - テーブル: signal_events, order_requests, executions（UTC タイムスタンプ、created_at/updated_at 等）。
  - order_requests に冪等キー（order_request_id）、発注種別ごとの CHECK 制約（limit/stop/market の必須/排他条件）を実装。
  - executions は broker_execution_id をユニークにして証券会社側の冪等性をサポート。
  - init_audit_schema(conn) / init_audit_db(db_path) で監査スキーマを初期化（UTC 保存を明示的に設定）。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 削除 (Removed)
- 初期リリースのため該当なし。

### その他・設計注記
- すべての TIMESTAMP は UTC を前提とする実装方針（監査周りで明示）。
- ETL は Fail-Fast ではなく全エラーを収集して報告する設計。
- データ保存は可能な限り冪等（ON CONFLICT DO UPDATE）を採用して再実行や部分失敗に耐性を持たせる。
- 外部 API の制限（120 req/min）やリトライ方針（指数バックオフ、Retry-After 優先など）を考慮して実装。

---

今後のバージョンでは、strategy / execution / monitoring 層の具現化、追加の品質チェック（重複・日付不整合など）、テストカバレッジ拡充、CLI / サービス化、監視・アラート統合などを予定しています。