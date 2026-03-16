CHANGELOG
=========
（このCHANGELOGは Keep a Changelog の形式に準拠しています）

[Unreleased]
------------

0.1.0 - 2026-03-16
------------------

Added
- 初期リリース。KabuSys: 日本株自動売買システムの基本機能を実装。
- パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- 環境変数・設定管理（src/kabusys/config.py）:
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートの特定に .git / pyproject.toml を使用）。
  - 自動読み込みの無効化環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env の読み込み順: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護（protected）される。
  - .env パーサは "export KEY=val" 形式、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメント処理等に対応。
  - Settings クラスを公開（settings）し、以下のプロパティを提供:
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - slack_bot_token, slack_channel_id
    - duckdb_path, sqlite_path
    - env（許可値: development, paper_trading, live）とそれに基づく is_live / is_paper / is_dev
    - log_level（許可値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - 必須環境変数未設定時は ValueError を送出するユーティリティを実装。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）:
  - API エンドポイント: https://api.jquants.com/v1 を使用。
  - レート制限を厳守する固定間隔スロットリング実装（120 req/min、最小間隔 60/120 秒）。
  - リトライロジックを実装（最大 3 回、指数バックオフ、対象ステータス: 408/429 および 5xx）。429 の場合は Retry-After を優先。
  - 401 受信時はトークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止のため allow_refresh フラグあり）。
  - モジュールレベルの ID トークンキャッシュを共有（ページネーション間でトークンを使い回し）。
  - メインの HTTP ラッパー _request 実装（JSON 変換エラー時は詳細メッセージ付きで例外）。
  - 認証ユーティリティ: get_id_token (refreshtoken -> idToken)。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes（株価日足、/prices/daily_quotes）
    - fetch_financial_statements（四半期財務、/fins/statements）
    - fetch_market_calendar（JPX カレンダー、/markets/trading_calendar）
  - DuckDB への保存ユーティリティ（冪等: ON CONFLICT DO UPDATE）:
    - save_daily_quotes -> raw_prices テーブルへ。PK 欠損行はスキップして警告ログ。
    - save_financial_statements -> raw_financials テーブルへ。PK 欠損行はスキップ。
    - save_market_calendar -> market_calendar テーブルへ。HolidayDivision を基に is_trading_day / is_half_day / is_sq_day を算出。
  - 値変換ユーティリティ: _to_float（失敗時 None）、_to_int（"1.0" 等の float 文字列を許容、非整数量は None）。

- データベーススキーマ（DuckDB）定義（src/kabusys/data/schema.py）:
  - 3層構造のテーブル設計（Raw / Processed / Feature / Execution 層）を定義。
  - Raw 層テーブル: raw_prices, raw_financials, raw_news, raw_executions。
  - Processed 層テーブル: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
  - Feature 層テーブル: features, ai_scores。
  - Execution 層テーブル: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 各テーブルに適切な型・CHECK 制約・PRIMARY KEY を設定。
  - 頻出クエリに基づくインデックス群を作成。
  - init_schema(db_path) で DB ファイルの親ディレクトリを自動作成し、全テーブルとインデックスを冪等に作成して接続を返す。
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない旨の API）。

- ETL パイプライン（src/kabusys/data/pipeline.py）:
  - 日次 ETL のメイン処理 run_daily_etl を実装（市場カレンダー -> 株価日足 -> 財務データ -> 品質チェック の順）。
  - 差分更新ロジック: DB の最終取得日を参照して未取得分のみを取得。デフォルトのバックフィルは 3 日（後出し修正を吸収）。
  - 市場カレンダーは lookahead（デフォルト 90 日）で先読み取得し、営業日調整に使用。
  - ペイロードは jq（jquants_client）を利用して取得/保存し、保存は冪等。
  - ETLResult dataclass を導入（target_date, fetched/saved 各種カウント、quality_issues, errors）。has_errors / has_quality_errors / to_dict を実装。
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl を提供（テストしやすいように id_token 注入可）。
  - 各ステップは個別に例外ハンドリングされ、1ステップ失敗でも残りは継続して処理（Fail-Fast ではない設計）。
  - 品質チェックとの統合（quality モジュールを呼び出し）。

- 監査ログ（audit, src/kabusys/data/audit.py）:
  - シグナルから約定に至る監査トレースを UUID 連鎖で追跡するテーブル群を実装:
    - signal_events（戦略が生成したシグナルを全て記録）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ。limit/stop/market の制約をチェック）
    - executions（証券会社の約定情報。broker_execution_id をユニークな冪等キーとして管理）
  - 監査テーブルは削除しない前提（FK は ON DELETE RESTRICT）。全 TIMESTAMP を UTC で保存するため init_audit_schema は SET TimeZone='UTC' を実行。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（後者は DB ファイル親ディレクトリ自動作成）。
  - 監査用のインデックス群を作成（検索・キュー処理を想定したインデックス）。

- データ品質チェック（src/kabusys/data/quality.py）:
  - QualityIssue dataclass を実装（check_name, table, severity, detail, rows）。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（volume は対象外）。検出時はサンプル最大 10 行を返す。重大度は "error"。
    - check_spike: 前日比のスパイク検出（LAG ウィンドウを使用）。デフォルト閾値は 50%（_SPIKE_THRESHOLD = 0.5）。サンプル最大 10 行を返す。
  - 設計方針として Fail-Fast ではなく全件収集し、呼び出し元が重大度に応じて対処する。

Changed
- （初期リリースのためなし）

Fixed
- （初期リリースのためなし）

Deprecated
- （初期リリースのためなし）

Removed
- （初期リリースのためなし）

Security
- （初期リリースのためなし）

Notes / 実装上の注記
- jquants_client の _request は JSON デコード失敗時にレスポンスの先頭 200 文字を含むエラーメッセージを出すため、API の不整合調査に役立つ。
- save_* 関数は fetched_at を UTC タイムスタンプ（Z 表記）で保存し、Look-ahead Bias を防ぐトレーサビリティを意識。
- .env の自動読み込みはテスト時などに KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- DuckDB の init 系関数は ":memory:" を受け入れるため、ユニットテストでのインメモリ DB 利用が容易。
- 日付の営業日調整や ETL の差分計算は market_calendar が存在する場合にそれを利用するフォールバックロジックを持つ。

今後の予定（例）
- 監査ログと実際のブローカー API（kabuステーション等）を繋ぐ execution 層の実装強化。
- 追加の品質チェック（重複・将来日付・日付不整合の詳細実装）と自動修復ルールの導入。
- モニタリング・アラート（Slack 通知等）機能の統合。