CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" と Semantic Versioning を想定しています。

[Unreleased]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-16
-------------------

Added
- 初期リリース。パッケージ名: kabusys、バージョン 0.1.0 を導入。
- パッケージ構成（モジュール骨格）を追加:
  - kabusys (トップレベル)
  - kabusys.config: 環境変数・設定管理
  - kabusys.data: データ取得・スキーマ・監査・品質チェック
  - kabusys.execution, kabusys.strategy, kabusys.monitoring: プレースホルダ（パッケージ初期化ファイル）
- 環境設定・自動 .env ロード機能 (kabusys.config):
  - プロジェクトルートの検出ロジック（.git または pyproject.toml を起点に探索）。
  - .env / .env.local の自動読み込み（優先度: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応（テスト用）。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（スペース/タブ直前の #）等に対応。
  - settings オブジェクトで以下の主要設定を公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live 検証）と LOG_LEVEL（DEBUG/INFO/... 検証）
    - is_live / is_paper / is_dev ヘルパー
  - 必須環境変数未設定時は ValueError を送出する _require() を実装。

- J-Quants API クライアント (kabusys.data.jquants_client):
  - API 呼び出しユーティリティ _request を実装（JSON パース、タイムアウト、エラーハンドリング）。
  - レート制限制御: 固定間隔スロットリングによる 120 req/min 制約 (_RateLimiter)。
  - リトライロジック: 指数バックオフ、最大再試行回数 3、対象ステータス 408/429/5xx をリトライ。
  - 401 受信時は自動でリフレッシュトークンを使って id_token を更新して 1 回だけリトライ（無限再帰防止）。
  - モジュールレベルの id_token キャッシュをページネーション間で共有。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes: 日足（OHLCV）
    - fetch_financial_statements: 四半期財務データ
    - fetch_market_calendar: JPX マーケットカレンダー
  - DuckDB へ保存する冪等的な保存関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - 各関数は fetched_at を UTC タイムスタンプで付与し、ON CONFLICT DO UPDATE による更新を行う。
  - ユーティリティ関数: _to_float / _to_int（安全な型変換。float 文字列からの int 変換で非ゼロ小数部は None を返す等のルールを明示）。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema):
  - 3 層＋実行層のスキーマを定義（Raw / Processed / Feature / Execution）。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）を設定。
  - 頻出クエリ向けのインデックスを作成（code, date、status、signal_id など）。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成およびテーブル作成を行う（冪等）。
  - get_connection() で既存 DB へ接続可能。

- 監査ログ（トレーサビリティ）スキーマ (kabusys.data.audit):
  - signal_events, order_requests (冪等キー order_request_id), executions を定義。
  - 監査設計方針を反映（UUID 連鎖、created_at/updated_at、UTC タイムゾーン）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。init_audit_schema は SET TimeZone='UTC' を実行。
  - インデックスを追加して戦略別・日付別検索や status ベースのキュー検索を効率化。

- データ品質チェックモジュール (kabusys.data.quality):
  - DataPlatform に基づく品質チェック関数群:
    - check_missing_data: raw_prices の OHLC 欠損検出（必須カラムの欠損。volume は対象外）。
    - check_spike: 前日比スパイク検出（LAG ウィンドウ、デフォルト閾値 50%）。
    - check_duplicates: 主キー重複検出（date, code）。
    - check_date_consistency: 将来日付チェック／market_calendar との整合性チェック（非営業日データ検出）。
    - run_all_checks: 上記をまとめて実行し QualityIssue のリストを返す。
  - 各チェックは QualityIssue dataclass（check_name, table, severity, detail, rows）を返す。複数結果を収集する Fail-not-Fast 方針。
  - SQL はパラメータバインド（?）で実行し、DuckDB 接続を受け取る設計。

Security / Reliability
- 環境変数自動ロード時に OS 環境変数を保護する仕組み（protected set）を導入。
- API クライアントはネットワーク障害・HTTP エラーに対して明確なリトライ・バックオフ戦略を実装。
- 監査ログでは削除を想定しない設計（ON DELETE RESTRICT）でトレーサビリティを確保。

Notes
- このリリースは実装の初期段階に相当し、多くの機能は DB スキーマ定義・クライアント・品質チェックの骨格を提供します。発注実行ロジックや戦略本体、外部ブローカーとの接続／コールバック処理等は今後追加・拡張される想定です。
- DuckDB 関連操作は duckdb パッケージに依存します。
- J-Quants のトークン取得や API 呼び出しには適切な環境変数（JQUANTS_REFRESH_TOKEN 等）が必要です。設定が不足すると起動時または呼び出し時に例外が発生します。

[リンク]
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/