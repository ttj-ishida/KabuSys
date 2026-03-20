KabuSys — 日本株自動売買基盤
======================

概要
----
KabuSys は日本株を対象としたデータ基盤＋戦略パイプラインのプロトタイプ実装です。  
主な目的は以下のとおりです。

- J-Quants API から株価・財務・市場カレンダー等を取得して DuckDB に保存する（ETL）
- 研究用ファクター（モメンタム・バリュー・ボラティリティ等）を計算し特徴量テーブルを構築する
- 正規化済み特徴量と AI スコアを統合して売買シグナルを生成する
- RSS からニュースを収集し記事と銘柄の紐付けを行う
- 発注・監査・実行のためのスキーマを備え、将来的な execution 層との結合を想定

本リポジトリは core ロジック（ETL, factor 計算, feature エンジニアリング, signal 生成, news collection, schema 定義など）を含みます。発注実行の broker 接続は別途実装する想定です。

主な機能
--------
- data/jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動更新・DuckDB への冪等保存）
- data/pipeline: 日次 ETL（差分取得、バックフィル、品質チェック呼び出しの統合）
- data/schema: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- data/news_collector: RSS フィード収集と前処理、raw_news / news_symbols への冪等保存（SSRF・gzip・XML攻撃対策あり）
- data/calendar_management: JPX カレンダー管理（営業日判定、next/prev_trading_day 等）
- data/stats, data/features: Zスコア正規化などの統計ユーティリティ
- research/factor_research: モメンタム・バリュー・ボラティリティ等のファクター計算
- research/feature_exploration: 将来リターン計算、IC（Spearman）やファクター統計サマリ
- strategy/feature_engineering: 生ファクターの正規化・フィルタ・features への保存処理
- strategy/signal_generator: features と ai_scores を統合して final_score を算出し BUY/SELL シグナルを生成
- audit（データベース内に監査テーブルを定義）: 発注から約定までトレース可能な監査ログスキーマ（schema.py / audit.py）

セットアップ
----------
前提:
- Python 3.10+（型注釈で Union 演算子等を使っている箇所があるため推奨）
- DuckDB（Python パッケージとしてインストール）
- ネットワークアクセス（J-Quants API、RSS）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   最低限必要なパッケージ:
   - duckdb
   - defusedxml

   例:
   - pip install duckdb defusedxml

   （プロジェクト化されていれば setup.py / pyproject.toml 経由で他の依存も管理してください）

3. 環境変数 / .env の準備
   プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただしテスト時等に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。必要な主要環境変数例:

   - JQUANTS_REFRESH_TOKEN=xxxxx
   - KABU_API_PASSWORD=xxxxx
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (デフォルト)
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=CXXXXXX
   - DUCKDB_PATH=data/kabusys.duckdb  (デフォルト)
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development | paper_trading | live
   - LOG_LEVEL=INFO

   .env の書式は bash の export やクォート、コメント部分に配慮した独自パーサーで扱えます（config.py を参照）。

4. データベース初期化
   DuckDB のスキーマを作成します。以下は Python での例:

   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")

   この関数は親ディレクトリを自動作成し、DDL を実行してテーブルを作成します（冪等）。

使い方（簡単な実行フロー例）
--------------------------

1) DuckDB の初期化（1 回目）
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL を実行（市場カレンダー・株価・財務の差分取得）
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date
   result = run_daily_etl(conn, target_date=date.today())
   # ETLResult オブジェクト: フェッチ件数・保存件数・品質問題・エラーメッセージなどを含む

3) 特徴量の計算（feature テーブルへ保存）
   from kabusys.strategy import build_features
   from datetime import date
   n = build_features(conn, target_date=date.today())
   # 戻り値は upsert された銘柄数

4) シグナル生成（signals テーブルへ保存）
   from kabusys.strategy import generate_signals
   total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
   # BUY + SELL 合計件数を返す

5) ニュース収集ジョブ（RSS → raw_news / news_symbols）
   from kabusys.data.news_collector import run_news_collection
   known_codes = {"7203","6758", ...}  # 銘柄コードセット（抽出用）
   results = run_news_collection(conn, sources=None, known_codes=known_codes)
   # sources を None にすると DEFAULT_RSS_SOURCES を使用。戻り値はソース毎の新規保存件数

