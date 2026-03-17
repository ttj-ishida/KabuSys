# CHANGELOG

すべての重要な変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のバージョン番号: 0.1.0

Unreleased
----------
（なし）

[0.1.0] - 2026-03-17
-------------------
Initial release — 日本株自動売買基盤ライブラリ「KabuSys」v0.1.0 を公開。

概要
- 日本株自動売買システム向けの基盤ライブラリを提供。
- データ取得/保存、ニュース収集、DuckDB スキーマ、ETL パイプライン、環境設定などのコア機能を実装。

Added
- パッケージ初期化
  - src/kabusys/__init__.py にパッケージ情報とエクスポート対象を定義。
  - バージョン: __version__ = "0.1.0"。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを提供。
  - 自動ロード機能:
    - プロジェクトルートを .git または pyproject.toml を基準に探索して自動で .env / .env.local をロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化をサポート。
    - .env の読み込みは既存の OS 環境変数を保護する仕組みあり（.env.local は上書き可能）。
  - 高度な .env パーサ:
    - コメント行、export プレフィックス、シングル/ダブルクォート内のエスケープ処理、インラインコメント判定をサポート。
  - 必須環境変数取得用の _require() と各種プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など。
  - 環境（development / paper_trading / live）やログレベルのバリデーションとヘルパープロパティ（is_live 等）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティ（_request）:
    - 基本URL、クエリ生成、JSON ボディ対応。
    - レート制御（120 req/min 固定間隔スロットリング）を実装する _RateLimiter。
    - 再試行ロジック（指数バックオフ、最大 3 回）、対象ステータス（408, 429, 5xx）。
    - 429 の場合は Retry-After ヘッダ優先。
    - 401 の場合はトークン自動リフレッシュを一回だけ行い再試行（無限再帰を防止）。
    - ページネーション対応（pagination_key）をサポート。
  - 認証ヘルパー get_id_token(refresh_token=None) を提供（refreshtoken -> idToken）。
  - データ取得関数:
    - fetch_daily_quotes: 日足（OHLCV）をページネーションで取得。
    - fetch_financial_statements: 四半期財務データをページネーションで取得。
    - fetch_market_calendar: JPX マーケットカレンダー取得。
    - 取得時に fetched_at（UTC）を採取する概念を踏襲（保存関数で付与）。
  - DuckDB への保存関数（冪等性を確保）:
    - save_daily_quotes: raw_prices テーブルに ON CONFLICT DO UPDATE を用いて保存。
    - save_financial_statements: raw_financials テーブルに冪等保存。
    - save_market_calendar: market_calendar テーブルに冪等保存。
  - 型変換ユーティリティ (_to_float, _to_int) による堅牢なデータ変換。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得と記事保存ワークフローを実装。
  - セキュリティ / 頑健性:
    - defusedxml を使用して XML Bomb 等を防止。
    - SSRF 対策:
      - リダイレクトごとにスキームとホストを検査するカスタム HTTPRedirectHandler を実装。
      - 初回接続前にホストがプライベートアドレスかを検査。
      - http/https 以外のスキームを拒否。
      - DNS 失敗時は安全側の扱い（ただしリダイレクト先は厳格に検証）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリ DoS を防止。
    - gzip 応答対応と解凍後サイズチェック（Gzip bomb 対策）。
  - URL 正規化と記事 ID:
    - トラッキングパラメータ（utm_*, fbclid 等）を除去してクエリをソート、フラグメント削除。
    - 正規化 URL の SHA-256 ハッシュ先頭32文字を記事 ID として生成（冪等性確保）。
  - テキスト前処理:
    - URL 除去、連続空白正規化、trim を行う preprocess_text。
  - RSS 解析と記事抽出:
    - content:encoded を優先、description をフォールバック。
    - pubDate を RFC2822 形式から UTC naive datetime に変換（解析失敗時は現在時刻で代替）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事 ID を返す。
    - chunked INSERT（チャンクサイズ 1000）および単一トランザクションで実行、失敗時はロールバック。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを ON CONFLICT DO NOTHING + RETURNING で保存。
  - 銘柄コード抽出:
    - 4 桁数字パターンから known_codes セットでフィルタリングする extract_stock_codes を提供。
  - run_news_collection: 複数ソースの収集をまとめるジョブ。各ソースを独立してエラーハンドリングし継続する設計。

- DuckDB スキーマ (src/kabusys/data/schema.py)
  - DataPlatform に基づく 3 層（Raw / Processed / Feature / Execution）スキーマを定義。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（PRIMARY KEY, CHECK, FOREIGN KEY 等）を付与。
  - 頻出クエリ向けのインデックスを作成。
  - init_schema(db_path) によりディレクトリ作成含め初期化可能（冪等）。
  - get_connection(db_path) で接続のみ取得可能（初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult dataclass により ETL の結果・状態（取得数、保存数、品質問題、エラー）を構造化。
  - 差分更新戦略:
    - DB の最終取得日を確認し、未取得範囲のみを取得。
    - デフォルトのバックフィル日数を導入（_DEFAULT_BACKFILL_DAYS = 3）して API の後出し修正を吸収。
    - 市場カレンダーの先読み (_CALENDAR_LOOKAHEAD_DAYS = 90)。
  - ヘルパー:
    - _table_exists, _get_max_date, _adjust_to_trading_day, get_last_price_date, get_last_financial_date, get_last_calendar_date を実装。
  - run_prices_etl: 差分ETL（取得 → 保存）の流れを実装（取得/保存の件数を返す）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- defusedxml 利用、SSRF 検査、URL スキーム制限、レスポンスサイズ制限、Gzip 解凍後のサイズ検査など、外部入力（RSS/HTTP）に対する複数の防御策を導入。

Notes / Implementation details
- jquants_client の _request は urllib を用いた実装で、タイムアウトや HTTPError のハンドリングを詳細に実装。ID トークンのキャッシュ（モジュールレベル）を保持してページネーション間で共有する。
- DuckDB への保存は SQL の ON CONFLICT を利用した冪等設計。news_collector は INSERT ... RETURNING を活用して実際に挿入された行情報を取得する。
- コード全体で明示的にログ出力（logger）を行い、運用時の監査・デバッグを想定。

Breaking Changes
- なし（初回リリース）

今後の予定（例）
- ETL パイプラインの完結（prices_etl 以外の job 実装・統合、品質チェックモジュールの呼び出し実装）
- execution（発注/注文管理）モジュールの具体実装
- 単体テスト、統合テストの追加、および CI 設定
- ドキュメント整備（DataPlatform.md 等の公開）

--- 
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートは運用ポリシーやリリース時点の差分に基づいて調整してください。）