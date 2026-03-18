# Changelog

すべての変更はこのリポジトリのソースツリーに基づいて推測・記述しています。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

（現時点では未リリースの差分はありません）

## [0.1.0] - 初回リリース
初期バージョン。日本株自動売買システムのコアコンポーネントを提供します。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。パッケージメタ情報として `__version__ = "0.1.0"` を定義。
  - サブモジュールのプレースホルダを追加: `data`, `strategy`, `execution`, `monitoring`（strategy と execution は初期状態では空の __init__）。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - 自動 .env ロード機能（読み込み順序: OS 環境 > .env.local > .env）。プロジェクトルートは `.git` または `pyproject.toml` を起点に探索して決定。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途）。
  - .env パーサーは次の仕様に対応:
    - コメント行、空行、`export KEY=val` 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォート無しの行でのインラインコメント認識（`#` の直前が空白/タブの場合）
  - Settings クラスを提供し、以下の設定取得プロパティを定義（必須/デフォルト値/バリデーション含む）:
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabuステーション API: KABU_API_PASSWORD、KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - Slack: SLACK_BOT_TOKEN、SLACK_CHANNEL_ID（必須）
    - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - システム: KABUSYS_ENV（development/paper_trading/live のバリデーション）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - 環境判定ユーティリティ: is_live/is_paper/is_dev

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する API クライアントを実装。
  - レート制限対応: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - 再試行ロジック: 指数バックオフ（最大 3 回）、対象ステータス 408, 429, 5xx をリトライ。
  - 401 受信時の自動トークンリフレッシュを 1 回行いリトライ（無限再帰を避けるため allow_refresh フラグ管理）。
  - モジュールレベルの ID トークンキャッシュを実装（ページネーションなどで共有）。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes
    - fetch_financial_statements
    - fetch_market_calendar
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - 型変換ユーティリティ: _to_float, _to_int（厳格な整数変換ルールを含む）
  - 取得時刻（fetched_at）を UTC ISO 形式で保存し、Look-ahead Bias のトレースを容易にする設計。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからニュースを収集し raw_news に保存する機能を実装。
  - 主な設計・実装点:
    - デフォルト RSS ソース（例: Yahoo Finance ビジネスカテゴリ RSS）
    - 受信最大バイト数制限（MAX_RESPONSE_BYTES = 10 MB）によるメモリ DoS 対策
    - Gzip 圧縮対応および解凍後のサイズ検査（Gzip bomb 対策）
    - defusedxml を用いた XML パース（XML Bomb 等への防御）
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - リダイレクト時にスキーム／ホストを検証するカスタムリダイレクトハンドラ（_SSRFBlockRedirectHandler）
      - ホストがプライベート・ループバック・リンクローカル・マルチキャストかどうかの判定（IP直接判定 + DNS 解決による検査）
      - _urlopen はテストでモック可能（差し替え容易）
    - トラッキングパラメータ除去と URL 正規化（_normalize_url）
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で算出し冪等性を確保
    - テキスト前処理（URL 除去、空白正規化）: preprocess_text
    - RSS pubDate のパースを UTC に正規化し、失敗時は現在時刻で補完
  - DB 保存:
    - save_raw_news: チャンク挿入（_INSERT_CHUNK_SIZE=1000）、INSERT ... RETURNING id を利用して実際に挿入された ID を返す。トランザクション内での一括挿入。失敗時はロールバック。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付け用保存（ON CONFLICT DO NOTHING + RETURNING を使用）。一括挿入とトランザクション管理。
  - 銘柄コード抽出: 4桁数字パターンから known_codes に含まれるものだけを返す extract_stock_codes。
  - run_news_collection: 全ソースの収集を管理し、各ソースは独立してエラーハンドリング。収集結果と新規保存件数を返す。既知銘柄リストがあれば新規記事に対する銘柄紐付け処理を行う。

- DuckDB スキーマ＆初期化（kabusys.data.schema）
  - 3層構造（Raw / Processed / Feature / Execution）に基づくテーブル群の DDL を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）とインデックスを定義して実行時の整合性と検索性能を向上。
  - init_schema(db_path) 関数でディレクトリ作成 -> DuckDB 接続 -> 全 DDL を適用（冪等）。get_connection で既存 DB へ接続可能。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新を基本とした ETL フローを実装するためのユーティリティを提供。
  - 設計ポイント:
    - 差分更新のデフォルト単位は「営業日1日分」
    - backfill_days による後出し修正の吸収（デフォルト 3 日）
    - カレンダーの先読み: _CALENDAR_LOOKAHEAD_DAYS = 90
    - 初回ロード用の最小データ日付: 2017-01-01
    - 品質チェックは fail-fast とせず、検出した問題は ETLResult へ収集
  - 提供 API/ユーティリティ:
    - ETLResult dataclass（取得件数、保存件数、quality issues、errors、has_errors/has_quality_errors など）
    - _table_exists, _get_max_date（汎用ユーティリティ）
    - 市場カレンダー補正: _adjust_to_trading_day（非営業日を直近営業日に調整）
    - 差分更新ヘルパー: get_last_price_date, get_last_financial_date, get_last_calendar_date
    - run_prices_etl: 株価日足の差分 ETL（date_from の自動計算、fetch と save の呼び出し）。（注: ソースは途中まで実装済みの箇所あり）

### Security
- ニュース収集での SSRF 対策、プライベートアドレスブロッキング、URL スキーム検証を実装。
- defusedxml を用いた XML パースで XML 関連の攻撃を軽減。
- ネットワーク受信量上限（MAX_RESPONSE_BYTES）と Gzip 解凍後のサイズ検査による DoS 対策。
- .env 読み込み時の OS 環境変数保護（protected set を使った上書き制御）。

### Internal / Testability
- jquants_client: id_token を引数注入できる設計でテスト容易性を担保。allow_refresh フラグでリフレッシュ挙動制御。
- news_collector: _urlopen を差し替え可能にして外部アクセスをモックできるようにしている。
- DuckDB の保存処理はトランザクション管理（conn.begin/commit/rollback）を行う実装。

### Notes / Breaking changes / Migration
- 必須環境変数（JQUANTS_REFRESH_TOKEN、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、KABU_API_PASSWORD 等）を設定しないと Settings プロパティ呼び出し時に ValueError が発生します。`.env.example` を参考に `.env` を用意してください。
- .env 自動読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後やテスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを抑制できます。
- DuckDB スキーマは init_schema() により自動作成されます。既存 DB のアップグレードやマイグレーションは手動対応が必要（初期リリースのためマイグレーション機能は未実装）。
- run_prices_etl 等の ETL 関数は差分更新ロジックに従いますが、外部設計書（DataPlatform.md, DataSchema.md）に従って拡張・チューニングを行う想定です。

----

今後のリリースでは下記のような項目が想定されます:
- ETL の品質チェックモジュール（quality）の実装と統合
- strategy / execution の具体的実装（シグナル生成、注文送信、約定ハンドリング）
- モニタリング（Slack 通知・ダッシュボード）機能の実装
- マイグレーションツール（スキーマ変更のためのマイグレーション）やより詳細なロギング・メトリクス

（以上）