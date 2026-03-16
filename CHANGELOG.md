# Changelog

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。

## [Unreleased]

（現在変更なし）

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。以下は主要な追加点と実装の要旨です。

### Added
- パッケージ基礎
  - パッケージトップを定義（src/kabusys/__init__.py）。バージョンを "0.1.0" に設定。
  - モジュール公開: data, strategy, execution, monitoring。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local からの自動環境変数ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーは export 形式、クォート（シングル/ダブル）およびバックスラッシュエスケープ、インラインコメントを正しく扱う実装を提供。
  - OS 環境変数を保護するための protected keys 機構と、.env と .env.local の優先順位（OS > .env.local > .env）を実装。
  - Settings クラスを提供し、以下の必須/既定値をプロパティで取得可能：
    - 必須（エラーを投げる）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値あり: KABU_API_BASE_URL (http://localhost:18080/kabusapi), DUCKDB_PATH (data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db)
    - KABUSYS_ENV の検証（development/paper_trading/live）、LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev 判定プロパティ

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出し共通処理を実装（_request）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408, 429, >=500）を実装。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時にはリフレッシュトークンから id_token を自動更新して 1 回リトライする仕組み。無限再帰防止のため allow_refresh 制御あり。
  - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）。
  - ページネーション対応のデータ取得関数：
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX 市場カレンダー）
  - DuckDB へ冪等に保存する save_* 関数を実装（ON CONFLICT DO UPDATE を使用）：
    - save_daily_quotes: raw_prices テーブルへ保存。fetched_at を UTC ISO 秒精度で記録。
    - save_financial_statements: raw_financials テーブルへ保存。fetched_at を記録。
    - save_market_calendar: market_calendar テーブルへ保存。HolidayDivision を is_trading_day / is_half_day / is_sq_day に変換。
  - 値変換ユーティリティ _to_float / _to_int を実装し、不正なフォーマットや空値を安全に処理。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DataPlatform の 3 層（Raw / Processed / Feature）＋ Execution 層に対応するテーブル群を DDL 定義として実装。
  - 主要テーブル（例）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - パフォーマンス向けのインデックス定義を提供（code × date、status 系等）。
  - init_schema(db_path) によりディレクトリ自動作成（必要時）、全テーブルおよびインデックスを冪等に作成して接続を返す。
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL のエントリ run_daily_etl を実装。処理順:
    1. 市場カレンダー ETL（先読み day: デフォルト 90 日）
    2. 株価日足 ETL（差分更新 + backfill。デフォルト backfill_days=3）
    3. 財務データ ETL（差分更新 + backfill）
    4. 品質チェック（quality モジュール。オプション）
  - 差分取得ロジック: DB の最終取得日から不足分のみ取得、date_from 未指定時は最終取得日 - backfill_days 相当で再取得（初回は 2017-01-01 を使用）。
  - ETLResult データクラスを導入し、各ステップの fetch/save カウント、品質問題、エラーを収集・返却。
  - 各ステップは独立して例外を捕捉（1 ステップ失敗でも他は継続）。ログおよび ETLResult.errors にエラー要約を記録。
  - 市場カレンダー取得後、_adjust_to_trading_day で target_date を直近の営業日に調整（最大 30 日遡り）。カレンダー未取得時は原値を返すフォールバック。

- 監査ログ（src/kabusys/data/audit.py）
  - シグナル → 発注 → 約定までの完全なトレーサビリティのための監査テーブル群を実装:
    - signal_events（戦略が生成したすべてのシグナルをログ）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（約定ログ、broker_execution_id をユニークキーにして冪等性を担保）
  - order_requests の制約: limit/stop/market に応じた価格必須チェック、signal_id FK（ON DELETE RESTRICT）、ステータス遷移を想定（pending/sent/filled/...）。
  - 全 TIMESTAMP は UTC 保存を前提とし、init_audit_schema / init_audit_db は SET TimeZone='UTC' を実行。
  - 監査用インデックス群を作成（status スキャン、戦略／日付検索、broker_id 関連検索など）。
  - init_audit_schema(conn) で既存 DuckDB 接続に監査テーブルを追加（冪等）。

- データ品質チェック（src/kabusys/data/quality.py）
  - QualityIssue データクラスを実装（check_name, table, severity, detail, rows）。
  - 以下のチェックを実装（DuckDB SQL ベース、パラメータバインド使用）:
    - check_missing_data: raw_prices の OHLC 欠損（open/high/low/close のいずれかが NULL）を検出（重大度：error）。
    - check_spike: 前日比スパイク検出（LAG を使った前日比算出、閾値デフォルト 0.5 = 50%）。
    - （設計文書に基づく）重複チェック、日付不整合検出等を想定（モジュール構成がそれらを実行可能に設計）。
  - 各チェックはサンプル行（最大 10 件）を返し、Fail-Fast ではなく全件収集を行う方針。

### Other notes / 設計上の特徴
- 冪等性重視:
  - DuckDB への挿入は ON CONFLICT DO UPDATE を用いて冪等に実行。
  - order_request_id / broker_execution_id 等で発注重複を防止する設計。
- トレーサビリティ:
  - データ取得時に fetched_at（UTC）を保存し、Look-ahead Bias を防止する設計。
  - 監査テーブルは削除を前提にせず（ON DELETE RESTRICT）、すべてのイベントを保持する方針。
- API 呼び出しの堅牢性:
  - レート制限、リトライ、401 自動リフレッシュ、ページネーション対応を備えたクライアント。
- テスト性:
  - id_token の注入可能性や KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化など、テストがしやすい設計。
- 日付／タイムゾーン:
  - 監査ログは UTC 固定。fetched_at なども UTC ISO 表記で保存。

### Known limitations / TODO
- strategy, execution, monitoring モジュールの実装は本リリースで骨格を置いているが、個別の戦略ロジックやブローカー統合の実装は今後の作業項目です（現状 src/kabusys/strategy/__init__.py と src/kabusys/execution/__init__.py は空）。
- 一部の品質チェック（重複・日付不整合など）は設計に沿って実装可能な状態にあるが、追加のチェックやアラートポリシーは今後拡張予定。

--- 

このリリースは基盤層（環境設定・データ取得・保存・スキーマ・ETL・監査・品質チェック）を中心に整え、上位の戦略・発注ロジックを実装するための安定した土台を提供します。