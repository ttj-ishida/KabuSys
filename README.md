KabuSys — 日本株自動売買基盤（README）
=================================

概要
----
KabuSys は日本株向けのデータ基盤・特徴量生成・リサーチ・監査・発注基盤を想定した Python パッケージ群です。  
主に以下の機能を備え、DuckDB を中心にデータを永続化・処理します。

- J-Quants API からの株価・財務・市場カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- RSS ベースのニュース収集と記事→銘柄紐付け
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ファクター計算（モメンタム、ボラティリティ、バリュー）と特徴量探索（将来リターン、IC、統計サマリー）
- 監査ログ（signal → order → execution のトレース）
- 市場カレンダー管理（営業日判定・next/prev_trading_day 等）

設計上のポイント
- DuckDB を利用したローカル（またはファイル）DB を前提とする
- J-Quants API 呼び出しはレート制御と堅牢なリトライ/認証リフレッシュを備える
- ETL / DB 保存処理は冪等（ON CONFLICT を用いた上書き）を意識
- 研究（research）モジュールは外部ライブラリに依存しない実装を目指す（標準ライブラリ中心）

主な機能一覧
--------------
- 環境設定:
  - 自動 .env ロード（プロジェクトルート検出） / KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化
  - settings オブジェクトで環境変数を型付きに取得（JQUANTS_REFRESH_TOKEN 等）
- データ取得・永続化:
  - data.jquants_client: fetch_* / save_*（daily_quotes, financials, market_calendar）
  - data.news_collector: RSS 取得 -> 前処理 -> raw_news 保存 -> news_symbols 紐付け
  - data.schema: DuckDB スキーマ定義 + init_schema / get_connection
  - data.pipeline: 差分ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - data.calendar_management: 営業日判定 / calendar_update_job
- 品質管理:
  - data.quality: 欠損・重複・スパイク・日付不整合チェック / run_all_checks
- 監査:
  - data.audit: 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
- 研究/特徴量:
  - research.factor_research: calc_momentum, calc_volatility, calc_value
  - research.feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats: zscore_normalize（再エクスポート：data.features）
- ETL 管理:
  - data.pipeline.ETLResult により ETL の結果を集約して返却

前提 / 必要環境
---------------
- Python >= 3.10（型ヒントと union 型（X | None）を使用）
- 必要パッケージ（代表例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS フィード）

セットアップ手順
----------------

1. リポジトリをクローン（既にある場合はスキップ）
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject.toml / requirements.txt がある場合はそれに従ってください）
   - 開発中は -e インストールも可: pip install -e .

4. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くと自動ロードされます（config モジュールにより .git または pyproject.toml を基準に探索）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能を使う場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を行う場合
   - 任意:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB など（デフォルト: data/monitoring.db）
   - 自動ロードを抑止したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（簡単な例）
-----------------

1) DuckDB スキーマ初期化
- Python から:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL を実行する（J-Quants から差分取得して保存）
- from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

3) 個別 ETL ジョブ（株価のみ）
- from kabusys.data.pipeline import run_prices_etl, get_last_price_date
  fetched, saved = run_prices_etl(conn, target_date=date.today())

4) ニュース収集ジョブ
- from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 有効銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)

5) ファクター計算 / 研究
- モメンタム等の計算:
  - from kabusys.research.factor_research import calc_momentum
    rows = calc_momentum(conn, target_date)
- 将来リターンと IC:
  - from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
    fwd = calc_forward_returns(conn, target_date)
    factor = ...  # calc_momentum の戻り値等
    ic = calc_ic(factor, fwd, factor_col="mom_1m", return_col="fwd_1d")

6) データ品質チェック
- from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues: print(i)

7) 監査ログ初期化（別DBを使う場合）
- from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

重要な API / 関数一覧（抜粋）
---------------------------
- kabusys.config.settings: 環境変数アクセスヘルパー
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.jquants_client:
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - save_daily_quotes(conn, records)
  - fetch_financial_statements(...)
  - save_financial_statements(conn, records)
  - fetch_market_calendar(...)
  - save_market_calendar(conn, records)
- kabusys.data.pipeline:
  - run_daily_etl(...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
- kabusys.data.news_collector:
  - fetch_rss(url, source)
  - save_raw_news(conn, articles)
  - run_news_collection(...)
- kabusys.data.quality.run_all_checks(...)
- kabusys.research.factor_research: calc_momentum, calc_volatility, calc_value
- kabusys.research.feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats.zscore_normalize (data.features 経由でも可)
- kabusys.data.audit.init_audit_schema / init_audit_db

運用上の注意 / 実装ノート
-----------------------
- J-Quants API のレート制限（120 req/min）を踏まえた実装で、モジュール内に _RateLimiter があるため基本的に過剰な呼び出しは防げますが、大規模バッチを独自に並列化する際は注意してください。
- jquants_client は 401 発生時に自動でリフレッシュを試みます（1 回）。再試行ロジックや指数バックオフを備えています。
- news_collector は SSRF や XML Bomb、gzip 解凍後のサイズチェック等の安全対策を実装していますが、外部フィードの扱いは引き続き注意が必要です。
- DuckDB の ON CONFLICT（冪等保存）を多用しており、ETL は再実行可能な設計です。
- audit モジュールは UTC タイムスタンプとトランザクション管理を重視しています。
- research モジュールの関数は外部 API にアクセスしない（prices_daily / raw_financials のみ参照）ため、オフラインでの検証が容易です。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                       # 環境変数 / settings
- data/
  - __init__.py
  - jquants_client.py              # J-Quants API クライアント + 保存ロジック
  - news_collector.py             # RSS 収集・前処理・保存
  - schema.py                     # DuckDB スキーマ定義・init_schema
  - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
  - etl.py                        # ETLResult 再エクスポート
  - quality.py                    # 品質チェック
  - features.py / stats.py        # 統計ユーティリティ（zscore_normalize）
  - calendar_management.py        # 市場カレンダー管理
  - audit.py                      # 監査ログスキーマ初期化
- research/
  - __init__.py
  - feature_exploration.py        # 将来リターン / IC / summary
  - factor_research.py            # momentum/value/volatility 計算
- strategy/
  - __init__.py                   # （戦略実装は別途拡張）
- execution/
  - __init__.py                   # （発注ロジックは別途実装）
- monitoring/
  - __init__.py                   # （監視・アラート用）

ライセンス / 貢献
----------------
本 README ではライセンスやコントリビューション手順は記載していません。リポジトリに LICENSE や CONTRIBUTING.md がある場合はそちらに従ってください。

最後に
-----
この README はコードベース（主要モジュール）をもとに作成しています。実運用前に以下を確認してください：

- 実際の .env（または環境変数）を正しく設定しているか
- DuckDB のバックアップ・スナップショット運用
- J-Quants の利用規約・レート制約の順守
- 発注機能を有効にする場合は paper_trading モード等で十分に検証を行うこと

必要であれば、README に含めるサンプル .env.example、より詳細な CLI / systemd / Airflow 連携例、テスト方法（ユニットテストの実行手順）なども追加できます。どの情報を追加したいか教えてください。