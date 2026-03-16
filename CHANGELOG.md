CHANGELOG
=========

すべての重要な変更点は Keep a Changelog 形式で記載しています。  
このファイルはコードベースから推測して作成した初回リリース向けの変更履歴です。

[Unreleased]
------------

- （無し）

0.1.0 - Initial release
-----------------------

Added
- 新規パッケージ「kabusys」を追加（日本株自動売買システムの初期実装）。
  - パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0"。

- 設定管理（kabusys.config）
  - .env ファイルと環境変数から設定を自動読み込みする機能を追加。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない自動読み込みを実現。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
  - .env パーサに以下の対応を実装:
    - export KEY=val 形式のサポート。
    - シングル／ダブルクォートされた値のバックスラッシュエスケープ処理。
    - クォートなし値でのインラインコメント認識（直前がスペース/タブの場合のみ）。
  - Settings クラスを提供（環境変数から値を取得するプロパティ群）。
    - J-Quants / kabu ステーション / Slack / データベースパス（DuckDB/SQLite）など主要設定を型安全に取得。
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証を実装。
    - is_live / is_paper / is_dev の利便性プロパティを追加。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装。
    - レート制限を守る固定間隔スロットリング（120 req/min, RateLimiter）。
    - 再試行ロジック（指数バックオフ, 最大3回）、対象ステータス: 408/429/5xx。
    - 401 受信時の ID トークン自動リフレッシュを1回だけ行う仕組み。
    - トークンのモジュールレベルキャッシュ（ページネーション処理で共有）。
    - JSON デコード失敗時の明確なエラー。
  - API のデータ取得関数を実装:
    - fetch_daily_quotes（OHLCV 日足、ページネーション対応）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPXマーケットカレンダー）
  - DuckDB への保存関数を実装（冪等性: ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
    - all 保存時に fetched_at を UTC ISO8601（Z）で記録
  - 変換ユーティリティを追加:
    - _to_float / _to_int（空値や不正な形式に寛容に変換）

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - 3層（Raw / Processed / Feature）+ Execution 層のテーブル定義を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK / FOREIGN KEY）やインデックスを用意し、頻出クエリを想定したインデックスを作成。
  - init_schema(db_path) によりディレクトリ自動作成と冪等なテーブル作成を実行。
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない旨を明記）。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL エントリ run_daily_etl を実装（市場カレンダー → 株価 → 財務 → 品質チェックの順）。
  - 差分更新ロジックを実装:
    - DB の最終取得日から差分を計算し、デフォルトで backfill_days=3 により後出し修正を吸収。
    - 市場カレンダーは lookahead_days=90 で先読み。
    - 取得対象日が非営業日の場合に直近の営業日に調整するヘルパーを追加。
  - 個別ジョブ: run_calendar_etl, run_prices_etl, run_financials_etl（それぞれ差分・ページネーション対応）。
  - ETL 実行結果を保持する ETLResult dataclass を実装（品質問題リスト、エラーリスト、has_errors 等の補助プロパティ、辞書化メソッド to_dict）。

- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定 を UUID 連鎖でトレースする監査テーブル群を実装。
    - signal_events（戦略シグナルログ）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ、各種 CHECK 制約）
    - executions（証券会社側約定ログ、broker_execution_id をユニーク冪等キーとして扱う）
  - 全 TIMESTAMP を UTC で保存するための SET TimeZone='UTC' を実行（init 関数内）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。
  - 監査用のインデックスも用意。

- データ品質チェック（kabusys.data.quality）
  - DataPlatform に基づく品質チェック機能を実装。
    - check_missing_data: raw_prices の OHLC 欠損検出（必須カラムの NULL を検出、重大度 error）。
    - check_spike: 前日比スパイク検出（LAG を使った変動率判定、デフォルト閾値 50%）。
    - QualityIssue dataclass によりチェック名・重大度・サンプル行を返す設計。
  - SQL を用いて効率的に検出し、Fail-Fast ではなく全件収集する方針。

Other
- ドキュメント参照をコード内に記載（DataPlatform.md, DataSchema.md 等）し、設計意図を明示。
- テスト容易性のため、ETL やクライアント関数で id_token を引数注入できる設計。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- API トークンの自動リフレッシュ処理は allow_refresh フラグで無限再帰を防止（get_id_token 呼び出し時など）。  

Notes / 注意事項
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされます。
- DuckDB のデフォルトパスは data/kabusys.duckdb、SQLite のデフォルトは data/monitoring.db（Settings で上書き可能）。
- run_daily_etl は各ステップで例外を捕捉して継続するため、部分的に失敗しても全体処理のログ・結果を返します。重大な品質問題は ETLResult.has_quality_errors で判断できます。

--- 

この CHANGELOG はコードベースの構造と docstring・コメントから推測して作成しています。実際のリリース作業時にはリリース日・差分の詳細（コミットやチケット番号等）を追記してください。