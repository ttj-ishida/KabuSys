# KabuSys

日本株自動売買システム用ライブラリ（KabuSys）の README（日本語）

バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買システムを構築するための内部ライブラリ群です。主に以下の機能を提供します。

- J-Quants API からの市場データ取得（株価日足、財務データ、マーケットカレンダー）
- RSS ベースのニュース収集と記事→銘柄紐付け
- DuckDB を使ったスキーマ定義・初期化
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日の取得）
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上のポイント
- API レート制御・リトライ・トークン自動リフレッシュ等、堅牢な通信処理
- DuckDB への保存は冪等（INSERT ... ON CONFLICT）を原則
- Look-ahead bias を避けるため取得時刻（fetched_at）を UTC で記録
- RSS 収集は SSRF・XML Bomb 等への対策を実施
- 品質チェックは Fail-Fast にせず全問題を収集して呼び出し側に伝える

主な機能一覧
-------------
- データ取得（kabusys.data.jquants_client）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- ニュース収集（kabusys.data.news_collector）
  - fetch_rss, save_raw_news, extract_stock_codes, run_news_collection
- スキーマ管理（kabusys.data.schema）
  - init_schema(db_path), get_connection(db_path)
- ETL（kabusys.data.pipeline）
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- 監査ログスキーマ（kabusys.data.audit）
  - init_audit_schema(conn), init_audit_db(db_path)
- 品質チェック（kabusys.data.quality）
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- 設定管理（kabusys.config）
  - 環境変数 / .env 自動読み込み、必須変数取得用 Settings オブジェクト

セットアップ手順
----------------

前提
- Python 3.10 以上（コードは PEP 604 の union 演算子（|）等を使用）
- ネットワークアクセス（J-Quants API、RSS フィード）

インストール（ローカル開発）
1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   追加パッケージ（プロジェクトで必要に応じて）
   - requests 等（本コードは標準ライブラリ urllib を使用しているため必須ではありません）

設定（環境変数 / .env）
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（読み込み順: OS 環境 > .env.local > .env）。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須の環境変数:
  - JQUANTS_REFRESH_TOKEN  — J-Quants API の refresh token
  - KABU_API_PASSWORD      — kabu ステーション API のパスワード
  - SLACK_BOT_TOKEN        — Slack 通知に使う Bot トークン
  - SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID
- 任意（デフォルト値あり）:
  - KABUSYS_ENV            — 実行環境（development / paper_trading / live）、デフォルト: development
  - LOG_LEVEL              — ログレベル（DEBUG/INFO/...）、デフォルト: INFO
  - KABU_API_BASE_URL      — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH            — SQLite モジュール用（デフォルト: data/monitoring.db）

例: .env（最小）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

使い方（簡単な例）
-----------------

DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# 既定で親ディレクトリを作成します
```

日次 ETL の実行（J-Quants からデータ取得して保存・品質チェック）
```
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")  # 初回のみ
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

マーケットカレンダーの夜間更新（バッチ）
```
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)  # デフォルトで先読み90日
print("saved", saved)
```

ニュース収集の実行（RSS から取り込み、銘柄紐付けまで）
```
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes は有効な銘柄コードセット（例: 全上場銘柄コード）
known_codes = {"7203", "6758", "8306", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # source_name -> 新規保存数
```

監査ログスキーマ初期化（戦略・発注の監査用）
```
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

品質チェックだけを実行
```
from kabusys.data.schema import get_connection
from kabusys.data.quality import run_all_checks
from datetime import date

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn, reference_date=date.today())
for i in issues:
    print(i)
```

設定オブジェクトの利用例
```
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必須: 未設定なら例外
print(settings.duckdb_path)            # Path オブジェクト
print(settings.is_live)                # 本番判定
```

テスト・開発時の便利な設定
- 自動 .env 読み込みを無効化して環境を独立させたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- id_token の自動リフレッシュ、レート制御、リトライはライブラリ側で処理されるため、テスト中は get_id_token の引数 id_token を注入して固定化できます。

ディレクトリ構成
----------------
（プロジェクト root の下に src/kabusys がある想定）

- src/
  - kabusys/
    - __init__.py  (パッケージ定義, __version__ = "0.1.0")
    - config.py    (環境変数・設定管理)
    - data/
      - __init__.py
      - jquants_client.py         (J-Quants API クライアント)
      - news_collector.py        (RSS ニュース収集)
      - schema.py                (DuckDB スキーマ定義・init)
      - pipeline.py              (ETL パイプライン)
      - calendar_management.py   (マーケットカレンダー管理)
      - audit.py                 (監査ログスキーマ)
      - quality.py               (データ品質チェック)
    - strategy/
      - __init__.py              (戦略に関するコード群: 空パッケージ)
    - execution/
      - __init__.py              (発注・実行管理: 空パッケージ)
    - monitoring/
      - __init__.py              (監視関連: 空パッケージ)

バージョン管理・リリース
-----------------------
パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください。

注意事項 / 既知の設計上の挙動
---------------------------
- J-Quants のレート制限（120 req/min）を厳守するため内部で固定間隔のレートリミッタを使用しています。大量並列でのリクエストは避けてください。
- ネットワークエラーや一時的エラーに対しては指数バックオフで最大 3 回リトライします（HTTP 408/429/5xx 対象）。401 はリフレッシュトークンから自動で再取得を試みます（1 回のみ）。
- RSS フィードの取得は SSRF 対策（スキーム検査、プライベートIPブロック、リダイレクト検査）や XML パース攻撃対策（defusedxml）を行っています。
- DuckDB への保存はできるだけ冪等になるよう ON CONFLICT を利用していますが、外部から直接 DB を変更した場合の不整合は別途検査が必要です。
- 全てのタイムスタンプは UTC の取り扱いが基本です（監査スキーマでは SET TimeZone='UTC' を実行します）。

貢献・拡張
-----------
- strategy や execution パッケージには戦略実装、ブローカー連携（kabuステーションや他の API）を追加できます。
- ニュース収集ソースは DEFAULT_RSS_SOURCES を拡張してください。
- ETL のスケジュールは cron / Airflow / Prefect 等で run_daily_etl を呼び出す形で運用できます。

サポート
-------
この README はライブラリ内部のコードをもとに作成しています。実運用前に必ずローカル環境で動作検証を行ってください。問い合わせ・バグ報告はリポジトリの issue をご利用ください。

以上。