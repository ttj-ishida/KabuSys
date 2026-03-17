# KabuSys

日本株自動売買向けのデータ基盤・ETL・監査モジュール群です。  
J-Quants API から市場データ・財務データ・カレンダーを取得し、DuckDB に保存・品質チェックを行う ETL、RSS ニュース収集、監査ログスキーマなどを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向け自動売買システムの基盤ライブラリです。主に次を目的とします：

- J-Quants API からのデータ取得（株価日足、財務データ、マーケットカレンダー）と DuckDB への永続化（冪等保存）。
- RSS を用いたニュース収集と記事→銘柄紐付け（raw_news / news_symbols）。
- ETL パイプライン（差分取得、バックフィル、品質チェック）をワンストップで実行。
- 監査ログ（信号→発注→約定のトレーサビリティ）テーブル定義と初期化機能。
- データ品質チェック（欠損、重複、将来日付、スパイク等）。

設計上の特徴：

- API レート制御（J-Quants: 120 req/min 固定間隔スロットリング）。
- リトライ・トークン自動リフレッシュ（401 受信時に refresh を試行）。
- DuckDB への保存は ON CONFLICT を用いた冪等性を確保。
- RSS 収集では SSRF や XML 攻撃・巨大レスポンスを防ぐ対策あり。

---

## 機能一覧

- data/jquants_client.py
  - J-Quants からの fetch/save:
    - fetch_daily_quotes / save_daily_quotes（OHLCV）
    - fetch_financial_statements / save_financial_statements（四半期財務）
    - fetch_market_calendar / save_market_calendar（JPX カレンダー）
  - トークン取得: get_id_token
  - レートリミッタ、リトライ/バックオフ、401 リフレッシュ対応

- data/pipeline.py
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の一括 ETL
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
  - 差分取得、backfill の自動算出

- data/schema.py
  - init_schema / get_connection: DuckDB スキーマの初期化と接続取得
  - Raw / Processed / Feature / Execution 層のテーブル定義

- data/news_collector.py
  - fetch_rss: RSS 取得（SSRF/サイズ/圧縮/XML 安全対策）
  - save_raw_news: raw_news テーブルへ冪等保存（INSERT ... RETURNING）
  - extract_stock_codes / run_news_collection: 記事から銘柄コード抽出・紐付け

- data/quality.py
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks: すべての品質チェックを実行し QualityIssue のリストを返す

- data/audit.py
  - 監査ログ用テーブル（signal_events / order_requests / executions）定義
  - init_audit_schema / init_audit_db

- config.py
  - 環境変数ロード（.env / .env.local の自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - Settings クラス（各種必須設定プロパティ）

---

## セットアップ手順（開発環境）

必要な Python バージョン: 3.10 以上（型注釈で | を使用）

1. リポジトリをクローン（例）
   - git clone <リポジトリURL>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows (PowerShell): .venv\Scripts\Activate.ps1

3. 依存パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - パッケージ化されている場合:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を作成できます（config.py は自動読み込みします）。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

サンプル .env:
    JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
    KABU_API_PASSWORD=あなたの_kabu_api_password
    # KABU_API_BASE_URL はオプション（デフォルト: http://localhost:18080/kabusapi）
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

注意: settings は必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を _require で検査します。

---

## 使い方（基本例）

以下のコードは Python REPL やスクリプトで実行できます。事前に .env を設定し、依存をインストールしてください。

1) DuckDB スキーマ初期化
    from kabusys.data.schema import init_schema
    from kabusys.config import settings

    conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成してテーブルを作る

2) 監査スキーマを追加で初期化する場合
    from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn)  # 既存の conn に監査テーブルを追加

または独立 DB として初期化:
    from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")

3) 日次 ETL を実行する
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)  # target_date を指定可能
    print(result.to_dict())

- run_daily_etl は市場カレンダー→株価→財務→品質チェックの順で処理します。各ステップは独立してエラーハンドリングされるため、一部失敗しても残りは継続します。

4) RSS ニュース収集ジョブ
    from kabusys.data.news_collector import run_news_collection
    # known_codes: 銘柄抽出に使用する既知の銘柄コード集合（例: {"7203","6758",...}）
    stats = run_news_collection(conn, sources=None, known_codes=known_codes)
    print(stats)  # {source_name: 新規保存件数}

5) J-Quants API を直接使う（トークン・取得）
    from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
    token = get_id_token()  # settings.jquants_refresh_token を利用
    recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

ログやエラーは Python の logging を通じて出力されます。LOG_LEVEL は環境変数で制御可能です。

---

## 主要設定（環境変数）

Settings で参照される主要な環境変数：

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略可、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (省略可、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live、デフォルト: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL、デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化

---

## ディレクトリ構成

以下はコードベースに含まれる主要ファイルとモジュール構成です（src/kabusys 配下）:

- __init__.py
  - パッケージのメタ情報（__version__）とサブモジュール一覧

- config.py
  - 環境変数/設定の読み込み・管理（Settings）

- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py  — RSS 収集、記事保存、銘柄抽出
  - schema.py          — DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
  - pipeline.py        — ETL パイプライン（差分取得、品質チェック）
  - audit.py           — 監査ログスキーマ（signal/order_request/executions）
  - quality.py         — データ品質チェック（欠損/重複/スパイク/日付整合性）
  - (その他)           — 将来的に ETL や監視用モジュールを追加予定

- strategy/
  - __init__.py  — 戦略モジュールのエントリ（実装は各戦略で追加）

- execution/
  - __init__.py  — 発注・ブローカ連携モジュール（実装は各ブローカごとに追加）

- monitoring/
  - __init__.py  — 監視 / メトリクス関連（実装を追加）

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り、接続単位で操作する設計です。

---

## 注意点 / 運用上のヒント

- J-Quants API レート制御（120 req/min）を遵守します。大量取得時は pipeline の間隔や page サイズに注意してください。
- get_id_token はリフレッシュトークンを元に id_token を取得します。jquants_client は 401 時に自動で再取得を試みる実装です。
- DuckDB のスキーマは冪等に作成されます。既存 DB に対しては init_schema を実行しても安全です。
- RSS 取得は外部 URL を直接アクセスするため、SSRF と巨大レスポンス対策が組み込まれています。テスト時は news_collector._urlopen をモックできます。
- 本パッケージは「基盤ライブラリ」です。実際の発注機能や Slack 通知等は別モジュールで統合して利用してください。

---

必要があれば、README に次の追加情報を作成できます：
- 具体的な ETL 定期実行例（cron / Airflow / Prefect など）
- サンプル .env.example ファイル
- よくあるトラブルシュート（トークン・DB 初期化・RSS パース失敗など）
- 単体テストの実行方法（pytest 設定）

ほか追加希望があれば教えてください。