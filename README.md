KabuSys

日本株向けの自動売買 / データパイプライン / バックテスト基盤ライブラリのリポジトリです。  
この README はコードベース（src/kabusys 以下）をもとに機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

概要
----
KabuSys は以下を提供する Python パッケージです。
- J-Quants API と RSS などからのデータ収集（株価・財務・マーケットカレンダー・ニュース）
- DuckDB を用いたデータスキーマと ETL パイプライン（冪等保存・品質チェック）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- 特徴量（features）作成とシグナル生成（final_score に基づく BUY/SELL）
- バックテストフレームワーク（シミュレータ・トレード記録・メトリクス）
- ニュース収集・記事と銘柄の紐付け（SSRF 対策、XML Bomb 対策）

主な設計方針:
- ルックアヘッドバイアス防止：target_date 時点のデータのみ使用
- 冪等性：DB 書き込みは ON CONFLICT / トランザクションで安全に
- ネットワーク耐性：API リトライ、レートリミット、SSRF/圧縮攻撃対策
- テストしやすさ：id_token 注入・モック可能な URLopen 等

機能一覧
--------
- Data
  - J-Quants API クライアント（jquants_client）
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
    - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
  - RSS ニュース収集（news_collector）
    - fetch_rss / save_raw_news / news と銘柄の紐付け
  - スキーマ管理（data.schema）
    - init_schema(db_path) で DuckDB スキーマを初期化
  - ETL パイプライン（data.pipeline）
    - 差分取得・保存・品質チェックを行うジョブ群（run_prices_etl 等）
  - 統計ユーティリティ（data.stats）
    - zscore_normalize 等
- Research
  - ファクター計算（research.factor_research）
    - calc_momentum / calc_volatility / calc_value
  - 特徴量解析（research.feature_exploration）
    - calc_forward_returns / calc_ic / factor_summary / rank
- Strategy
  - 特徴量作成（strategy.feature_engineering）
    - build_features(conn, target_date)
  - シグナル生成（strategy.signal_generator）
    - generate_signals(conn, target_date, threshold, weights)
- Backtest
  - シミュレータ / トレード記録 / メトリクス（backtest）
  - run_backtest(conn, start_date, end_date, ...) による日次バックテスト
  - CLI エントリポイント: python -m kabusys.backtest.run
- Execution / Monitoring
  - 発注・監視層のためのテーブル定義や空のパッケージプレースホルダ

要件（代表）
--------------
- Python 3.10+（型アノテーションや typing 機能を利用）
- duckdb
- defusedxml
- （標準ライブラリのみで実装されている機能も多いが、上記外部パッケージが必要）

インストール（開発環境）
-----------------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. 開発インストール（任意）
   - pip install -e .

環境変数
--------
設定は .env ファイル（プロジェクトルート）または実環境の環境変数で行います。config.Settings を通じて参照されます。
自動ロード:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を読み込みます。
- テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

重要な環境変数（必須とデフォルト）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- KABUSYS_ENV (任意, default=development) — development | paper_trading | live
- LOG_LEVEL (任意, default=INFO)
- DUCKDB_PATH (任意, default=data/kabusys.duckdb)
- SQLITE_PATH (任意, default=data/monitoring.db)

例 (.env)
---------
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb

データベース初期化
-----------------
DuckDB スキーマを初期化します（初回のみ）。
Python REPL かスクリプトで:

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # :memory: でインメモリ DB も可
conn.close()

ETL（データ取得・保存）の実行（概略）
-----------------------------------
- J-Quants から株価・財務・カレンダーを差分取得して保存する ETL は data.pipeline モジュールにあります（run_prices_etl など）。
- ニュース収集は data.news_collector.run_news_collection を使います。

例（ニュース収集）:

from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection
conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
conn.close()

特徴量作成とシグナル生成
-----------------------
- 特徴量の作成（features テーブルへ書き込み）:
  from kabusys.strategy import build_features
  build_features(conn, target_date)

