# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants API や RSS を用いたデータ収集、DuckDB を用いたデータ格納、ETL パイプライン、データ品質チェック、監査ログ（発注〜約定のトレース）などを提供します。

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（基本例）
- 環境変数（設定）
- ディレクトリ構成

---

プロジェクト概要
----------------
KabuSys は、J-Quants や RSS などから日本株の市場データ・財務データ・ニュースを取得して DuckDB に保存し、特徴量生成や戦略/発注モジュールに渡せるようにするためのライブラリ群です。設計上のポイント:
- API レート制御、リトライ、トークン自動リフレッシュ（J-Quants）
- データ取得の冪等性（DuckDB の ON CONFLICT / DO UPDATE を活用）
- ニュース収集は SSRF や XML 攻撃対策を含む堅牢な実装
- ETL の差分更新・バックフィル・品質チェックを備えた日次パイプライン
- 発注・監査ログのための監査スキーマ（order_request_id による冪等制御）

主な機能
---------
- 環境/設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック用 Utilities
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務諸表、マーケットカレンダーの取得
  - レートリミット制御・リトライ（指数バックオフ）・トークン自動リフレッシュ
  - DuckDB へ冪等保存する save_* 関数群
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得、URL 正規化、記事ID（SHA-256先頭部）生成
  - SSRF/圧縮サイズ/XML 攻撃対策、DuckDB へ挿入（チャンク、トランザクション）
  - 銘柄コード抽出・news_symbols による紐付け
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema() による初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル・品質チェックの組み合わせ
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、calendar_update_job
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合の検出
  - QualityIssue オブジェクトで問題を返却
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義
  - init_audit_db による監査DB初期化

セットアップ手順
----------------
前提:
- Python 3.10 以上（PEP 604 の Union 表記 (X | None) を使用）
- DuckDB を使用するため duckdb パッケージが必要
- RSS パースで defusedxml を利用

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   代表的なパッケージ:
   - duckdb
   - defusedxml

   例:
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

3. ソースをインストール / パスを通す
   - 開発中: pip install -e .
   - または PYTHONPATH を通して直接 import できるようにします。

4. 環境変数の準備
   - プロジェクトルートに .env または .env.local を作成します（既定で .env.local が .env を上書き）。
   - 自動ロードはプロジェクトルート（.git または pyproject.toml の存在）を検出して行われます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - 監査DB初期化:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

使い方（基本例）
----------------

1) 設定読み込み（自動的に .env が読み込まれます）
- 必要環境変数が揃っていることを確認してください（下記参照）。

2) データベース初期化と日次 ETL 実行例
- Python スクリプト例:
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（ファイルがなければ作成）
  conn = init_schema("data/kabusys.duckdb")

  # 日次 ETL を実行（引数で target_date や id_token を指定可能）
  result = run_daily_etl(conn)
  print(result.to_dict())

- run_daily_etl は market_calendar → prices → financials → 品質チェック の順で実行し、ETLResult を返します。

3) ニュース収集の実行例
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

4) J-Quants API 直接呼び出し例
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  from kabusys.config import settings

  token = get_id_token()  # settings.jquants_refresh_token を使って取得
  records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

5) カレンダー更新ジョブ（夜間バッチ）
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved={saved}")

重要な設計的注意点
- J-Quants API は 120 req/min の制限を想定しており、モジュール内で RateLimiter による制御を行います。
- jquants_client は 401 を検知した場合、リフレッシュトークンを用いて id_token を自動更新してリトライします（1 回のみ）。
- ニュース収集は SSRF、XML Bomb、gzip-size 等の保護機構を備えています。
- DuckDB への保存はなるべく冪等に設計されており、ON CONFLICT を用いて重複更新を防ぎます。

環境変数（主要）
----------------
以下はコード内で参照される主な環境変数と説明です。

必須:
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（get_id_token に使用）

- KABU_API_PASSWORD
  - kabuステーション API 用パスワード

- SLACK_BOT_TOKEN
  - Slack 通知用ボットトークン

- SLACK_CHANNEL_ID
  - Slack チャンネル ID

オプション / デフォルトあり:
- KABUSYS_ENV
  - 環境: one of "development", "paper_trading", "live"（デフォルト: development）

- LOG_LEVEL
  - ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 1 を設定すると .env 自動ロードを無効化

- KABUSYS_API_BASE_URL
  - kabu API ベース URL を上書きする場合に利用されることがあります（デフォルト: http://localhost:18080/kabusapi）

ストレージパス（デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db

（注記）.env 自動ロードの挙動:
- プロジェクトルートは __file__ を起点に .git または pyproject.toml を上位ディレクトリで探して決定します。
- 読み込み順: OS 環境 > .env.local > .env
- .env のパースは bash 形式の export KEY=val にも対応し、クォートや inline コメントなどを考慮します。

ディレクトリ構成
----------------
以下は主要なパッケージ/ファイル配置の概要（src/kabusys 以下）:

- src/
  - kabusys/
    - __init__.py  (パッケージ定義, __version__=0.1.0)
    - config.py  (環境変数・設定管理)
    - data/
      - __init__.py
      - jquants_client.py       (J-Quants API クライアント、取得・保存関数)
      - news_collector.py      (RSS ニュース収集・保存)
      - schema.py              (DuckDB スキーマ定義 & init_schema)
      - pipeline.py            (ETL パイプライン / run_daily_etl 等)
      - calendar_management.py (市場カレンダー管理・ジョブ)
      - audit.py               (監査ログスキーマ・初期化)
      - quality.py             (データ品質チェック)
    - strategy/
      - __init__.py            (戦略関連モジュールのエントリ)
    - execution/
      - __init__.py            (発注・実行関連モジュールのエントリ)
    - monitoring/
      - __init__.py            (監視用モジュールのエントリ)

各モジュールは責務ごとに分かれており、ETL -> feature -> strategy -> execution といったワークフローを組み立てられます。

開発・拡張のヒント
------------------
- 単体テストや CI で環境変数を汚さないためには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い、必要な設定をテスト側で注入してください。
- jquants_client のネットワーク呼び出しは urllib を使用しているため、テストでは urllib のオープナーや _urlopen 等をモックして外部呼出しを防いでください（news_collector では _urlopen を差し替え可能）。
- DuckDB をメモリで使う場合は db_path に ":memory:" を渡してください（init_schema(":memory:")）。

ライセンス / 貢献
----------------
（プロジェクトに合わせてライセンス表記や CONTRIBUTING を追加してください）

---

必要に応じて README に含めるサンプル .env, 実行スクリプト、あるいは CLI の使い方（将来的な拡張）を追加できます。補足や具体的なコマンド例を追加したい場合は、利用シナリオ（ETL の定期実行方法、cron/systemd, Docker での運用等）を教えてください。