CHANGELOG
=========

すべての重要な変更を記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。  

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-16
--------------------

Added
- 初回リリース。日本株自動売買システム (KabuSys) の骨格実装を追加。
  - パッケージメタ:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
    - パッケージ公開対象モジュールに data, strategy, execution, monitoring を含める設定。

- 環境変数・設定管理:
  - src/kabusys/config.py を追加。
    - .env / .env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml を基準に自動検出）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は protected として上書きを防止。
    - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサは export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
    - 必須環境変数取得用関数 _require を提供（未設定時は ValueError を送出）。
    - settings オブジェクトを公開。J-Quants / kabuAPI / Slack / DB パス / 実行環境 (development, paper_trading, live) / ログレベル検証等のプロパティを実装。

- データ取得クライアント（J-Quants）:
  - src/kabusys/data/jquants_client.py を実装。
    - API 呼び出しの共通処理を実装（JSON デコード検証、タイムアウト、詳細なエラーメッセージ）。
    - レート制限制御: 固定間隔スロットリングで 120 req/min を保証（内部 RateLimiter）。
    - 再試行ロジック: 指数バックオフ、最大 3 回、HTTP 408/429/5xx およびネットワークエラーをリトライ。
    - 401 エラー時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰回避のため allow_refresh 制御）。
    - ID トークンのキャッシュ共有実装（モジュールレベル、ページネーション間で共有可能）。
    - ページネーション対応の取得関数を提供:
      - fetch_daily_quotes（OHLCV、ページネーション対応）
      - fetch_financial_statements（四半期 BS/PL、ページネーション対応）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB へ保存する冪等化された保存関数を実装（ON CONFLICT DO UPDATE）:
      - save_daily_quotes（raw_prices）
      - save_financial_statements（raw_financials）
      - save_market_calendar（market_calendar）
    - 保存時に fetched_at（UTC）を付与し、Look-ahead バイアスのトレーサビリティを確保。
    - 型変換ユーティリティ (_to_float / _to_int) を設置。意図しない切り捨てを防ぐための厳密な int 変換ロジックを実装。

- DuckDB スキーマ定義・初期化:
  - src/kabusys/data/schema.py を追加。
    - 3 層（Raw / Processed / Feature）＋ Execution 層を含む包括的なテーブル定義を DDL として実装。
    - raw_prices / raw_financials / raw_news / raw_executions を含む Raw レイヤー。
    - prices_daily / market_calendar / fundamentals / news_articles / news_symbols を含む Processed レイヤー。
    - features / ai_scores を含む Feature レイヤー。
    - signals / signal_queue / portfolio_targets / orders / trades / positions / portfolio_performance を含む Execution レイヤー。
    - 各テーブルに適切な CHECK 制約 / PRIMARY KEY / FOREIGN KEY を設計（発注や監査と連携しやすい制約を考慮）。
    - 頻出クエリパターンを想定したインデックス群を定義。
    - init_schema(db_path) で親ディレクトリ自動作成、全テーブルとインデックスを冪等に作成。
    - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない旨を明記）。

- 監査ログ（トレーサビリティ）:
  - src/kabusys/data/audit.py を追加。
    - signal_events / order_requests / executions の監査用テーブル定義を提供。
    - order_requests は order_request_id を冪等キーとし、limit/stop/market のチェック制約を実装。
    - executions は broker_execution_id をユニークな冪等キーとして扱う。
    - すべての TIMESTAMP を UTC 保存するため init_audit_schema は SET TimeZone='UTC' を実行。
    - init_audit_schema(conn) で既存接続に監査テーブルを追加、init_audit_db(db_path) で監査専用 DB を初期化可能。
    - 監査用インデックス群を追加（検索・結合の高速化、broker_order_id での紐付け用 UNIQUE インデックスなど）。

- データ品質チェック:
  - src/kabusys/data/quality.py を追加。
    - QualityIssue dataclass を導入し、すべてのチェックは QualityIssue のリストを返す設計（Fail-Fast ではなく全件収集）。
    - 実装済みチェック:
      - check_missing_data: raw_prices の OHLC 欠損検出（volume は許容）。
      - check_duplicates: raw_prices の主キー重複検出。
      - check_spike: 前日比スパイク検出（デフォルト閾値 50%）。
      - check_date_consistency: 将来日付検出および market_calendar と整合しない非営業日データ検出（market_calendar テーブルがなければスキップ）。
    - run_all_checks(conn, ...) で全チェックをまとめて実行し、エラー・警告の件数をログ出力。
    - SQL はパラメータバインドを用いてインジェクションリスクを排除し、DuckDB を効率的に利用。

- モジュール初期化ファイル:
  - src/kabusys/data/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/monitoring/__init__.py を追加（将来の拡張用に空のパッケージ初期化）。

Notes / 使い方メモ
- 設定:
  - settings オブジェクトを import して利用（例: from kabusys.config import settings; settings.jquants_refresh_token）。
  - 自動 .env 読み込みをテストで無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- データベース初期化:
  - DuckDB スキーマを作るには: from kabusys.data.schema import init_schema; conn = init_schema("data/kabusys.duckdb")
  - 監査ログを既存接続に追加するには: from kabusys.data.audit import init_audit_schema; init_audit_schema(conn)

- J-Quants 利用:
  - トークン取得: from kabusys.data.jquants_client import get_id_token
  - データ取得/保存: fetch_* 系で取得し、save_* 系で DuckDB に冪等保存

Known limitations / TODO（今後の予定）
- strategy / execution / monitoring パッケージは初期化ファイルのみで、実際の戦略実装・発注連携・監視ロジックは未実装。
- エラーの詳細なハンドリングやメトリクス収集、外部サービスとの統合テストは今後追加予定。

Security
- 環境変数自動ロードにおいて OS 環境変数を保護する仕組みを実装（.env による上書きを防止）。ただし .env ファイル自体は機密情報を含む可能性があるため、適切なファイルパーミッション運用を推奨。

詳細な差分・設計資料はリポジトリ内の DataPlatform.md / DataSchema.md 等を参照してください。