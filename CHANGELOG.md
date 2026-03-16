CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-16
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0"
    - 公開サブパッケージ: data, strategy, execution, monitoring（__all__ に列挙）

- 環境設定・自動読み込み機能（src/kabusys/config.py）
  - .env と .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env パーサーは export 形式、シングル/ダブルクォート、エスケープ、インラインコメントなどに対応。
  - OS 環境変数の保護（.env.local による上書き制御、protected set）。
  - Settings クラスを提供し、J-Quants/Slack/DB/システム設定をプロパティ経由で取得（必須値の検証と既定値を実装）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）およびユーティリティプロパティ（is_live / is_paper / is_dev）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出し用ユーティリティ _request を実装（JSON デコード、エラーハンドリング、詳細ログ）。
  - レート制限遵守（120 req/min）を固定間隔スロットリングで実装する RateLimiter。
  - 再試行ロジック（指数バックオフ、最大 3 回）。HTTP 429 の場合は Retry-After ヘッダを尊重。
  - 401 Unauthorized 受信時にリフレッシュトークンで自動的に id_token をリフレッシュして 1 回リトライする仕組み。
  - id_token のモジュールレベルキャッシュ（ページネーション間で共有）。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務諸表）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - get_id_token（リフレッシュトークンからの idToken 取得、POST 実装）。
  - DuckDB に対する冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - 取得時刻（fetched_at）を UTC 形式で保存し、Look-ahead Bias のトレーサビリティを確保。
  - 型変換ユーティリティ（_to_float, _to_int）で安全に数値変換を処理。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - 3 層（Raw / Processed / Feature）＋ Execution 層を含む包括的なスキーマ DDL を提供。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル群。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル群。
  - features, ai_scores 等の Feature テーブル群。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル群。
  - 頻出クエリ向けのインデックス定義（例: code×date、status 検索など）。
  - init_schema(db_path) による初期化関数および get_connection(db_path) を提供。:memory: のサポート、親ディレクトリ自動作成。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL の主要ワークフローを実装（run_daily_etl）。
    - 市場カレンダー ETL（先読み lookahead）
    - 株価日足 ETL（差分更新 + バックフィル）
    - 財務データ ETL（差分更新 + バックフィル）
    - 品質チェックの実行（オプション）
  - 差分更新ヘルパー（最終取得日の計算 get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - backfill_days による後出し修正吸収用の再取得ロジック（デフォルト 3 日）。
  - カレンダー先読み（デフォルト 90 日）と営業日調整（非営業日に対する直近の営業日調整）。
  - 各ステップは独立してエラーハンドリングされ、1 ステップ失敗でも他ステップを継続する設計。
  - ETLResult データクラスで実行結果、品質問題、エラー一覧を構造化して返却。

- 監査ログ / トレーサビリティ（src/kabusys/data/audit.py）
  - シグナル → 発注リクエスト → 約定 までを UUID 連鎖でトレースする監査スキーマを実装。
    - signal_events（戦略が生成したシグナルログ）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
    - executions（証券会社からの約定ログ）
  - order_requests のチェック制約（limit/stop/market の価格要件）を明記。
  - init_audit_schema(conn) / init_audit_db(db_path) による監査テーブル初期化。すべての TIMESTAMP を UTC で保存するために SET TimeZone='UTC' を実行。
  - 監査用インデックス群を用意（status 検索、signal_id 紐付け、broker_order_id での検索など）。

- データ品質チェックモジュール（src/kabusys/data/quality.py）
  - QualityIssue データクラスを導入し、各チェック結果を構造化して返却。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（サンプル行を最大 10 件返す）。
    - check_spike: 前日比スパイク検出（LAG ウィンドウを使用、閾値デフォルト 50%）。
  - チェックは Fail-Fast ではなく問題を全件収集して返す設計。DuckDB のプレースホルダ（?）を使った安全な SQL を実行。

Other
- 全体として型注釈を多用しテスト容易性を考慮（id_token の注入など）。
- ロギング箇所を豊富に配置し運用時のトラブルシュートを容易化。

Security
- 環境変数の取り扱いに配慮（必須キーは _require で明示的に検証、.env の読み込み時に OS 環境を保護する protected 処理）。
- API トークンの自動リフレッシュとキャッシュにより認証フローを安全に管理。

Notes / Limitations
- strategy/ と execution/ パッケージは __init__ のみが存在し、各戦略・実行ロジックは今後実装予定。
- quality モジュールは主要チェック（欠損・スパイク）を実装しているが、ドキュメントにある重複チェックや日付不整合の一部は将来拡張を予定。
- DuckDB の UNIQUE/FOREIGN KEY の動作や NULL 扱いは DB 実装依存のため運用時に検証が必要。

---

（本 CHANGELOG はコードベースから実装内容を推測して作成しています。詳細な変更履歴やリリース日付は実際のリリース運用に合わせて調整してください。）