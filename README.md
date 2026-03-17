KabuSys
=======

KabuSys は日本株のデータ収集・ETL・品質管理・監査ログなどを備えた自動売買システムのコアライブラリです。J-Quants API と RSS ニュースを取り込み、DuckDB に保存して戦略レイヤや実行層と連携できるように設計されています。

主な目的
- J-Quants API から株価・財務・マーケットカレンダーを差分取得して保存
- RSS からニュースを収集して記事・銘柄紐付けを行う
- ETL パイプライン（差分更新・バックフィル）とデータ品質チェックを提供
- DuckDB に対するスキーマ定義と監査ログ（発注／約定トレーサビリティ）を提供

特徴
- API レート制御（120 req/min）・リトライ・トークン自動更新を実装
- DuckDB を用いた永続化（冪等保存: ON CONFLICT DO UPDATE / DO NOTHING）
- ニュース収集での SSRF 対策、XML 攻撃対策、受信サイズ制限
- 品質チェック（欠損・スパイク・重複・日付不整合）の一括実行
- 監査ログ（signal → order_request → execution のトレース）を用意
- .env / 環境変数による設定管理（プロジェクトルートを自動検出して読み込み）

機能一覧
- データ取得・保存（kabusys.data.jquants_client）
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
- ニュース収集（kabusys.data.news_collector）
  - fetch_rss / save_raw_news / save_news_symbols
  - トラッキングパラメータ除去、記事IDを SHA-256（先頭32文字）で生成
- スキーマ管理（kabusys.data.schema）
  - init_schema / get_connection（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義
- ETL パイプライン（kabusys.data.pipeline）
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl（カレンダー取得 → 株価差分 → 財務差分 → 品質チェック）
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチ）
- データ品質チェック（kabusys.data.quality）
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（QualityIssue リストを返す）
- 監査ログ（kabusys.data.audit）
  - init_audit_schema / init_audit_db（signal_events, order_requests, executions 等）

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 環境を用意（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要なパッケージをインストール
   - pip install -r requirements.txt
     （本リポジトリに requirements.txt がない場合は少なくとも以下をインストールしてください）
     - duckdb
     - defusedxml
4. パッケージを編集可能モードでインストール（任意）
   - pip install -e .

環境変数 / .env
- 自動ロード:
  - パッケージはプロジェクトルート（.git 又は pyproject.toml を基準）を探索し、.env → .env.local の順で自動読み込みします。
  - OS 環境変数が優先されます。テストなどで自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数（Settings 経由で参照されます）
  - JQUANTS_REFRESH_TOKEN  （J-Quants リフレッシュトークン）
  - KABU_API_PASSWORD      （kabuステーション API パスワード）
  - SLACK_BOT_TOKEN        （Slack 通知に使う Bot トークン）
  - SLACK_CHANNEL_ID       （通知先チャンネル ID）
- 任意 / デフォルト
  - KABUSYS_ENV            （development / paper_trading / live、デフォルト: development）
  - LOG_LEVEL              （DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（1 で自動ロード無効化）
  - DUCKDB_PATH            （デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH            （デフォルト: data/monitoring.db）

基本的な使い方（例）
- DuckDB スキーマ初期化
  Python REPL やスクリプトで:
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  # ":memory:" を指定するとインメモリ DB になります

- 日次 ETL 実行
  from kabusys.data import pipeline
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())

  - id_token を外部で取得して注入することも可能（テストや並列処理向け）。
  - run_daily_etl はカレンダー取得 → 株価差分 → 財務差分 → 品質チェックを順に実行します。
  - ETLResult に処理結果・品質問題・エラーがまとめられます。

- RSS ニュース収集ジョブ
  from kabusys.data import news_collector
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  # デフォルトソースを使う場合
  results = news_collector.run_news_collection(conn)
  # 特定ソース・known_codes を指定して実行
  sources = {"yahoo": "https://news.yahoo.co.jp/rss/categories/business.xml"}
  known_codes = {"7203", "6758"}
  results = news_collector.run_news_collection(conn, sources=sources, known_codes=known_codes)

- カレンダー更新ジョブ（夜間）
  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)

- 監査ログ初期化（監査用スキーマ追加）
  from kabusys.data import audit, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  audit.init_audit_schema(conn)

主要モジュール一覧（ファイル単位）
- kabusys/
  - __init__.py                 : パッケージ初期化、バージョン情報
  - config.py                   : 環境変数 & 設定管理（Settings）
- kabusys/data/
  - __init__.py
  - jquants_client.py           : J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py           : RSS ニュース収集・保存・銘柄抽出
  - schema.py                   : DuckDB スキーマ定義・初期化
  - pipeline.py                 : ETL パイプライン（差分更新・品質チェック）
  - calendar_management.py      : マーケットカレンダー管理・営業日判定
  - audit.py                    : 監査ログ（signal/order_request/executions）
  - quality.py                  : データ品質チェック
- kabusys/strategy/             : 戦略関連（パッケージプレースホルダ）
- kabusys/execution/           : 実行（発注）関連（パッケージプレースホルダ）
- kabusys/monitoring/          : 監視関連（パッケージプレースホルダ）

推奨運用メモ
- ETL は差分更新とバックフィル（デフォルト 3 日）を組み合わせて API の後出し修正に耐える設計です。cron や Airflow 等で日次ジョブとして実行してください。
- J-Quants のレート制限（120 req/min）を厳守するため、ライブラリ内で固定間隔レートリミッタを実装しています。短時間に大量リクエストしないでください。
- ニュース収集は外部 URL を取得するため SSRF・XML リスク対策を行っていますが、社内ポリシーに従いホワイトリストやプロキシ経由で実行するのが安全です。
- DuckDB ファイルは定期的にバックアップを取ってください。監査ログは削除しない前提です。

開発・テスト
- 自動 .env 読み込みが邪魔な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。
- jquants_client のテストでは get_id_token / _request の外部呼び出しをモックして単体テストを行うのが良いです。
- news_collector._urlopen をモックすればネットワークを介さずに RSS 取得処理をテストできます。

ライセンス / 貢献
- 本リポジトリのライセンスと貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING ファイルを参照してください（存在する場合）。

バージョン
- 現在のライブラリバージョン: 0.1.0（kabusys.__version__）

問合せ
- 実行や導入に関する質問はリポジトリの Issue を利用してください。README に記載の Slack 設定を行えば、運用中の通知連携が可能です。

以上。README に記載したコード利用例はライブラリ内部の API に合わせた最小例です。実運用では適切なエラーハンドリング・ログ出力・シークレット管理を行ってください。