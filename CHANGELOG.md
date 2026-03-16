# CHANGELOG

すべての重要な変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の慣習に従います。
セマンティックバージョニングを採用します（https://semver.org/）。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買プラットフォームの基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ初期化ファイルを追加（kabusys.__init__）。公開モジュールとして data, strategy, execution, monitoring を定義。

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - プロジェクトルート判定は .git または pyproject.toml を基準に探索（CWD 非依存）。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを考慮）。
  - 環境変数保護（OS 環境変数を protected として .env.local の上書きを制御）。
  - Settings クラスを提供し、以下の設定をプロパティとして取得／バリデーション:
    - J-Quants / kabuAPI / Slack トークン類の必須チェック（未設定時は ValueError を送出）
    - DB パス（DuckDB / SQLite）の既定値と Path 型返却
    - KABUSYS_ENV の有効値チェック（development / paper_trading / live）
    - LOG_LEVEL の有効値チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパープロパティ

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API 呼び出し共通実装:
    - ベース URL とタイムアウト、Accept/Content-Type ヘッダの設定
    - JSON デコードのエラーハンドリング（デコード失敗時に詳細を含む例外）
  - レート制御:
    - 固定間隔スロットリング（120 req/min）を実装する RateLimiter（モジュール単位で共有）
  - リトライ / バックオフ:
    - 指数バックオフを用いた最大 3 回のリトライ（408/429/5xx 等を対象）
    - 429 の場合は Retry-After ヘッダを優先
  - 認証トークン管理:
    - リフレッシュトークンから ID トークンを取得する get_id_token()
    - モジュールレベルの ID トークンキャッシュと、401 受信時の自動リフレッシュ（1 回のみ）
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX カレンダー）
    - ページネーションキーを保持して続ページを取得し、重複検出でループ終了
  - DuckDB への保存関数（冪等化）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - 保存時に fetched_at を UTC ISO8601 で記録
    - INSERT ... ON CONFLICT DO UPDATE による重複排除（冪等性）
    - PK 欠損レコードはスキップして警告ログ出力

- DuckDB スキーマ定義と初期化 (`kabusys.data.schema`)
  - DataPlatform 設計に基づく 3 層（Raw / Processed / Feature）＋Execution レイヤのテーブル定義を実装
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェック制約（CHECK）や主キーを付与
  - 頻出クエリに対するインデックス定義を追加
  - init_schema(db_path) によりディレクトリ作成→全 DDL 実行（冪等）
  - get_connection(db_path) による既存 DB への接続

- ETL パイプライン (`kabusys.data.pipeline`)
  - run_daily_etl による日次 ETL エントリポイントを実装（市場カレンダー→株価→財務→品質チェック）
  - run_calendar_etl / run_prices_etl / run_financials_etl の差分更新ロジックを実装
    - 差分更新は DB の最終取得日を基に自動算出
    - backfill_days による再取得（後出し修正吸収）デザイン（デフォルト 3 日）
    - calendar は lookahead（デフォルト 90 日）を先読みして営業日調整に利用
  - ETLResult データクラスを実装（取得件数／保存件数／品質問題／エラー保持）
  - 各ステップを独立して例外ハンドリング（1 ステップ失敗でも他ステップを継続）
  - quality モジュールと連携して品質チェックを実行（run_all_checks を想定）

- 監査ログ（トレーサビリティ） (`kabusys.data.audit`)
  - シグナル→発注→約定の監査テーブルを実装（UUID 連鎖で完全トレース可能）
    - signal_events（戦略が生成したシグナルを記録）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ）
      - order_type に応じた CHECK（limit/stop の価格必須制約など）
    - executions（証券会社からの約定ログ、broker_execution_id をユニークキーとして冪等）
  - 監査テーブル用のインデックスを定義（status / date / code 等の検索を高速化）
  - init_audit_schema(conn) / init_audit_db(db_path) を提供
  - すべての TIMESTAMP を UTC で扱う（SET TimeZone='UTC' を実行）

- データ品質チェック (`kabusys.data.quality`)
  - QualityIssue データクラスを実装（チェック名・対象テーブル・重大度・サンプル行等を含む）
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欠損検出（サンプル取得・件数カウント・severity="error"）
    - check_spike: LAG ウィンドウを用いた前日比スパイク検出（デフォルト閾値 50%）
  - 各チェックは DuckDB SQL を用い効率的に実行し、サンプル行（最大 10 件）を返却
  - 品質チェックは Fail-Fast とせず、全問題を収集して呼び出し元に返す設計

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 外部 API トークンは環境変数経由で取得し、コード内に埋め込まない運用を想定（Settings に必須チェックを導入）。

---

注:
- 一部機能（例: quality モジュール内の全チェック群の完全実装、strategy や execution 層の具体的実装）は今後の実装対象です。pipeline からは quality.run_all_checks が呼ばれていますが、運用時は全チェックの実装と統合を確認してください。
- 本 CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やリリースノート作成時にはコミット履歴・リリースプロセスに基づき加筆修正してください。