KabuSys
=======

日本株向け自動売買基盤のコアライブラリ（データ取得・ETL・監査・品質チェック等）

バージョン: 0.1.0

概要
----
KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。  
主に以下を提供します。

- J-Quants API を利用したデータ取得（株価日足、財務データ、JPXカレンダー）
- RSS ニュース収集と記事→銘柄紐付け処理
- DuckDB を用いたスキーマ定義・初期化（Raw/Processed/Feature/Execution 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日取得）
- 監査ログ（signal → order → execution のトレーサビリティ）
- データ品質チェック（欠損／スパイク／重複／日付不整合検出）

機能一覧
--------
主な機能（モジュール別）

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルートを探索）
  - 必須環境変数の取得をラップした Settings クラス
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

- kabusys.data.jquants_client
  - J-Quants API クライアント
  - レート制限（120 req/min）とリトライ、トークン自動リフレッシュ対応
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への冪等保存関数: save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（リフレッシュトークン→IDトークン）

- kabusys.data.news_collector
  - RSS フィード取得（gzip 対応）
  - XML パースに defusedxml を使用（セキュリティ対策）
  - SSRF 対策（スキーム検証、プライベートホスト検出、リダイレクト検査）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）
  - save_raw_news / save_news_symbols（DuckDB へ冪等保存、INSERT ... RETURNING を使用）
  - extract_stock_codes（本文から4桁銘柄コード抽出）

- kabusys.data.schema
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution / Audit 補助）
  - init_schema, get_connection

- kabusys.data.pipeline
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 差分更新・backfill による後出し修正吸収
  - ETLResult による実行結果レポート

- kabusys.data.calendar_management
  - market_calendar を基にした営業日判定・前後営業日取得・レンジの営業日取得
  - calendar_update_job（夜間バッチで JPX カレンダー差分更新）

- kabusys.data.audit
  - 監査ログ用テーブル（signal_events / order_requests / executions）定義と初期化
  - init_audit_schema / init_audit_db

- kabusys.data.quality
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - run_all_checks（QualityIssue オブジェクトの一覧を返す）

セットアップ手順
--------------
前提
- Python 3.10 以上（PEP 604 の型アノテーション（|）等を使用）
- 仮想環境推奨

1. リポジトリをチェックアウト
   - 例: git clone ...

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトに setup/pyproject があれば pip install -e . で依存を追加できます）

4. 環境変数を設定
   - プロジェクトルートに .env を作成すると自動読み込みされます（.env.local も上書きで読み込む）
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite (monitoring) パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development, paper_trading, live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

使い方（スニペット）
------------------

DB スキーマ初期化（DuckDB）:
- Python REPL やスクリプトで:

from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# ":memory:" を指定するとインメモリ DB

日次 ETL を実行（J-Quants トークンは設定済み前提）:

from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())

特定の API 呼び出し（例: 株価取得）:

from kabusys.data import jquants_client as jq
data = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
# DuckDB に保存する場合:
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
jq.save_daily_quotes(conn, data)

ニュース収集ジョブ（RSS → raw_news / news_symbols）:

from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# known_codesは銘柄コードセット（抽出に使用）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}

監査ログの初期化:

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")

品質チェック（個別／全体実行）:

from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)

マーケットカレンダーのユーティリティ:

from kabusys.data.calendar_management import is_trading_day, next_trading_day
is_open = is_trading_day(conn, date.today())
next_day = next_trading_day(conn, date.today())

設定（Settings）利用例:

from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.is_live, settings.log_level)

注意点・運用ヒント
-----------------
- J-Quants API にはレート制限があるため、jquants_client は固定間隔でスロットリングを行います（120 req/min）。
- get_id_token は 401 応答時に自動でリフレッシュを行う設計です。
- ETL は差分更新＋バックフィルを行うため、初回は広範囲取得、以後は差分のみ取得します。
- news_collector は SSRF / XML Bomb / Gzip Bomb に対する防護（検証・サイズ上限・defusedxml）を組み込んでいます。
- DuckDB のファイルはデフォルトで data/ 配下に作成されます。バックアップ/権限に注意してください。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を起点）から行われます。CI/テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

src/
  kabusys/
    __init__.py               # パッケージ定義（__version__）
    config.py                 # 環境変数／設定管理
    data/
      __init__.py
      jquants_client.py       # J-Quants API クライアント（取得＋保存）
      news_collector.py       # RSS → raw_news、news_symbols
      schema.py               # DuckDB スキーマ定義・初期化
      pipeline.py             # ETL パイプライン（run_daily_etl 等）
      calendar_management.py  # カレンダー管理ユーティリティ
      audit.py                # 監査ログ（signal / order / execution）
      quality.py              # データ品質チェック
    strategy/
      __init__.py             # 戦略層（将来的な拡張用）
    execution/
      __init__.py             # 発注・ブローカー連携（将来的な拡張用）
    monitoring/
      __init__.py             # 監視／アラート（将来的な拡張用）

バージョン
--------
__version__ = "0.1.0"

ライセンス
--------
リポジトリ内の LICENSE を参照してください。（本READMEにはライセンス表記を含めていません）

補足
----
README に書かれている例はライブラリ API の利用例です。実運用ではログ設定、エラーハンドリング、シークレット管理、バックアップ・監査要件に応じた追加実装・監視を行ってください。質問や利用例の追加が必要であれば教えてください。