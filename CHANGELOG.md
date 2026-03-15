Keep a Changelog
すべての重要な変更はこのファイルに記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

履歴
====

Unreleased
----------

（なし）

[0.1.0] - 2026-03-15
-------------------

Added
- 初回リリース (kabusys v0.1.0)
  - パッケージ構成
    - kabusys パッケージを導入。公開 API として data, strategy, execution, monitoring を __all__ でエクスポート。
    - 空のサブパッケージ skeleton: strategy/, execution/, monitoring/（将来の拡張ポイント）。

  - 環境設定 / 設定管理 (src/kabusys/config.py)
    - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
      - プロジェクトルートを .git または pyproject.toml で探索する _find_project_root() を採用し、CWD に依存しない自動読み込み。
      - 読み込み順: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き回避）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途向け）。
    - .env の行パーサ _parse_env_line() を実装。export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントルール等に対応。
    - _load_env_file() によりファイル読み込み時のエラーハンドリングと protected キーによる上書き制御を実装。
    - Settings クラスを導入し、アプリ用設定プロパティを提供:
      - J-Quants / kabu API / Slack / データベース（DuckDB / SQLite） / システム設定（KABUSYS_ENV, LOG_LEVEL）など。
      - env/log_level の検証（許容値チェック）と便利プロパティ is_live / is_paper / is_dev。
      - 必須変数取得時に未設定なら例外を投げる _require() を提供。

  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - API レート制限（120 req/min）を守る固定間隔スロットリング _RateLimiter を実装。
    - リトライロジックを実装（指数バックオフ、最大 3 回）。408/429/5xx 系やネットワークエラーに対して再試行。
    - 401 Unauthorized 受信時に自動でトークンをリフレッシュして 1 回リトライする仕組みを導入（無限再帰保護あり）。
    - ページネーション対応の取得関数:
      - fetch_daily_quotes(): 日足（OHLCV）取得（pagination_key 対応）
      - fetch_financial_statements(): 四半期財務データ取得（pagination_key 対応）
      - fetch_market_calendar(): JPX マーケットカレンダー取得
    - get_id_token(): リフレッシュトークンから ID トークンを取得する POST 呼び出しを実装。
    - モジュールレベルの ID トークンキャッシュを導入し、ページネーション間でトークンを再利用。
    - DuckDB への保存用関数（冪等性を考慮）:
      - save_daily_quotes(), save_financial_statements(), save_market_calendar()
      - 各関数は ON CONFLICT DO UPDATE を用いて重複を排除、PK 欠損行はスキップしてログ出力。
      - fetched_at を UTC ISO8601（Z）で記録し、Look-ahead Bias のトレースを容易に。
    - 値変換ユーティリティ _to_float() / _to_int() を実装（空値・不正値の安定処理、int 変換時の丸め回避など）。

  - DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
    - DataLayer（Raw / Processed / Feature / Execution）に基づくテーブル群を定義:
      - Raw: raw_prices, raw_financials, raw_news, raw_executions
      - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature: features, ai_scores
      - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに適切な型チェック・NOT NULL 制約・PRIMARY KEY を付与。
    - 頻出クエリに備えたインデックス群を定義（銘柄×日付, ステータス検索等）。
    - init_schema(db_path) によりディレクトリ自動作成・DDL 実行を行い、冪等にテーブルを作成して接続を返す。
    - get_connection(db_path) を用意（既存 DB への接続用途）。

  - 監査ログ（トレーサビリティ）モジュール (src/kabusys/data/audit.py)
    - strategy→signal→order_request→execution の一連フローをトレースする監査用テーブルを定義:
      - signal_events（シグナル生成ログ）
      - order_requests（発注要求ログ、order_request_id を冪等キーとして利用）
      - executions（証券会社からの約定ログ、broker_execution_id をユニークな冪等キー）
    - すべての TIMESTAMP を UTC に設定する（init_audit_schema() 内で SET TimeZone='UTC' を実行）。
    - order_requests には order_type ごとのチェック制約（limit/stop/market 時の価格フィールド整合性）を実装。
    - インデックス群を追加（status スキャン、signal_id→order_requests、broker_order_id 紐付け等）。
    - init_audit_schema(conn) / init_audit_db(db_path) を提供し、既存接続へ冪等的に監査テーブルを追加可能。

  - ロギング
    - 各主要処理で logger に情報/警告を出力（取得件数、スキップ件数、リトライログ等）。

  - 依存・実装上の注意
    - DuckDB を利用するデータ格納レイヤを前提。
    - 外部 API 呼び出しに対しタイムアウトやエラーハンドリング、再試行ポリシーを組み込んでいるため、実稼働での堅牢性を考慮。

Changed
- （なし）

Fixed
- （なし）

Removed
- （なし）

Notes
- このリリースは初期実装であり、strategy / execution / monitoring の各パッケージは将来的な機能追加のためのプレースホルダとして用意されています。