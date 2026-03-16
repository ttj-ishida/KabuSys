CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- なし

0.1.0 - 2026-03-16
------------------

Added
- パッケージ初期リリース。
  - パッケージメタ情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - public API: data, strategy, execution, monitoring

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - OS 環境変数は保護され、.env/.env.local による上書きを防止。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルート検出は __file__ を基点として .git または pyproject.toml を探索（CWD に依存しない）。
  - .env パーサーは以下に対応:
    - 空行 / コメント行（#）を無視
    - "export KEY=val" 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理
    - インラインコメント処理（クォート無しでは直前にスペース/タブがある # をコメントとして認識）
  - Settings クラスで必要な設定をプロパティとして提供（型変換・検証付き）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV の妥当性チェック（development/paper_trading/live）
    - LOG_LEVEL の妥当性チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 基本設計:
    - API レート制限厳守 (120 req/min)
    - 冪等的保存（DuckDB に ON CONFLICT DO UPDATE）
    - リトライ（指数バックオフ、最大 3 回、ネットワーク系 408/429/5xx を再試行）
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ
    - 取得日時（fetched_at）を UTC ISO 形式で保存（Look-ahead バイアス対策）
  - 機能:
    - get_id_token: リフレッシュトークンから ID トークンを取得（POST、allow_refresh=False による再帰防止）
    - _RateLimiter: 固定間隔スロットリング実装（内部で時間管理）
    - id_token キャッシュ機構（ページネーション間で共有、force_refresh をサポート）
    - _request: 汎用 HTTP リクエスト実装（JSON デコードエラーの詳細をログ）
    - fetch_* 系: ページネーション対応の取得関数
      - fetch_daily_quotes (日足 OHLCV)
      - fetch_financial_statements (四半期 BS/PL)
      - fetch_market_calendar (JPX カレンダー)
    - save_* 系: DuckDB への保存（冪等）
      - save_daily_quotes -> raw_prices（PK 欠損行はスキップし警告ログ）
      - save_financial_statements -> raw_financials
      - save_market_calendar -> market_calendar（取引有無・半日・SQ を boolean に変換）
  - ユーティリティ:
    - _to_float / _to_int: 安全な数値変換（空値・不正値は None、"1.0" 形式は許容、非整数の小数は int 変換を拒否）

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を実装。
  - 代表的なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な CHECK 制約・PRIMARY KEY を設定
  - インデックス定義（頻出クエリを想定）
  - init_schema(db_path) でディレクトリ作成、DDL 実行、冪等な初期化（":memory:" サポート）
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない）

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL ワークフロー実装（run_daily_etl をエントリポイントに以下を実行）:
    1. 市場カレンダー ETL（デフォルト先読み 90 日）
    2. 株価日足 ETL（差分 + バックフィル、デフォルト backfill_days=3）
    3. 財務データ ETL（差分 + バックフィル）
    4. 品質チェック（オプション）
  - 差分更新ロジック:
    - DB 側の最終取得日を参照して差分のみ取得。差分未指定時は最終取得日から backfill_days 前から再取得。
    - 初回ロード用の最小日付: 2017-01-01
  - カレンダー関連:
    - _adjust_to_trading_day で非営業日は直近の過去営業日に調整（market_calendar がない場合はフォールバックでそのまま）
  - ETLResult データクラス:
    - 各種取得/保存件数、品質問題リスト、エラーメッセージを収集・返却
    - 品質チェックでの重大エラー判定メソッドを提供
  - 各ステップは独立して例外を捕捉し、あるステップが失敗しても他は継続（エラーは ETLResult.errors に記録）

- 監査ログ（トレーサビリティ）モジュール (src/kabusys/data/audit.py)
  - 監査用テーブルを別モジュールで定義・初期化:
    - signal_events（戦略→シグナル記録。棄却やエラーも記録）
    - order_requests（冪等キー order_request_id、各種 CHECK、外部キー制約）
    - executions（証券会社からの約定ログ、broker_execution_id は一意）
  - init_audit_schema(conn) で UTC タイムゾーン設定後にテーブル/インデックスを作成
  - init_audit_db(db_path) で専用 DB を初期化するヘルパーを提供

- データ品質チェックモジュール (src/kabusys/data/quality.py)
  - QualityIssue データクラスで問題を構造化して返却
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欄の欠損検出（volume は許容）
    - check_spike: 前日比スパイク検出（デフォルト閾値 50%）、LAG を用いた SQL 実装
    - （設計上）重複チェック・日付不整合チェック等を想定（モジュール構成に合わせて実装可能）
  - すべてのチェックは Fail-Fast ではなく問題を収集して返す設計
  - DuckDB に対してパラメータバインド SQL を使用（インジェクションリスク低減）

Other notes
- ロギング:
  - 各モジュールで logger を設置。主要イベント（取得件数、保存件数、警告・エラー）をログ出力。
- エラーハンドリング:
  - ネットワーク/HTTP エラー、JSON デコードエラー、ファイル I/O エラー等に対して適切に警告・例外処理を行う。
- テスト性:
  - id_token の注入や自動ロードの無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD）によりユニットテストが容易に行える設計を採用。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

セキュリティ・運用上の注意
- 必須トークン（JQUANTS_REFRESH_TOKEN 等）は .env や環境変数で安全に管理してください。
- 自動 .env ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

補足（開発者向け）
- DuckDB 初期化は data.schema.init_schema() を推奨。初回のみディレクトリを作成します。
- 監査ログを別 DB に分離したい場合は data.audit.init_audit_db() を使用してください。