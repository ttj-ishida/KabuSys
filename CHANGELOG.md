# CHANGELOG

すべての注目すべき変更をここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。重要な変更・追加・修正を時系列で残してください。

なお、本 CHANGELOG はソースコードから推測して作成しています。実装上の意図や設計方針、公開 API の一覧・注意点なども記載しています。

## [Unreleased]

（現在未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-18

初回公開リリース。日本株自動売買システム「KabuSys」のコアデータ層・設定・ETLパイプライン・ニュース収集モジュール等を実装しました。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名、バージョン (__version__ = "0.1.0")、公開サブパッケージ一覧を定義（data, strategy, execution, monitoring）。

- 設定管理
  - src/kabusys/config.py:
    - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート検出ロジックを使用し、.env → .env.local を優先して読み込む）。
    - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須環境変数取得ヘルパー（_require）と Settings クラスを提供。
    - サポートされる設定（プロパティ）:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development/paper_trading/live。デフォルト development）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト INFO）
    - 環境値検証（env/log_level の許容値チェック）と簡易ユーティリティ (is_live/is_paper/is_dev)。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py:
    - J-Quants API から株価日足（OHLCV）、財務データ（四半期BS/PL）、JPXマ―ケットカレンダーを取得するクライアントを実装。
    - APIレート制限（120 req/min）を守る固定間隔レートリミッタを実装。
    - リトライロジック（指数バックオフ、最大3回）を実装。HTTP 408/429/5xx に対してリトライ。
    - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動更新して1回リトライ。
    - ページネーション対応（pagination_key を用いたループ）。
    - データ保存関数（DuckDB向けの冪等保存）:
      - save_daily_quotes (raw_prices テーブルへ ON CONFLICT DO UPDATE)
      - save_financial_statements (raw_financials テーブルへ ON CONFLICT DO UPDATE)
      - save_market_calendar (market_calendar テーブルへ ON CONFLICT DO UPDATE)
    - 型変換ユーティリティ (_to_float, _to_int) を実装し不正値を安全に扱う。
    - get_id_token: リフレッシュトークンから id_token を取得する POST 実装。

- ニュース収集（RSS）モジュール
  - src/kabusys/data/news_collector.py:
    - RSS フィードからニュース記事を安全に取得・前処理・DB保存する機能を実装。
    - セキュリティ対策:
      - defusedxml を使用した XML パース（XML Bomb 等の防止）
      - SSRF 対策（許可スキームは http/https のみ、リダイレクト先のスキーム/ホスト検証、内部アドレス拒否）
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）でメモリDoS対策、gzip 解凍後も検査
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）を実装。
    - 記事ID生成: 正規化 URL の SHA-256 ハッシュ先頭32文字を使用し冪等性を確保。
    - 主な関数:
      - fetch_rss(url, source, timeout): RSS 取得→記事リスト（NewsArticle TypedDict）を返す
      - save_raw_news(conn, articles): raw_news テーブルへバルク挿入（チャンク、1トランザクション、INSERT ... RETURNING で実際に挿入されたIDを返す）
      - save_news_symbols(conn, news_id, codes): news_symbols への紐付けを挿入（RETURNING を利用して挿入数を返す）
      - extract_stock_codes(text, known_codes): 4桁コード抽出（既知コードフィルタ）
      - run_news_collection(conn, sources, known_codes, timeout): 複数ソースを処理し DB に保存（各ソースは個別にエラーハンドリング）

- DuckDB スキーマ定義／初期化
  - src/kabusys/data/schema.py:
    - DataSchema.md に基づき、Raw / Processed / Feature / Execution 層のテーブルを定義する DDL を実装。
    - 主要テーブル（例）:
      - Raw: raw_prices, raw_financials, raw_news, raw_executions
      - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature: features, ai_scores
      - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックスを定義（頻出クエリを想定したインデックス群）。
    - init_schema(db_path) によりディレクトリ作成→DuckDB 接続→全 DDL とインデックスを実行して初期化（冪等）。
    - get_connection(db_path) で既存DBへ接続可能（スキーマ初期化は行わない点に注意）。

- ETL / パイプライン
  - src/kabusys/data/pipeline.py:
    - 差分更新を行う ETL パイプラインの骨格を実装（差分取得、保存、品質チェックの流れ）。
    - 設計パラメータ:
      - データ最小開始日: 2017-01-01
      - カレンダー先読み: 90日
      - デフォルトの backfill_days: 3（最終取得日の数日前から再取得）
    - ETL 結果を表す dataclass: ETLResult（品質問題、エラー一覧、各処理の取得/保存件数を格納）。
    - テーブル存在／最大日付取得ユーティリティ（_table_exists, _get_max_date）。
    - 市場カレンダーを用いた営業日調整ヘルパー: _adjust_to_trading_day。
    - 差分更新ヘルパー: get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - 個別ジョブの雛形: run_prices_etl（差分算出→jq.fetch_daily_quotes→jq.save_daily_quotes。backfill_days を利用）。

### Security
- news_collector にて SSRF 対策・XML パース安全化（defusedxml）・レスポンス上限（10MB）・gzip 検査など複数の防御策を実装。
- jquants_client の HTTP リトライ処理で 401 時にトークンリフレッシュを行う際に無限再帰を防止するロジック（allow_refresh フラグ）を導入。

### Documentation / Examples
- 各モジュールに詳細な docstring や使用例・設計方針の記述を追加。Settings の使用例を config.py に記載。

### Known limitations / Notes
- strategy/ と execution/ パッケージの __init__.py は存在するが、具体的な戦略実装・発注制御ロジックは未実装（今後の拡張対象）。
- pipeline.run_prices_etl の戻り値の末尾がソースコード切り出しの都合で不完全に見える箇所がある（実際のリポジトリでは完全実装を確認してください）。
- DuckDB に依存。実行時は duckdb パッケージをインストールすること。
- news_collector は defusedxml を使用するため、同ライブラリのインストールが必要。
- 環境変数が不足していると Settings のプロパティで ValueError を送出するため、実行前に .env を作成するか環境変数を設定してください。
- init_schema はデータディレクトリを自動作成するが、既存のデータと互換性を保つためスキーマ変更は慎重に行ってください。

### Public API（主な関数 / クラス）
- kabusys.config.Settings, settings
- kabusys.data.jquants_client:
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.news_collector:
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection, extract_stock_codes, preprocess_text
- kabusys.data.schema:
  - init_schema, get_connection
- kabusys.data.pipeline:
  - ETLResult, run_prices_etl, get_last_price_date, get_last_financial_date, get_last_calendar_date

---

もしリポジトリに追加のコミット履歴やバージョン管理情報（git タグ・コミットメッセージ）があれば、それに合わせて CHANGELOG をより正確に更新できます。特にリリース日・細かな修正履歴・互換性のある API 変更（breaking changes）がある場合は教えてください。