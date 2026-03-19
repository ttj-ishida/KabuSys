KabuSys
======

日本株向けの自動売買・データ基盤ライブラリ。  
DuckDB をデータ層として用い、J-Quants API から市場データ・財務データ・カレンダーを取得して ETL を実行し、特徴量計算・品質チェック・ニュース収集などを行うためのモジュール群を提供します。

主な特徴
--------
- データ取得 (J-Quants)／保存（DuckDB）を冪等（idempotent）に実行
- 日次 ETL パイプライン（市場カレンダー → 株価 → 財務 → 品質チェック）
- 特徴量計算（モメンタム、ボラティリティ、バリュー等）および Z スコア正規化
- ニュース収集（RSS）と記事 → 銘柄紐付け（SSRF 対策・トラッキング除去）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal / order_request / executions）用のスキーマ初期化機能
- レートリミット / 再試行 / トークン自動リフレッシュ等を備えた J-Quants クライアント

機能一覧
--------
- 環境設定:
  - kabusys.config.Settings: 必須/任意の環境変数を管理。自動でプロジェクトルートの .env / .env.local を読み込み（無効化可）。
- データ取得・保存:
  - data.jquants_client: fetch_* / save_* (daily_quotes, financial_statements, market_calendar)
  - data.pipeline: 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - data.schema: DuckDB スキーマ生成（init_schema / get_connection）
  - data.audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- ニュース:
  - data.news_collector: RSS 取得（fetch_rss）、前処理、保存（save_raw_news / save_news_symbols）、記事から銘柄抽出
- 品質管理:
  - data.quality: 欠損・重複・スパイク・日付不整合チェック（run_all_checks 等）
- 特徴量・リサーチ:
  - research.factor_research: calc_momentum / calc_volatility / calc_value
  - research.feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats: zscore_normalize（再エクスポートあり）
- その他:
  - calendar_management: 営業日判定、next/prev/get_trading_days、calendar_update_job

セットアップ手順
----------------

1. リポジトリをクローン（例）
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - またはプロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。

4. 環境変数の設定
   - プロジェクトルートに .env（および必要なら .env.local）を作成してください。
   - 例（.env.example を参考に）:

     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   - 自動で .env を読み込む機能を無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベーススキーマ初期化（DuckDB）
   - Python REPL / スクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - 監査ログ専用に分けて初期化する場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

使い方（例）
-----------

- 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")  # まだ作成していない場合
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 個別 ETL（株価のみ）
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  conn = get_connection("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())

- カレンダーの夜間更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)

- ニュース収集（RSS）を走らせる
  from kabusys.data.news_collector import run_news_collection
  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 有効銘柄コードの集合（省略可）
  results = run_news_collection(conn, sources=None, known_codes=known_codes)
  # results は {source_name: new_count} の辞書

- J-Quants の生データフェッチ（テストや個別利用）
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  fin = fetch_financial_statements(date_from=date(2023,1,1), date_to=date(2024,1,1))

- 特徴量計算（研究用途）
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  conn = get_connection("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date.today())
  volatility = calc_volatility(conn, target_date=date.today())
  value = calc_value(conn, target_date=date.today())

  forward = calc_forward_returns(conn, target_date=date.today(), horizons=[1,5,21])
  ic = calc_ic(factor_records=momentum, forward_records=forward, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(momentum, ["mom_1m", "mom_3m", "ma200_dev"])

- Z スコア正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m"])

設定（環境変数）
----------------
主要な必須環境変数（Settings クラス参照）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション関連パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）

その他（デフォルト値あり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 用監視 DB（デフォルト: data/monitoring.db）

ディレクトリ構成（主要ファイル）
----------------------------
- src/kabusys/
  - __init__.py
  - config.py                     - 環境変数/設定読み込みロジック
  - data/
    - __init__.py
    - jquants_client.py            - J-Quants API クライアント（fetch/save）
    - news_collector.py            - RSS 収集・保存・銘柄抽出
    - schema.py                    - DuckDB スキーマ定義 / init_schema
    - pipeline.py                  - ETL パイプライン（run_daily_etl 等）
    - quality.py                   - データ品質チェック
    - stats.py                     - zscore_normalize 等の統計ユーティリティ
    - features.py                  - features の公開インターフェース
    - calendar_management.py       - market_calendar 管理・ユーティリティ
    - audit.py                     - 監査ログ用スキーマ初期化
    - etl.py                       - ETLResult の公開インターフェース
  - research/
    - __init__.py
    - factor_research.py           - momentum/volatility/value 等
    - feature_exploration.py       - forward returns / IC / summary / rank
  - strategy/                       - （戦略関連のエントリポイント）
  - execution/                      - （発注 / ブローカー連携）
  - monitoring/                     - （モニタリング関連）

設計上の注意点
-------------
- DuckDB の INSERT は ON CONFLICT DO UPDATE / DO NOTHING を使い冪等性を担保します。
- J-Quants API はレート制限（120 req/min）に従い、内部で間引き・再試行を行います。
- research モジュールは本番の発注 API にアクセスせず、DuckDB に格納された prices_daily / raw_financials のみを参照する設計です（look-ahead bias を避ける）。
- news_collector は SSRF 対策・XML の安全パース（defusedxml）・レスポンスサイズ制限を実装しています。

貢献 / 開発
-----------
- 新しいテーブルを追加する場合は data/schema.py に DDL を追加し、init_schema を使って初期化してください。
- ユニットテストは DuckDB の :memory: を利用して実行できます。
- 自動環境変数読み込みはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

ライセンス
---------
- ライセンスはリポジトリの LICENSE ファイルを参照してください（ここでは明示していません）。

補足
----
- README の内容は現コードベース（src/kabusys 以下）に基づいてまとめています。各関数の詳細な挙動・引数仕様は該当モジュールの docstring を参照してください。必要であればサンプルスクリプトや CLI ラッパーの追加例も作成できます。