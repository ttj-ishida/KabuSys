# CHANGELOG

すべての注目すべき変更を記録します。これは Keep a Changelog のガイドラインに準拠した形式です。

なお、このログはリポジトリのコード内容から推測して作成した初期リリース向けの要約です。

## [0.1.0] - 2026-03-16

### Added
- パッケージ基盤
  - kabusys パッケージ初期バージョンを追加。バージョンは __version__ = "0.1.0"。
  - 公開サブパッケージ: data, strategy, execution, monitoring をエクスポート。

- 設定・環境管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - プロジェクトルートを .git または pyproject.toml を基準に探す `_find_project_root()` を実装し、CWD に依存しない自動 .env ロードを実現。
  - .env パーサー `_parse_env_line()` を実装:
    - コメント、空行を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のエスケープ処理を適切に処理。
    - クォート無しの場合のインラインコメント処理を実装。
  - 自動ロードの優先順位を実装: OS 環境変数 > .env.local > .env。  
    - OS の既存キーは保護され、.env.local は override=True による上書きが可能。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装し、必要な環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）やデフォルト値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV、LOG_LEVEL）をプロパティで提供。
  - `env` / `log_level` の値検証（許容値チェック）を実装。`is_live`, `is_paper`, `is_dev` のユーティリティプロパティを追加。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants API から日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得するクライアントを実装。
  - レート制限対応: 固定間隔スロットリング `_RateLimiter` を導入し、120 req/min を遵守（最小間隔計算を実装）。
  - リトライ機構: 指数バックオフ（最大 3 回）を実装。対象はネットワークエラー、HTTP 408/429 および 5xx 系。429 の場合は Retry-After を優先。
  - 認証トークン管理:
    - refresh token から id_token を取得する `get_id_token()` を実装（POST）。
    - モジュールレベルで id_token をキャッシュし、401 受信時には自動的に 1 回だけリフレッシュしてリトライするロジックを実装（無限再帰防止のため allow_refresh フラグを使用）。
    - ページネーション間でトークンを共有できるようにキャッシュを利用。
  - ページネーション対応のデータ取得関数を追加:
    - `fetch_daily_quotes(...)`
    - `fetch_financial_statements(...)`
    - `fetch_market_calendar(...)`
    - 取得時に fetched_at を UTC で記録するなど、look-ahead bias 対策を意識した設計。
  - DuckDB への保存関数（冪等性）:
    - `save_daily_quotes(conn, records)`
    - `save_financial_statements(conn, records)`
    - `save_market_calendar(conn, records)`
    - 各関数は ON CONFLICT DO UPDATE により重複を排除、PK 欠損行はスキップして警告ログを出力。
  - 型変換ユーティリティ `_to_float` / `_to_int` を実装。文字列や None を安全に数値に変換（厳密な int 変換ルールを導入）。

- データベーススキーマ (kabusys.data.schema)
  - DuckDB 用のスキーマ定義を実装。DataPlatform の 3 層（Raw / Processed / Feature）+ Execution レイヤーに対応したテーブル群を定義。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - テーブル作成 DDL をリスト化し、外部キー依存順に作成する `init_schema(db_path)` を実装。親ディレクトリの自動作成、":memory:" 対応あり。
  - スキーマ初期化は冪等（CREATE IF NOT EXISTS）で安全に何度でも実行可能。
  - 検索パフォーマンスを考慮したインデックス群を作成。

- 監査ログ (kabusys.data.audit)
  - シグナル→発注→約定の監査ログを保存する専用テーブル群を実装（トレーサビリティ重視）。
  - トレーサビリティ階層および設計原則を実装:
    - signal_events（戦略生成シグナル）
    - order_requests（冪等キー order_request_id を持つ発注要求）
    - executions（証券会社の約定ログ、broker_execution_id を冪等キーとして扱う）
  - すべての TIMESTAMP を UTC で保存するように `init_audit_schema(conn)` 内で `SET TimeZone='UTC'` を実行。
  - 監査専用 DB を初期化して接続を返す `init_audit_db(db_path)` を実装。
  - 監査向けのインデックスも作成（status や broker_order_id 等での検索高速化）。

- データ品質チェック (kabusys.data.quality)
  - DataPlatform の品質チェック実装:
    - 欠損データ検出（check_missing_data）：raw_prices の OHLC 欄の NULL を検出（volume は除外）。
    - 異常値検出（check_spike）：前日比スパイク検出。デフォルト閾値は 0.5（50%）。
    - 重複チェック（check_duplicates）：主キー（date, code）の重複を検出。
    - 日付不整合チェック（check_date_consistency）：将来日付や market_calendar と整合しないデータを検出（market_calendar が存在しない場合はスキップ）。
    - 全チェックをまとめて実行する run_all_checks() を実装。
  - QualityIssue データクラスを導入し、各チェックは QualityIssue のリストを返す（Fail-Fast ではなく全件収集）。
  - SQL はパラメータバインドを使用しており、DuckDB の接続を受け取って効率的に処理。

### Changed
- （初期リリースのため変更点はなし）: すべてはこのリリースで導入。

### Fixed
- （初期リリースのため修正点はなし）

### Deprecated
- なし

### Removed
- なし

### Security
- 認証トークンの取り扱いに関してはリフレッシュとキャッシュの制御を実装し、無限再帰を回避する設計を採用。個別のセキュリティ対策（資格情報の暗号化など）は別途検討が必要。

---

Notes / 備考:
- DuckDB を使用するためランタイムに duckdb パッケージが必要です。
- J-Quants API 呼び出しはネットワーク IO を行うため、エラーやレート制限に注意して運用してください。
- 設定値やトークンは .env または環境変数で供給する設計です。`.env.example` を参照して .env を準備することを想定しています。
- 本 CHANGELOG はコードの内容から推測して作成しています。実際のリリースノートは運用ポリシーや追加ドキュメントに合わせて修正してください。