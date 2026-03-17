# Changelog

すべての注目すべき変更はこのファイルに記録されます。  
フォーマットは Keep a Changelog に準拠しています。  

注: バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づきます。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、モジュール公開: data, strategy, execution, monitoring を __all__ に設定。
  - バージョン: 0.1.0。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装。
  - OS環境変数を保護する読み込み順序: OS 環境 > .env.local (上書き可) > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装（コメント、export プレフィックス、クォート内のエスケープ処理、インラインコメント処理 等に対応）。
  - 必須環境変数取得ヘルパー `_require` を提供。
  - Settings クラスを提供し、主な設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development, paper_trading, live のバリデーション）および LOG_LEVEL の検証プロパティ
    - is_live / is_paper / is_dev のショートハンド

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティ `_request` を実装:
    - レート制限（120 req/min、固定間隔スロットリング）
    - リトライ（指数バックオフ、最大3回、408/429/5xx を対象）
    - 429 の場合は Retry-After ヘッダ優先
    - 401 受信時は ID トークンを自動リフレッシュして 1 回のみリトライ（無限再帰を回避）
    - JSON デコード失敗時の明確なエラーメッセージ
  - トークン取得ヘルパー get_id_token（refreshtoken → idToken を POST で取得）
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足 / OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT による upsert）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - fetched_at を UTC で記録し、Look-ahead バイアスの追跡を意識
  - 型変換ユーティリティ `_to_float`, `_to_int`（安全な None 処理、"1.0" の扱い等）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news に保存するフローを実装:
    - fetch_rss: RSS 取得・XML パース（defusedxml 利用）、gzip 解凍対応、Content-Length/サイズ上限チェック（MAX_RESPONSE_BYTES=10MB）、XML パースエラーは安全にハンドリング
    - セキュリティ対策: SSRF 対策のためのリダイレクトハンドラ（_SSRFBlockRedirectHandler）、ホストがプライベートアドレスか判定（_is_private_host）し拒否
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去）および記事 ID を SHA-256（先頭32文字）で生成
    - テキスト前処理（URL 除去、空白正規化）
    - save_raw_news: チャンク化したバルク INSERT をトランザクションで実行し、INSERT ... RETURNING で実際に挿入された記事 ID を返す（ON CONFLICT DO NOTHING による冪等性）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをトランザクションかつチャンクで保存し、実際に挿入された件数を返す
    - extract_stock_codes: テキスト内の 4 桁銘柄コード抽出（known_codes によるフィルタ）を提供
    - デフォルト RSS ソース: Yahoo Finance のビジネスカテゴリ RSS を設定（DEFAULT_RSS_SOURCES）
    - テスト観点: ネットワーク呼び出しの差し替えポイント（_urlopen）を用意

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に準拠した 3 層＋実行層のテーブル定義を実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型制約、チェック制約、主キー・外部キーを付与
  - 頻出クエリ向けのインデックス定義を追加
  - init_schema(db_path) で DB ファイルの親ディレクトリ自動作成と DDL 実行（冪等）
  - get_connection(db_path) を提供（スキーマ初期化は行わない）

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult データクラス（処理結果、品質問題、エラー集約、辞書変換ユーティリティを含む）
  - DB ヘルパー: _table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date
  - 市場カレンダー補正: _adjust_to_trading_day（非営業日を直近の営業日に補正）
  - run_prices_etl の差分更新ロジック（最終取得日に基づく date_from 自動算出、backfill_days の取扱い、J-Quants からの取得 → 保存 を実行）
  - 設計方針として品質チェックモジュール（quality）を呼び出す想定（品質問題は収集を止めずに報告）

### Security
- 各種外部データ取得処理にセキュリティ対策を導入:
  - RSS: defusedxml を用いた XML パース、SSRF 対策（リダイレクト検査・プライベート IP の拒否）
  - 外部 URL のスキーム検証（http/https のみ許可）
  - レスポンスサイズ上限（メモリ DoS / Gzip Bomb 対策）

### Other / Developer ergonomics
- ロギングを詳細に出力（取得件数、保存件数、警告等）
- テストしやすい設計（トークン取得・キャッシュ、_urlopen の差し替えポイント、id_token 注入が可能）
- SQL インジェクションに注意してプレースホルダを使用（ただし一部バルク INSERT 文はフォーマット文字列で値部分をプレースホルダ化して実行）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

## Upgrade / Migration notes
- 初回利用時は必ず schema.init_schema(settings.duckdb_path) を実行して DuckDB のテーブルを作成してください（init_schema は冪等）。
- 環境変数の必須項目が未設定の場合、Settings のプロパティアクセスで ValueError が発生します。必要な環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。

---

既知の制限 / TODO（メモ）
- pipeline.run_prices_etl など一部 ETL の品質チェック連携やエラーハンドリングの詳細は品質モジュール（quality）との結合でさらに拡張する想定。
- strategy / execution / monitoring の各パッケージは初期のプレースホルダであり、実際の売買ロジックや発注連携は今後追加予定。

--- 

（以上）