# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-16
初回リリース

### Added
- パッケージ初期構成: kabusys (バージョン 0.1.0)
  - src/kabusys/__init__.py にてパッケージ名と公開モジュールを定義。

- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - コメント（#）の扱いを文脈に応じて処理。
  - .env の読み込み時に OS 環境変数を保護する protected 上書き制御を実装（.env と .env.local の読み込み優先順位を維持）。
  - Settings クラスを提供:
    - J-Quants / kabu ステーション / Slack / データベースパス等のプロパティ。
    - 必須環境変数未設定時は ValueError を送出する _require() を採用。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - is_live / is_paper / is_dev ヘルパーを追加。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）
  - 取得対象: 日足（OHLCV）、四半期財務（BS/PL）、JPX マーケットカレンダー。
  - レート制御: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
  - リトライロジック: 指数バックオフ（基数=2）、最大リトライ回数 3、対象ステータスコード（408, 429, 5xx）を考慮。
  - 401 レスポンス時は ID トークンを自動リフレッシュして 1 回だけリトライ（無限再帰を防止する allow_refresh フラグ実装）。
  - ページネーション対応（pagination_key を利用して全ページを取得）。
  - フェッチ時刻（fetched_at）を UTC で記録（Look-ahead Bias 対策）。
  - DuckDB へ保存するための冪等な保存関数を提供（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 型変換ユーティリティ: _to_float, _to_int（float 文字列の扱い、切り捨て回避ロジックを含む）。
  - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）。

- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）
  - 3 層設計（Raw / Processed / Feature）および Execution 層を含むテーブル定義を実装。
  - 主なテーブル（例）:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種インデックス定義（頻出クエリを考慮）。
  - init_schema(db_path) によりディレクトリ作成→テーブル/インデックス作成（冪等）。
  - get_connection(db_path) を提供（既存 DB への接続）。

- 監査ログ（トレーサビリティ）モジュールを追加（src/kabusys/data/audit.py）
  - シグナル／発注要求／約定を記録する監査テーブルを提供:
    - signal_events, order_requests (order_request_id を冪等キーとして扱う), executions
  - テーブル作成順とインデックス（signal_events 日付／銘柄検索、order_requests.status 検索等）を定義。
  - init_audit_schema(conn) は接続上でタイムゾーンを UTC に設定して監査テーブルを初期化。
  - init_audit_db(db_path) により監査用 DB の初期化をサポート。

- データ品質チェックモジュールを追加（src/kabusys/data/quality.py）
  - 主な品質チェック:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欄の欠損検出（サンプル最大 10 件返却）。
    - 異常値検出 (check_spike): 前日比スパイク検出（デフォルト閾値 50%）。
    - 重複チェック (check_duplicates): raw_prices の主キー重複検出。
    - 日付不整合検出 (check_date_consistency): 将来日付・market_calendar と矛盾するデータ検出。
  - 各チェックは QualityIssue オブジェクトのリストを返す（エラー／警告レベルを含む）。
  - run_all_checks(conn, ...) で一括実行し、検出したすべての問題を返却。
  - SQL は DuckDB を直接使用し、パラメータバインド（?）でインジェクションリスクを低減。

- プレースホルダモジュール:
  - src/kabusys/execution/__init__.py（空）
  - src/kabusys/strategy/__init__.py（空）
  - src/kabusys/monitoring/__init__.py（空）
  - これらは将来の戦略・発注実行・監視機能の拡張ポイント。

### Changed
- 該当なし（初回リリース）

### Fixed
- 該当なし（初回リリース）

### Security
- J-Quants トークンの自動リフレッシュとキャッシュ制御により、認証の扱いを安全に実装。
- .env 読み込みは OS 環境変数を保護する仕組みを提供（意図しない上書きを防止）。

---

注:
- 各モジュールの詳細な仕様（例: DataPlatform.md, DataSchema.md への言及）はソース内ドキュメントに記載されています。使用方法・初期化手順はそれらを参照してください。