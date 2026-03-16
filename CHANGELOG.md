# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

全般的な方針:
- 日付はリリース日を示します。
- 各項目は大まかな機能追加・変更・修正を分かりやすくまとめています。
- 実装の設計意図・注意点（ETLの差分更新・冪等性・トレーサビリティ等）も注記しています。

## [0.1.0] - 2026-03-16

Added
- 初期リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。
  - パッケージ構成
    - kabusys パッケージとサブモジュール（data, strategy, execution, monitoring）の基本構成を追加。
  - 環境設定 / 設定管理（src/kabusys/config.py）
    - .env ファイルおよび環境変数から設定を自動読み込みする機能を追加。
    - プロジェクトルート探索（.git または pyproject.toml を基準）により CWD に依存しない自動読み込みを実装。
    - .env と .env.local の優先順位をサポート（OS 環境変数は保護）。
    - export プレフィックス、シングル/ダブルクォートやエスケープ、インラインコメントなど多様な .env 文法を考慮したパーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化（テスト用途）をサポート。
    - Settings クラスで必須設定の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）や
      DB パス（DUCKDB_PATH, SQLITE_PATH）・環境（KABUSYS_ENV）・ログレベル（LOG_LEVEL）のバリデーションを実装。

  - J-Quants クライアント（src/kabusys/data/jquants_client.py）
    - API からのデータ取得機能を実装（株価日足、四半期財務データ、JPX マーケットカレンダー）。
    - レート制限（120 req/min）を守る固定間隔スロットリングを実装（RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回）を実装。対象ステータス: 408, 429, 5xx。
    - 429 時は Retry-After ヘッダを尊重。
    - 401 (Unauthorized) 受信時はトークンを自動リフレッシュして 1 回だけリトライする仕組みを実装（無限再帰防止の allow_refresh フラグ）。
    - id_token キャッシュをモジュールレベルで保持しページネーション間で共有。
    - 取得時刻（fetched_at）を UTC ISO8601 形式で記録し、Look-ahead Bias を防止。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）では ON CONFLICT DO UPDATE を使い冪等性を確保。
    - 入力データの型変換ユーティリティ（_to_float, _to_int）を追加し、不正な数値や空値への寛容性を提供。

  - DuckDB スキーマと初期化（src/kabusys/data/schema.py）
    - DataPlatform 設計（Raw / Processed / Feature / Execution 層）に基づくテーブル定義を実装。
    - raw_prices, raw_financials, raw_news, raw_executions 等の Raw Layer。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed Layer。
    - features, ai_scores 等の Feature Layer。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution Layer。
    - 検索・結合の高速化を目的としたインデックス群を定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
    - init_schema(db_path) による冪等的なスキーマ初期化と接続取得。また get_connection() を提供。
    - db_path の親ディレクトリ自動作成（メモリ用 ":memory:" サポート）。

  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 日次 ETL の実装（run_daily_etl）:
      1. 市場カレンダー ETL（先読み lookahead_days、デフォルト 90 日）
      2. 株価日足 ETL（差分更新、バックフィル default 3 日）
      3. 財務データ ETL（差分更新、バックフィル default 3 日）
      4. 品質チェック（オプション）
    - 差分更新ロジック: DB の最終取得日を確認し未取得範囲のみ取得。date_from 指定がなければ最終取得日から backfill_days 分を遡る。
    - ETLResult データクラスを導入し、フェッチ数・保存数・品質問題・エラー等を構造化して返却。
    - 各ステップは独立したエラーハンドリングとし、1 ステップの失敗でも残りは継続（Fail-Fast でない設計）。
    - id_token の注入（引数）を許容してテスト容易性を確保。

  - 監査ログ（src/kabusys/data/audit.py）
    - シグナル→発注→約定のトレーサビリティを確保する監査スキーマを実装。
    - signal_events, order_requests, executions テーブルを定義（UUID ベースの ID、冪等キー、ステータス管理、created_at/updated_at）。
    - order_requests に対する発注タイプ別チェック（limit/stop/market の価格チェック）や外部キー制約（ON DELETE RESTRICT）を実装。
    - init_audit_schema(conn) と init_audit_db(db_path) を提供。UTC タイムゾーン保存を強制（SET TimeZone='UTC'）。
    - 監査用インデックスを複数追加してクエリ性能を向上。

  - データ品質チェック（src/kabusys/data/quality.py）
    - QualityIssue データクラスを導入し、各チェックで検出された問題を構造化して返却。
    - 実装済みチェック:
      - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損を検出（volume は許容）。
      - スパイク検出 (check_spike): 前日比の変動率が閾値（デフォルト 50%）を超える銘柄を検出（LAG ウィンドウを利用）。
    - 各チェックはサンプル行（最大 10 件）と件数を返す。重大度（"error" / "warning"）を付与。
    - ETL 側で run_all_checks の呼び出しを想定（pipeline.run_daily_etl で利用）。

  - その他ユーティリティ
    - 市場カレンダーを用いた営業日調整機能（_adjust_to_trading_day）。
    - DuckDB のテーブル存在確認・最大日付取得ユーティリティ。
    - ロガー出力を適切に埋め込み（各処理の開始・完了・件数ログ、警告/エラー等）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- 環境変数の取り扱いに注意:
  - OS 環境変数は .env によって上書きされないよう保護（protected set）。
  - 自動ロードを無効にする環境変数（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供し、テストや CI 環境での制御を容易に。

Notes / 実装上の注意
- J-Quants API 呼び出しはレート制限に厳格に従う設計だが、外部環境（ネットワーク状況、API 側の挙動）に依存するため、運用時はログ監視とリトライパラメータの見直しを推奨します。
- DuckDB の型制約や CHECK 制約を多用しており、不正データは SQL レベルで弾かれます。必要に応じて保存前にデータクレンジングを行ってください。
- run_daily_etl は品質チェックで重大な問題が見つかっても ETL 自体は継続する設計です。品質問題を受けて処理を中止したい場合は呼び出し元で ETLResult を確認してください。
- 取得時刻（fetched_at）や監査ログのタイムスタンプは UTC で保存する運用を想定しています。

今後の予定（例）
- strategy / execution 層の具体的実装（発注ハンドラ、ポートフォリオ最適化、リスク管理）。
- Slack / 監視周りの通知統合（既に設定項目は追加済み）。
- run_all_checks の追加チェック実装（重複チェック、日付不整合チェック等の拡張）。
- 単体テスト・統合テストの整備および CI パイプライン構築。

---

（注）本 CHANGELOG は与えられたコードベースの内容から推測して作成した初期リリース記録です。実際のリリースノート整備時にはリリース番号・日付・担当者・外部依存情報などを合わせて更新してください。