主要 API の説明（抜粋）
--------------------
- init_schema(db_path) -> DuckDB 接続
  全テーブルを作成します。":memory:" を指定してメモリ DB として起動可能。

- run_daily_etl(conn, target_date, id_token=None, run_quality_checks=True, ...)
  日次 ETL の統合エントリポイント。ETLResult を返します。

- build_features(conn, target_date)
  research モジュールから計算したファクターを正規化・フィルタリングして features テーブルへ UPSERT します。

- generate_signals(conn, target_date, threshold=0.6, weights=None)
  features と ai_scores を使って最終スコアを算出し、BUY/SELL シグナルを signals テーブルへ書き込みます。戻り値は書き込み件数。

- run_news_collection(conn, sources=None, known_codes=None)
  RSS を収集して raw_news に保存し、既知銘柄との紐付けを行います。

設定（config）
--------------
- 環境変数は kabusys.config.Settings 経由で参照します（settings オブジェクト）。必須変数は _require() により未設定時に ValueError を投げます。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して .env → .env.local を読み込みます。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- ログレベルは LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）で制御します。

DB スキーマ / テーブル（主なもの）
---------------------------------
（詳しくは data/schema.py を参照）

- raw_prices, raw_financials, raw_news, raw_executions
- prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- features, ai_scores
- signals, signal_queue, orders, trades, positions, portfolio_targets, portfolio_performance
- audit 用テーブル: signal_events, order_requests, executions など（監査/トレーサビリティ）

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定読み込み
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント & DuckDB 保存ユーティリティ
  - news_collector.py            — RSS 取得・前処理・保存
  - pipeline.py                  — ETL パイプライン（run_daily_etl など）
  - schema.py                    — DuckDB スキーマ定義 & init_schema
  - stats.py                     — zscore_normalize 等の統計ユーティリティ
  - features.py                  — features インターフェース（再エクスポート）
  - calendar_management.py       — 市場カレンダー管理ユーティリティ
  - audit.py                     — 監査ログ用 DDL と初期化ロジック
- research/
  - __init__.py
  - factor_research.py           — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py       — forward returns / IC / summary utilities
- strategy/
  - __init__.py
  - feature_engineering.py       — build_features
  - signal_generator.py          — generate_signals
- execution/                      — 発注実装を想定したパッケージ（現状空リリース）
- monitoring/                     — 監視・メトリクス系（将来追加想定）

注意事項 / 開発上のポイント
-------------------------
- DuckDB を用いた設計上、INSERT は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実装されています。
- J-Quants API のレート制御（120 req/min）は jquants_client の RateLimiter が担保します。大量ページング時は注意してください。
- NewsCollector は SSRF 対策・XML パーサー硬化（defusedxml）・gzip サイズ制限など複数の安全対策を組み込んでいます。RSS ソースはデフォルトで Yahoo Finance を含みますが必要に応じて sources を差し替えてください。
- Strategy 層はルックアヘッドバイアス回避のため、target_date 時点までのデータのみを参照する設計です。
- 本リポジトリは発注ブローカーや実口座接続の実装を含みません。実口座で動かす際は KABU API 等との安全な連携・リスク管理を別途実装してください。

ライセンス / 貢献
-----------------
本リポジトリのライセンスは（ここにライセンス情報を記載してください）。バグ報告・機能提案は Issues を利用してください。

補足（サンプルスクリプト）
-------------------------
簡単なワンライン実行イメージ（スクリプト）:

#!/usr/bin/env python3
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.strategy import build_features, generate_signals

conn = init_schema("data/kabusys.duckdb")
etl_res = run_daily_etl(conn, target_date=date.today())
build_count = build_features(conn, target_date=date.today())
signals = generate_signals(conn, target_date=date.today())
print("ETL:", etl_res.to_dict())
print("features:", build_count, "signals:", signals)

以上。README に書ききれない詳細は各モジュール（data/*.py, research/*.py, strategy/*.py）内の docstring を参照してください。必要であれば README の改善・使用例の追加を行います。