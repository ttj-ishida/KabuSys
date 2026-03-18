KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けのデータ取得・ETL・品質チェック・監査（トレーサビリティ）を中心に設計された自動売買基盤のライブラリ群です。  
主に下記を提供します：

- J-Quants API を利用した株価・財務・マーケットカレンダーの取得と DuckDB への冪等保存
- RSS ベースのニュース収集と記事→銘柄紐付け
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、翌営業日/前営業日取得など）
- 監査ログ（シグナル→発注→約定のトレース用スキーマ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計方針の例：
- API レート制限厳守、指数バックオフによるリトライ、トークン自動リフレッシュ
- DuckDB への保存は ON CONFLICT/DO UPDATE 等で冪等化
- SSRF・XML Bomb 等への対策（news_collector）
- ETL は Fail-Fast せず問題を検出して呼び出し元が判断できる形にする

機能一覧
--------
主なモジュール／機能（抜粋）：

- kabusys.config
  - .env / 環境変数の自動ロード（プロジェクトルート検出）
  - settings オブジェクト（J-Quants トークン、kabu API、Slack、DBパス、環境等）
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB 保存）
  - レート制限・リトライ・トークンキャッシュ実装
- kabusys.data.news_collector
  - RSS フィード取得・前処理（URL正規化、トラッキング除去）
  - raw_news へ冪等保存、news_symbols（銘柄紐付け）
  - SSRF 対策、サイズ制限、gzip 対応
- kabusys.data.schema
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema / get_connection
- kabusys.data.pipeline
  - run_daily_etl（カレンダー→株価→財務→品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl（差分更新・バックフィル）
- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチでカレンダー差分更新）
- kabusys.data.audit
  - 監査ログスキーマの初期化（signal_events, order_requests, executions）
  - init_audit_schema / init_audit_db
- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks（QualityIssue のリストを返す）

セットアップ手順
----------------

前提
- Python 3.10 以降（ソース中での型ヒント（X | None）を使用しているため）
- DuckDB が利用可能な環境
- ネットワーク接続（J-Quants / RSS / kabu API）

インストール（例）
1. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクト全体をパッケージ化している場合）pip install -e .

必須環境変数
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション/ブローカー API のパスワード（必須）
- SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
- SLACK_CHANNEL_ID      : 通知先 Slack チャネル ID（必須）

任意/デフォルト値あり
- KABUSYS_ENV           : development | paper_trading | live （デフォルト: development）
- LOG_LEVEL             : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : "1" をセットすると .env の自動ロードを無効化
- KABUSYS_DISABLE_AUTO_ENV_LOAD を除き、プロジェクトルートにある .env/.env.local が自動で読み込まれます。

データベースのパス（環境変数で上書き可能）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)

初期化
- DuckDB スキーマを作成する（例）
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- 監査ログ専用 DB を初期化する場合
  from kabusys.data import audit
  audit_conn = audit.init_audit_db("data/audit_kabusys.duckdb")

使い方（クイックスタート）
-------------------------

1) 設定の読み込み
- settings = from kabusys.config import settings を使って、必要な環境値を参照できます。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

2) ETL（日次パイプライン）を実行する
- 例（簡単なスクリプト）:

  from kabusys.data import schema, pipeline
  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())

  - run_daily_etl は市場カレンダー取得→株価差分取得→財務差分取得→品質チェック の順に実行し、ETLResult を返します。

3) ニュース収集ジョブを実行する
- 例:

  from kabusys.data import schema, news_collector
  conn = schema.get_connection("data/kabusys.duckdb")
  sources = {"yahoo_finance": "https://news.yahoo.co.jp/rss/categories/business.xml"}
  # known_codes は銘柄抽出フィルタ（例: 証券コードセット）
  res = news_collector.run_news_collection(conn, sources=sources, known_codes={"7203","6758"})
  print(res)  # ソースごとの新規保存数を返す

4) カレンダー夜間更新ジョブ
- calendar_update_job を定期実行（cron 等）すると market_calendar が更新されます。

  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print(f"saved={saved}")

5) J-Quants API の利用（手動取得等）
- id_token を取得する:

  from kabusys.data import jquants_client as jq
  token = jq.get_id_token()  # settings.jquants_refresh_token を使用して取得

- 日足を取得して保存:

  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = jq.save_daily_quotes(conn, records)

運用・開発上のポイント
--------------------
- 自動環境読み込み:
  - プロジェクトルートに .env/.env.local がある場合、config モジュールが自動で読み込みます。
  - .env.local は .env の上書き（override=True）として読み込まれます。
- API レート制限:
  - jquants_client は 120 req/min のレート制限を守るよう内部でスロットリングしています。
- トークンリフレッシュ:
  - 401 を受け取ると自動でリフレッシュを行い 1 回だけリトライします（無限再帰防止済）。
- テストのしやすさ:
  - news_collector._urlopen 等の内部実装をモックできる箇所があります。
- 品質チェック:
  - quality.run_all_checks は QualityIssue オブジェクトを返します。ETL は重大な品質問題が見つかっても全処理を試み、呼び出し側で停止・通知判断を行う設計です。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
- execution/        (発注実行関連のプレースホルダ)
- strategy/         (戦略関連のプレースホルダ)
- monitoring/       (監視・メトリクス関連のプレースホルダ)
- data/
  - __init__.py
  - jquants_client.py        # J-Quants API クライアント + DuckDB 保存
  - news_collector.py        # RSS 収集・前処理・DB 保存
  - schema.py                # DuckDB スキーマ定義・初期化
  - pipeline.py              # ETL パイプライン（差分・品質チェック）
  - calendar_management.py   # マーケットカレンダー操作 / 夜間更新ジョブ
  - audit.py                 # 監査ログ（signal/order/execution）スキーマ
  - quality.py               # データ品質チェック

補足
----
- コード内にあるログ出力（logger）を利用して運用監視・アラートを行ってください。settings.log_level でログレベルを制御できます。
- .env.example の作成・管理を推奨します（リポジトリには含めない機密情報は .env.local 等で管理）。
- 実際の発注（実資金を動かす）部分は execution/ 以下に実装を追加して使用してください（本リポジトリのコードはデータ取得・ETL・監査を中心に提供しています）。

ライセンスや貢献
----------------
- 本 README には記載がありません。実プロジェクトでは LICENSE を設定してください。貢献ルール（CONTRIBUTING.md）等の整備を推奨します。

質問や追加したいドキュメント（例: 環境変数の .env.example、運用ガイド、デプロイ手順、docker-compose 例など）があれば教えてください。必要に応じて追記・テンプレート作成を行います。