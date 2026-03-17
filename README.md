# KabuSys

日本株向け自動売買プラットフォーム用ライブラリセット（KabuSys）。データ収集（J-Quants / RSS）、ETLパイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレース）などを提供します。

---

## プロジェクト概要

KabuSys は日本株自動売買システムの基盤ライブラリ群です。主に以下を目的としています。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存
- RSS ベースのニュース収集と銘柄抽出・保存
- 日次の ETL パイプライン（差分取得・バックフィル・品質チェック）
- JPX カレンダー管理（営業日判定、前後営業日の計算）
- 監査ログ（signal → order_request → execution のトレース用スキーマ）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

設計上の主な配慮点：
- API レート制御・リトライ・トークン自動更新（J-Quants クライアント）
- ETL は差分更新／バックフィルに対応し冪等に保存
- ニュース収集は SSRF / XML Bomb / 大容量レスポンス対策済み
- DuckDB を主要な永続層として想定（軽量で高速な分析DB）

---

## 主な機能一覧

- データ取得
  - 株価日足（OHLCV）取得・ページネーション対応（jquants_client.fetch_daily_quotes）
  - 財務データ（四半期 BS/PL）取得（jquants_client.fetch_financial_statements）
  - JPX マーケットカレンダー取得（jquants_client.fetch_market_calendar）
- DuckDB スキーマ管理
  - init_schema() によるスキーマ作成（raw / processed / feature / execution 層）
  - 監査ログ用スキーマ（init_audit_schema / init_audit_db）
- ETL
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- ニュース収集
  - RSS フィード取得（gzip 対応・最大サイズ制限）
  - URL 正規化（トラッキングパラメータ除去）と記事ID生成（SHA-256）
  - raw_news 保存／news_symbols（銘柄紐付け）
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（夜間バッチで先読み更新・バックフィル）
- 品質チェック
  - 欠損データ / スパイク検出 / 重複チェック / 日付不整合検査
  - run_all_checks でまとめて実行
- 設定管理
  - 環境変数読み込み（.env, .env.local、自動ロード・オプトアウト可能）
  - 必須設定の検証（settings オブジェクト）

---

## セットアップ手順

前提: Python 3.9+（型注釈から推奨）。パッケージ依存として少なくとも以下が必要です（プロジェクトの requirements.txt を参照してください）:

- duckdb
- defusedxml

基本手順（例）:

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install -U pip
   pip install duckdb defusedxml
   # もしローカルでパッケージとして使うなら:
   pip install -e .

4. 環境変数を準備
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` として以下のような値を設定してください（例: .env.example を参照）。

   必須環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API のパスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   任意 / デフォルト:
   - KABUSYS_ENV (development | paper_trading | live) - default: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) - default: INFO
   - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化

   設定値は `kabusys.config.settings` からアクセスできます。

5. DuckDB スキーマ初期化（Python REPL またはスクリプト）
   以下は簡単な例です：

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   監査ログ用に別 DB を使う場合：
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（代表的な例）

以下はライブラリ内 API を直接呼ぶ例です。実運用ではこれらを CLI / ワーカー / airflow 等から呼び出します。

- DuckDB 初期化

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

  run_daily_etl は市場カレンダー取得 → 株価差分取得（バックフィル） → 財務差分取得 → 品質チェック の順で実行します。品質チェックはオプションで無効化可能。

- 個別 ETL（株価）:

  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date.today())

- RSS ニュース収集

  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
  # results: {source_name: 新規保存件数}

- カレンダー夜間更新ジョブ

  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)

- 品質チェック単体実行

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues: print(i)

- J-Quants API トークン取得（直接呼ぶ場合）

  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用

- ニュースから銘柄コード抽出（内部ユーティリティ）

  from kabusys.data.news_collector import extract_stock_codes
  codes = extract_stock_codes("本日の話題: 7203 と 6758 が急騰", known_codes=set(...))

注意点:
- jquants_client は内部でレート制御とリトライを行います。
- 多くの保存操作は ON CONFLICT を使った冪等化を担保しています。
- ニュース収集は SSRF / XML Bomb / メモリ DoS への耐性を持つ設計です。

---

## 設定（環境変数）

主要な環境変数一覧:

- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) : kabuステーション API のパスワード
- KABU_API_BASE_URL : kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) : Slack Bot トークン
- SLACK_CHANNEL_ID (必須) : Slack チャンネル ID
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視系などで使う SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 環境（development | paper_trading | live）デフォルトは development
- LOG_LEVEL : ログレベル（DEBUG|INFO|...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化する（値を設定）

自動ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml がある場所）を探索し、.env を自動で読み込みます。
- .env.local は .env を上書きする目的で読み込まれます。
- テストやカスタム環境で自動ロードを無効化したいときは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

リポジトリの主要ファイル（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - news_collector.py      # RSS ニュース収集・保存
    - schema.py              # DuckDB スキーマ定義・初期化
    - pipeline.py            # ETL パイプライン（run_daily_etl など）
    - calendar_management.py # カレンダー関連ユーティリティ・バッチ
    - audit.py               # 監査ログ（signal / order_requests / executions）
    - quality.py             # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

主な責務の分離:
- data/ 以下: データ取得、保存、ETL、品質、カレンダー、監査ログ
- strategy/: 戦略実装を格納（このリポジトリでは空の初期パッケージ）
- execution/: 発注・ブローカー連携用コード用（初期パッケージ）
- monitoring/: 監視・メトリクス用（初期パッケージ）

---

## 開発メモ / 注意事項

- DuckDB はファイルベースで軽量に使えるため、本番では専用ファイルを推奨します（デフォルト: data/kabusys.duckdb）。
- jquants_client は API レート（120 req/min）を守るために固定間隔のスロットリングとリトライ戦略を実装しています。負荷をかけるバッチを設計するときはこの制約に注意してください。
- ニュース収集では外部 URL を開くため SSRF 対策（リダイレクト先の検査、プライベートアドレス拒否）を行っています。テストでネットワークリクエストを行わない場合は _urlopen をモックすると良いです。
- スキーマは冪等で作成されるため、init_schema を何度呼んでも安全です。
- audit スキーマはタイムゾーンを UTC に固定して運用する前提です（init_audit_schema は SET TimeZone='UTC' を実行します）。

---

もし README に含めたい具体的な usage スクリプト、CI 設定、requirements.txt などがあれば、それらを元にさらに導入手順や運用手順を詳細化できます。必要であればサンプル .env.example や systemd / cron での運用例も作成できます。