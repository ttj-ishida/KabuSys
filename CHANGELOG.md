# Changelog

すべての notable な変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠します。  

リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-16

### 追加 (Added)
- パッケージ初期リリース: kabusys（日本株自動売買システムの基盤モジュール群）
  - バージョン: 0.1.0

- パッケージ公開情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" として定義。
  - __all__ に data, strategy, execution, monitoring をエクスポート。

- 環境設定管理モジュール (src/kabusys/config.py)
  - .env/.env.local の自動読み込みをプロジェクトルート（.git または pyproject.toml を探索）から行う実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env ファイルパースを独自実装（コメント、export KEY=val、シングル/ダブルクォート、エスケープ処理に対応）。
  - Settings クラスによる型付きプロパティ経由の設定取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須化（未設定時は ValueError）。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値を提供。
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証ロジック。
    - is_live / is_paper / is_dev の便宜プロパティ。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価（日足）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する関数群を実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - 再試行ロジック（最大 3 回、指数バックオフ、HTTP 408/429/5xx を再試行）。
  - 401 受信時はリフレッシュトークンで id_token を自動更新して1回だけリトライ。
  - ページネーション対応（pagination_key の追跡、ページ間での id_token キャッシュ共有）。
  - JSON デコードエラーやネットワークエラーの取り扱いとログ出力。
  - fetch_* 系関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。

  - DuckDB への保存関数（冪等性を担保）:
    - save_daily_quotes: raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE。
    - save_financial_statements: raw_financials テーブルへ同様の冪等保存。
    - save_market_calendar: market_calendar テーブルへ保存。
  - 取得時刻（fetched_at）を UTC ISO8601 形式（末尾 Z）で付与。
  - 文字列→数値変換ユーティリティ（_to_float, _to_int）を実装（安全な変換・不正値は None）。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataPlatform 設計に基づく多層スキーマを実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型制約・チェック制約・PRIMARY KEY を定義（データ品質向上）。
  - 頻出クエリ向けのインデックス群を作成（例: code×date, status 検索など）。
  - init_schema(db_path) による冪等的な初期化処理（親ディレクトリ作成処理、":memory:" 対応）。
  - get_connection(db_path) による既存 DB への接続取得。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 日次 ETL を行う run_daily_etl を実装。処理フロー:
    1. 市場カレンダー ETL（デフォルト先読み 90 日）
    2. 株価日足 ETL（差分更新・バックフィル、backfill_days デフォルト 3日）
    3. 財務データ ETL（差分更新・バックフィル）
    4. 品質チェック（オプション）
  - 差分更新ロジック:
    - DB の最終取得日から差分を算出し未取得分のみ取得。
    - 初回ロード時は最小データ開始日（2017-01-01）を使用。
    - backfill_days により過去数日分を再取得して API の後出し修正に対応。
  - カレンダー調整機能（_adjust_to_trading_day）により非営業日は直近営業日に調整。
  - 各ジョブは独立したエラーハンドリングを行い、1ステップ失敗でも他ステップを継続する設計。
  - ETLResult データクラスにより実行結果（取得数、保存数、品質問題、エラー）を集約。
  - id_token の注入によりテスト容易性を確保。

- 監査ログ（トレーサビリティ）モジュール (src/kabusys/data/audit.py)
  - signal_events / order_requests / executions を含む監査用テーブル群を定義。
  - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）を設計。
  - order_request_id を冪等キーとして二重発注防止を想定。
  - すべての TIMESTAMP を UTC 保存するための初期化処理（SET TimeZone='UTC'）。
  - init_audit_schema(conn) / init_audit_db(db_path) による冪等初期化と接続取得。
  - 発注種別ごとの CHECK 制約やステータス遷移、インデックス定義を実装。

- データ品質チェックモジュール (src/kabusys/data/quality.py)
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - チェック実装（DuckDB 上の SQL ベース）:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損を検出（severity=error）。
    - スパイク検出 (check_spike): 前日比の変動率が閾値（デフォルト 50%）を超えるレコードを検出。
    - （設計文書に基づき重複・日付不整合検出も想定。実装はモジュール内で拡張可能）
  - 各チェックは全件収集方式（Fail-Fast ではない）。

- パッケージ構造
  - data, strategy, execution, monitoring のパッケージが存在（各 __init__.py を配置）。
  - 実運用を想定した設計原則（冪等性、UTC 時刻、インデックス、制約、監査不可逆性、ログ出力）を反映。

### 仕様/設計ノート (Notes)
- J-Quants クライアントは 120 req/min の制限を想定し固定間隔スロットリングを採用。連続呼び出しが多いバッチ処理でのスループットを制御。
- 再試行ポリシー: 最大3回、指数バックオフ（ベース 2 秒）、429 の場合は Retry-After ヘッダを優先。
- 保存処理は DuckDB で ON CONFLICT DO UPDATE を使用し冪等性を担保。
- すべての監査ログは基本的に削除しない前提（FK は ON DELETE RESTRICT 等で保護）。
- .env パーサは bash 風の記法をある程度サポート（実運用の .env 互換性を向上）。

### 既知の制限 / 注意点
- DuckDB が必須の依存となる（接続と SQL 実行を前提）。
- J-Quants / kabu API / Slack 連携には環境変数による認証情報が必要（Settings で必須化）。
- quality モジュールは設計に基づくチェック群を提供するが、運用に応じた追加チェックや閾値調整が想定される。

---
今後のリリースでは、strategy / execution / monitoring 層の実装拡充、単体テストと統合テストの追加、CI 自動化、ドキュメント（DataSchema.md, DataPlatform.md 参照）の公開を予定しています。