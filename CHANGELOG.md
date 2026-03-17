# Changelog

すべての注目すべき変更点を記録します。本プロジェクトは Keep a Changelog の慣習に従います。  
未リリースの変更は Unreleased に記載します。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- セキュリティ (Security)

## [Unreleased]
- なし

## [0.1.0] - 2026-03-17
初回リリース

### Added
- パッケージ初期構成
  - パッケージメタ情報 (src/kabusys/__init__.py) を追加。公開モジュールは data, strategy, execution, monitoring。バージョンは `0.1.0`。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを導入。
  - プロジェクトルートは .git または pyproject.toml を基準に解決（CWD に依存しない）。
  - .env の行パーサ実装（コメント/export/クォート/エスケープ対応）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - 必須設定取得ヘルパー `_require` と、Settings クラスを提供。J-Quants / kabu / Slack / DB パス等のプロパティを定義。
  - KABUSYS_ENV / LOG_LEVEL の値検証（ホワイトリスト化）と環境判定プロパティ（is_live / is_paper / is_dev）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 基本的な API ベース実装（_BASE_URL）。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter 実装。
  - 再試行/バックオフ: ネットワークおよび一部ステータスコード (408, 429, 5xx) に対する指数バックオフ（最大 3 回）。
  - 401 Unauthorized を検知した場合の自動トークンリフレッシュ（1 回のみ）とリトライ対応、トークンキャッシュ。
  - JSON デコードエラーハンドリング、タイムアウト、ページネーション対応。
  - データ取得関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）。
  - DuckDB への保存関数: save_daily_quotes / save_financial_statements / save_market_calendar。fetched_at を UTC で記録し、ON CONFLICT DO UPDATE による冪等保存を実現。
  - 型変換ユーティリティ (_to_float, _to_int) を実装（空値・不正値耐性）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS からニュース記事を収集し raw_news に保存するフローを実装。
  - デフォルト RSS ソース（例: Yahoo Finance のビジネスカテゴリ）。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）とチャンク処理でメモリ DoS を緩和。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と、正規化 URL から SHA-256（先頭32文字）で記事 ID を生成し冪等性を担保。
  - XML 解析に defusedxml を利用して XML Bomb 等の攻撃を軽減。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - ホストがプライベート/ループバック/リンクローカル/IP マルチキャストでないことの検査（DNS 解決による A/AAAA 検査）。
    - リダイレクト時に事前検査するカスタム RedirectHandler を使用。
  - gzip 圧縮処理と解凍後サイズ検査（Gzip bomb 対策）。
  - テキスト前処理 (URL 除去、空白正規化)。
  - DuckDB への保存: save_raw_news（チャンク化、トランザクション、INSERT ... RETURNING による実際に挿入された ID の取得）および save_news_symbols / _save_news_symbols_bulk（銘柄紐付けの一括挿入）。
  - 銘柄コード抽出関数 extract_stock_codes（4桁の候補から known_codes でフィルタ、重複除去）。
  - 統合ジョブ run_news_collection を実装（各ソース個別エラーハンドリング、銘柄紐付けの一括処理）。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataPlatform 設計に従った 3 層（Raw / Processed / Feature / Execution）向けのテーブル定義を追加。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw 層テーブル定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed 層。
  - features, ai_scores 等の Feature 層。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等 Execution 層。
  - 主要クエリ向けのインデックス定義を含む。
  - init_schema(db_path) によりディレクトリ作成と DDL 実行を行い、冪等的にスキーマ初期化を実現。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計原則に基づくパイプライン基盤を追加。
  - ETLResult dataclass を導入し、実行結果・品質問題・エラーの集約と to_dict() 出力をサポート。
  - スキーマ/テーブル存在チェック、テーブル最終日取得ユーティリティ (_table_exists, _get_max_date) を実装。
  - 取引日補正ヘルパー (_adjust_to_trading_day) を実装（market_calendar ベース）。
  - 差分更新ヘルパー get_last_price_date / get_last_financial_date / get_last_calendar_date を追加。
  - run_prices_etl を実装：差分取得（最終取得日からの backfill）、J-Quants からの取得→保存の流れを実現。

### Security
- ニュース収集で以下のセキュリティ対策を実装
  - defusedxml による安全な XML パース（XML External Entity / XML Bomb 対策）。
  - SSRF 対策: スキーム検証、プライベート IP/ホスト判定、リダイレクト時検証。
  - レスポンスサイズ・解凍後サイズの上限チェック（メモリ攻撃対策）。

### Notes / Migration
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等は Settings によって必須参照されます。未設定時は ValueError を送出します。
- 自動 .env 読み込みを避けたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化は init_schema() を呼び出してください。既存テーブルがある場合はスキップされます。
- news_collector の既定 RSS ソースは DEFAULT_RSS_SOURCES で定義されています。独自ソースは run_news_collection の引数で上書き可能です。

---

今後の作業候補（未実装/改善点の想定）
- ETL の品質チェックモジュール (quality) の詳細実装と結果に基づく自動アクション。
- strategy / execution / monitoring モジュールの実装拡張（現状はパッケージエントリのみ）。
- 単体テスト、統合テスト、CI ワークフローの追加。
- jquants_client のページネーション・エラーケースに対する追加テストとログ強化。

--- 

（この CHANGELOG はコードベースの内容から推測して記載しています。実際の変更履歴・日付はリポジトリ運用に合わせて調整してください。）