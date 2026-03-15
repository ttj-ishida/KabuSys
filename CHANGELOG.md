CHANGELOG
=========

このファイルは Keep a Changelog の形式に従っています。  
すべての重要な変更を時系列で記録します。

Unreleased
----------

（なし）

0.1.0 - 2026-03-15
------------------

Added
- 新規パッケージ "kabusys" を追加（バージョン 0.1.0）。
  - パッケージのトップレベル定義（src/kabusys/__init__.py）。
- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
  - .env および環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式対応、コメント（#）の扱い、シングル／ダブルクォートとバックスラッシュエスケープ対応。
    - 無効行をスキップする堅牢な実装。
  - 環境変数保護機構: OS 環境変数を protected として .env による上書きを防止可能。
  - Settings クラスを提供し、必須キー取得メソッド（_require）と以下のプロパティを公開:
    - J-Quants / kabu ステーション / Slack / データベース（duckdb/sqlite）関連の設定
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の便利プロパティ
- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - 取得可能データ:
    - 株価日足（OHLCV）
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー（祝日・半日・SQ）
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - 冪等性・ページネーション対応の取得関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（pagination_key の処理を含む）
  - リトライ戦略:
    - 指数バックオフ（最大 3 回）、HTTP 408/429 および 5xx をリトライ対象。
    - 429 時は Retry-After ヘッダを優先。
    - ネットワークエラー（URLError / OSError）に対するリトライ。
  - 認証トークン管理:
    - get_id_token でリフレッシュトークンから id_token を取得（POST）。
    - モジュールレベルで id_token をキャッシュし、401 受信時は 1 回のみ自動リフレッシュして再試行（無限再帰回避）。
  - データ保存（DuckDB）ユーティリティ:
    - save_daily_quotes, save_financial_statements, save_market_calendar：ON CONFLICT DO UPDATE を用いた冪等な保存。
    - fetched_at（UTC ISO 8601）を付与して Look-ahead バイアスのトレースを可能に。
  - 値変換ユーティリティ: _to_float / _to_int（堅牢な数値変換ルールを実装）。
- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）。
  - 3 層アーキテクチャに基づくテーブル群を定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を豊富に定義。
  - 実行時に親ディレクトリを自動作成する init_schema(db_path) を提供（":memory:" 対応）。
  - 頻出クエリに対するインデックス群を定義・作成。
  - get_connection(db_path) を提供（既存 DB への接続）。
- 監査ログ・トレーサビリティモジュールを追加（src/kabusys/data/audit.py）。
  - 監査用テーブルを定義:
    - signal_events（戦略生成シグナルの全記録、拒否やエラーも含む）
    - order_requests（発注要求、order_request_id を冪等キーとして保証）
    - executions（証券会社流し込みの約定ログ、broker_execution_id を冪等キーとして扱う）
  - ステータス遷移、価格フィールドの検証、created_at/updated_at の方針を文書化。
  - init_audit_schema(conn) により既存の DuckDB 接続に監査テーブルを追加（UTC タイムゾーン設定）。
  - init_audit_db(db_path) による監査専用 DB 初期化も提供。
  - 監査用の検索性を高めるインデックス群を定義。
- パッケージ構成ファイル（各サブパッケージの __init__.py）を追加（strategy / execution / monitoring / data）。

Changed
- （初回リリースのため該当なし）

Fixed
- 認証トークンリフレッシュ時の無限再帰を防止（allow_refresh フラグ、1 回のみのリフレッシュ保証）。
- .env 読み込み時にファイル IO エラー発生時の警告出力（ワーニングで安全に継続）。
- DuckDB 初期化時に親ディレクトリが存在しない場合は自動作成することでファイル作成エラーを回避。

Notes / Design decisions
- すべてのタイムスタンプは UTC で扱う方針（特に監査ログ）。
- 監査ログは削除せず永続化する前提（FK は ON DELETE RESTRICT を採用）。
- データ取得時の fetched_at を記録することでデータが「いつシステムで利用可能になったか」をトレース可能にしている。
- id_token はモジュールキャッシュで共有し、ページネーション間で同一トークンを再利用することで不要な認証リクエストを抑制。
- 空値や異常な文字列に対しては安全に None を返すことで DB 格納時の不整合を低減する設計を採用。

Security
- シークレット（refresh token 等）は Settings 経由で必須扱いにしており、明示的に設定されていない場合は ValueError を発生させることで未設定検出を容易にしている。

今後の予定（例）
- strategy / execution / monitoring の実装拡充。
- テストカバレッジの追加（ネットワーク・DBモックを含む）。
- メトリクス・監視（Prometheus, Slack 通知など）の統合。