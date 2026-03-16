# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。<br>
初版リリース: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買システムのコアライブラリを実装しました。主要な追加点を以下に示します。

### Added
- パッケージ基本情報
  - パッケージ名とバージョンを定義（kabusys/__init__.py, __version__ = "0.1.0"）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする機能を追加。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（配布後の動作を配慮）。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env パーサは export KEY=val 形式、シングル/ダブルクオート、エスケープ、インラインコメントに対応。
  - Settings クラスを実装し、アプリ設定をプロパティ経由で取得可能（J-Quants トークン、kabu API、Slack、DB パス、環境種別、ログレベル等）。
  - 環境変数の必須チェック（_require）と値検証（KABUSYS_ENV / LOG_LEVEL の妥当性チェック）を実装。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得用 API クライアントを実装。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - レート制限制御: 固定間隔スロットリングで 120 req/min に対応する RateLimiter を実装。
  - 再試行ロジック: 指数バックオフで最大 3 回リトライ（ネットワークエラー、HTTP 408/429/5xx を対象）。429 の場合は Retry-After を尊重。
  - 401 応答時の自動トークンリフレッシュ（1回のみ）とトークンキャッシュ（_ID_TOKEN_CACHE / _get_cached_token）。
  - 取得タイミングのトレースのため fetched_at を UTC タイムスタンプで付与。
  - DuckDB へ保存する save_* 関数を用意（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - 挿入は冪等性を考慮して ON CONFLICT DO UPDATE を使用。
    - PK 欠損レコードはスキップしログ出力。

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - DataPlatform に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を実装。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw 層テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層。
  - features, ai_scores 等の Feature 層。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層。
  - 検索パフォーマンスを考慮したインデックス定義を実装。
  - init_schema(db_path) によりディレクトリ自動作成＋全テーブル・インデックス作成（冪等）。
  - get_connection(db_path) による既存 DB 接続取得を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL のエントリポイント run_daily_etl を実装。
    - 処理順: カレンダー取得（先読み） → 株価差分取得（backfill） → 財務差分取得（backfill） → 品質チェック（オプション）。
    - 個別ジョブ: run_calendar_etl, run_prices_etl, run_financials_etl を提供。
  - 差分更新ロジック:
    - DB の最終取得日を基に未取得分のみを取得。
    - backfill_days（デフォルト 3）で最終取得日の数日前から再取得して API の後出し修正を吸収。
    - カレンダーは target_date + lookahead_days（デフォルト 90 日）まで先読み。
  - 品質チェック実行のフラグ（run_quality_checks）とスパイク閾値の注入をサポート。
  - ETL 実行結果を ETLResult データクラスで返却（品質問題・エラーの集約、JSON 互換辞書化 to_dict）。

- データ品質チェック（kabusys.data.quality）
  - QualityIssue データクラスと複数のチェック関数を実装。
    - 欠損データ検出（check_missing_data）: raw_prices の OHLC 欠損を検出（volume は許容）。
    - スパイク検出（check_spike）: 前日比の絶対変動率が閾値（デフォルト 50%）を超えるレコードを検出（LAG ウィンドウを使用）。
    - 各チェックはサンプル行（最大 10 件）付きで QualityIssue のリストを返す設計（Fail-Fast ではなく収集）。
  - SQL パラメータバインドを利用し、効率的かつ安全に実行。

- 監査ログ・トレーサビリティ（kabusys.data.audit）
  - 戦略→シグナル→発注→約定までのトレースを支える監査スキーマを実装。
    - signal_events（シグナル生成ログ）、order_requests（冪等キー付きの発注要求）、executions（約定ログ）。
    - UUID ベースの ID 層次構造、order_request_id を冪等キーとして二重発注を防止。
  - すべての TIMESTAMP を UTC で保存する方針（init_audit_schema は SET TimeZone='UTC' を実行）。
  - テーブル制約（チェック制約、FOREIGN KEY）とインデックスを整備。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供。

- ユーティリティ関数
  - 型変換ユーティリティ: _to_float, _to_int（文字列・数値を安全に変換し不整合時は None を返す）。
  - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists, _get_max_date）。
  - 営業日調整ヘルパー（_adjust_to_trading_day）：非営業日の場合、直近の過去の営業日に調整。

- ロギングとエラーハンドリング
  - 各主要処理でのログ出力（info/warning/error/exception）を追加。
  - ETL は各ステップを独立して例外処理し、1 ステップの失敗が他を停止させない設計。

### Changed
- 該当なし（初回リリース）

### Fixed
- 該当なし（初回リリース）

### Security
- 該当なし（初回リリース）

注意:
- ここに記載している機能はコード内容から推測した実装概要に基づきます。実際の挙動や運用上の要件（例: DB スキーマの追加制約や運用手順等）は別途ドキュメントを参照してください（DataSchema.md / DataPlatform.md 等への言及がコード内にあります）。