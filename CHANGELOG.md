# CHANGELOG

すべての注目すべき変更は Keep a Changelog を準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [0.1.0] - 2026-03-16

初回リリース — 日本株自動売買システム「KabuSys」の骨組みを実装しました。

### Added
- パッケージ基本情報
  - パッケージ名とバージョンを定義（kabusys.__version__ = "0.1.0"）。
  - 公開モジュールとして data, strategy, execution, monitoring を __all__ に追加。

- 環境変数 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダー実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルート検出は __file__ を起点に親ディレクトリから ".git" または "pyproject.toml" を探索（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途を想定）。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理や対応する閉じクォートの正しい検出。
    - クォートなしの場合は inline コメント（#）判定の挙動を制御（直前が空白/タブの場合はコメントと判定）。
  - OS 環境変数を保護するための protected キーセットを導入し、.env.local による既存 OS 値の上書きを制御。
  - Settings クラスを実装し、主要設定値のプロパティを提供（必須項目は未設定時に ValueError を送出）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須取得。
    - デフォルト値を持つ項目: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本設計:
    - API レート制限: 120 req/min を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。
    - 401 受信時はトークンを自動リフレッシュして最大 1 回リトライ（無限再帰を防止するフラグ allow_refresh）。
    - ページネーション対応、ページ間での ID トークン共有のためのモジュールレベルキャッシュ。
    - 取得日時（fetched_at）を UTC で記録し、Look-ahead Bias 防止を考慮。
    - DuckDB への保存は冪等性を重視（ON CONFLICT DO UPDATE）で重複を排除。
  - HTTP ユーティリティ関数 _request を実装（GET/POST、JSON ボディ、タイムアウト、ヘッダ管理、JSON デコードエラーハンドリング）。
  - get_id_token(refresh_token) を実装（/token/auth_refresh への POST）。
  - データ取得関数を実装:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB 保存関数を実装（冪等）:
    - save_daily_quotes → raw_prices（fetched_at を UTC ISO8601 で保存）
    - save_financial_statements → raw_financials
    - save_market_calendar → market_calendar（HolidayDivision を基に is_trading_day / is_half_day / is_sq_day を算出）
  - データ変換ユーティリティを追加:
    - _to_float（空値・変換失敗は None）
    - _to_int（"1.0" のような文字列を float 経由で処理、非整数の小数は None）

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - DataSchema.md に沿った 3 層（Raw / Processed / Feature）＋Execution 層のテーブル定義を実装。
  - 主なテーブル（抜粋）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY / CHECK）を設定してデータ整合性を強化。
  - 頻出クエリ向けのインデックスを追加。
  - init_schema(db_path) でディレクトリ自動作成後にテーブルとインデックスを作成（冪等）。
  - get_connection(db_path) を提供（既存 DB への接続、初回は init_schema を推奨）。

- 監査ログ（Audit）スキーマ（kabusys.data.audit）
  - シグナル→発注→約定のトレーサビリティを担保する監査テーブル群を定義。
  - トレーサビリティ階層（business_date → strategy_id → signal_id → order_request_id → broker_order_id）を明示。
  - テーブル:
    - signal_events: 戦略が生成したすべてのシグナル（棄却やエラーも記録）
    - order_requests: 発注要求（order_request_id を冪等キーとして扱う、各種チェック制約あり）
    - executions: 証券会社からの約定ログ（broker_execution_id を冪等キーとして扱う）
  - init_audit_schema(conn) で UTC タイムゾーン設定（SET TimeZone='UTC'）およびテーブル/インデックス作成。
  - init_audit_db(db_path) で独立した監査 DB を初期化して接続を返す。

- データ品質チェックモジュール（kabusys.data.quality）
  - DataPlatform.md に基づく品質チェックを実装。各チェックは QualityIssue のリストを返す。
  - 実装されたチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（必須カラムの NULL を検出、volume は対象外）
    - check_spike: 前日比スパイク検出（LAG ウィンドウで前日 close を参照、デフォルト閾値 50%）
    - check_duplicates: raw_prices の主キー重複検出（ON CONFLICT による通常排除の補助）
    - check_date_consistency: 将来日付レコードおよび market_calendar と不整合な非営業日のデータ検出
  - run_all_checks(conn, ...) で全チェックをまとめて実行し、検出した問題を返却。
  - QualityIssue dataclass を定義（チェック名、テーブル、重大度、詳細、サンプル行）。

- ロギング
  - 各モジュールで logger を使用した情報/警告/エラーログを追加（取得件数、保存件数、リトライ情報、スキップ件数等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

---

備考:
- 本バージョンは基盤実装（設定管理、外部 API クライアント、DB スキーマ、監査、品質チェック）を重点的に実装しており、戦略ロジック（strategy）、実行ランタイム（execution）、運用監視（monitoring）の詳細実装は今後のバージョンで追加予定です。
- DB 初期化は冪等で安全に何度でも実行可能ですが、初回起動時は init_schema()/init_audit_db() を呼んでテーブルを作成してください。