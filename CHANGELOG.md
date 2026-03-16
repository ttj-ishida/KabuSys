# CHANGELOG

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」準拠です。

## [Unreleased]

---

## [0.1.0] - 2026-03-16

初回公開リリース。日本株自動売買プラットフォームのコア基盤を実装しました。

### Added
- パッケージ基盤
  - パッケージメタ情報（kabusys.__version__ = 0.1.0）およびパッケージ公開モジュール一覧を追加（data, strategy, execution, monitoring）。
- 設定・環境変数管理（kabusys.config）
  - .env ファイル（および .env.local）や OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出ロジックを導入（.git / pyproject.toml を探索）。これにより CWD に依存せずに .env を自動読み込み可能。
  - .env パーサーを実装：コメント、 export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント処理に対応。
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を追加（テスト等で使用可能）。
  - Settings クラスを追加し、主要設定値をプロパティとして提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須取得時は ValueError を送出）
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH（デフォルト値あり）
    - 環境（KABUSYS_ENV）の検証（development / paper_trading / live）および LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の補助プロパティ
- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants から日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - API レート制御（固定間隔スロットリング）を導入し、デフォルトで 120 req/min を遵守する RateLimiter を実装。
  - リトライロジックを実装（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）。429 の場合は Retry-After ヘッダを考慮。
  - 401 Unauthorized 受信時にリフレッシュトークンから自動で id_token を再取得して 1 回リトライする仕組みを実装（無限再帰防止のため内部呼び出しではリフレッシュ無効化）。
  - id_token のモジュールレベルキャッシュ（ページネーション間で共有）を実装。
  - JSON デコードエラーやネットワークエラーの明示的な扱い（例外メッセージの強化）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を追加。すべて ON CONFLICT DO UPDATE により冪等化。
  - 取得日時（fetched_at）を UTC ISO8601 で記録し、Look-ahead Bias のトレーサビリティを確保。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正な値や空値を安全に扱う。
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataPlatform 構造に基づいたテーブル群を定義（Raw / Processed / Feature / Execution 層）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに妥当性チェック用の型制約・CHECK 制約・PRIMARY/FOREIGN KEY を追加。
  - パフォーマンス考慮のためインデックスを定義（銘柄×日付、ステータス検索、外部キー参照等）。
  - init_schema(db_path) により DB ファイル作成（親ディレクトリ自動作成）、DDL 実行、インデックス作成を行い DuckDB 接続を返す関数を追加。
  - get_connection(db_path) を提供（既存 DB に接続するユーティリティ）。
- 監査ログ（audit）スキーマ（kabusys.data.audit）
  - シグナル→発注→約定のトレーサビリティを保証する監査テーブルを定義：
    - signal_events（戦略が生成したシグナルを全て記録、ステータス理由を含む）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ、価格チェック制約、ステータス遷移カラム等）
    - executions（証券会社側の約定情報を記録、broker_execution_id を冪等キーとして保持）
  - 監査用インデックスを定義（シグナル検索、order_requests.status スキャン、broker_order_id 紐付け等）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供（UTC タイムゾーン設定を実行）。
- データ品質チェック（kabusys.data.quality）
  - DataPlatform の品質ルールに基づくチェック関数を実装：
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は許容）
    - check_spike: 前日比の急騰・急落（デフォルト閾値 50% = 0.5）検出（LAG ウィンドウ使用）
    - check_duplicates: raw_prices の主キー重複検出
    - check_date_consistency: 将来日付および market_calendar と齟齬のある日付（非営業日）の検出
    - run_all_checks: 上記すべてのチェックを実行して結果を集約
  - 各チェックは QualityIssue データクラス（check_name, table, severity, detail, rows）を返し、複数問題を一括で収集可能（Fail-fast ではない）。
  - チェックは DuckDB 上で SQL を用いて実行し、パラメータバインドを行うことで安全に実装。
- 監視層のプレースホルダ（kabusys.monitoring.__init__ および空の strategy / execution パッケージ）を追加し、今後の拡張を容易にする基盤を整備。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- J-Quants クライアントはレート制限・リトライ・トークンリフレッシュ・ページネーションを組み合わせて堅牢に設計されています。運用環境では settings.jquants_refresh_token 等の必須環境変数を正しく設定してください。
- DuckDB スキーマは多くの CHECK 制約や外部キー、インデックスを含みます。初期化は idempotent（冪等）であり、既存テーブルを上書きしません。
- 監査ログは削除しない前提（ON DELETE RESTRICT）で設計されており、タイムスタンプは UTC で保存します。アプリ側は updated_at を更新する際に current_timestamp を設定してください。
- データ品質チェックはあくまで検出器であり、運用フローでは検出結果に応じた ETL 停止・警告出力の判断を行ってください。

---

今後の予定（例）
- strategy / execution 層の具体的なアルゴリズム・ブローカー接続実装
- 監視（Slack 通知など）およびオペレーション用 CLI / サービス化
- テストカバレッジと CI/CD パイプラインの整備

---