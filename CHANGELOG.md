CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。
セマンティック バージョニングを使用します。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-15
--------------------

Added
- 初期リリースを追加。
  - パッケージメタ情報
    - kabusys パッケージの __version__ を 0.1.0 に設定し、公開サブパッケージとして data, strategy, execution, monitoring をエクスポート。

  - 環境設定 / ロード (kabusys.config)
    - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機構を実装。
      - プロジェクトルートの検出は __file__ の親階層を .git または pyproject.toml で探索して行うため、CWD に依存しない設計。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で利用）。
    - .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメントの取り扱いなどに対応）。
    - 環境変数の保護（既存 OS 環境変数を保護する protected set）と override ロジックを実装。
    - Settings クラスを公開:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得するヘルパー。
      - KABUSYS_API_BASE_URL のデフォルト、DB パス設定（DUCKDB_PATH, SQLITE_PATH）のデフォルト、環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証ロジック。
      - is_live / is_paper / is_dev の便宜プロパティ。

  - J-Quants API クライアント (kabusys.data.jquants_client)
    - API 呼び出しユーティリティを実装（_request）。
      - ベース URL は https://api.jquants.com/v1。
      - レート制限 (120 req/min) を守るための固定間隔スロットリング実装（_RateLimiter）。
      - リトライロジック（最大 3 回、指数バックオフ、ステータス 408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
      - 401 Unauthorized を検出した場合、リフレッシュトークンで id_token を自動再取得して最大 1 回リトライ（無限再帰を防止）。
      - ページネーション対応（pagination_key を用いたループ）およびモジュールレベルの id_token キャッシュ共有。
    - 認証ユーティリティ get_id_token を実装（refreshtoken を POST）。
    - データ取得関数を実装:
      - fetch_daily_quotes: 株価日足（OHLCV）のページネーション取得。
      - fetch_financial_statements: 四半期財務データのページネーション取得。
      - fetch_market_calendar: JPX マーケットカレンダーの取得。
      - すべての取得関数は取得件数ログ出力や pagination_key の二重取得回避を行う。
    - DuckDB へ保存する関数を実装（冪等保存を保証する ON CONFLICT DO UPDATE を利用）:
      - save_daily_quotes: raw_prices テーブルへ保存（fetched_at を UTC ISO8601 で記録）。
      - save_financial_statements: raw_financials テーブルへ保存（fetched_at を記録）。
      - save_market_calendar: market_calendar テーブルへ保存（HolidayDivision を解釈し is_trading_day / is_half_day / is_sq_day を設定）。
      - PK 欠損レコードはスキップし、スキップ件数をログ出力。
    - 入出力変換ユーティリティ:
      - _to_float / _to_int: 型安全に変換。_to_int は "1.0" のようなケースを許容するが小数部が 0 以外の場合は None を返す仕様。

  - DuckDB スキーマ定義・初期化 (kabusys.data.schema)
    - DataLayer に基づく包括的な DDL を追加:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - テーブル制約・チェック（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を詳細に定義。
    - よく使うクエリ向けのインデックスを定義。
    - init_schema(db_path) を実装: 親ディレクトリ自動作成、すべてのテーブル・インデックスを作成（冪等）。
    - get_connection(db_path) を提供（既存 DB への接続。初回は init_schema を推奨）。

  - 監査ログ・トレーサビリティ (kabusys.data.audit)
    - 監査トレース用テーブルを実装（DataPlatform.md に準拠）:
      - signal_events: 戦略が生成したシグナルを全て記録（ステータスや拒否理由を含む）。
      - order_requests: 発注要求ログ（order_request_id を冪等キーとして扱う。limit/stop のチェック制約あり）。
      - executions: 証券会社からの約定情報を記録（broker_execution_id を固有キーとして冪等を担保）。
    - 監査テーブル用のインデックス群を定義（検索・結合効率化）。
    - init_audit_schema(conn) および init_audit_db(db_path) を実装。全 TIMESTAMP を UTC で保存するために初期化時に "SET TimeZone='UTC'" を実行。

  - その他
    - モジュール構成: data パッケージ下に jquants_client, schema, audit を含む実装を追加。strategy, execution, monitoring パッケージのプレースホルダを追加。
    - ロギング箇所を適所に実装して動作ログ・警告を出力。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes
- 設計上の注意点:
  - J-Quants から取得したデータの fetched_at は UTC で記録され、Look-ahead Bias の追跡に利用可能。
  - DuckDB への保存は冪等化されており、既存レコードは ON CONFLICT で上書きされる。
  - 監査ログは原則削除しない運用を想定（ON DELETE RESTRICT の制約を利用）。
- 今後の予定（例）:
  - strategy / execution / monitoring の具象実装（シグナル生成・ポートフォリオ最適化・発注経路など）。
  - テストカバレッジの追加、CI 用設定、外部 API 呼び出しのモック化ヘルパー。