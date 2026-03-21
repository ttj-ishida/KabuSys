KabuSys — 日本株自動売買基盤（README）
=================================

概要
----
KabuSys は日本株のデータ収集・加工・特徴量生成・シグナル生成・監査を念頭に設計された自動売買プラットフォームのライブラリ群です。  
主に以下レイヤーを備えます。

- Data Layer: J-Quants API からのデータ取得（OHLCV, 財務, 市場カレンダー）、RSS ニュース収集、DuckDB での永続化
- Processed / Feature Layer: prices_daily / features / ai_scores / signals 等の整形・特徴量生成
- Strategy Layer: ファクタ処理（モメンタム/ボラティリティ/バリュー）とシグナル生成
- Execution / Audit: 発注・約定・ポジション管理・監査ログ（スキーマ定義）

バージョン
----------
パッケージバージョンは src/kabusys/__init__.py の __version__ で管理されています（例: 0.1.0）。

主な機能一覧
--------------
- J-Quants API クライアント（レート制限・リトライ・トークン自動更新を実装）
- DuckDB スキーマ初期化（init_schema）
- ETL パイプライン（差分取得、バックフィル、品質チェックを伴う日次ETL）
- ファクター計算（モメンタム, ボラティリティ, バリュー）
- 特徴量構築（Zスコア正規化、ユニバースフィルタ、日次UPSERT）
- シグナル生成（final_score 計算、Bear 判定、BUY/SELL 生成、冪等保存）
- RSS ニュース収集（SSRF 対策・トラッキング除去・記事ID生成・銘柄抽出）
- マーケットカレンダー管理（営業日判定、next/prev trading day 等）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）

前提条件
--------
- Python 3.10 以上（型注釈や union 演算子（|）を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

インストール
------------
1. リポジトリをクローン／配置し、開発環境にインストール（例: 仮想環境推奨）
   - pip install -e .（セットアップ用の setup.cfg/pyproject がある想定）
2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - 追加でプロジェクト固有の依存があれば requirements.txt / pyproject を参照

環境変数（必須／推奨）
---------------------
パッケージは .env / .env.local / OS 環境変数から設定を読み込みます（priority: OS > .env.local > .env）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

主な環境変数（settings で参照されるもの）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabu ステーション API パスワード（execution 層用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite (monitoring 等) パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

セットアップ手順（簡易）
---------------------
1. 環境変数を設定 or プロジェクトルートに .env を作成
   - .env.example を参照して必要なキーを設定してください（リポジトリに .env.example がある想定）。
2. DuckDB スキーマを初期化
   - Python REPL やスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - これにより必要な全テーブル／インデックスが作成されます。
3. 必要なら SQLite DB 等も用意

使い方（主要ユースケース）
------------------------

- 日次 ETL を実行して市場データを取り込む
  - 例（Python スクリプト）:
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl

    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

  - run_daily_etl は市場カレンダー・株価・財務データを差分取得して DuckDB に保存し、品質チェックを実行します。

- 特徴量を構築（features テーブルへの UPSERT）
  - 例:
    from datetime import date
    from kabusys.data.schema import get_connection
    from kabusys.strategy import build_features

    conn = get_connection("data/kabusys.duckdb")
    n = build_features(conn, target_date=date(2024, 1, 31))
    print(f"features upserted: {n}")

- シグナルを生成して signals テーブルへ保存
  - 例:
    from datetime import date
    from kabusys.data.schema import get_connection
    from kabusys.strategy import generate_signals

    conn = get_connection("data/kabusys.duckdb")
    total = generate_signals(conn, target_date=date(2024, 1, 31))
    print(f"signals created: {total}")

- RSS ニュース収集ジョブの実行
  - 例:
    from kabusys.data.schema import get_connection
    from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

    conn = get_connection("data/kabusys.duckdb")
    known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
    results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
    print(results)

- カレンダー更新バッチ
  - 例:
    from kabusys.data.calendar_management import calendar_update_job
    from kabusys.data.schema import get_connection

    conn = get_connection("data/kabusys.duckdb")
    saved = calendar_update_job(conn)
    print(f"calendar saved: {saved}")

設定オブジェクトの利用
---------------------
kabusys.config.settings オブジェクトから環境設定を取得できます。例:
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)

注意点 / 設計上の留意事項
------------------------
- J-Quants クライアントは内部で固定間隔のレートリミッタ、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュを実装しています。
- ETL / feature / signal 等は「ルックアヘッドバイアス」を避ける設計で、target_date 時点のデータのみを使用するようになっています。
- DB 操作は可能な限り冪等（ON CONFLICT など）かトランザクションで原子性を確保しています。
- RSS 収集は SSRF/zip bomb 等に対する防御（スキームチェック、プライベートIPチェック、受信サイズ上限、defusedxml）を組み込んでいます。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主なモジュール構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - (その他: quality.py 等が想定される)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  (モジュール群は存在する想定)

（実際のファイル一覧はリポジトリの src/kabusys 配下を参照してください。）

よくある初期化手順（まとめ）
--------------------------
1. .env を作成して環境変数を設定（JQUANTS_REFRESH_TOKEN 等）
2. Python 仮想環境を作成・有効化
3. pip install -e .
4. 必要パッケージを pip install duckdb defusedxml
5. 初期スキーマ作成:
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
6. run_daily_etl / build_features / generate_signals 等を順に実行

サポート / 拡張
----------------
- 新しい RSS ソース追加は data.news_collector.DEFAULT_RSS_SOURCES を拡張してください。
- strategy の重みや閾値は generate_signals の引数で上書き可能です（weights / threshold）。
- execution 層（kabu API 連携）や監視（Slack 通知など）は別モジュールでの実装を想定しています（設定は config.py を参照）。

ライセンス
---------
本リポジトリ内にライセンスファイルがある場合はそちらを参照してください。

最後に
------
この README はコードベースの主要機能と使い方の概要をまとめたものです。詳細な仕様（StrategyModel.md、DataPlatform.md 等）はリポジトリ内ドキュメントを参照してください。必要であれば、よく使う CLI スクリプト例や cron / Airflow 連携例の追加ドキュメントも作成できます。