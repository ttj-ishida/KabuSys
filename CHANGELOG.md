# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。<https://keepachangelog.com/ja/1.0.0/>

なお、この CHANGELOG はリポジトリ内のコードから推測して作成した初期リリース記録です。

## [Unreleased]

- （今後の変更をここに記載）

---

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システム「KabuSys」のコアコンポーネントを実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ基礎
  - パッケージ初期化（kabusys.__init__）を追加。バージョン情報と公開サブモジュールを定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーを実装（export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメントの扱い、無効行スキップ等）。
  - .env 読み込み時の保護機構（OS 環境変数を protected として上書き防止、.env.local による上書きサポート）。
  - Settings クラスを実装し、アプリ設定のプロパティ化（J-Quants、kabu API、Slack、DB パス、実行環境、ログレベル等）。入力検証（env 値・ログレベル）とヘルパーメソッド（is_live / is_paper / is_dev）を提供。
  - デフォルトの DB パス: DuckDB は data/kabusys.duckdb、SQLite は data/monitoring.db。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API との通信を行う HTTP ユーティリティを実装。JSON デコードエラーの検出とエラーメッセージ整備。
  - レートリミッタ（固定間隔スロットリング）を実装し、J-Quants の制限（120 req/min）を守る設計。
  - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）。429 の場合は Retry-After ヘッダを優先。
  - 401 Unauthorized 受信時にリフレッシュトークンで自動的に id_token を再取得して一度だけリトライする機能（無限再帰対策あり）。
  - id_token のモジュールレベルキャッシュを実装（ページネーション間で共有）。
  - ページネーション対応の取得関数を実装:
    - fetch_daily_quotes: 株価日足（OHLCV）
    - fetch_financial_statements: 四半期財務データ（BS/PL）
    - fetch_market_calendar: JPX マーケットカレンダー
  - DuckDB への保存関数（冪等性を保証）:
    - save_daily_quotes: raw_prices に ON CONFLICT DO UPDATE で保存。fetched_at を UTC ISO 形式で保存。
    - save_financial_statements: raw_financials に冪等保存。
    - save_market_calendar: market_calendar に冪等保存（HolidayDivision を解釈して is_trading_day/is_half_day/is_sq_day を決定）。
  - 入力変換ユーティリティ (_to_float, _to_int) を追加。文字列・空文字・数値混在に対する堅牢な変換ロジックを実装（例: "1.0" を int に変換する際の注意点、非整数の切り捨てを避ける等）。
  - トークン取得ヘルパー get_id_token(refresh_token=None) を実装（settings からの既定トークン参照、POST による取得）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataPlatform に基づく 3 層（Raw / Processed / Feature）および Execution 層を含む包括的な DDL を定義。
  - Raw 層: raw_prices, raw_financials, raw_news, raw_executions
  - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature 層: features, ai_scores
  - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - パフォーマンス向上のためのインデックス定義（銘柄×日付やステータス検索パターン等）。
  - init_schema(db_path) によりデータベースファイルの親ディレクトリ自動作成とテーブル一括作成（冪等）。get_connection(db_path) で既存 DB へ接続。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL フローを実装（run_daily_etl）。処理は市場カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック の順で実行。
  - 差分更新ロジック: DB の最終取得日を基に date_from を自動算出、backfill_days による再取得（デフォルト 3 日）で API の後出し修正を吸収。
  - 市場カレンダーは lookahead をサポート（デフォルト 90 日）し、営業日調整に利用。
  - 個別ジョブ関数を公開:
    - run_prices_etl, run_financials_etl, run_calendar_etl（各々差分取得と保存を行う）
  - ETLResult dataclass を導入（取得数・保存数・品質問題・エラーを集約）。品質チェックの結果や例外は収集して ETL を継続する設計（Fail-Fast ではない）。
  - DB 存在確認、最大日付取得ヘルパー (_table_exists, _get_max_date) を実装。
  - 営業日調整ヘルパー (_adjust_to_trading_day) を実装（market_calendar が無い場合はフォールバック）。

- 監査ログ（トレーサビリティ）実装（kabusys.data.audit）
  - シグナル→発注→約定のトレーサビリティを保証する監査用テーブルを定義:
    - signal_events（戦略の生成したシグナルを全て記録）
    - order_requests（order_request_id を冪等キーとして保持）
    - executions（証券会社の約定情報、broker_execution_id をユニークに管理）
  - テーブル制約（チェック、外部キー、limit/stop/market の価格要求チェック等）を厳密に定義。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供。全 TIMESTAMP を UTC で保存するために init で SET TimeZone='UTC' を実行。
  - 監査用途のインデックスを追加（ステータス検索、signal_id や broker_order_id による結合高速化等）。
  - 監査ログは削除しない前提（ON DELETE RESTRICT）で設計。

- 品質チェックモジュール（kabusys.data.quality）
  - DataPlatform の品質チェックを実装:
    - 欠損検出（raw_prices の OHLC 欄）
    - 異常値（スパイク）検出（前日比の絶対変動率が閾値を超える場合、デフォルト 50%）
    - （重複・日付不整合等のチェックは設計に明示、SQL ベースで実装可能な枠組みを提供）
  - QualityIssue dataclass を導入（check_name, table, severity, detail, sample rows）。
  - 各チェックは問題点を全件収集して QualityIssue のリストを返す（Fail-Fast ではない）。

- パッケージ構造（空 __init__）
  - data, strategy, execution 各サブパッケージの __init__ を用意し、将来の拡張に備える。

### Security
- 環境変数取り扱いにおいて、OS 環境変数を protected として .env による上書きを防止する仕組みを導入。

### Notes / Usage / Migration
- 環境変数必須項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は Settings のプロパティ経由で取得され、未設定時は ValueError が発生します。
- DuckDB 初期化は data.schema.init_schema() を呼び出して行ってください。監査ログは init_schema の接続に対して data.audit.init_audit_schema() を呼ぶことで追加できます。
- J-Quants の API 呼び出しは内部でレート制御・リトライ・トークンリフレッシュを行うため、通常の利用ではこれらを意識せずに fetch_* 関数を呼べます。ただしテストや特殊用途で自動トークンロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

---

開発者向けの補足や追加の仕様（DataPlatform.md, DataSchema.md 等）についてはリポジトリ内のドキュメントに従ってください。必要であれば、この CHANGELOG をもとにより詳細なリリースノート（導入手順、環境変数一覧、サンプル利用例など）を作成します。