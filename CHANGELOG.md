# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

※ 初期リリース（0.1.0）はリポジトリ内コードから推測した機能一覧・設計意図を元に作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-16
初回リリース。日本株自動売買システムのコア基盤（設定管理、データ取得・保存、スキーマ、監査、データ品質チェック）を提供します。

### Added
- パッケージ基礎
  - kabusys パッケージを追加。パッケージバージョンは `0.1.0`。
  - 公開サブパッケージ: data, strategy, execution, monitoring（現状モジュール初期化ファイルを含む）。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む `Settings` を実装。
  - 自動 .env ロード:
    - プロジェクトルート判定は `.git` または `pyproject.toml` を探索して行う（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は .env を上書き）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途想定）。
  - .env 解析の挙動:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のエスケープ、インラインコメントの扱いを考慮。
    - クォートなしの場合は '#' の手前が空白/タブのときのみコメント扱い。
  - 必須設定アクセス時は `_require()` で未設定なら ValueError を投げる。
  - 主要設定プロパティ:
    - J-Quants: JQUANTS_REFRESH_TOKEN
    - kabuステーション API: KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - 環境種別: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL バリデーション

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 基本機能:
    - base URL は https://api.jquants.com/v1、主に日次株価、財務データ、マーケットカレンダーを取得。
  - レート制御:
    - 固定間隔スロットリングで 120 req/min（最小間隔: 60/120 秒）を守る `_RateLimiter` を実装。
  - 再試行・エラーハンドリング:
    - 指数バックオフに基づくリトライ（最大 3 回）。
    - 再試行対象ステータス: 408, 429, および 5xx。
    - 429 の場合は `Retry-After` を優先して待機時間を決定。
    - ネットワークエラー（URLError/OSError）も再試行。
  - 認証トークン処理:
    - `get_id_token()` でリフレッシュトークンから ID トークンを取得（POST `/token/auth_refresh`）。
    - GET 系の `_request()` はモジュールレベルの ID トークンキャッシュを使用し、401 受信時は一度だけトークン自動リフレッシュして再試行する。
  - ページネーション対応取得関数:
    - fetch_daily_quotes (日足 OHLCV)
    - fetch_financial_statements (四半期 BS/PL)
    - fetch_market_calendar (JPX カレンダー)
    - すべて pagination_key によるページングを扱う。
  - DuckDB 保存用関数（冪等化）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE を用いて重複を排除・更新する（fetched_at を UTC で記録）。
  - 型変換ユーティリティ:
    - _to_float: 無効値は None。
    - _to_int: "1.0" のような小数文字列は float 経由で int に変換する。ただし小数部が 0 以外（例: "1.9"）は None を返す（意図しない切り捨てを防止）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - 3 層データモデル（Raw / Processed / Feature）と Execution 層のテーブル DDL を定義。
  - 主なテーブル（抜粋）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリ向け）を追加。
  - init_schema(db_path) によりディレクトリ自動作成後、すべてのテーブル/インデックスを作成（冪等）。":memory:" によるインメモリ DB 対応。
  - get_connection(db_path) で既存 DB に接続（初期化は行わない）。

- 監査ログ（kabusys.data.audit）
  - シグナルから約定までのトレーサビリティ用 DDL を提供。
  - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）を意識した設計。
  - テーブル:
    - signal_events: 戦略が生成したすべてのシグナル（棄却含む）を記録。decision カラムで棄却理由等を表現。
    - order_requests: 発注要求（order_request_id が冪等キー）。order_type に応じたチェック制約（limit/stop の価格制約）を実装。
    - executions: 証券会社からの約定ログ（broker_execution_id はユニークで冪等）。
  - init_audit_schema(conn) / init_audit_db(db_path) を提供。全 TIMESTAMP を UTC で保存するために接続時に `SET TimeZone='UTC'` を実行。
  - インデックスを用意し、status / date / id などで効率的に検索可能。

- データ品質チェック（kabusys.data.quality）
  - DataPlatform 指針に基づく品質チェック実装。
  - チェック項目:
    - 欠損データ検出: check_missing_data — raw_prices の OHLC 欠損を検出（volume は許容）。
    - 異常値（スパイク）検出: check_spike — 前日比の絶対変化率が閾値（デフォルト 50%）を超えるレコードを検出。LAG ウィンドウを使用。
    - 重複チェック: check_duplicates — raw_prices の主キー重複（date, code）を検出。
    - 日付不整合検出: check_date_consistency — 将来日付、market_calendar と矛盾する非営業日のデータを検出（market_calendar テーブルが存在する場合のみチェック）。
  - QualityIssue dataclass を定義し、各チェックは QualityIssue のリスト（全問題を収集）を返す。run_all_checks によりまとめて実行可能。
  - SQL はパラメータバインドを用いて注入リスクを低減。
  - 異常判定閾値: 変数化（_SPIKE_THRESHOLD = 0.5）され、run_all_checks により上書き可能。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 認証トークンは環境変数経由で取得し、モジュール内で ID トークンをキャッシュするが、リフレッシュは安全策として一度のみの自動再試行に制限している（無限再帰防止）。
- .env 読み込みはプロジェクトルート検出に依存し、意図しないディレクトリからの読み込みを防止。

## 注意事項 / 運用メモ
- 必須の環境変数（実行に必須）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 未設定だと Settings のプロパティアクセス時に ValueError を発生させます。
- DuckDB: init_schema() はスキーマとインデックスを全て作成します。初回は必ず init_schema() を使用し、以降は get_connection() で接続する運用を想定。
- J-Quants API のレート上限（120 req/min）を厳守するため、長時間の大量データ取得時は間隔を考慮してください。
- .env パーサーは Bash 互換の単純なサブセットをサポートします。非常に特殊な .env 構成（複雑な改行内クォートなど）は想定外の挙動をする可能性があります。

---

（今後のリリースでは "Added / Changed / Fixed / Security" を分けて記載してください）