CHANGELOG
=========
すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠し、セマンティックバージョニングを採用します。

フォーマット
-----------
- すべての変更はバージョンごとに分類されています。
- 日付はリリース日を示します。

[Unreleased]
------------
（現在未リリースの変更はここに記載します）

0.1.0 - 2026-03-15
-----------------

Added
-----
- 初期リリース。パッケージ名: kabusys, バージョン: 0.1.0
  - src/kabusys/__init__.py
    - パッケージメタ情報を追加（__version__ = "0.1.0"、__all__ の設定）。
  - 環境設定管理モジュール（src/kabusys/config.py）
    - .env ファイルまたは環境変数から設定値を読み込む仕組みを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により、CWD に依存しない自動 .env ロードを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。なお OS 環境変数は保護される（上書きされない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途向け）。
    - .env パーサを実装:
      - 空行・コメント行（# 開始）の無視。
      - export KEY=val 形式に対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
      - クォートなし値におけるインラインコメントの扱い（直前が空白/タブの場合をコメントと認識）。
    - 必須環境変数取得ヘルパ _require を実装（未設定時は ValueError）。
    - Settings クラスを公開:
      - J-Quants / kabuステーション / Slack / データベース関連設定をプロパティで取得。
      - デフォルトパス（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）。
      - KABUSYS_ENV（development, paper_trading, live）の検証。
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
      - is_live / is_paper / is_dev の簡易判定プロパティ。
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - ベース機能:
      - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
      - ページネーション対応（pagination_key の取得と繰り返し取得）。
      - レスポンスの JSON デコード時エラーを検出して例外化。
    - レート制御:
      - 固定間隔スロットリング (_RateLimiter) による 120 req/min 制約（最小間隔算出）。
    - リトライ/エラーハンドリング:
      - 指数バックオフによるリトライ（最大 3 回）。対象ステータス: 408、429、5xx、およびネットワークエラー。
      - 429 の場合、Retry-After ヘッダを優先して待機時間を決定。
      - ネットワークエラーや 5xx はバックオフで再試行。
    - 認証トークン管理:
      - get_id_token(refresh_token=None) でリフレッシュトークンから ID トークンを取得（POST /token/auth_refresh）。
      - モジュールレベルの ID トークンキャッシュを保持し、ページネーション間で共有。
      - 401 を受けた場合はトークンを1回だけ自動リフレッシュして再試行（無限再帰対策の allow_refresh フラグ）。
    - トレーサビリティ / 再現性:
      - データ取得時の fetched_at を UTC ISO 8601 形式で記録（Look-ahead Bias 防止）。
    - DuckDB への保存関数:
      - save_daily_quotes / save_financial_statements / save_market_calendar を実装。ON CONFLICT DO UPDATE により冪等性を実現。
      - PK 欠損行はスキップしログ出力。
      - 保存件数のログ出力。
    - 型変換ユーティリティ:
      - _to_float: 空値や変換失敗は None を返す。
      - _to_int: "1.0" 等を許容して float 経由で整数変換。小数部が0以外の場合は None を返す。
    - ロギング: 操作の情報・警告を logger で出力。
  - DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
    - 3 層（Raw / Processed / Feature）＋Execution 層のテーブル定義を実装。
    - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions。
    - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
    - Feature レイヤー: features, ai_scores。
    - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
    - 各テーブルに適切な型・制約（CHECK、PRIMARY KEY、FOREIGN KEY）を設定。
    - 頻出クエリに備えたインデックスを定義（銘柄×日付スキャン、ステータス検索等）。
    - init_schema(db_path) により DB ファイルの親ディレクトリ作成とテーブル/インデックスの作成を行い、DuckDB 接続を返す（冪等）。
    - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。
  - 監査ログ（トレーサビリティ）モジュール（src/kabusys/data/audit.py）
    - 監査用テーブル定義（signal_events, order_requests, executions）を実装。
    - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）を明確化。
    - order_request_id を冪等キーとし、二重発注防止を設計に組み込む。
    - すべての TIMESTAMP を UTC で保存するよう init_audit_schema が SET TimeZone='UTC' を実行。
    - order_requests における価格必須チェック（limit/stop の場面に応じた CHECK 制約）。
    - インデックスを複数定義（シグナル検索、status スキャン、broker_order_id, broker_execution_id など）。
    - init_audit_schema(conn) で既存接続に監査テーブルを追加（冪等）。
    - init_audit_db(db_path) で監査専用 DB を初期化して接続を返す。
  - パッケージ構造
    - 空のパッケージ初期化ファイルを追加（execution, strategy, monitoring, data の __init__.py を配置）。

Changed
-------
- 初回リリースのため該当なし。

Fixed
-----
- 初回リリースのため該当なし。

Removed
-------
- 初回リリースのため該当なし。

Notes / Migration
-----------------
- 最初に利用する際は .env または環境変数を正しく設定してください。主な必須キー:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で有用）。
- DuckDB の初期化は data.schema.init_schema() を使用してください。既存 DB に追加で監査テーブルを作る場合は data.audit.init_audit_schema(conn) を使用します。
- J-Quants API 呼び出しは rate limit（120 req/min）と再試行ロジックを組み込んでいますが、外部要因（API 仕様変更等）に注意してください。

ライセンス / 著作権
-----------------
- 本リリースに関するライセンス情報はリポジトリの LICENSE を参照してください。

----- End -----