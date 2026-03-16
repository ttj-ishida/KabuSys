# CHANGELOG

すべての変更は「Keep a Changelog」準拠の形式で記載しています。日付は当該コードベース（初回リリース）作成日として記載しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-16
初回リリース

### 追加 (Added)
- パッケージ概要
  - kabusys: 日本株自動売買システム向けのライブラリ基盤を追加。
  - パッケージ公開 API: kabusys.config.settings を通じた設定読み取りを提供。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを追加。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - プロジェクトルートの検出: .git または pyproject.toml を探索して自動検出（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env 行パーサを実装（コメント、export プレフィックス、クォートとバックスラッシュエスケープ対応）。
  - 環境変数必須チェック用の _require と Settings クラスを提供。
    - 主な必須環境変数:
      - JQUANTS_REFRESH_TOKEN（J-Quants API 用リフレッシュトークン）
      - KABU_API_PASSWORD（kabuステーション API パスワード）
      - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知）
    - その他の設定とデフォルト:
      - KABUSYS_ENV: development / paper_trading / live の検証
      - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL の検証
      - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
      - DUCKDB_PATH デフォルト data/kabusys.duckdb, SQLITE_PATH デフォルト data/monitoring.db

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API から日次株価（OHLCV）、財務（四半期 BS/PL）、市場カレンダーを取得するクライアントを実装。
  - 設計上の特徴:
    - API レート制限遵守（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）。対象ステータス: 408, 429, 5xx。429 の場合は Retry-After を優先。
    - 401 受信時はリフレッシュトークンから id_token を自動再取得して 1 回リトライ（無限再帰防止）。
    - Look-ahead bias 対策のため取得時刻（fetched_at）を UTC で記録。
    - ページネーション対応（pagination_key の追従、モジュールレベルで id_token をキャッシュして共有）。
  - 公開 API:
    - get_id_token(refresh_token: str | None) -> str
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
    - save_daily_quotes(conn, records) — DuckDB への冪等保存（ON CONFLICT DO UPDATE）
    - save_financial_statements(conn, records) — 同上
    - save_market_calendar(conn, records) — 同上
  - 入出力変換ユーティリティを実装: _to_float, _to_int（細かい型/値チェックを含む）

- DuckDB スキーマ定義・初期化モジュール (src/kabusys/data/schema.py)
  - DataPlatform の 3 層＋実行層に対応するスキーマ DDL を実装（Raw / Processed / Feature / Execution）。
  - 主要テーブル（抜粋）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 複数の補助インデックスを定義（頻出クエリを想定したインデックス群）。
  - init_schema(db_path) でディレクトリ自動作成を行い、全テーブル／インデックスを冪等に作成して DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL 処理の統合エントリ run_daily_etl を実装。
  - 個別ジョブ:
    - run_calendar_etl: 市場カレンダーの差分 + 先読み（デフォルト 90 日先まで）
    - run_prices_etl: 株価の日次差分 ETL（差分取得 + バックフィルデフォルト 3 日）
    - run_financials_etl: 財務データの差分 ETL（差分取得 + バックフィル）
  - 差分ロジック: DB の最終取得日を参照し、未取得範囲のみ取得。最初の取得時は 2017-01-01 を下限として使用。
  - ETLResult データクラスを追加（取得数、保存数、品質問題、エラー一覧を集約）。
  - 品質チェック (quality モジュール) を ETL 後にオプションで実行し、重大度に応じて呼び出し元が判断可能。

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - シグナルから約定までを UUID 連鎖でトレースするための監査用テーブルを追加:
    - signal_events, order_requests, executions
  - 設計上のポイント:
    - order_request_id を冪等キーとして扱う
    - 全ての TIMESTAMP を UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）
    - FK は ON DELETE RESTRICT（監査ログは削除しない想定）
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（冪等初期化）。

- データ品質チェックモジュール (src/kabusys/data/quality.py)
  - QualityIssue データクラスを導入（チェック名・テーブル・重大度・詳細・サンプル行）。
  - 実装済みのチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は許容）
    - check_spike: 前日比スパイク検出（LAG ウィンドウ、閾値デフォルト 50%）
  - 各チェックは問題を全件収集し、Fail-Fast とせず呼び出し元が重大度に基づいて判断可能。

- パッケージ構造
  - 空のパッケージ __init__ を配置（execution, strategy, data のパッケージ化）。
  - バージョン情報: __version__ = "0.1.0"

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### 既知の制約 / 注意点
- J-Quants API のレート制限: 120 req/min（RateLimiter が固定間隔スロットリングで制御）。
- リトライは最大 3 回。429 レスポンス時は Retry-After を優先する実装。
- get_id_token は refresh_token を参照し、settings.jquants_refresh_token の設定が必須。
- DuckDB テーブル初期化は init_schema() を使用すること（get_connection() は初期化しない）。
- .env パーサは一般的なシェル系 .env 形式をサポートするが、極端に特殊な行は想定外の動作となる可能性あり。
- quality モジュールのスパイク閾値既定値は 50%（pipeline から閾値を上書き可能）。

### API（主な公開関数 / オブジェクト）
- kabusys.__version__
- kabusys.config.settings (Settings インスタンス)
- jquants_client:
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- data.schema:
  - init_schema(db_path), get_connection(db_path)
- data.pipeline:
  - run_daily_etl(...), run_prices_etl(...), run_financials_etl(...), run_calendar_etl(...)
- data.audit:
  - init_audit_schema(conn), init_audit_db(db_path)
- data.quality:
  - QualityIssue, check_missing_data, check_spike

---

今後の予定（例）
- strategy / execution 層の実装（実際のシグナル生成・発注連携）
- Slack や監視周りの統合（通知、モニタリング）
- 単体テスト、統合テスト、CI ワークフローの追加

もし特定の項目（例: 各関数の利用例や環境変数の一覧）を CHANGELOG に追記したい場合は指示してください。