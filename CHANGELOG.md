Keep a Changelog に準拠した CHANGELOG.md

すべての注目すべき変更を追跡します。フォーマットとセクションは Keep a Changelog のガイドラインに従います。

注: 日付はこのリリース作成日時です。

Unreleased
----------
- 今後のリリースでの変更点をここに記載します。

[0.1.0] - 2026-03-16
-------------------
Added
- パッケージ初回リリースを追加。
  - パッケージ名: kabusys、バージョン: 0.1.0

- 環境設定管理モジュール (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みするロジックを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルート判定: .git または pyproject.toml を起点に探索（__file__ を基準にするため CWD 非依存）。
  - .env のパース実装:
    - コメント行、export プレフィックス、クォート文字列（エスケープ対応）、インラインコメントの扱い等に対応。
  - Settings クラスを提供（settings インスタンスを公開）。
    - J-Quants 用: jquants_refresh_token（必須）
    - kabuステーション API: kabu_api_password、kabu_api_base_url（デフォルト http://localhost:18080/kabusapi）
    - Slack: slack_bot_token、slack_channel_id（必須）
    - DB パス: duckdb_path（デフォルト data/kabusys.duckdb）、sqlite_path（デフォルト data/monitoring.db）
    - システム設定: KABUSYS_ENV 検証（development, paper_trading, live のみ許可）、LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパープロパティ: is_live / is_paper / is_dev

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本設計:
    - API レート制限遵守（120 req/min）を実装（固定間隔スロットリングの _RateLimiter）。
    - リトライ機構（指数バックオフ、最大 3 回、対象: 408/429/5xx、ネットワークエラーも再試行）。
    - 401 受信時はリフレッシュトークンで自動的に id_token を再取得して 1 回だけリトライ（無限再帰防止のため allow_refresh フラグ）。
    - ページネーション対応（pagination_key を利用し、ループで全ページ取得）。
    - データ取得時に fetched_at（UTC）を付与して Look-ahead Bias を防止。
  - 公開 API:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(id_token: Optional[str], code: Optional[str], date_from: Optional[date], date_to: Optional[date]) -> list[dict]
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
  - DuckDB への保存関数（冪等: ON CONFLICT DO UPDATE）:
    - save_daily_quotes(conn, records) -> int
    - save_financial_statements(conn, records) -> int
    - save_market_calendar(conn, records) -> int
  - ユーティリティ関数:
    - 型変換ヘルパー _to_float / _to_int（不正な値や空値を None にする堅牢化）

- DuckDB スキーマ定義と初期化モジュール (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の 3 層（+ Execution 層）に基づくスキーマを定義。
  - 多数のテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 標準的なインデックスを作成（頻出クエリパターンに対応）。
  - 公開 API:
    - init_schema(db_path) -> duckdb connection（親ディレクトリ自動作成、:memory: サポート、冪等でテーブル作成）
    - get_connection(db_path) -> duckdb connection（スキーマ初期化は行わない）

- データ ETL パイプライン (kabusys.data.pipeline)
  - ETL フローを実装:
    - 差分更新（DB の最終取得日から取得範囲を計算）
    - backfill_days による再取得（デフォルト 3 日）で API の後出し修正を吸収
    - カレンダーの先読み（デフォルト 90 日）
    - 品質チェック（quality モジュールとの連携）
  - 主な関数:
    - run_prices_etl(conn, target_date, id_token=None, date_from=None, backfill_days=3) -> (fetched, saved)
    - run_financials_etl(...)
    - run_calendar_etl(..., lookahead_days=90)
    - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, spike_threshold=0.5, backfill_days=3, calendar_lookahead_days=90) -> ETLResult
  - ETLResult データクラスを提供:
    - ETL 実行結果（取得数・保存数・品質問題リスト・エラー一覧）を保持
    - has_errors / has_quality_errors / to_dict を提供
  - 設計方針:
    - 各ステップは独立してエラーハンドリング（1 ステップ失敗でも他ステップは継続）
    - id_token を注入可能（テスト容易性）

- 監査ログ（トレーサビリティ）モジュール (kabusys.data.audit)
  - シグナル → 発注 → 約定 を UUID 連鎖でトレースする監査テーブルを定義
    - signal_events, order_requests, executions
  - 発注の冪等性（order_request_id を冪等キー）をサポート
  - すべての TIMESTAMP を UTC で保存する（init_audit_schema で SET TimeZone='UTC' を実行）
  - 公開 API:
    - init_audit_schema(conn)  （既存接続に監査テーブルを追加）
    - init_audit_db(db_path) -> duckdb connection（監査用 DB を単独で初期化）

- データ品質チェックモジュール (kabusys.data.quality)
  - チェック項目の設計と実装（DuckDB 上の SQL を用いて効率的に検査）
    - check_missing_data(conn, target_date=None): raw_prices の OHLC 欠損を検出（sample を返す）
    - check_spike(conn, target_date=None, threshold=0.5): 前日比スパイク（±50% 既定）を検出
  - QualityIssue データクラスを提供（check_name, table, severity, detail, rows）
  - 設計方針:
    - 各チェックは QualityIssue のリストを返す（Fail-Fast ではなく全件収集）
    - 呼び出し元 (pipeline) は重大度に応じて停止／警告を判断

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 注意事項
- .env パーサは多くのケース（export プレフィックス、クォート、エスケープ、インラインコメントなど）に対応しますが、特殊なフォーマットの .env を使用する場合は動作確認を行ってください。
- J-Quants API クライアントは 120 req/min の固定スロットリングを採用しています。厳密なスループット制御や分散環境での共有が必要な場合は拡張が必要です。
- quality モジュールには記載されているチェック（欠損、スパイク、重複、日付不整合）を想定しています。現状の実装は一部（欠損・スパイク）を中心に実装されています。追加チェックや閾値調整は今後の改良項目です。
- DuckDB スキーマは多くの制約（CHECK、PRIMARY KEY、FOREIGN KEY）やインデックスを定義しています。既存 DB に導入する際は互換性に注意してください。

今後の予定（例）
- 追加の品質チェック（重複、将来日付の検出など）の実装完了と pipeline への組み込み
- execution（発注）層の実装（kabu ステーション連携など）と監査ログの運用
- テストカバレッジの充実（単体テスト、統合テスト、API モック）
- ドキュメント（DataSchema.md / DataPlatform.md に基づく利用ガイド）の整備

--- End of CHANGELOG ---