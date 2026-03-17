# Changelog

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、語彙は日本語で記載します。

- リリース日は ISO 8601 形式（YYYY-MM-DD）で記載しています。
- バージョンはパッケージの __version__（src/kabusys/__init__.py）に一致します。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買システム「KabuSys」のコア基盤を実装します。
主に以下の機能・設計方針を含みます。

### 追加 (Added)
- パッケージ構成
  - モジュール群を用意：kabusys、kabusys.data、kabusys.strategy、kabusys.execution、kabusys.monitoring（パッケージ公開 API を __all__ で定義）。
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得ヘルパー _require() と各設定プロパティ:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等。
  - 設定バリデーション: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）の検証。
  - Path 型での DB パス取得（DUCKDB_PATH、SQLITE_PATH）。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティ _request() を実装（JSON デコード、タイムアウト、エラーハンドリング）。
  - レート制限 (_RateLimiter)：120 req/min に合わせた固定間隔スロットリング。
  - 冪等性と再試行:
    - 指数バックオフによるリトライ（最大 3 回、対象ステータス: 408, 429, 5xx）。
    - 401 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライ。
    - ページネーション対応（pagination_key を用いる）。
  - データ取得関数:
    - fetch_daily_quotes (日足 OHLCV)、fetch_financial_statements（四半期財務）、fetch_market_calendar（JPX カレンダー）。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes、save_financial_statements、save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE を使用して重複や後出し更新を吸収。
  - 値変換ユーティリティ: _to_float / _to_int（型安全な変換ロジック）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集フローを実装（DEFAULT_RSS_SOURCES デフォルトを含む）。
  - セキュリティ・堅牢性:
    - defusedxml による XML パース（XML Bomb 等対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）・リダイレクト先の検査・プライベートアドレス拒否。
    - 大きすぎるレスポンスの拒否（MAX_RESPONSE_BYTES、デフォルト 10 MB）と Gzip 展開後の再チェック。
  - URL 正規化と記事 ID:
    - トラッキングパラメータ（utm_* など）除去、クエリソート、フラグメント削除。
    - 記事ID は正規化 URL の SHA-256 の先頭 32 文字で生成（冪等性確保）。
  - 取得と前処理:
    - fetch_rss(): RSS 取得→記事構築→content:encoded の優先利用→テキスト前処理（URL除去・空白正規化）。
    - _parse_rss_datetime: pubDate を UTC ベースでパース、失敗時は現在 UTC を代替。
  - DuckDB 保存:
    - save_raw_news(): チャンク INSERT + INSERT ... RETURNING id で実際に挿入された記事IDを返す（トランザクション内で処理）。
    - save_news_symbols() / _save_news_symbols_bulk(): 記事と銘柄コードの紐付けを一括保存（ON CONFLICT で重複スキップ）。
    - バルク挿入チャンク化で SQL 長・パラメータ数を制御。
  - 銘柄コード抽出:
    - extract_stock_codes(): 正規表現で 4 桁数字を抽出し、既知銘柄セットでフィルタ。重複除去。
  - 統合ジョブ:
    - run_news_collection(): 複数 RSS ソースの収集と保存、既知銘柄が与えられれば紐付けまで実施。各ソースは独立して失敗をハンドリング。

- スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DuckDB 用のスキーマを定義（Raw / Processed / Feature / Execution 層をカバー）。
  - 主要テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約やチェック (CHECK、PRIMARY KEY、FOREIGN KEY) を付与してデータ整合性を担保。
  - インデックス定義（頻出クエリに対する最適化）。
  - init_schema(db_path): DB ファイル親ディレクトリの自動作成、全 DDL 実行（冪等）。
  - get_connection(db_path): 既存 DB への接続取得（初期化は行わない）。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult データクラス: ETL 実行結果の構造化（品質問題、エラー、取得/保存件数等）。
  - 差分更新ユーティリティ:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - _get_max_date / _table_exists の共通ユーティリティ実装。
  - 市場カレンダー補助:
    - _adjust_to_trading_day(): 非営業日を直近過去の営業日に調整。
  - run_prices_etl(): 株価日足の差分 ETL（backfill_days による再取得・最小日付補正、fetch_daily_quotes と save_daily_quotes の利用）。
  - 設計方針として品質チェック（quality モジュール）を ETL の外から評価可能にする（Fail-Fast を避ける）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector の SSRF 対策（リダイレクト時の事前検査、プライベートアドレスチェック）。
- defusedxml を使った XML パースで XML 関連の脆弱性緩和。
- .env 自動読み込み時に OS 環境変数を保護する protected パラメータを導入。

### パフォーマンス (Performance)
- J-Quants API のレート制御（固定間隔スロットリング）により API 制限の順守を簡素化。
- bulk insert とチャンク処理により DB への大量挿入時のオーバーヘッドを低減。
- DuckDB のインデックスをあらかじめ作成して頻出クエリを高速化。

### 既知の注意点 / マイグレーション (Notes / Migration)
- 初回利用時は schema.init_schema(db_path) を呼んでスキーマを作成してください。
- get_connection() はスキーマ初期化を行わないため、初回は init_schema() を使用すること。
- 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途等）。
- J-Quants API の認証情報（JQUANTS_REFRESH_TOKEN）は Settings.jquants_refresh_token 経由で取得されます。未設定の場合は ValueError が発生します。
- news_collector.fetch_rss() は HTTP/HTTPS のみ許可し、ローカル/内部ネットワークの URL は拒否されます（SSRF 防止）。
- pipeline.run_prices_etl() は差分更新を行います。date_from を明示的に与えない場合は DB 内の最終取得日を元に自動計算（backfill_days を考慮）。

---

開発・保守に関する問い合わせや改善提案があれば Issue を作成してください。