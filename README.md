# KabuSys

日本株向け自動売買・データ基盤ライブラリ。  
J-Quants / RSS 等の外部データを取得し、DuckDB に格納して ETL・品質チェック・監査ログを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買システムのデータ取得・ETL・監査基盤を提供する Python パッケージです。主に以下を目的とします。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存
- RSS からニュース記事を収集して正規化・DB保存し、銘柄コード抽出
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 監査ログ（シグナル→発注→約定 のトレーサビリティ）用スキーマの初期化
- マーケットカレンダーの管理（営業日判定・前後営業日探索）

設計面では、API レート制限・リトライ・冪等性（ON CONFLICT）・Look-ahead バイアス対策（fetched_at の保存）等に配慮しています。

---

## 主な機能一覧

- J-Quants クライアント
  - 株価日足（OHLCV）fetch_daily_quotes / save_daily_quotes
  - 財務データ fetch_financial_statements / save_financial_statements
  - マーケットカレンダー fetch_market_calendar / save_market_calendar
  - レート制限・リトライ・トークン自動リフレッシュ実装

- ニュース収集
  - RSS フィード取得（gzip 対応、SSRF/サイズ制限/XML 脆弱性対策）
  - URL 正規化、記事ID生成（SHA-256）
  - raw_news / news_symbols への冪等保存

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 各レイヤーの DDL を定義
  - init_schema() / get_connection()

- ETL パイプライン
  - run_daily_etl(): カレンダー→株価→財務→品質チェック の一括処理
  - 差分更新、バックフィル、品質チェックの実行

- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job()

- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出
  - QualityIssue 型で詳細を返却

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査スキーマ
  - init_audit_db / init_audit_schema

---

## 要件

- Python 3.10+
- パッケージ依存（少なくとも）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants, RSS）

必要パッケージはプロジェクトの packaging/requirements に依存しますが、開発用途では少なくとも上記を pip で入れてください。

例:
pip install duckdb defusedxml

---

## 環境変数 / .env

KabuSys は .env から自動的に環境変数を読み込みます（プロジェクトルートに .git または pyproject.toml がある場合）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数:
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API のパスワード（発注モジュールで使用）
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID

オプション / デフォルト:
- KABUSYS_ENV            — "development"（デフォルト） / "paper_trading" / "live"
- LOG_LEVEL              — "INFO"（デフォルト） 等
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化（値がセットされていれば無効）
- DUCKDB_PATH            — デフォルト "data/kabusys.duckdb"
- SQLITE_PATH            — デフォルト "data/monitoring.db"
- KABUS_API_BASE_URL     — kabu API base URL（デフォルト "http://localhost:18080/kabusapi"）

例 .env（実際のトークンは置き換えてください）:
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repository_url>
   cd <repository>

2. Python 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows

3. 必要パッケージをインストール
   pip install -U pip
   pip install duckdb defusedxml

   （プロジェクトに packaging がある場合は pip install -e . を使ってローカルインストールできます）

4. 環境変数（.env）を作成
   プロジェクトルートに .env を置くと自動ロードされます。上記の必須変数を設定してください。

5. DuckDB スキーマ初期化
   例: Python REPL やスクリプトで以下を実行して DB を初期化します。

   from kabusys.data import schema
   from kabusys.config import settings
   conn = schema.init_schema(settings.duckdb_path)

   init_schema は parent ディレクトリを自動作成します。

6. 監査ログ用 DB（必要な場合）
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主要ワークフロー例）

以下は典型的な運用例のコードスニペットです。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  from datetime import date
  import duckdb
  from kabusys.data import schema, pipeline
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)  # 初回のみ
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 市場カレンダー更新ジョブ（夜間バッチ）
  from kabusys.data import calendar_management
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  saved = calendar_management.calendar_update_job(conn)
  print("saved:", saved)

- ニュース収集と銘柄紐付け
  from kabusys.data import news_collector, schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  # known_codes: 既知の銘柄コードセット（例: 上場銘柄一覧）
  results = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
  print(results)

- J-Quants トークン取得 / データフェッチ（テスト・デバッグ用）
  from kabusys.data import jquants_client as jq
  token = jq.get_id_token()  # settings.jquants_refresh_token を使用
  quotes = jq.fetch_daily_quotes(id_token=token, code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))

注意点:
- run_daily_etl 等は内部でエラーを個別にハンドリングします。戻り値の ETLResult.errors / quality_issues を確認してください。
- J-Quants API 呼び出しはレート制限（120 req/min）を自動で制御します。
- fetch_rss は SSRF / Gzip Bomb / XML 漏洩対策を実装しています。

---

## API / モジュール要約

- kabusys.config
  - settings: 環境変数からの設定取得（例: settings.jquants_refresh_token, settings.duckdb_path）
  - 自動 .env ロード（プロジェクトルート検出）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - 各種チェック関数 (check_missing_data, check_spike, ...)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成

以下は主要なファイル / モジュール構成（src 配下）です。

src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      schema.py
      pipeline.py
      calendar_management.py
      audit.py
      quality.py
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py

---

## 開発メモ / 注意事項

- 型ヒントや union 型（|）を使用しているため Python 3.10 以上を推奨します。
- DuckDB の接続は軽量ですが、トランザクション管理には注意してください（audit.init_audit_schema の transactional 引数等）。
- J-Quants の API レート制限・429 ヘッダ（Retry-After）の尊重、401 発生時のトークン自動リフレッシュ等の実装が含まれます。運用時はログを監視してください。
- RSS 処理では外部から不正な XML / 大容量データ / リダイレクトによる内部アドレス到達等を防止するための対策を行っていますが、運用ポリシーに合わせてソースのホワイトリスト化などを行ってください。

---

もし README に追加したい実行スクリプトや CI / デプロイ手順、あるいはより具体的な .env.example を用意したい場合は、その内容を教えてください。README を拡張してサンプルスクリプトや運用手順を追記します。