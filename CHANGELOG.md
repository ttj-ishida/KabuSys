CHANGELOG.md
=============

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。  

Unreleased
----------
（なし）

0.1.0 - 2026-03-16
-----------------
初回公開リリース。

Added
- パッケージ基盤
  - パッケージバージョンを設定: kabusys __version__ = 0.1.0
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を公開

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込みをプロジェクトルート（.git または pyproject.toml）から行う機能を追加
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能
  - .env 行パーサを実装（コメント、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープの取り扱い、インラインコメントの扱い等に対応）
  - 環境変数の上書き制御（override と protected による既存 OS 環境変数保護）
  - Settings クラスを追加してアプリ設定をプロパティ経由で提供
    - 必須値のバリデーション（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等を必須として ValueError を送出）
    - デフォルト値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）のサポート
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の検証ユーティリティ
    - is_live / is_paper / is_dev のブールプロパティ

- J-Quants クライアント (kabusys.data.jquants_client)
  - API ベース URL とデータ取得関数を実装
    - fetch_daily_quotes: 日次株価（OHLCV）のページネーション対応取得
    - fetch_financial_statements: 四半期財務データのページネーション対応取得
    - fetch_market_calendar: JPX マーケットカレンダー取得
  - 認証トークン取得: get_id_token を実装（refresh token から idToken を取得）
  - HTTP レイヤーでの堅牢性
    - 固定間隔スロットリングによるレート制限遵守（120 req/min）
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）
    - 401 時はトークン自動リフレッシュして 1 回リトライ（無限再帰を防止）
    - タイムアウトや JSON デコード失敗時の明示的な例外化
  - モジュールレベルでの id_token キャッシュ（ページネーション間共有）
  - DuckDB への保存ユーティリティ（冪等）
    - save_daily_quotes / save_financial_statements / save_market_calendar: ON CONFLICT DO UPDATE による重複排除
    - fetched_at を UTC ISO8601（Z）で記録
    - PK 欠損行のスキップとログ出力
    - データ型変換補助関数 (_to_float, _to_int) を実装（変換ルールを明確化）

- DuckDB スキーマ (kabusys.data.schema)
  - DataPlatform の 3 層（Raw / Processed / Feature）＋ Execution Layer に基づくテーブル定義を実装
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（NOT NULL / CHECK / PRIMARY KEY / FOREIGN KEY）を付与
  - 頻出クエリ向けのインデックスを定義
  - init_schema(db_path) による初期化（冪等、親ディレクトリ自動作成対応）と get_connection を提供

- ETL パイプライン (kabusys.data.pipeline)
  - run_daily_etl による日次 ETL パイプラインを実装（カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）
  - 差分更新ロジック
    - DB 側の最終取得日から差分のみ取得（未取得時は初期日付から取得）
    - backfill_days による再取得で後出し修正を吸収する設計（デフォルト 3 日）
    - 市場カレンダーは lookahead で先読み（デフォルト 90 日）
  - run_prices_etl / run_financials_etl / run_calendar_etl を個別に提供
  - ETLResult クラスを導入して取得数・保存数・品質問題・エラーを構造化して返却
  - 個々のステップは独立して例外処理され、一部失敗しても他ステップを継続する設計（Fail-Fast ではない）

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - signal_events, order_requests, executions の監査テーブルを実装
  - UUID ベースのトレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）
  - order_request_id を冪等キーとして扱う設計、注文種別に応じた価格チェック（limit/stop/market のチェック）
  - すべての TIMESTAMP を UTC で保存するための SET TimeZone='UTC' を初期化時に実行
  - init_audit_schema(conn) / init_audit_db(db_path) を提供
  - 監査用インデックス群を追加（status / date/code / broker_order_id 等での検索高速化）

- データ品質チェック (kabusys.data.quality)
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）
  - 実装済チェック
    - check_missing_data: raw_prices の OHLC 欠損検出（これを重大エラー扱い）
    - check_spike: 前日比によるスパイク検出（LAG ウィンドウ関数を使用、デフォルト閾値 50%）
  - SQL ベースで DuckDB を直接クエリして効率的に検出、すべてのチェックは問題の全件収集を行う（Fail-Fast ではない）
  - run_all_checks の呼び出しを想定した設計（pipeline から利用）

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数（トークン等）は Settings で必須チェックを行い、.env の自動読み込みは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）としてテストや CI での誤用を緩和

Notes / Known limitations
- 実際の API 呼び出しは urllib をベースにしており、より高度な HTTP クライアント（requests, httpx など）へ移行すると利便性が上がる可能性あり
- DuckDB の制約・インデックスは設計上設定してあるが、運用データ量やクエリパターンに応じてチューニングが必要
- quality モジュールはチェックを増やす拡張性を想定しているが、現時点のチェックは raw_prices を中心としている

---------------------------------------------------------------------------
参照
- パッケージエントリ: src/kabusys/__init__.py (__version__ = "0.1.0")
- 主なモジュール: src/kabusys/config.py, src/kabusys/data/*.py

以上。