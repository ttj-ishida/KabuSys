KabuSys
======

日本株向けのデータ基盤・リサーチ・自動売買コンポーネント群をまとめたパッケージです。  
DuckDB を中心としたデータレイヤ（Raw / Processed / Feature / Execution）、J-Quants API クライアント、RSS ベースのニュース収集、リサーチ用ファクター計算・特徴量探索、ETL パイプライン、データ品質チェック、監査ログ用スキーマ等を提供します。

バージョン
---------
パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)

特徴（主な機能）
----------------
- データ取得
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - レート制御・リトライ・401 自動リフレッシュを備えた堅牢な HTTP 層
- データ保存・スキーマ
  - DuckDB 用スキーマ定義・初期化（raw / processed / feature / execution / audit）
  - 冪等な保存（ON CONFLICT を利用した保存 API）
- ETL / パイプライン
  - 差分更新（backfill を考慮）、カレンダー先読み、品質チェックを含む日次 ETL 実行（data.pipeline.run_daily_etl）
- ニュース収集
  - RSS 取得・XML パース（defusedxml）、SSRF / サイズ制限 / URL 正規化、raw_news への冪等保存
  - テキストから銘柄コード抽出と news_symbols への紐付け
- リサーチ / 特徴量
  - momentum / volatility / value 等のファクター計算（prices_daily, raw_financials 参照のみ）
  - 将来リターン計算、IC（Spearman ρ）計算、ファクターサマリ
  - z-score 正規化ユーティリティ
- 品質チェック
  - 欠損、スパイク、重複、日付不整合などの検出（結果は QualityIssue オブジェクトで返却）
- 監査ログ（audit）
  - signal → order_request → execution まで追跡可能な監査テーブル群の初期化ユーティリティ

前提 / 必要環境
---------------
- Python 3.10+
  - 型指定に PEP 604 (|) を用いているため Python 3.10 以上が必要です。
- 必須パッケージ（最低限）
  - duckdb
  - defusedxml
- 開発 / 実運用では logging、urllib 等標準ライブラリを利用

インストール（例）
-----------------
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb defusedxml

3. パッケージ（ローカル開発）としてインストール
   - pip install -e .

環境変数 / 設定
----------------
kabusys は環境変数（あるいは .env / .env.local）から設定を読み込みます（自動ロード）：src/kabusys/config.py

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）

任意の設定（デフォルトあり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 値を 1 にすると .env 自動ロードを無効化
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

例（.env）
- JQUANTS_REFRESH_TOKEN=xxxx
- KABU_API_PASSWORD=yyyy
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C0123456
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

セットアップ手順（簡易チュートリアル）
-----------------
1. DuckDB スキーマを初期化する
   - Python REPL またはスクリプトで:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     # 監査ログを別 DB にしたい場合:
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

   - init_schema はディレクトリを自動作成します。":memory:" を指定するとインメモリ DB。

2. 日次 ETL を実行する（例: 今日分）
   - from kabusys.data.pipeline import run_daily_etl
     from kabusys.data.schema import get_connection
     from datetime import date
     conn = get_connection("data/kabusys.duckdb")
     result = run_daily_etl(conn, target_date=date.today())
     print(result.to_dict())

3. ニュース収集を走らせる
   - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
     conn = get_connection("data/kabusys.duckdb")
     known_codes = {"7203", "6758", ...}  # 自前で保有する有効銘柄一覧
     res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)

使い方（主な API 例）
-------------------

- J-Quants データ取得 & 保存
  - fetch + save の流れは jquants_client にまとまっています。
    from kabusys.data import jquants_client as jq
    from kabusys.data.schema import get_connection
    conn = get_connection("data/kabusys.duckdb")
    records = jq.fetch_daily_quotes()  # id_token は環境変数から自動取得
    jq.save_daily_quotes(conn, records)

- ETL（差分更新を含む）
  - 先述の run_daily_etl を使います。品質チェック / スパイク閾値 / backfill 日数等は引数変更可能。

- リサーチ（ファクター計算）
  - calc_momentum, calc_volatility, calc_value（src/kabusys/research/factor_research.py）
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    conn = get_connection("data/kabusys.duckdb")
    res_mom = calc_momentum(conn, target_date)
    res_vol = calc_volatility(conn, target_date)
    res_val = calc_value(conn, target_date)

  - 将来リターン・IC・summary
    from kabusys.research import calc_forward_returns, calc_ic, factor_summary, rank
    fwd = calc_forward_returns(conn, target_date)
    ic = calc_ic(factor_records, fwd, "mom_1m", "fwd_1d")
    summary = factor_summary(factor_records, ["mom_1m", "ma200_dev"])

  - z-score 正規化
    from kabusys.data.stats import zscore_normalize
    normalized = zscore_normalize(records, ["mom_1m", "mom_3m"])

- ニュース収集（RSS）
  - fetch_rss / save_raw_news / run_news_collection を利用。
    from kabusys.data.news_collector import fetch_rss, save_raw_news
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
    saved_ids = save_raw_news(conn, articles)

注意点（セキュリティ / 運用）
-------------------------
- J-Quants API のレート制限（120 req/min）に従うため内部で固定間隔スロットリングを実装しています。
- ニュース収集では SSRF を防ぐためリダイレクト先検査・ホストのプライベートアドレス検査・レスポンスサイズ制限等を実装しています（defusedxml を利用）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト時など自動ロードを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の ON CONFLICT / RETURNING を多用しているため、DuckDB のバージョン互換性に注意してください（推奨は最新の安定版）。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント + 保存ロジック
  - news_collector.py            — RSS ニュース収集・保存・銘柄抽出
  - schema.py                    — DuckDB スキーマ定義・初期化
  - stats.py                     — 統計ユーティリティ（zscore_normalize）
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - features.py                  — 特徴量公開インターフェース
  - calendar_management.py       — market_calendar 関連ユーティリティ
  - quality.py                   — データ品質チェック
  - audit.py                     — 監査ログスキーマ初期化
  - etl.py                       — ETL 公開型（ETLResult の再エクスポート）
- research/
  - __init__.py
  - feature_exploration.py       — 将来リターン計算 / IC / summary / rank
  - factor_research.py           — momentum/volatility/value 計算
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

開発上のメモ
-------------
- ほとんどのリサーチ機能は DuckDB の prices_daily / raw_financials テーブルのみ参照します。実運用での発注 API には直接アクセスしない設計です（安全対策）。
- テストやスクリプト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD をセットして環境を明示的に制御すると便利です。
- 各モジュールは標準ライブラリで多くを実装しており、外部依存は最小化されています（ただし DuckDB と defusedxml は必須）。

サンプル（最短起動例）
--------------------
1) 簡易セットアップ
   pip install duckdb defusedxml
   export JQUANTS_REFRESH_TOKEN=... SLACK_BOT_TOKEN=... SLACK_CHANNEL_ID=...
   python -c "from kabusys.data import schema; schema.init_schema('data/kabusys.duckdb')"

2) 日次 ETL 実行
   python -c "from kabusys.data.schema import get_connection; from kabusys.data.pipeline import run_daily_etl; conn=get_connection('data/kabusys.duckdb'); print(run_daily_etl(conn).to_dict())"

問い合わせ / 貢献
-----------------
- 本 README はコードベースのみから生成されています。実行時の環境変数や外部 API の利用には注意し、機密情報（トークン等）は漏洩しないよう管理してください。
- バグ報告や改善提案はリポジトリの Issue へお願いします。

以上。