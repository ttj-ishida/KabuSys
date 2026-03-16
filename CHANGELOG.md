Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

Unreleased
----------

（なし）

0.1.0 - 2026-03-16
------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - 基本パッケージ情報:
    - バージョン: 0.1.0
    - パッケージ公開名: kabusys
    - __all__ に data, strategy, execution, monitoring を公開

- 設定/環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を自動読み込み
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化
    - プロジェクトルート検出は __file__ を基準に .git または pyproject.toml を探索
  - .env 行パーサ実装
    - export KEY=val 形式対応
    - シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを考慮
    - 無効行（空行、コメント、キー無し行）はスキップ
  - Settings クラスを提供（プロパティでアクセス）
    - J-Quants / kabu API / Slack / データベースパス等の設定をプロパティ経由で取得
    - 必須変数は未設定時に ValueError を送出
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）
    - duckdb/sqlite のパスを Path オブジェクトで返却

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティ（JSON 入出力、パラメータエンコード）
  - レート制御: 固定間隔スロットリング実装（デフォルト 120 req/min）
  - リトライロジック:
    - 指数バックオフ、最大 3 回
    - 対象ステータス: 408, 429, >=500、およびネットワークエラー
    - 429 の場合は Retry-After ヘッダを優先
  - トークン管理:
    - リフレッシュトークンから id_token を取得する get_id_token()
    - モジュールレベルの id_token キャッシュを利用し、401 発生時は自動リフレッシュして1回リトライ
  - ページネーション対応でデータ取得関数を提供:
    - fetch_daily_quotes (株価日足 / OHLCV)
    - fetch_financial_statements (財務データ：四半期 BS/PL)
    - fetch_market_calendar (JPX マーケットカレンダー)
  - DuckDB への保存関数（冪等）
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE を使用して重複を排除
    - fetched_at を UTC タイムスタンプで付与
    - PK 欠損行はスキップし、スキップ件数をログ出力
  - 入力値変換ユーティリティ:
    - _to_float, _to_int（安全に None を返す挙動、"1.0" などの変換ルールを考慮）

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - 3 層アーキテクチャのテーブル定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェックと PRIMARY KEY/FOREIGN KEY 制約を定義
  - 検索用インデックスを多数定義（頻出クエリパターンを想定）
  - init_schema(db_path) によりディレクトリ自動作成・DDL 実行で初期化（冪等）
  - get_connection(db_path) で既存 DB への接続を返却

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL のエントリ run_daily_etl を実装
    - 処理順: 市場カレンダー ETL → 株価日足 ETL → 財務データ ETL → 品質チェック（オプション）
    - 各ステップは個別に例外処理され、1 ステップ失敗でも他ステップは継続
    - backfill_days により最終取得日の数日前から再取得して API の後出し修正を吸収
    - calendar_lookahead_days によりカレンダーを先読み
    - ETLResult データクラスで実行結果（取得件数、保存件数、品質問題、エラー）を返却
  - 差分更新ユーティリティ:
    - テーブル最終日取得関数（get_last_price_date / get_last_financial_date / get_last_calendar_date）
    - 営業日調整ロジック（_adjust_to_trading_day）：非営業日を直近の過去営業日に補正
    - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl（差分取得 + 保存）

- 監査ログ（トレーサビリティ） (kabusys.data.audit)
  - 監査用テーブル群を定義・初期化する機能を追加
    - signal_events: 戦略が生成したシグナルを記録（棄却・エラー含む）
    - order_requests: 発注要求（order_request_id を冪等キーとして採用）、複数チェック制約（limit/stop/market の必須/排他条件）
    - executions: 証券会社からの約定ログ（broker_execution_id をユニーク・冪等キーとして扱う）
  - init_audit_schema(conn) で UTC タイムゾーンを設定しテーブル・インデックスを作成（冪等）
  - init_audit_db(db_path) による専用 DB 初期化サポート
  - 監査設計に関するドキュメント化（トレーサビリティ階層、ステータス遷移、削除禁止方針など）

- データ品質チェック (kabusys.data.quality)
  - QualityIssue データクラスを定義（check_name, table, severity, detail, rows）
  - チェック実装（SQL ベース、DuckDB で効率処理、パラメータバインド使用）
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欄の欠損（volume は除外）
    - スパイク検出 (check_spike): 前日比の急騰・急落を LAG ウィンドウで検出（デフォルト 50%）
    - （今後）重複チェック・日付不整合チェック等を想定する設計
  - 各チェックは全件収集方式（Fail-Fast ではない）、呼び出し側で重大度に応じて対応可能

Misc / Utilities
- ロギング位置取りおよび INFO/WARNING/ERROR ログ出力を整備（各モジュール）
- モジュール設計時にテスト容易性を考慮（id_token 注入、明確な引数 / 戻り値）

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Security
- （無し）

注記
- 各 save_* 関数は DuckDB に対して ON CONFLICT DO UPDATE を利用するため冪等性を担保しています。ただしスキーマや制約の変更は既存データに影響する可能性があるため、アップグレード時はマイグレーション方針を検討してください。
- J-Quants API のレート制限（120 req/min）やリトライ方針は実運用に合わせて変更可能です（定数で調整）。
- ETL の品質チェックは警告／エラーを返しつつ ETL を継続する設計です。重大度の高い問題は運用側で自動停止するか通知する仕組みを追加することを推奨します。