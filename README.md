KabuSys — 日本株自動売買プラットフォーム（README）
================================

概要
----
KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤のコアライブラリです。本リポジトリには以下を提供します。

- J-Quants API からのデータ取得（株価日足、四半期財務、JPX カレンダー）と冪等保存（DuckDB）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・トラッキング除去など）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- データ品質チェックモジュール（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal/order/execution のトレーサビリティ用テーブル定義）

設計上のポイント
- DuckDB をストレージ層に使用（オンメモリ or ファイル）
- J-Quants API はレート制限（120 req/min）とリトライ/トークンリフレッシュを組み込み
- ETL や保存は冪等（ON CONFLICT）を想定
- セキュリティ対策（RSS の SSRF 防止、defusedxml を利用した XML パース保護 等）
- 自動環境変数読み込み機構を備え、プロジェクトルートの .env / .env.local を読み込む

主な機能一覧
----------------
- data/jquants_client.py
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar
  - RateLimiter、リトライ、401 時の自動リフレッシュ、fetched_at 記録
- data/news_collector.py
  - fetch_rss（gzip 対応、SSRF/プライベートアドレス検査）
  - save_raw_news, save_news_symbols, run_news_collection
  - URL 正規化 / トラッキングパラメータ除去 / 記事ID は SHA-256 の先頭32文字
- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）と init_schema()
- data/pipeline.py
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl（差分更新・バックフィル・品質チェック）
- data/calendar_management.py
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- data/quality.py
  - 各種品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
- data/audit.py
  - 監査ログ用テーブル定義と init_audit_db / init_audit_schema
- config.py
  - 環境変数読み込み（.env/.env.local）、Settings オブジェクト経由の設定アクセス

必要条件（前提）
----------------
- Python 3.10 以上（PEP 604 の型表記などを使用）
- pip
- 必須パッケージ（例）
  - duckdb
  - defusedxml
（実際の要件はプロジェクトの pyproject.toml / requirements.txt を参照してください）

セットアップ手順
----------------
1. リポジトリを取得
   - git clone ... / or pip install -e .（パッケージ化されている場合）

2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 環境変数の設定
   - プロジェクトルートに .env（および .env.local）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（config.Settings 参照）
     - JQUANTS_REFRESH_TOKEN (J-Quants のリフレッシュトークン)
     - KABU_API_PASSWORD (kabuステーション API パスワード)
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (通知用)
   - 任意 / デフォルト
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG|INFO|...) — default: INFO
     - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db

   - サンプル .env（例）
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで：
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - 監査ログ専用 DB を初期化する場合：
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

基本的な使い方（コード例）
----------------

- DuckDB スキーマを初期化して ETL を走らせる（日次 ETL）
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定しないと today が使われる
  print(result.to_dict())

- 個別 ETL（株価差分）
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date(2026,1,1))

- J-Quants から直接データを取得（テストやデバッグ）
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()
  rows = fetch_daily_quotes(id_token=token, code="7203", date_from=date(2024,1,1), date_to=date(2024,12,31))

- ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 上場銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)

- マーケットカレンダーの判定/util
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_td = is_trading_day(conn, date(2026,3,1))
  nxt = next_trading_day(conn, date(2026,3,1))

- 品質チェック
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,1))
  for i in issues:
      print(i)

注意点・運用上のポイント
----------------
- J-Quants のレート制限（120 req/min）をライブラリ側で守る実装になっていますが、運用では複数プロセスからの同時呼び出しに注意してください（モジュール内の RateLimiter はプロセスローカル）。
- ETL は差分更新＋バックフィル設計のため、backfill_days を適切に設定して API の後出し修正を吸収してください。
- RSS 収集は外部 URL を扱うため、SSRF 対策やレスポンスサイズチェックを実装していますが、外部ソースの信頼性に依存します。
- DuckDB はトランザクションや同時接続の扱いが SQLite 等とは異なる点があるため、複数プロセスからの同時書き込みは運用設計で考慮してください。
- 環境変数の自動ロードを一時的に無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。

ディレクトリ構成（概要）
----------------
- src/kabusys/
  - __init__.py
  - config.py           — 環境変数と Settings
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存）
    - news_collector.py  — RSS ニュース収集と DB 保存
    - schema.py          — DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py        — ETL パイプライン（差分更新・日次 ETL）
    - calendar_management.py — カレンダー管理（営業日判定・更新ジョブ）
    - audit.py           — 監査テーブル定義 / 初期化
    - quality.py         — データ品質チェック
  - strategy/
    - __init__.py        — （戦略層の拡張ポイント）
  - execution/
    - __init__.py        — （発注/約定・ブローカー連携の拡張ポイント）
  - monitoring/
    - __init__.py        — （監視/アラート用の拡張ポイント）

拡張ガイドライン
----------------
- 戦略（strategy）や実行層（execution）はプレースホルダとして用意されています。戦略を追加する場合は strategy パッケージ配下に戦略モジュールを実装し、シグナル生成 → signal_queue 登録 → 発注処理のフローをつなげてください。
- 発注ブローカー連携は execution パッケージに実装し、監査テーブル（audit.py）へ適切に記録してください。
- モニタリング（Slack 等への通知）は config.Settings 経由で SLACK_* を読み、ログやアラートで利用してください。

ライセンス / 貢献
----------------
本 README ではライセンス情報は含めていません。実際のリポジトリの LICENSE ファイルを参照してください。バグ報告・機能追加は Issue / PR を通じてお願いします。

最後に
------
この README はコードベースの公開 API と主要な使い方、セットアップの出発点を説明しています。実運用では CI/CD、定期ジョブ（cron / Airflow など）、監視・ロギング構成を併せて設計してください。質問や追加でドキュメント化したい箇所があれば教えてください。