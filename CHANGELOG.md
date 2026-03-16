# CHANGELOG

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠しています。

なお、このリポジトリの初期公開バージョンは 0.1.0 です。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-16

### Added
- パッケージ初期構成を追加。
  - モジュール構成: kabusys パッケージとサブパッケージ data, strategy, execution, monitoring（strategy/execution/monitoring は現時点ではプレースホルダ）。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルート判定は `.git` または `pyproject.toml` を起点に行い、CWD に依存しないように設計。
    - 優先順位: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - OS 環境変数を保護するための protected キー集合を導入。
  - 強力な .env パーサ `_parse_env_line` を実装:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い、無効行のスキップ等を正しく処理。
  - `Settings` クラスを導入し、アプリケーション設定をプロパティ経由で提供:
    - J-Quants / kabu API / Slack トークン類の必須設定を取得 (`_require` による必須チェック)。
    - デフォルト値を持つ設定: Kabu API base URL、DuckDB/SQLite のデフォルトパスなど。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の値検証（許可値の列挙）。
    - is_live / is_paper / is_dev の便宜プロパティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本設計:
    - API レート制御（120 req/min）を守る固定間隔スロットリング `_RateLimiter` を実装。
    - リトライ（指数バックオフ）を実装（最大 3 回、対象: 408 / 429 / 5xx、429 は Retry-After を優先）。
    - 401 Unauthorized 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰回避のため allow_refresh フラグ）。
    - ページネーション対応とページ間での id_token キャッシュ共有（_ID_TOKEN_CACHE）。
    - 取得時刻（fetched_at）を UTC で記録し look-ahead bias に配慮。
    - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で実装。
  - API 呼び出しユーティリティ `_request` と認証ヘルパ `get_id_token` を提供。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX 市場カレンダー）
  - DuckDB への保存関数:
    - save_daily_quotes（raw_prices テーブルへ保存、fetched_at を付与、PK 欠損行をスキップ）
    - save_financial_statements（raw_financials テーブルへ保存）
    - save_market_calendar（market_calendar テーブルへ保存、HolidayDivision を解釈）
  - 値変換ユーティリティ `_to_float` / `_to_int`（空値/不正値の安全な処理、"_to_int" は "1.0" を許容し小数部が非ゼロなら None を返す等）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataPlatform 構造に基づく 3 層＋実行層のスキーマを定義。
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY、CHECK、FOREIGN KEY など）を定義。
  - 頻出クエリを考慮したインデックス群を定義。
  - init_schema(db_path) による冪等な初期化関数、get_connection(db_path) を提供。
  - db_path の親ディレクトリが存在しない場合は自動作成。":memory:" によるインメモリ DB にも対応。

- 監査（Audit）スキーマ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定のトレーサビリティを担保する監査テーブル群を実装:
    - signal_events（戦略が生成したシグナルのログ）
    - order_requests（冪等キー order_request_id を持つ発注要求）
    - executions（実際の約定ログ、broker_execution_id を冪等キーとして扱う）
  - すべての TIMESTAMP を UTC で保存する方針（init_audit_schema は接続に対して SET TimeZone='UTC' を実行）。
  - 発注タイプごとのチェック制約（limit / stop / market に対する必須/排他条件）を導入。
  - 監査用インデックス群を定義。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供（既存接続への追加初期化も可能）。

- データ品質チェック（kabusys.data.quality）
  - DataPlatform に基づく品質チェックを実装:
    - 欠損データ検出（check_missing_data）: raw_prices の OHLC 欄の NULL を検出（volume は除外）。
    - 異常値（スパイク）検出（check_spike）: 前日比の絶対変動率が閾値（デフォルト 50%）を超えるものを検出。LAG ウィンドウを使用。
    - 重複チェック（check_duplicates）: raw_prices の主キー重複検出。
    - 日付不整合チェック（check_date_consistency）: 将来日付検出と market_calendar との整合性チェック（非営業日に株価データが入っているか）。
  - QualityIssue dataclass を導入し、各チェックは QualityIssue のリスト（最大サンプル行）を返す設計（Fail-Fast ではなく全件収集）。
  - run_all_checks により全チェックをまとめて実行可能。ログ出力と severity 分類（error / warning）。

### Documentation
- 各モジュールに詳細な docstring を追加し、設計原則や使い方（例: settings の使用例、各関数の挙動）を明記。

### Internal / Implementation
- type hints と現代的な型注釈（| 演算子等）を使用してコードの可読性を向上。
- duckdb を主要な永続層として採用し、DB 初期化の自動化（DDL 実行とインデックス作成）を実装。
- ロギング（logger）を各モジュールに導入し、重要なイベント（取得レコード数、スキップ件数、リトライ警告等）を記録。

### Known limitations / Notes
- strategy, execution, monitoring サブパッケージは現時点では実装の足がかり（__init__.py のみ）となっており、具体的な戦略実装、発注インターフェイス、監視ロジック等は今後の実装予定。
- テストコードは含まれていない（ユニット/統合テストの追加が必要）。
- J-Quants / kabu API の実際の戻り値フォーマットに依存するため、本クライアントの一部は実運用での実データに合わせて微調整が必要な場合がある。

---

この CHANGELOG はコードから推測して作成しています。実際のコミット履歴やリリースノートがある場合はそちらを優先して更新してください。