Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。

CHANGELOG.md
------------

すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-03-16
-------------------

Added
- パッケージの初期リリース: kabusys 0.1.0
  - パッケージエントリポイント: src/kabusys/__init__.py を追加（__version__ = "0.1.0"、公開モジュール指定）。
- 環境設定管理（src/kabusys/config.py）
  - .env ファイルや環境変数から設定を自動読み込み（読み込み順: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD 非依存で自動ロードを実現。
  - export KEY=val 形式やクォート／エスケープ、インラインコメント（スペース前の#）に対応した .env パーサ実装。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - OS 環境変数を保護する protected 機能（.env の上書きを制御）。
  - Settings クラスで主要設定をプロパティ化:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）および LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live/is_paper/is_dev ヘルパープロパティ
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、四半期財務データ、JPX 市場カレンダーを取得する API クライアントを実装。
  - 設計上の特徴:
    - レート制限遵守（120 req/min）を固定間隔スロットリングで制御（_RateLimiter）。
    - 再試行（指数バックオフ、最大 3 回）を実装（対象: 408/429/>=500、429 の場合は Retry-After を優先）。
    - 401 受信時には ID トークンを自動リフレッシュして 1 回だけリトライ（トークン取得の再帰を防止）。
    - ページネーション対応（pagination_key を用いた繰り返し取得）。
    - データ取得時刻（fetched_at）を UTC で記録して Look-ahead バイアスを抑止。
  - DuckDB 向け保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）:
    - ON CONFLICT DO UPDATE により冪等に保存。
    - PK 欠損行はスキップし、スキップ件数をログ出力。
    - 型変換ユーティリティ (_to_float, _to_int) を提供し、安全に数値変換。
- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - 3 層（Raw / Processed / Feature）＋ Execution レイヤのテーブルを包括的に定義。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores 等の Feature テーブル。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等の Execution テーブル。
  - 頻出クエリのためのインデックスを定義。
  - init_schema(db_path) によりディレクトリ自動作成とテーブル／インデックス作成を行う（冪等）。
  - get_connection(db_path) を提供（既存 DB への接続）。
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL の統合実装（run_daily_etl を提供）。
  - 処理フロー:
    1. カレンダー ETL（先読み: デフォルト 90 日）
    2. 株価日足 ETL（差分更新 + デフォルトバックフィル 3 日）
    3. 財務データ ETL（差分更新 + バックフィル）
    4. 品質チェック（オプション）
  - 差分更新ヘルパー（DB の最終取得日取得関数 get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - run_prices_etl/run_financials_etl/run_calendar_etl は差分算出・API 取得・保存を個別に実行し、失敗しても他処理は継続。
  - ETLResult データクラスで結果・品質問題・エラー概要を集約。
- 監査ログ（トレーサビリティ）（src/kabusys/data/audit.py）
  - signal_events, order_requests, executions の監査テーブルを定義。
  - order_request_id を冪等キーとして扱い、発注再送で二重発注を防止する制約を導入。
  - 各テーブルは created_at / updated_at を持ち、UTC 保存を前提（init_audit_schema は SET TimeZone='UTC' を実行）。
  - 複数のチェック制約（limit/stop/market における価格必須／排他）や外部キー制約（ON DELETE RESTRICT）を定義。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。
- データ品質チェック（src/kabusys/data/quality.py）
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）。
  - 実装済みチェック（少なくとも）:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損を検出しエラーとして報告。
    - スパイク検出 (check_spike): 前日比が閾値（デフォルト 50%）を超える価格変動を検出。
  - 各チェックはサンプル行（最大 10 件）を返し、Fail-Fast ではなく全件収集を行う設計。
  - pipeline 側から run_all_checks を呼べる設計（ETL と統合）。

Notes / マイグレーション
- データベース初期化:
  - 全テーブルを含む DB を作成するには data.schema.init_schema(db_path) を実行してください（db_path の親ディレクトリは自動作成されます）。
  - 監査ログのみを追加する場合は init_audit_schema(conn) を既存接続に対して呼び出してください。
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings のプロパティ参照）。
  - 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
- ETL 実行例:
  - init_schema() で DB 初期化後、run_daily_etl(conn) を呼ぶことで市場カレンダー取得→価格取得→財務取得→品質チェックの一連処理を実行できます。
- ロギング/運用:
  - Settings.log_level によりロギング閾値を検証します（不正値は例外を投げます）。
  - J-Quants API クライアントは 120 req/min に合わせたスロットリングと再試行を実装していますが、大量のバッチ処理では運用面のレート管理・監視を推奨します。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

補足
- README や DataPlatform.md / DataSchema.md 等の設計ドキュメントに基づいて実装しています。将来的に以下の点を拡張予定です:
  - 追加の品質チェック（重複チェック、日付不整合チェック等）の拡張／強化。
  - execution 層のブローカー接続ラッパー（kabuステーション等）と監査ログの連携実装。
  - 単体テストおよび E2E テストの追加（トークンリフレッシュ・ページネーション・レート制御の検証）。

-----

必要であれば、各リリース項目を英語版にしたり、より詳細な移行手順（コードスニペット・コマンド）を追記します。どのレベルの詳細が必要か教えてください。