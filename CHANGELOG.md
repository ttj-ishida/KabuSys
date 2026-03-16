CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
安定版へのリリースや後続変更の記録に利用してください。

[Unreleased]
------------

- （現在なし）

[0.1.0] - 2026-03-16
-------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基盤機能を追加。
  - パッケージ初期化
    - kabusys.__version__ = 0.1.0 を設定。
    - パッケージ公開 API: data, strategy, execution, monitoring（サブパッケージのプレースホルダを含む）。
  - 設定管理（kabusys.config）
    - .env ファイルおよび環境変数から設定を自動ロードする機能を実装。
      - プロジェクトルートの検出：.git または pyproject.toml を起点に探索（CWD に依存しない）。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - export KEY=val やクォート・エスケープ・コメントの取り扱いに対応した .env パーサを実装。
    - Settings クラスを追加（プロパティによる遅延取得）。
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須取得メソッド。
      - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値。
      - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL のバリデーション。
      - is_live / is_paper / is_dev の便利プロパティ。
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - データ取得機能: 株価日足（OHLCV）, 財務データ（四半期 BS/PL）, JPX マーケットカレンダー を取得する API ラッパーを実装。
    - 設計上の重要点:
      - レート制御: 固定間隔スロットリング（デフォルト 120 req/min）で API レートを順守。
      - リトライ: 指数バックオフ（最大 3 回）、対象ステータス（408/429/5xx）に対応。
      - 401 受信時にリフレッシュトークンを用いて id_token を自動更新し 1 回のみリトライ。
      - ページネーション対応（pagination_key を利用）。
      - fetched_at（UTC）を記録して取得タイミングをトレース可能に。
    - DuckDB への保存関数（冪等性を保つ ON CONFLICT DO UPDATE を利用）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
    - 型変換ユーティリティ: _to_float, _to_int（厳密な変換ルールを実装）。
  - DuckDB スキーマ定義（kabusys.data.schema）
    - DataPlatform に基づく 3 層（Raw / Processed / Feature）+ Execution / Audit のテーブル設計を実装。
    - 主なテーブル:
      - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
      - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature 層: features, ai_scores
      - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 監査ログ用に多くのインデックスを定義（頻出クエリを考慮）。
    - init_schema(db_path) により DB 初期化（親ディレクトリ自動作成、冪等実行）と接続取得を提供。
    - get_connection(db_path) で既存 DB 接続を取得可能（初期化は行わない）。
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分更新・バックフィル・品質チェックを組み合わせた日次 ETL を実装。
    - 主要機能:
      - run_prices_etl, run_financials_etl, run_calendar_etl: 各データの差分取得と保存（backfill デフォルト 3 日）。
      - run_daily_etl: 市場カレンダー取得 → 営業日調整 → 株価・財務データ差分 ETL → 品質チェック（任意）の統合処理。
      - ETLResult dataclass: 各種取得数・保存数・品質問題・エラーの集約とシリアライズ用メソッド。
      - カレンダー先読みデフォルト: 90 日（_CALENDAR_LOOKAHEAD_DAYS）。
      - データ未取得時の初回ロード開始日: 2017-01-01（_MIN_DATA_DATE）。
      - _adjust_to_trading_day による非営業日の調整（market_calendar 利用）。
    - 設計方針:
      - 各ステップは独立して例外を捕捉し、1 ステップ失敗でも他ステップを継続（Fail-Fast ではない）。
      - テスト容易性のため id_token 注入可能。
  - データ品質チェック（kabusys.data.quality）
    - QualityIssue dataclass を導入し、チェック結果を構造化して返す設計。
    - 実装済みチェック:
      - check_missing_data: raw_prices の OHLC 欠損（open/high/low/close）検出。重大度は error。
      - check_spike: 前日比に基づくスパイク検出（LAG ウィンドウを使用）。デフォルト閾値 50%。
      - 各チェックは最大 10 行のサンプルを返す（全件収集アプローチ）。
    - SQL による効率的な実行、パラメータバインディングを採用（SQL インジェクション対策）。
  - 監査ログ・トレーサビリティ（kabusys.data.audit）
    - シグナル → 発注要求 → 約定 のトレーサビリティを保証する監査テーブルを実装。
    - テーブル:
      - signal_events（戦略が生成したシグナルを全て記録）
      - order_requests（冪等キー order_request_id を持つ発注要求ログ）
      - executions（証券会社からの約定ログ）
    - 制約・ポリシー:
      - 全ての TIMESTAMP は UTC 保存（init_audit_schema 内で SET TimeZone='UTC' を実行）。
      - order_request_id を冪等キーとして二重発注を防止。
      - FK は ON DELETE RESTRICT（監査ログは削除しない前提）。
      - ステータス列とチェック制約で状態遷移や入力整合性を担保。
    - init_audit_schema(conn) / init_audit_db(db_path) により監査スキーマの初期化を提供。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Removed
- 新規リリースのため該当なし。

Security
- 新規リリースのため該当なし。

Notes / 制限事項
- J-Quants API のレートはコード内定数（120 req/min）で固定制御されている。運用上の要件に応じて調整が必要な場合あり。
- DuckDB の ON CONFLICT による冪等化はテーブル定義に依存するため、スキーマ変更時にはマイグレーションが必要。
- quality モジュールは現状で主に raw_prices を検査。追加チェックやカスタムルールは今後の拡張対象。
- .env パーサは一般的な .env 構文をサポートするが、複雑なケース（多行値など）は未対応。

参照
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)