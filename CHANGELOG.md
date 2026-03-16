# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングに基づいています。  

[Unreleased]

[0.1.0] - 2026-03-16
--------------------

Added
- パッケージ初期リリース。日本株自動売買システム「KabuSys」のコアモジュールを追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py: __version__ = "0.1.0"、サブモジュール公開（data, strategy, execution, monitoring）。

- 環境設定管理
  - src/kabusys/config.py:
    - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント処理）。
    - override/protected 機能により OS 環境変数の保護や .env.local による上書きをサポート。
    - Settings クラスでアプリ設定を提供（J-Quants refresh token、kabu API password、Slack トークン/チャンネル、DB パス等）。
    - KABUSYS_ENV と LOG_LEVEL のバリデーション（有効値チェック）と is_live/is_paper/is_dev のヘルパーを追加。

- データ取得クライアント（J-Quants）
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアントを実装。株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得に対応。
    - レート制限対応（120 req/min 固定スロットリング）を実装する RateLimiter を導入。
    - 冪等なページネーション処理を実装（pagination_key を利用、ページ間でトークンを共有するキャッシュ）。
    - 再試行（リトライ）ロジックを導入：指数バックオフ、最大 3 回、対象ステータス（408, 429, 5xx）。
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（再帰防止フラグあり）。
    - id_token キャッシュ機構（ページネーション間で共有）を実装。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供。
    - save_daily_quotes / save_financial_statements / save_market_calendar により DuckDB へ保存（ON CONFLICT DO UPDATE による冪等性）。
    - 保存時に必須 PK 欠損行はスキップしてログ出力し、fetched_at（UTC）を記録。
    - _to_float / _to_int 等のユーティリティで型変換と厳格な変換ルールを定義（例: 小数を伴う数値の整数変換は無効化）。

- DuckDB スキーマ定義・初期化
  - src/kabusys/data/schema.py:
    - DataPlatform 設計に基づく多層スキーマ定義（Raw / Processed / Feature / Execution 層）。
    - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
    - features, ai_scores 等の Feature テーブル。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
    - パフォーマンス向けに想定クエリ向けのインデックスを作成。
    - init_schema(db_path) によるディレクトリ自動作成、DDL の冪等実行、DuckDB 接続返却を提供。
    - get_connection(db_path) による既存 DB 接続取得（初期化は行わない旨を明示）。

- ETL パイプライン
  - src/kabusys/data/pipeline.py:
    - 日次 ETL パイプラインを実装（run_daily_etl）。
    - 処理フロー：市場カレンダー → 株価日足 → 財務データ → 品質チェック（オプション）。
    - 差分更新ロジック：DB の最終取得日から未取得分のみを取得。backfill_days（デフォルト 3 日）で後出し修正を吸収。
    - 市場カレンダーは先読み（lookahead_days デフォルト 90 日）で取得し、営業日調整に利用。
    - 各 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）は独立してエラーハンドリングし、1 ステップ失敗でも他は継続（エラーは収集して返却）。
    - ETLResult データクラスを追加し、取得数・保存数・品質問題・エラーを集計可能。
    - _adjust_to_trading_day により target_date が非営業日の場合、直近（最大 30 日遡り）の営業日に調整。

- 監査ログ（トレーサビリティ）
  - src/kabusys/data/audit.py:
    - シグナル → 発注要求 → 約定 のフローを UUID 連鎖でトレースする監査テーブルを定義。
    - signal_events（戦略生成ログ）、order_requests（冪等キー付き発注要求）、executions（約定ログ）を提供。
    - order_requests には order_request_id を冪等キーとして定義。注文種別ごとのチェック制約（limit/stop/market）あり。
    - init_audit_schema(conn) / init_audit_db(path) により監査スキーマを初期化。すべての TIMESTAMP を UTC 保存する設定を行う（SET TimeZone='UTC'）。
    - 監査用のインデックスも作成。

- データ品質チェック
  - src/kabusys/data/quality.py:
    - DataPlatform に基づく品質チェック実装。
    - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
    - check_missing_data: raw_prices における OHLC 欠損検出（volume は許容）を実装。サンプル行と件数を返却。
    - check_spike: 前日比スパイク検出（デフォルト閾値 50%）を実装。LAG ウィンドウを使った SQL ベースの検出。
    - 各チェックは Fail-Fast ではなく問題を全件収集して返却。SQL はパラメータバインドを使用していることを明記。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 要件
- Python バージョン: ソース内の型注釈（| を使った union）やその他構文から Python 3.10+ を想定。
- 依存: duckdb（DuckDB Python バインディング）、標準ライブラリの urllib、json、logging 等。
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等は Settings で必須化されているため、実行環境に設定が必要。
- DuckDB パスのデフォルト:
  - DUCKDB_PATH: data/kabusys.duckdb（ユーザのホーム展開をサポート）
  - SQLITE_PATH: data/monitoring.db（監視/Slack 等の目的で使用想定）
- セキュリティ: トークン取得・自動リフレッシュのロジック実装に注意。id_token のキャッシュはモジュールレベルで保持される。

Upgrade / Migration Notes
- 初回リリースのためアップグレード注意点はなし。

今後の予定（想定）
- strategy / execution / monitoring の具体的実装の追加（現在はパッケージ構造のみ用意）。
- 監査テーブルへの書き込みユーティリティ、発注コネクタ（kabu API 連携）の実装。
- 追加の品質チェック（重複チェック、日付不整合検出の詳細実装など）とアラート連携。