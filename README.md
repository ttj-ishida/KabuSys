KabuSys
======

日本株向けの自動売買・データ基盤ライブラリです。  
DuckDB を内部データベースに使い、J-Quants API から市場データ・財務データ・カレンダーを取得して ETL → 特徴量生成 → シグナル生成 → 発注のワークフローをサポートします。ライブラリは研究（research）用途と本番（execution）用途の両方を想定し、安全性・冪等性・トレーサビリティ（監査ログ）を重視して設計されています。

主な特徴
--------
- データ取得（J-Quants）／差分ETL（duckdb）をサポート（差分取得・バックフィル）
- DuckDB スキーマ定義と初期化（init_schema）
- ファクター計算（Momentum / Volatility / Value 等：research/factor_research）
- 特徴量正規化（Zスコア）と features テーブルへの保存（strategy/feature_engineering）
- シグナル生成（final_score の計算、Buy / Sell 判定、signals テーブル書込）
- ニュース収集（RSS → raw_news、銘柄抽出・紐付け）
- 市場カレンダー管理（JPX カレンダー、営業日判定ヘルパー）
- API クライアント（J-Quants）にレート制御・リトライ・トークン自動更新等を実装
- 安全対策（SSRF ブロック、XML 脆弱性対策、レスポンスサイズ制限 等）
- 監査ログ（signal_events / order_requests / executions）用DDL を用意

要件
-----
- Python 3.10+
- duckdb
- defusedxml
（その他、環境により urllib 標準ライブラリ・datetime 等を使用）

インストール
------------
仮想環境を作成して依存パッケージをインストールしてください（例）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

（パッケージ化されている場合は pip install . などでインストールしてください）

環境変数（設定）
----------------
パッケージは .env/.env.local または環境変数から設定を自動ロードします。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : Kabusation API（発注連携）パスワード
- SLACK_BOT_TOKEN       : Slack 通知用ボットトークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

その他オプション:
- KABUSYS_ENV (development | paper_trading | live) デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) デフォルト: INFO
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 sqlite パス（デフォルト data/monitoring.db）

例 (.env)
---------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABUS_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

セットアップ手順（最小例）
------------------------
1. DuckDB スキーマを初期化

Python REPL もしくはスクリプトで:
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# これで必要なテーブルがすべて作成されます

2. 日次 ETL 実行（J-Quants から差分取得 → 保存 → 品質チェック）
from datetime import date
from kabusys.data.pipeline import run_daily_etl, get_last_price_date
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

3. 特徴量の構築
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")

4. シグナル生成
from datetime import date
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")

5. ニュース収集（RSS）→ raw_news 保存
from kabusys.data.news_collector import run_news_collection
conn = duckdb.connect("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使う有効な銘柄コードセット（例: all コードセット）
res = run_news_collection(conn, sources=None, known_codes=None)
print(res)

6. カレンダー夜間更新ジョブ
from kabusys.data.calendar_management import calendar_update_job
conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")

利用方法（API 参照）
------------------
主な公開 API（モジュール / 関数）
- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.news_collector
  - fetch_rss / save_raw_news / run_news_collection
- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job
- kabusys.research
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)

注意・設計上のポイント
--------------------
- ETL・保存処理は可能な限り冪等（ON CONFLICT / INSERT ... DO UPDATE）で実装されています。
- J-Quants API はレート制限（120 req/min）とリトライ、401 のトークン自動更新に対応しています。
- ニュース収集は SSRF 対策、gzip サイズチェック、XML 脆弱性対策を組み込んでいます。
- Strategy 層はルックアヘッドバイアスを防ぐため、target_date 時点のデータのみ参照する設計です。
- KABUSYS_ENV によって is_live/is_paper/is_dev の挙動判定を行います（本番モードはより慎重な処理を行う想定）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                         # .env / 環境変数管理
- data/
  - __init__.py
  - jquants_client.py               # J-Quants API クライアント
  - news_collector.py               # RSS ニュース収集・保存
  - schema.py                       # DuckDB スキーマ定義 / init_schema
  - stats.py                        # zscore_normalize 等の共通統計関数
  - pipeline.py                     # ETL パイプライン（run_daily_etl 等）
  - features.py                     # data 層公開ユーティリティ
  - calendar_management.py          # カレンダー管理・判定機能
  - audit.py                        # 監査ログ用 DDL
- research/
  - __init__.py
  - factor_research.py              # Momentum/Value/Volatility 計算
  - feature_exploration.py          # forward returns, IC, summary, rank
- strategy/
  - __init__.py
  - feature_engineering.py          # features テーブル構築（Z正規化・フィルタ）
  - signal_generator.py             # final_score 計算・BUY/SELL 生成
- execution/                         # 発注連携層（空モジュール／拡張用）
- monitoring/                        # 監視用ユーティリティ（DB/Slack通知 等想定）

開発に関して
-------------
- 自動環境変数ロードはプロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を読み込みます。テストや CI で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB の初期化は init_schema を使用してください（ファイル DB の親ディレクトリを自動作成します）。
- 監査ログ（audit）DDL はトレーサビリティ要件を満たすよう設計されています。実際の発注ブリッジを実装する際は order_requests.order_request_id を冪等キーとして利用してください。

ライセンス / コントリビュート
-----------------------------
（ここにはプロジェクトのライセンスや貢献方法を記載してください）

最終メモ
-------
この README はコードベースの主要モジュールと典型的な操作をまとめたものです。詳細な API パラメータや追加のユーティリティは各モジュールの docstring・関数コメントを参照してください。質問や実運用に関する相談があれば教えてください。