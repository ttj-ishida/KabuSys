KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けのデータ取得・ETL、特徴量生成、リサーチユーティリティ、監査ログ等を備えた自動売買プラットフォームのコアライブラリです。  
モジュール設計は「データ取得（Raw） → 整形（Processed） → 特徴量（Feature） → 発注/監査（Execution/Audit）」の階層を想定しており、DuckDB を内部データベースとして利用します。

バージョン
---------
パッケージ定義上の version: 0.1.0

主な機能
--------
- 環境変数 / 設定管理
  - .env / .env.local から自動ロード（OS 環境変数優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須設定の検査（未設定時は ValueError）。
- Data（データ取得・保存・スキーマ）
  - J-Quants API クライアント（fetch / 保存用の冪等関数付き）
  - RSS ニュース収集（SSRF対策・トラッキング削除・前処理）
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - 監査ログ（信号→発注→約定のトレーサビリティ）
- Research（特徴量・リサーチ）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - Z スコア正規化ユーティリティ
- ニュース抽出
  - RSS フィード取得・正規化・DB への冪等保存・銘柄抽出

重要モジュール（抜粋）
--------------------
- kabusys.config — 設定読み込み（settings オブジェクト）
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token (自動トークンリフレッシュ対応)
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult クラス
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=...), save_raw_news, run_news_collection
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize

セットアップ手順
---------------
1. Python 環境準備
   - Python 3.9+（コードは型ヒントに | を使っているため 3.10 推奨）
   - 仮想環境作成例:
     python -m venv .venv
     source .venv/bin/activate

2. 依存パッケージのインストール（例）
   - 必須（コードで利用されているもの）
     pip install duckdb defusedxml
   - 開発・利用にあわせて追加パッケージを導入してください（logging 等は標準ライブラリ）。
   - パッケージ配布があれば: pip install -e .

3. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（.git または pyproject.toml を基準にルート検出）。  
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: モニタリング用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）

使い方（簡易例）
----------------

1) DuckDB スキーマの初期化
- Python スクリプト例:
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  conn = init_schema(settings.duckdb_path)

  これで必要なテーブルとインデックスが作成されます。

2) 日次 ETL 実行
- run_daily_etl を使って市場カレンダー・株価・財務の差分取得と品質チェックを行います。
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

3) ニュース収集ジョブ
- RSS から収集して raw_news / news_symbols に保存:
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes
  known_codes = {"7203", "6758", ...}  # あらかじめ有効銘柄セット
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(res)

4) リサーチ（特徴量・IC 等）
- DuckDB 接続を与えてファクターを計算:
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, zscore_normalize
  recs_m = calc_momentum(conn, target_date)
  recs_v = calc_volatility(conn, target_date)
  recs_val = calc_value(conn, target_date)
  fwd = calc_forward_returns(conn, target_date)
  ic = calc_ic(recs_m, fwd, "mom_1m", "fwd_1d")
  norm = zscore_normalize(recs_m, ["mom_1m", "mom_3m", "mom_6m"])

5) J-Quants API を直接使いたい場合
- jquants_client の fetch_* 系を使用（内部でレートリミット・リトライ・トークン自動更新を実装）
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=..., date_to=...)
  saved = save_daily_quotes(conn, records)

挙動上のポイント / 注意点
-----------------------
- .env 読み込みの優先順位:
  OS 環境変数 > .env.local > .env
  .env 読み込みはプロジェクトルート（.git または pyproject.toml）を起点に自動検出されます。
- settings は実行時に環境変数を参照し、必須キーが未設定の場合は ValueError を投げます。
- J-Quants API は 120 req/min を想定した固定間隔レートリミッタを備えています。429 や一部 5xx に対してリトライ（指数バックオフ）を行います。401 はトークン自動更新処理があります。
- DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実装されています。
- ニュース収集は SSRF 対策や gzip サイズチェック等の防御策を備えています。

ディレクトリ構成（ソースの主要ファイル）
---------------------------------------
src/kabusys/
- __init__.py
- config.py                            -- 環境設定・.env 読み込み
- data/
  - __init__.py
  - jquants_client.py                   -- J-Quants API クライアント（fetch/save）
  - news_collector.py                   -- RSS 収集・前処理・保存
  - schema.py                           -- DuckDB スキーマ定義と init_schema
  - pipeline.py                         -- ETL パイプライン
  - features.py                         -- features の公開 API（zscore_normalize 再エクスポート）
  - stats.py                            -- 統計ユーティリティ（zscore_normalize 実装）
  - quality.py                          -- データ品質チェック
  - calendar_management.py              -- 市場カレンダー管理ユーティリティ
  - audit.py                            -- 監査ログスキーマ・初期化
  - etl.py                              -- ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py                  -- Momentum/Volatility/Value の実装
  - feature_exploration.py              -- forward returns, IC, summary, rank
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

（上記は現時点で実装済みの主要ファイル群の一覧です。strategy / execution / monitoring の実装は別途拡張されます）

開発メモ
--------
- テスト時やスクリプト実行時に .env の自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化は init_schema を一度呼ぶだけで OK。in-memory テストは db_path=":memory:" を利用可能です。
- jquants_client は urllib を直接使用しており、ユニットテストでは HTTP 部分や _urlopen 等をモックすると容易にテスト可能です。

ライセンス / 貢献
----------------
（このリポジトリにライセンスファイルがあればここに記載してください）

最後に
------
この README はコードベースの主要機能と使い方の概要をまとめたものです。実運用ではログ設定・エラー監視・Slack 通知や発注ロジック（risk 管理等）を適切に実装してから live 環境で利用してください。必要であればサンプルスクリプトや運用手順（Cron / Airflow / Prefect などでの実行例）も追記します。