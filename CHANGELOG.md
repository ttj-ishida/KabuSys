# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- 変更はバージョン単位で記録します（Unreleased → リリース済み）。
- 各バージョンは Added / Changed / Fixed / Deprecated / Removed / Security のカテゴリで整理します。

## [Unreleased]

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買システム「KabuSys」のコア基盤を実装しました。

### Added
- パッケージ基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。
  - 公開サブパッケージとして data / strategy / execution / monitoring を列挙。

- 環境変数・設定管理 (`kabusys.config`)
  - .env ファイル（および .env.local）または OS 環境変数から設定を読み込む自動ローダ実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を起点に探索（作業ディレクトリに依存しない）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサを実装（`export KEY=val`、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - 読み込み時の上書きポリシー:
    - `.env` は既存 OS 環境変数を保護して読み込み（未設定のみ）。
    - `.env.local` は上書き可能（ただし OS 環境変数は保護）。
  - Settings クラスを実装。プロパティ経由で設定を取得:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB, SQLite）等。
    - デフォルト値（例: KABU_API_BASE_URL のローカルデフォルト、DUCKDB_PATH/SQLITE_PATH の既定値）を提供。
    - 入力バリデーション（KABUSYS_ENV は development/paper_trading/live のみ、LOG_LEVEL は標準ログレベルのみ有効）と判定用ユーティリティ（is_live, is_paper, is_dev）。
    - 必須項目が欠けている場合は明示的に ValueError を発生させるヘルパ `_require`。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API 呼び出しユーティリティ `_request` を実装:
    - レート制限（120 req/min）を守る固定間隔スロットリング `_RateLimiter`。
    - 再試行ロジック（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）と Retry-After ヘッダ優先処理。
    - 401 発生時はトークンを自動リフレッシュして 1 回リトライ（無限再帰回避のため allow_refresh フラグを用意）。
    - JSON デコードエラーやネットワークエラーに対する適切な例外処理とログ出力。
    - モジュールレベルの ID トークンキャッシュを提供（ページネーション間で共有）。
  - 認証ヘルパ `get_id_token` を実装（refresh_token → idToken を取得）。
  - データ取得関数（ページネーション対応）を実装:
    - fetch_daily_quotes: 日足 OHLCV 取得（pagination_key 処理）。
    - fetch_financial_statements: 四半期 BS/PL 取得（pagination_key 処理）。
    - fetch_market_calendar: JPX 市場カレンダー取得。
    - 取得件数ログ出力および pagination の二重ループ防止（seen_keys）。
  - DuckDB 保存関数（冪等）を実装:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE による冪等性。PK 欠損行はスキップして警告ログ。
    - fetched_at（UTC ISO 8601）を記録して Look-ahead Bias を防止。

- DuckDB スキーマ定義と初期化 (`kabusys.data.schema`)
  - DataPlatform設計に基づく 3 層＋実行層のテーブル群を DDL で定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）・型定義を含む堅牢なスキーマを提供。
  - 検索パフォーマンスのためのインデックス定義（頻出クエリパターンを想定）。
  - init_schema(db_path) でディレクトリ自動作成を行い、全テーブル／インデックスを作成して接続を返す（冪等）。
  - get_connection で既存 DB への接続を返す（初期化は行わない）。

- 監査ログ（トレーサビリティ） (`kabusys.data.audit`)
  - シグナル → 発注 → 約定までを UUID 連鎖でトレースする監査テーブルを実装:
    - signal_events, order_requests, executions
    - order_request_id を冪等キーとすることで二重発注を防止。
    - 詳細なステータス列、エラーメッセージ、updated_at を含む。
  - 監査用のインデックス群を定義（status スキャンや broker_order_id 紐付けなど）。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供。タイムゾーンを UTC に固定（SET TimeZone='UTC'）。

- データ品質チェックモジュール (`kabusys.data.quality`)
  - QualityIssue データクラス（チェック名、テーブル、重大度、詳細、サンプル行）を定義。
  - 以下のチェックを実装:
    - check_missing_data: raw_prices の OHLC 欠損検出（必須カラムの NULL 検出）。
    - check_spike: 前日比によるスパイク検出（デフォルト閾値 0.5 = 50%）。
    - check_duplicates: raw_prices の主キー重複検出。
    - check_date_consistency: 将来日付と market_calendar による非営業日データの検出（market_calendar が存在しない場合はスキップ）。
  - run_all_checks で一括チェックを実行し、すべての検出結果を返す（Fail-Fast ではなく全件収集）。
  - DuckDB 上で効率的に動作する SQL 実装とパラメータバインド（?）を使用した安全なクエリ。

- パッケージ構成（空の __init__ を準備）
  - data / strategy / execution / monitoring のサブパッケージ用の初期ファイルを配置。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- なし。

### Removed
- なし。

### Security
- 環境変数読み込みでは既存の OS 環境変数をプロテクトする仕組みを導入（`.env` の読み込みで上書きされない）。
- .env ファイル読み込み時はファイル読み込み失敗を警告に留め、例外でアプリを停止しない設計。

### Notes / Implementation details / Limitations
- DuckDB に依存します（duckdb パッケージが必要）。
- HTTP クライアントは標準ライブラリ urllib を使用。必要に応じて後日 Requests 等への切替を検討できます。
- J-Quants API のエンドポイントは v1 固定（_BASE_URL）。
- get_id_token は refresh token を settings から取得する想定。トークン管理のさらなる強化（期限管理など）は今後の課題です。
- 市場カレンダーの HolidayDivision は実装内で解釈（取引日/半日/SQ）されています。
- 各保存処理は ON CONFLICT DO UPDATE を利用した冪等処理だが、外部からの直接挿入やスキーマ変更による不整合に備えてデータ品質チェックを提供しています。

---

（注）この CHANGELOG はソースコードから推測して作成しています。実際のリリースノートは、実装経緯や意図に応じて適宜更新してください。