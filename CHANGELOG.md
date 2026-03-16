CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」フォーマットに準拠します。

[未リリース]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-16
-------------------

初回公開リリース。日本株自動売買システムのコア基盤を実装しました。主要な追加点と設計方針は以下の通りです。

Added
-----

- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0, 公開サブパッケージ: data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよびOS環境変数からの設定読み込み機能を実装。
  - プロジェクトルート探索: __file__ を起点に .git または pyproject.toml を検出してプロジェクトルートを特定（カレントワーキングディレクトリに依存しない自動読み込み）。
  - .env パーサ:
    - export KEY=val 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ処理、インラインコメントの扱いを実装。
    - クォート無しの行では # の前に空白がある場合のみコメントと認識。
  - 自動ロード順序: OS環境 > .env.local > .env。既存OS環境は保護（protected）され、.env.local は上書きを許可。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト等用）。
  - Settings クラス:
    - J-Quants / kabuステーション / Slack / DBパス 等のプロパティを提供。
    - KABUSYS_ENV と LOG_LEVEL の検証（有効値チェック）。
    - duckdb/sqlite 用のデフォルトパス展開、is_live/is_paper/is_dev の便利プロパティ。
  - 必須キー取得ヘルパー _require()（未設定時に ValueError を送出）。

- J-Quants クライアント（kabusys.data.jquants_client）
  - API 呼び出し共通処理を実装:
    - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
    - リトライ（指数バックオフ、最大3回）、対象ステータス 408, 429, 5xx。
    - 429 の場合は Retry-After ヘッダ優先。
    - 401 受信時はリフレッシュトークンから id_token を再取得して 1 回だけ再試行（無限再帰防止）。
    - ページネーション対応。ページ間で共有される id_token のモジュールレベルキャッシュ。
    - JSON デコードエラーやネットワークエラーに対する適切な例外ラップ。
  - 取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - 保存関数（DuckDB 向け、冪等設計）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - ON CONFLICT DO UPDATE を用いた upsert により重複を排除（冪等性保証）。
    - fetched_at を UTC タイムスタンプ（ISO8601 Z）で記録し、Look-ahead Bias のトレースを可能に。
  - ユーティリティ: _to_float, _to_int（厳密な数値変換・空値ハンドリング）。

- DuckDB スキーマ定義（kabusys.data.schema）
  - 3層（Raw / Processed / Feature）＋ Execution 層に基づく詳細な DDL を実装。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤー。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed レイヤー。
  - features, ai_scores を含む Feature レイヤー。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等の Execution レイヤー。
  - 頻出クエリに対するインデックス定義を多数追加（code/date, status, order_id 等）。
  - init_schema(db_path)：ファイルパスの親ディレクトリ自動作成、テーブル作成（冪等）。
  - get_connection(db_path)：既存 DB への接続を返す（初期化は行わない）。

- データ ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL 処理のエントリポイント run_daily_etl を実装（市場カレンダー → 株価 → 財務 → 品質チェック の順）。
  - 差分更新ロジック:
    - DB の最終取得日からの差分取得（backfill_days により数日前から再取得して後出し修正を吸収）。
    - run_prices_etl, run_financials_etl, run_calendar_etl を個別に実装。
    - calendar は先読み（lookahead_days、デフォルト90日）して営業日調整に利用。
  - ETLResult データクラス:
    - 各ステップの取得/保存数、品質問題リスト、エラーメッセージを格納。has_errors / has_quality_errors 等の補助プロパティ、辞書化メソッドを提供。
  - エラーハンドリング方針:
    - 各ステップは独立して例外処理（1ステップ失敗でも他ステップ継続）。
    - 品質チェックは Fail-Fast ではなく全件収集し、呼び出し側が判断可能。

- 品質チェック（kabusys.data.quality）
  - QualityIssue データクラスを導入（check_name, table, severity, detail, rows）。
  - 実装されたチェック:
    - check_missing_data：raw_prices における OHLC 欠損検出（欠損はエラー扱い）。
    - check_spike：前日比によるスパイク検出（デフォルト閾値 50%）。
  - DuckDB 上で効率的に SQL 実行し、サンプル行（最大10件）を返すデザイン。
  - エラーの重大度（"error" / "warning"）に基づく分類。

- 監査ログ / トレーサビリティ（kabusys.data.audit）
  - signal_events, order_requests, executions の監査テーブルを実装。
  - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）を想定。
  - order_request_id を冪等キーとして設計（重複防止）。
  - 全 TIMESTAMP は UTC で保存するよう init_audit_schema が SET TimeZone='UTC' を実行。
  - init_audit_db(db_path)：監査用 DB の初期化用ユーティリティ提供。
  - 各種制約（CHECK、FOREIGN KEY）、ステータス遷移の設計方針、インデックスを追加。

Changed
-------

- 新規リリースのため該当なし。

Fixed
-----

- 新規リリースのため該当なし。

Security
--------

- 認証情報の取り扱い:
  - J-Quants リフレッシュトークンは settings.jquants_refresh_token 経由で必須取得。自動 .env ロードは保護されたOS環境変数を上書きしない設計。
  - id_token の自動リフレッシュは 401 の場合に限定して 1 回のみ実行し、無限再帰を回避。

Notes
-----

- 本リリースは基盤実装に注力しており、戦略ロジック（strategy パッケージ）や発注実装（execution パッケージ）の具体的な実装は含まれていません（パッケージ空 __init__ を用意）。
- jquants_client の HTTP 呼び出しは urllib を直接利用しており、上位でのセッション共有や非同期化は将来の改良候補です。
- DuckDB スキーマは現時点で要求される整合性チェックやインデックスを備えていますが、実運用でのクエリプロファイルに応じて追加調整が推奨されます。

Authors
-------

- 実装元のコードに基づき自動生成（コードコメントと設計文書節に沿って記載）。

ライセンス
---------

- ソースコードのライセンス情報はリポジトリ内の LICENSE ファイルを参照してください。