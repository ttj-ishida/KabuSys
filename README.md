# KabuSys

日本株向けの自動売買/データ基盤ライブラリ（KabuSys）。  
J-Quants や RSS など外部データソースから市場データ・ニュースを取得し、DuckDB に蓄積、品質チェック、監査ログ、カレンダー管理、ETL パイプラインを提供します。戦略・発注・監視の各レイヤーと連携するための基盤コンポーネント群を含みます。

## 特徴（概要）
- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レート制限（120 req/min）を厳守する内部 RateLimiter
  - リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録、Look-ahead バイアス対策
- DuckDB ベースのスキーマ設計
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - 冪等性を重視した INSERT（ON CONFLICT ...）でデータ整合性を確保
- RSS ニュース収集（news_collector）
  - RSS 取得、HTML/URL 正規化、記事ID は URL 正規化の SHA-256（先頭32文字）
  - SSRF・XML Bomb 対策（defusedxml、ホスト検査、サイズ制限）
  - 銘柄コード抽出・news_symbols への紐付け機能
- データ品質チェック（quality）
  - 欠損、スパイク（急騰/急落）、重複、日付不整合の検出
  - 問題は QualityIssue として収集（Fail-fast でなく全件収集）
- マーケットカレンダー管理
  - 営業日判定、前後営業日の取得、夜間カレンダー更新ジョブ
- 監査ログ（audit）
  - シグナル→発注→約定までトレース可能な監査テーブル群
  - order_request_id による冪等性、UTC タイムスタンプ運用

---

## 機能一覧
- データ取得
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
- データ保存（DuckDB）
  - save_daily_quotes, save_financial_statements, save_market_calendar
- ETL
  - run_daily_etl（カレンダー→株価→財務→品質チェック のパイプライン）
  - run_prices_etl, run_financials_etl, run_calendar_etl（個別ジョブ）
- ニュース収集
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
- カレンダー管理
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- 監査ログ初期化
  - init_audit_db, init_audit_schema
- スキーマ管理
  - init_schema, get_connection
- 品質チェック
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency

---

## 動作要件
- Python 3.10+（型注釈などで recent な機能を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトの requirements.txt に依存関係をまとめてください）

---

## セットアップ手順

1. リポジトリをクローン／プロジェクトに入る
   - 例: git clone ... && cd kabusys

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 例:
     pip install duckdb defusedxml

   - またはプロジェクトに requirements.txt があれば:
     pip install -r requirements.txt

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くことで自動ロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動読み込みを無効化できます）。
   - 必須環境変数（概要）:
     - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（必須）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID      : 通知先 Slack チャンネル ID（必須）
   - 任意 / デフォルト:
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|...) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   - .env の例:
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb

   ※ センシティブな値は絶対にリポジトリに含めないでください。

---

## 使い方（クイックスタート）

以下は Python から直接利用する最小例です。事前に環境変数を適切に設定してください。

1) スキーマ初期化（DuckDB）
- Python で実行:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

  - init_schema(":memory:") でインメモリ DB を利用できます。
  - 親ディレクトリが無ければ自動作成されます。

2) 日次 ETL（市場カレンダー→株価→財務→品質チェック）
- 実行例:
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)
  print(result.to_dict())

  - id_token を外から注入したい場合は run_daily_etl(conn, id_token="...") のように渡せます。
  - run_daily_etl は ETLResult を返します（各種件数・品質問題・エラー情報を含む）。

3) ニュース収集ジョブ
- 実行例:
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, known_codes={"7203","6758"})
  print(results)

  - DEFAULT_RSS_SOURCES がデフォルトRSSを提供します。sources を渡して独自フィードを指定可能です。

4) カレンダー更新ジョブ（夜間バッチ用）
- 実行例:
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved", saved)

5) 監査ログスキーマ初期化（audit）
- 既存の接続に監査テーブルを追加:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- 監査専用 DB を作る場合:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

---

## 主要 API（抜粋）
- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path, settings.env, settings.log_level など
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
- kabusys.data.news_collector
  - fetch_rss(url, source), save_raw_news(conn, articles), run_news_collection(conn, ...)
- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
- kabusys.data.calendar_management
  - is_trading_day(conn, d), next_trading_day(conn, d), calendar_update_job(conn, ...)

詳細は各モジュールの docstring を参照してください（型注釈と docstring を重視して設計されています）。

---

## ディレクトリ構成

プロジェクトの主要ファイルとディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py               -- 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py             -- DuckDB スキーマ・初期化
      - jquants_client.py     -- J-Quants API クライアント（取得・保存）
      - pipeline.py           -- ETL パイプライン（run_daily_etl 等）
      - news_collector.py     -- RSS ニュース収集・保存
      - calendar_management.py-- マーケットカレンダー管理
      - audit.py              -- 監査ログ（トレーサビリティ）
      - quality.py            -- データ品質チェック
      - pipeline.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（README はリポジトリの実際のツリーに合わせて追記・整備してください）

---

## 運用上の注意・設計方針のポイント
- 秘匿情報（トークン・パスワード等）は環境変数で管理し、リポジトリに含めないこと。
- J-Quants の API レート制限に従うよう内部でスロットリング・リトライを実装していますが、ETL の大量実行は注意してください。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に作成されます。バックアップや権限管理を運用で確保してください。
- ニュース収集は外部 HTTP を行うため SSRF 対策やタイムアウト設定を有効にしています。フィードの信頼性に依存する点に注意してください。
- テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動的な .env 読み込みを無効化できます（テスト用に環境を明示的に制御するため）。

---

## 貢献・拡張
- 戦略（strategy）、実行（execution）、監視（monitoring）レイヤーは拡張ポイントです。戦略は features / ai_scores を利用してシグナル生成し、signal_queue / orders テーブル経由で発注フローに連携してください。
- 新たなデータソース（例: 別API や Web スクレイピング）は data 以下にクライアント/保存ロジックを追加し、ETL pipeline に統合してください。

---

必要があれば、セットアップ用のスクリプト、requirements.txt、サンプル .env.example、簡易 CLI ラッパーの README 追加も可能です。必要な内容を教えてください。