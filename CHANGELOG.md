CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングに従います。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-16
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - src/kabusys/__init__.py にてパッケージを公開（サブパッケージ: data, strategy, execution, monitoring）。
- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込み（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - プロジェクトルート判定: __file__ を起点に .git または pyproject.toml を探索してルートを特定（CWD に依存しない実装）。
  - .env パーサー強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、無効行スキップ等。
  - .env 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数を protected として上書きを防止。
  - Settings クラスでアプリケーション設定をプロパティ経由で提供。必須環境変数は _require() で検査して未設定時に ValueError を送出。
  - デフォルト値とバリデーション: KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL の検証、データベースパスの Path 変換（duckdb/sqlite）。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - レート制御: 固定間隔スロットリング実装（120 req/min を守る _RateLimiter）。
  - リトライ戦略: 指数バックオフによるリトライ（最大試行回数 3、408/429/5xx 対象）。429 の場合は Retry-After を優先。
  - 認証: リフレッシュトークンから id_token を取得する get_id_token、ID トークンのモジュールレベルキャッシュと自動リフレッシュ（401 で 1 回だけ再取得してリトライ）。
  - Look-ahead bias 防止: データ保存時に fetched_at を UTC タイムスタンプで記録。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性を確保し、PK 欠損行をスキップしてログ出力。
  - データ変換ユーティリティ _to_float / _to_int を実装（安全な None ハンドリング、"1.0" のような文字列 float を int に変換する際の丸め防止ロジック等）。
- DuckDB スキーマ / 初期化（src/kabusys/data/schema.py）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を DDL として実装。
  - 主要テーブルを含む多数の CREATE TABLE 文を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - クエリパターンを考慮したインデックス群（例: prices_daily(code, date), signal_queue(status), orders(status) 等）を追加。
  - init_schema(db_path) によるディレクトリ自動作成、DDL 実行、インデックス作成、DuckDB 接続返却（:memory: もサポート）。get_connection() で既存 DB に接続可能。
- 監査ログスキーマ（src/kabusys/data/audit.py）
  - シグナル → 発注 → 約定へと連鎖する監査テーブルを実装（signal_events, order_requests, executions）。
  - 冪等キー（order_request_id）や broker_execution_id の一意性等、監査用途に応じた制約を設定。
  - order_requests のチェック制約（order_type に応じた limit_price / stop_price の必須制御）や FK（ON DELETE RESTRICT）を採用し履歴削除を防止。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。すべての TIMESTAMP を UTC で保存するために SET TimeZone='UTC' を実行。
  - 監査用インデックス群を追加（status 検索、signal_id / broker_order_id などの高速検索用）。
- データ品質チェック（src/kabusys/data/quality.py）
  - DataPlatform.md に基づく品質チェック群を実装:
    - check_missing_data: raw_prices の OHLC 欠損検出（必須カラムの NULL 検出）。
    - check_spike: 前日比スパイク検出（LAG を用いた変動率判定、デフォルト閾値 50%）。
    - check_duplicates: 主キー重複（date, code）の検出。
    - check_date_consistency: 将来日付検出 / market_calendar と非営業日の整合性検査（market_calendar がない場合はスキップ）。
    - run_all_checks: 上記チェックをまとめて実行し QualityIssue のリストを返却。
  - QualityIssue データクラスを定義し、各チェックは問題のサンプル行（最大 10 件）を返す設計。重大度（error / warning）を区別。
  - SQL はパラメータバインド（?）を使用しインジェクションリスクを低減。
- プレースホルダ/パッケージ構成
  - src/kabusys/strategy, src/kabusys/execution, src/kabusys/monitoring に初期 __init__ を設置してサブパッケージ構成を確立（実装は個別モジュールで追加予定）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 環境変数の自動ロードで OS 環境変数を保護する仕組み（protected set）を導入。これにより外部 .env ファイルが既存の OS 環境変数を不用意に上書きすることを防止。
- .env 自動ロードを明示的に無効化できる KABUSYS_DISABLE_AUTO_ENV_LOAD を用意（テストや CI 用）。

Notes / Implementation details
- J-Quants API クライアントはネットワークエラー・HTTP エラーに対して慎重にリトライを行うよう実装されていますが、本番運用ではモニタリング（メトリクス・アラート）を併設することを推奨します。
- DuckDB スキーマでは外部キー等の制約を多用していますが、パフォーマンス要件に応じてインデックス・DDL の最適化が必要になる可能性があります。
- 全ての TIMESTAMP は UTC 想定（監査ログモジュールで明示的に SET TimeZone='UTC' を実行）。アプリ側でも UTC を前提に扱うことを推奨します。

Authors
- 初期実装（コードベースに基づく CHANGELOG 作成）

License
- リポジトリの LICENSE を参照してください。