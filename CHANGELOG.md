# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージを追加。__version__ を "0.1.0" に設定し、主要モジュール（data, strategy, execution, monitoring）をエクスポート。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルと環境変数から設定を自動読み込みする仕組みを実装。プロジェクトルートは .git または pyproject.toml を起点に探索（CWDに依存しない）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト向け）。
  - .env パーサーは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。
  - Settings クラスを提供。J-Quants / kabu / Slack / データベースなどの必須/任意設定をプロパティで取得（必須項目未設定時は ValueError を送出）。
  - デフォルト値を提供（例: KABU_API_BASE_URL, DUCKDB_PATH -> data/kabusys.duckdb, SQLITE_PATH -> data/monitoring.db）。
  - KABUSYS_ENV と LOG_LEVEL の値検証 (許容値チェック)。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装。
  - レート制限制御（固定間隔スロットリング）を実装し、デフォルトで 120 req/min（最小間隔 0.5s）を遵守。
  - リトライロジック（指数バックオフ、最大 3 回、対象: 408/429/>=500 / ネットワークエラー）を実装。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時はリフレッシュ処理を行い 1 回リトライ（無限再帰を防止する allow_refresh フラグ）。
  - ID トークンのモジュールレベルキャッシュを実装し、ページネーション間で共有。
  - ページネーション対応のデータ取得関数を提供:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務四半期データ）
    - fetch_market_calendar（JPX カレンダー）
  - 取得日時（fetched_at）を UTC ISO8601 で付与して返却/保存を意識（Look-ahead Bias 防止のためトレース可能）。
  - 型変換ユーティリティ (_to_float, _to_int) を実装。float/int の変換ルールを明確化（不正な小数は None）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataLayer（Raw / Processed / Feature / Execution）を想定した包括的な DDL を提供。
  - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
  - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature レイヤー: features, ai_scores
  - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）を付与。
  - 頻出クエリに対するインデックス群を定義。
  - init_schema(db_path) 関数で冪等にスキーマを初期化、get_connection 関数で既存 DB に接続可能。
  - ディレクトリ自動作成（db_path の親ディレクトリが存在しない場合）。

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL のエントリ run_daily_etl を実装。処理フロー:
    1. 市場カレンダー ETL（先読み lookahead、デフォルト 90 日）
    2. 株価日足 ETL（差分更新 + backfill、デフォルト backfill_days=3）
    3. 財務データ ETL（差分更新 + backfill）
    4. 品質チェック（オプション）
  - 差分取得ロジック: DB の最終取得日を取得して未取得範囲のみ API から取得。初回ロード時は J-Quants データ開始日（2017-01-01）を使用。
  - run_prices_etl / run_financials_etl / run_calendar_etl を個別に実行可能。
  - ETL 実行結果を表す ETLResult dataclass を導入。品質問題やエラーを集約して返す。各ステップは独立してエラーハンドリングされ、1 ステップ失敗でも他ステップは継続する設計（Fail-Fast ではない）。
  - カレンダー取得後に非営業日は直近の営業日に調整するヘルパー _adjust_to_trading_day を実装。

- データ品質チェック（kabusys.data.quality）
  - QualityIssue dataclass を導入し、チェック結果を構造化して返却。
  - チェック実装（少なくとも以下を実装／設計）:
    - check_missing_data: raw_prices の必須カラム（open/high/low/close）の欠損検出（検出時は error として報告）。
    - check_spike: 前日比のスパイク検出（LAG ウィンドウを用い、デフォルト閾値 50%）。
  - DuckDB 上の SQL を用いて効率的に検査。サンプル行（最大 10 件）を返す。

- 監査ログ（トレーサビリティ）（kabusys.data.audit）
  - シグナルから約定に至る監査階層をサポートするテーブル群を追加:
    - signal_events（戦略が生成したシグナルのログ）
    - order_requests（発注要求 / 冪等キー order_request_id）
    - executions（証券会社からの約定ログ / broker_execution_id をユニークに保持）
  - init_audit_schema(conn) / init_audit_db(db_path) により監査テーブルを初期化。UTC タイムゾーンを強制（SET TimeZone='UTC'）。
  - 各テーブルに詳細な制約とインデックスを設定（status カラムや created_at/updated_at、チェック制約、外部キー、ユニークインデックス等）。
  - order_request_id を冪等キーとして設計し、二重発注防止を想定。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Security
- 認証トークンの取り扱いに注意:
  - get_id_token はリフレッシュトークンを使って ID トークンを取得。_request は 401 を検出した場合に自動リフレッシュを試みる仕組みを持つ（ただし allow_refresh=False により無限再帰を防止）。
  - 環境変数保護: .env の自動ロード時に OS 環境変数は protected として上書きされない。

### Notes / Implementation details
- DuckDB の INSERT は ON CONFLICT DO UPDATE を使い冪等性を担保（raw → processed 層のアップサート方針）。
- jquants_client のレート制限は固定間隔スロットリング（最小間隔）で実装しており、短時間のバーストが許容されない環境を想定。
- quality モジュールの設計では複数チェックを行い、呼び出し元が重要度に応じて処理継続/停止を判断することを想定している（ETL は Fail-Fast ではなく全件収集）。
- データベース・ファイルのデフォルトパスや API のエンドポイント等は Settings 経由でカスタマイズ可能。

今後の予定（例）
- strategy、execution、monitoring サブモジュールの実装（現状はパッケージ配下にプレースホルダあり）。
- quality モジュールの追加チェック（主キー重複、将来日付・営業日外のデータ検出など）を拡充。
- テストカバレッジの拡充と CI ワークフロー整備。

---------------------------------------------------------------------
この CHANGELOG はコードベースとそのドキュメント文字列から推測して作成しています。実際の機能は実装・仕様変更により差異が生じる可能性があります。