- シグナル生成（signals テーブルへ書き込み）:
  from kabusys.strategy import generate_signals
  generate_signals(conn, target_date, threshold=0.6, weights=None)

これらは DuckDB 接続（init_schema で作成）を受け取り、features / ai_scores / positions / prices_daily 等を参照します。処理は日付単位で冪等（既存レコードは置換）です。

バックテストの実行
------------------
CLI から実行:

python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --db data/kabusys.duckdb \
  --cash 10000000

または Python API:

from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest
conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
# 結果: result.history, result.trades, result.metrics

run_backtest の主な引数:
- conn: 本番 DuckDB 接続（読み取り専用で使用）
- start_date / end_date: バックテスト期間（含む）
- initial_cash / slippage_rate / commission_rate / max_position_pct

出力は BacktestResult（history, trades, metrics）です。metrics には CAGR / Sharpe / MaxDD / WinRate / PayoffRatio / TotalTrades が含まれます。

サンプル（Python スニペット）
--------------------------
DB を初期化してニュース収集 → 特徴量作成 → シグナル生成 の簡単な流れ:

from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection
from kabusys.strategy import build_features, generate_signals

conn = init_schema("data/kabusys.duckdb")
# ニュース収集（known_codes 指定）
_ = run_news_collection(conn, known_codes={"7203", "6758"})
# 特徴量作成
build_features(conn, target_date=date(2024, 1, 4))
# シグナル生成
generate_signals(conn, target_date=date(2024, 1, 4))
conn.close()

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py               — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py     — J-Quants API クライアント + 保存関数
  - news_collector.py     — RSS 取得・保存・銘柄抽出
  - pipeline.py           — ETL パイプラインの実装（差分取得等）
  - schema.py             — DuckDB スキーマ定義と init_schema
  - stats.py              — zscore_normalize 等の統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py    — calc_momentum / calc_volatility / calc_value
  - feature_exploration.py— calc_forward_returns / calc_ic / factor_summary / rank
- strategy/
  - __init__.py
  - feature_engineering.py— build_features
  - signal_generator.py   — generate_signals（BUY/SELL 判定）
- backtest/
  - __init__.py
  - engine.py             — run_backtest（バックテストループ）
  - simulator.py          — PortfolioSimulator, TradeRecord, DailySnapshot
  - metrics.py            — バックテスト評価指標計算
  - run.py                — CLI エントリポイント
  - clock.py              — SimulatedClock（将来用途）
- execution/               — 発注/実行層（パッケージ placeholder）
- monitoring/              — 監視関連（パッケージ placeholder）

注意点 / 運用メモ
-----------------
- セキュリティ: .env に機密トークンを保存する際はファイルのパーミッション管理に注意してください。
- 自動 .env ロード: config モジュールは起動時にプロジェクトルートの .env / .env.local を自動読み込みします。テストで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- レートリミット / リトライ: jquants_client は 120 req/min に合わせた固定間隔スロットリングとリトライロジックを実装しています。429/408/5xx に対する指数バックオフを行います。
- 冪等性: DB への保存は ON CONFLICT / トランザクションで実装されており、再実行しても重複しません（設計上の前提）。
- Bear レジーム等の市場判定やシグナルロジックの詳細は source 内のコメント（StrategyModel.md 等参照）を参照してください。

貢献 / 開発
------------
- コードは型注釈とユニットテストを追加して拡張してください。
- 外部 API 呼び出し箇所（jquants_client, news fetch）をモックしてテストを作成すると良いです。
- 新しい ETL ジョブや品質チェックは data.pipeline / data.quality（未展示）に追加してください。

ライセンス
---------
（ここにはプロジェクトのライセンス情報を明記してください）

おわりに
--------
本 README はソースコードに記載された設計方針・関数仕様をもとに要点をまとめたものです。各モジュール内の docstring を参照すると、より詳しい挙動（引数・返り値・副作用）が分かります。必要であれば README に使い方の具体的な例や運用手順（cron/tui）を追記します。