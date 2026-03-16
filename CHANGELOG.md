Keep a Changelog
=================

すべての重要な変更点をここに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

0.1.0 - 2026-03-16
------------------

Added
- 初回リリース: kabusys パッケージ（バージョン 0.1.0）。
  - パッケージ公開情報: src/kabusys/__init__.py に __version__ = "0.1.0"、パッケージ外部公開モジュールとして data, strategy, execution, monitoring を定義。
- 環境設定/読み込み機能（src/kabusys/config.py）
  - .env / .env.local の自動読み込みを実装（OS 環境変数を優先、.env.local は .env を上書き）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env のパースは export KEY=val 形式、クォート文字（'"/"）・バックスラッシュエスケープ・行内コメントの取り扱いに対応。
  - Settings クラスを提供。必須値取得（_require）や各種設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）、DuckDB/SQLite の既定パス、KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）を実装。
  - is_live / is_paper / is_dev のヘルパーを提供。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する API 呼び出し関数を実装: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - レート制限対応（120 req/min）: 固定間隔スロットリング RateLimiter を実装。
  - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408, 429, 5xx）。429 時は Retry-After ヘッダ優先。
  - 401 受信時は自動的にリフレッシュトークンで id_token を再取得して 1 回だけリトライ（無限再帰防止）。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead bias のトレーサビリティを確保。
  - DuckDB へ冪等に保存するための保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE による重複排除を行う。
  - 型安全な変換ユーティリティ _to_float / _to_int を提供（空値・変換失敗時は None、float 文字列からの int 変換では小数部非ゼロを除外）。
- データベーススキーマと初期化（src/kabusys/data/schema.py）
  - DataSchema に基づく DuckDB 用の DDL を多数定義（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions、prices_daily, market_calendar, fundamentals、features, ai_scores、signals, signal_queue, orders, trades, positions, portfolio_performance などを含むテーブル定義。
  - 頻出クエリのためのインデックス定義を含む。
  - init_schema(db_path) でディレクトリ作成 → DuckDB 接続 → テーブル・インデックス作成（冪等）を行う。get_connection() を併設。
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL の高レベルエントリ run_daily_etl を実装。処理順序: カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック。
  - 差分更新ロジック: DB の最終取得日から backfill_days 日分をさかのぼって再取得することで API の後出し修正を吸収（デフォルト backfill_days=3）。
  - カレンダーは target_day + lookahead_days（デフォルト 90 日）まで先読みして取得。
  - ETLResult dataclass を導入（取得数・保存数・品質問題・エラー一覧・ユーティリティメソッドを含む）。
  - 各ステップは独立して例外処理され、1 ステップ失敗でも他ステップは継続（全件収集型のエラーハンドリング）。
  - jquants_client の id_token を注入可能にしてテスト容易性を確保。
- 監査ログ（audit）スキーマ（src/kabusys/data/audit.py）
  - signal_events, order_requests, executions の監査テーブル群を定義し、init_audit_schema(conn) / init_audit_db(db_path) を提供。
  - order_request_id を冪等キーとして扱う、すべての TIMESTAMP を UTC で保存する方針（init で SET TimeZone='UTC' を実行）。
  - 発注・約定フローを UUID 連鎖でトレースするための制約・チェック（ステータス列、価格チェック、外部キー等）を実装。
- データ品質チェック（src/kabusys/data/quality.py）
  - QualityIssue dataclass を導入（check_name, table, severity, detail, rows）。
  - 実装されたチェック:
    - check_missing_data: raw_prices の OHLC 欠損を検出（volume は対象外）。問題は severity="error" として報告。
    - check_spike: LAG ウィンドウを用いて前日比スパイク（デフォルト閾値 50%）を検出。サンプル行を取得して QualityIssue を生成。
  - チェックは Fail-Fast ではなく全件収集し、呼び出し元が重大度に応じて対処を決定できる設計。

Changed
- （初版のため該当なし）パッケージ初期実装。

Fixed
- （初版のため該当なし）

Notes / 補足
- 保存時の主キー欠損行はスキップされ、スキップ件数をログ出力（warning）する。
- DuckDB の ON CONFLICT / インデックスを多用することで再実行可能な ETL（冪等性）を確保。
- jquants_client の内部トークンはモジュールレベルでキャッシュされ、ページネーション間で共有される。
- src/kabusys/strategy と src/kabusys/execution の __init__.py は存在するが、今回のリリースに含まれる具象実装は最小限（将来的な拡張ポイント）。

既知の制約 / 今後の改善ポイント
- quality モジュール内のチェックは拡張可能（重複チェック、日付不整合チェックなどは設計に記載されているが、実装の追加が今後の課題）。
- monitoring モジュールはパッケージ公開対象に含まれるが、今回のソースでは実装が確認できない（今後追加予定）。
- 外部 API エラーやネットワーク障害に対する観測・アラート連携（Slack 通知等）は設定値はあるが、実働通知の実装は別途実装が必要。

ライセンス
- 本リリースに関するソースコードはリポジトリ内の LICENSE（未提示）に従います。