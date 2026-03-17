# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

<!--
  例:
  ## [Unreleased]
  ## [0.1.0] - 2026-03-17
-->

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。

### 追加
- パッケージ初期化
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
  - 公開モジュール: `data`, `strategy`, `execution`, `monitoring`（パッケージのエントリポイント）

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは `.git` または `pyproject.toml` を基準に検出）。
  - 読み込み順序: OS 環境 > .env.local（上書き） > .env（未設定のみ）。
  - 自動ロード無効化オプション: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応）。
  - 必須値の取得ヘルパー `_require()` と型検証（`KABUSYS_ENV`, `LOG_LEVEL` の検証）。
  - Settings クラスで主要設定をプロパティとして公開:
    - J-Quants: `jquants_refresh_token`
    - kabuステーション: `kabu_api_password`, `kabu_api_base_url`
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`（デフォルト `data/kabusys.duckdb`）、`sqlite_path`（デフォルト `data/monitoring.db`）
    - 環境フラグ: `env`, `is_live`, `is_paper`, `is_dev`
    - ログレベル検証

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - レート制御: 固定間隔スロットリングで 120 req/min を保証する `_RateLimiter` を実装。
  - 冪等性を考慮した DuckDB 保存ロジック（`save_*` 関数群）は `ON CONFLICT DO UPDATE` を利用。
  - リトライ戦略: 指数バックオフ、最大リトライ回数 3（408/429/5xx を対象）。429 の場合 `Retry-After` を尊重。
  - 401 応答時の自動トークンリフレッシュ（1 回だけリトライ）を実装。
  - ページネーション対応で `pagination_key` を追跡する fetch 関数:
    - fetch_daily_quotes / save_daily_quotes（株価日足、OHLCV）
    - fetch_financial_statements / save_financial_statements（四半期財務データ）
    - fetch_market_calendar / save_market_calendar（JPX マーケットカレンダー）
  - 取得時刻（fetched_at）を UTC ISO 形式で記録して look-ahead bias を抑制。
  - 型変換ユーティリティ `_to_float`, `_to_int`（変換失敗時は None を返す）。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからの記事収集（デフォルトソース: Yahoo Finance のビジネス RSS）。
  - セキュリティ対策:
    - defusedxml を使った XML パース（XML Bomb 等への備え）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先の事前検証、内部アドレス（プライベート/ループバック等）へのアクセス拒否。
    - レスポンスサイズ制限（最大 10 MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（utm_* 等を除去、クエリソート、フラグメント除去）。
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）。
  - DuckDB へ安全に保存:
    - save_raw_news: チャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、新規挿入 ID を正確に返す。1 トランザクションでコミット。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コード紐付けをチャンクで保存、INSERT ... ON CONFLICT DO NOTHING RETURNING を利用。
  - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し、known_codes セットでフィルタ（extract_stock_codes）。
  - 統合ジョブ run_news_collection: 各ソースを独立エラーハンドリングで処理、known_codes が与えられた場合は新規記事に対して銘柄紐付けを実施。

- DuckDB スキーマ定義 (`kabusys.data.schema`)
  - DataSchema に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル群を定義。
  - 主要テーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）を幅広く定義しデータ整合性を確保。
  - 実行時インデックスを多数定義（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) でディレクトリ自動生成とテーブル作成（冪等）を実装。get_connection() で既存 DB へ接続。

- ETL パイプライン基盤 (`kabusys.data.pipeline`)
  - ETLResult データクラスで ETL 実行結果・品質問題・エラーを集約して返す。
  - 差分更新ヘルパー:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - 市場カレンダーを使った非営業日調整 `_adjust_to_trading_day`
  - run_prices_etl の骨子実装:
    - 差分取得ロジック（DB の最終取得日から backfill_days を遡る）
    - J-Quants からの差分取得 & save（fetch_daily_quotes, save_daily_quotes）を利用する設計
    - バックフィルデフォルト: 3 日、カレンダー先読み: 90 日、最小データ日付: 2017-01-01

### セキュリティ
- RSS/HTTP 周りで SSRF 対策と応答サイズチェックを実装（news_collector）。
- XML パースに defusedxml を使用して脆弱性に備える。
- .env の読み込みで OS 環境変数を保護する仕組み（protected set）を導入。

### 注意事項 / 既知の問題
- run_prices_etl の戻り値実装がファイル内容上で途中に見える（現状の実装断片ではタプルの第2要素を返す部分が途切れている可能性があります）。ETL の完全動作確認時には該当箇所（戻り値・ログ出力）を確認してください。
- 初期リリースのため、strategy / execution / monitoring モジュールはパッケージインターフェースとして存在しますが、個別実装は今後追加される見込みです。

### マイグレーション / 利用メモ
- DB 初期化: kabusys.data.schema.init_schema(settings.duckdb_path) を実行してテーブルを作成してください。
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意: KABUSYS_ENV（development|paper_trading|live）, LOG_LEVEL（DEBUG|INFO|...）, DUCKDB_PATH, SQLITE_PATH
- 自動 .env 読み込みをテストから無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ニュース収集の銘柄紐付けには known_codes セット（有効銘柄コードの集合）を渡す必要があります。

----

今後の予定（例）
- run_prices_etl を含む ETL ワークフローの完成（品質チェック・エラーハンドリングの強化、レポート出力）。
- strategy / execution 層のトレードロジック実装と狭い単体テストの追加。
- テストカバレッジと CI の整備。