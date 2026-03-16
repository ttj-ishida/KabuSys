# Changelog

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。  

リリースは逆順（最新が上）で並べています。

## [0.1.0] - 2026-03-16

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムのコアモジュール群を追加。
  - src/kabusys/__init__.py
    - パッケージメタ情報（__version__ = "0.1.0"）と公開サブパッケージ定義を追加。
- 設定/環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数からの設定自動読み込み機能を実装（プロジェクトルート検出ロジック: .git または pyproject.toml を基準）。
  - .env と .env.local の読み込み順と override 挙動の実装。OS 環境変数を保護する protected セットを導入。
  - export KEY=val 形式、クォートやエスケープ、インラインコメントの扱いに対応したパーサー実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル 等のプロパティを取得。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）と便利な is_live / is_paper / is_dev プロパティを追加。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得 API を実装。
  - API レート制限対応（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
  - リトライ戦略を実装（最大 3 回、指数バックオフ、408/429/5xx の自動リトライ、429 の Retry-After 優先）。
  - 401 Unauthorized 受信時の ID トークン自動リフレッシュ（一回のみ）を実装。
  - ページネーション対応（pagination_key を用いたループ）。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead Bias 的な追跡を可能にする設計。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性を確保。
  - 型安全な変換ユーティリティ（_to_float / _to_int）を実装。
- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - DataPlatform の3層（Raw / Processed / Feature / Execution）に基づくテーブル群を定義。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤー。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed レイヤー。
  - features, ai_scores など Feature レイヤー。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など Execution レイヤー。
  - 頻出クエリ向けのインデックス群を定義。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成とテーブル/インデックス作成（冪等）を実装。get_connection() も提供。
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 日次 ETL のエントリ run_daily_etl を実装（市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック の順）。
  - 差分更新ロジック: DB 最終取得日を基に date_from を算出、backfill_days により数日前から再取得して API の後出し修正を吸収。
  - 市場カレンダーは lookahead（デフォルト 90 日）分を先読み。
  - 各ステップは独立してエラーハンドリングされ、1 ステップ失敗でも他ステップを継続（Fail-Fast ではない）。
  - ETL 実行結果を表す ETLResult データクラスを追加（品質問題・エラーの収集、辞書化機能あり）。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date 等の差分ヘルパーを提供。
- 監査ログ（Audit）モジュール（src/kabusys/data/audit.py）
  - 信頼できるトレーサビリティを確保するための監査テーブル群を実装（signal_events, order_requests, executions）。
  - order_request_id を冪等キーとして扱う設計、すべての TIMESTAMP を UTC で保存する方針（init_audit_schema で SET TimeZone='UTC' を設定）。
  - 発注フローを追跡するためのインデックス群を定義（status 検索、ID 関連の結合など）。
  - init_audit_db(db_path) により監査ログ専用 DB を初期化可能。
- データ品質チェック（src/kabusys/data/quality.py）
  - 欠損データ検出（OHLC の NULL チェック）、スパイク検出（前日比が閾値超：デフォルト 50%）、主キー重複、日付不整合検出の設計方針を実装。
  - QualityIssue データクラスを追加し、各チェックは QualityIssue のリストを返す（Fail-Fast ではなく全件収集）。
  - DuckDB 上で効率的に動作する SQL ベースのチェック実装（パラメータバインド使用）。
  - check_missing_data / check_spike などのチェック実装（サンプル行の収集とログ出力）。
- パッケージ構造
  - data, strategy, execution, monitoring のパッケージエントリを追加（空 __init__ も配置）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / 補足
- 設計文書（DataPlatform.md, DataSchema.md 等）に基づく構成を想定した実装となっている（各モジュールの docstring に参照記載）。
- ネットワーク/API の挙動（レートリミット、再試行ポリシー、トークンリフレッシュ）は定数で定義されており、将来的に調整可能（例: _RATE_LIMIT_PER_MIN, _MAX_RETRIES, _RETRY_BACKOFF_BASE）。
- 現状はファイルベースで DuckDB を想定。":memory:" を指定してインメモリ DB での実行も可能。
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 今後のリリースで以下が期待されます:
  - strategy / execution / monitoring 層の具体的実装（現在はパッケージエントリのみ）
  - 追加の品質チェック・ETL モニタリング機能・テストカバレッジ強化

---

この CHANGELOG はコードベースの実装内容から推測して作成しています。追加の変更点や補足情報があれば反映します。