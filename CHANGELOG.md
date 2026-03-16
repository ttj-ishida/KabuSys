CHANGELOG
=========

すべての注目すべき変更をこのファイルに記載します。
フォーマットは「Keep a Changelog」に準拠しています。

v0.1.0 - 2026-03-16
------------------

初回リリース。日本株自動売買システムの基盤機能を実装しました。

Added
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" に設定。
  - kabase の公開モジュール一覧に data, strategy, execution, monitoring を含める。

- 環境設定 / 読み込み（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点に探索する _find_project_root() を実装し、CWD に依存しない自動読み込みを実現。
  - .env パーサーの実装（引用符・エスケープ・export 形式・インラインコメント対応）。無効行はスキップ。
  - .env の読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / システム環境 (KABUSYS_ENV) / LOG_LEVEL の取得とバリデーションを提供。
  - デフォルトの DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"（expanduser 対応）。
  - settings インスタンスをプロジェクト単位で公開。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - レート制御: 固定間隔スロットリングで 120 req/min を厳守する _RateLimiter を実装。
  - 冪等かつ堅牢な HTTP リクエストロジック: 最大 3 回のリトライ（指数バックオフ）、対象ステータス 408/429/5xx に対応。429 の場合は Retry-After を優先。
  - 401 受信時にはトークンを自動リフレッシュして最大 1 回リトライ（無限再帰を防ぐため allow_refresh フラグを使用）。
  - ページネーション対応とモジュールレベルの id_token キャッシュ（ページ間でトークン共有）。
  - get_id_token(refresh_token=None) を実装。
  - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（いずれもページネーション対応、取得件数ログ出力）。
  - DuckDB へ保存する Idr・冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用して重複を排除）。
  - 取得時刻のトレーサビリティ: fetched_at フィールドを UTC (ISO8601, "Z") で付与して Look-ahead Bias を防止。
  - 型変換ユーティリティ: _to_float, _to_int（"1.0" 等の float 文字列を安全に扱い、小数部がある文字列は int 変換を抑止）。

- DuckDB スキーマ定義 / 初期化（kabusys.data.schema）
  - DataPlatform の 3 層（Raw / Processed / Feature / Execution）に基づくスキーマを一式定義。
  - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等の DDL を実装。
  - 性能を見越したインデックス定義群を追加（頻出クエリパターンを想定）。
  - init_schema(db_path) で DB ファイルの親ディレクトリ自動生成とテーブル作成（冪等）を実行。":memory:" 対応。
  - get_connection(db_path) による既存 DB 接続取得。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL の主要ワークフローを実装（run_daily_etl）。
    - 市場カレンダー ETL → 株価日足 ETL（差分・バックフィル）→ 財務データ ETL → 品質チェック の順で処理。
    - 各ステップは個別にエラーハンドリングされ、1 ステップ失敗でも他ステップを継続（Fail-Fast ではない）。
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl（差分更新ロジック、backfill_days、calendar lookahead をサポート）。
  - 差分算出ヘルパー: get_last_price_date, get_last_financial_date, get_last_calendar_date。
  - 営業日調整: market_calendar を参照して非営業日を直近営業日に調整する _adjust_to_trading_day。
  - ETLResult dataclass により、取得件数・保存件数・品質問題・エラー一覧を返却。品質問題をシリアライズ可能に変換する to_dict() を提供。
  - デフォルト値: backfill_days=3, calendar_lookahead_days=90。J-Quants のデータ最古日 _MIN_DATA_DATE=2017-01-01 を考慮。

- 品質チェック（kabusys.data.quality）
  - QualityIssue dataclass を定義（check_name, table, severity, detail, rows）。
  - check_missing_data: raw_prices の OHLC 欠損を検出（volume は除外）。サンプル最大 10 件を返却。
  - check_spike: 前日比のスパイク検出（デフォルト閾値 50%）。LAG ウィンドウで前日の close を参照し、異常レコードを抽出。
  - 各チェックは DuckDB 接続を用いた SQL ベースで効率的に実行し、Fail-Fast ではなく全件収集する設計。

- 監査ログ（kabusys.data.audit）
  - 戦略→シグナル→発注要求→約定 に至るトレーサビリティ用の監査テーブルを定義（signal_events, order_requests, executions）。
  - order_request_id を冪等キーとするなど、二重発注防止と完全な監査痕跡を考慮。
  - すべての TIMESTAMP は UTC で保存（init_audit_schema 内で SET TimeZone='UTC' を実行）。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（既存の DB に監査テーブルを追加する場合に使用）。
  - 多数のインデックスを用意し、戦略別・日付別検索やステータス別キュー取得を高速化。

- その他
  - data パッケージとサブモジュールの初期化ファイルを追加。
  - strategy/execution パッケージはプレースホルダとして存在（今後実装予定）。

Fixed / Improved
- .env の引用符・エスケープ処理や export 形式に対応することで、実運用での柔軟な環境変数管理を改善。
- _to_int の実装で "1.9" のような小数表現の誤った切り捨てを防止。
- jquants_client のリトライで Retry-After ヘッダを優先する対応を追加。

Security
- 認証トークンリフレッシュ処理は allow_refresh フラグにより無限再帰を防止。
- 環境変数読み込み時に既存の OS 環境変数を protected として上書きから保護可能。

Known issues / Notes
- strategy と execution パッケージは現時点で実装がありません（エントリポイントは空）。監視・実行ロジックは今後実装予定。
- jquants_client は同期的に urllib を利用しており、非同期処理や高スループット並列化は未対応。マルチプロセス/マルチスレッド環境でのレートリミッタはプロセス間共有されない点に注意。
- DuckDB の UNIQUE / インデックスの NULL 挙動などは注釈を README 等で補足する必要あり。
- 品質チェックは収集指向（Fail-Fast しない）なので、ETL を停止するかどうかは呼び出し側が決定する必要がある。

Deprecated
- なし（初回リリース）。

---

今後の予定（例）
- strategy / execution 層の具体実装（シグナル生成・リスク制御・発注エンジン）。
- 非同期 API クライアントや複数プロセス環境での分散レート制御の検討。
- 監査ログの外部エクスポート（監査レポート）機能、運用監視・アラート連携（Slack 等）の実装。