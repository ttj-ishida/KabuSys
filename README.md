KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株アルゴリズム取引（研究・データ収集・シグナル生成・バックテスト・シミュレーション）を目的とした Python パッケージです。  
主に以下を提供します：

- J-Quants API からの市場データ取得と DuckDB への保存（データ ETL）
- ニュース（RSS）収集と記事→銘柄の紐付け
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- 特徴量構築（正規化・クリップ）とシグナル生成（BUY/SELL）
- ポートフォリオ構築（候補選定・配分計算・リスク調整・サイジング）
- バックテストフレームワーク（シミュレータ、約定モデル、評価指標）
- 環境変数ベースの設定管理

本 README はリポジトリ内の主要モジュール実装に基づく使用ガイドです。

機能一覧
--------
主な機能（モジュール別）:

- kabusys.config
  - .env / .env.local の自動読込（プロジェクトルート判定）
  - 環境変数の取得ラッパ（必須チェック、型変換、環境切替）
- kabusys.data.jquants_client
  - J-Quants API クライアント（認証、自動リフレッシュ、レート制限、リトライ）
  - 株価日足 / 財務データ / 上場銘柄情報 / カレンダーの取得と DuckDB への保存
- kabusys.data.news_collector
  - RSS 取得（SSRF対策、gzip対応、サイズ制限）
  - 記事正規化、SHA-256 による記事ID生成、raw_news 保存、銘柄抽出と news_symbols 保存
- kabusys.research
  - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily/raw_financials からファクター計算
  - feature_exploration：将来リターン計算、IC 計算、ファクター統計
- kabusys.strategy
  - feature_engineering.build_features：複数ファクターのマージ・Zスコア正規化・features テーブルへ UPSERT
  - signal_generator.generate_signals：features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを signals テーブルへ書き込み
- kabusys.portfolio
  - select_candidates / calc_equal_weights / calc_score_weights
  - calc_position_sizes：等配分・スコア配分・リスクベースの株数計算（単元丸め、aggregate cap）
  - apply_sector_cap / calc_regime_multiplier：セクター制限・レジームに基づく乗数
- kabusys.backtest
  - engine.run_backtest：バックテストループ（データコピー、シミュレータとシグナル生成の連携）
  - simulator.PortfolioSimulator：擬似約定・資産評価・トレード記録
  - metrics.calc_metrics：CAGR / Sharpe / MaxDrawdown / WinRate / PayoffRatio 等の算出
  - CLI: python -m kabusys.backtest.run のエントリポイント
- その他
  - data.schema（init_schema 等、DB スキーマ初期化）※実装ファイル参照

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の | 演算子などを使用）
- DuckDB（Python 用パッケージ duckdb）
- ネットワーク接続（J-Quants / RSS 閲覧用）

推奨パッケージ（最低限）
- duckdb
- defusedxml

例（venv を使ったセットアップ）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate    # macOS / Linux
   - .venv\Scripts\activate       # Windows

2. 必要パッケージのインストール（例）
   - pip install duckdb defusedxml

（リポジトリに requirements.txt がある場合は pip install -r requirements.txt を使用）

環境変数
- .env（プロジェクトルート）または OS の環境変数を利用します。
- 自動ロードは kabusys.config により .env → .env.local の順でロードされます（OS 環境変数が最優先）。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主要な環境変数（必須 / 任意）:
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API のパスワード（実行時の取引 API 用）
- KABU_API_BASE_URL (任意): kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャネル ID
- DUCKDB_PATH (任意): デフォルト DB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意): 環境 "development" | "paper_trading" | "live"（デフォルト development）
- LOG_LEVEL (任意): ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

DB 初期化
- data.schema.init_schema(db_path) のような関数でスキーマを初期化することを想定しています（実装を参照してください）。
- バックテスト用に DuckDB を事前に prices_daily / features / ai_scores / market_regime / market_calendar テーブルで準備してください。

使い方
------

1) バックテスト（CLI）
- コマンド例:
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db path/to/kabusys.duckdb

- 主要オプション:
  --start / --end : 開始・終了日 (YYYY-MM-DD)
  --db : DuckDB ファイルパス（必須）
  --allocation-method : equal | score | risk_based（デフォルト risk_based）
  --slippage / --commission / --lot-size 等を調整可能

2) バックテスト API（Python 呼び出し）
例:
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("path/to/kabusys.duckdb")
result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
conn.close()

戻り値は BacktestResult(history, trades, metrics) です。

3) 特徴量構築（features の作成）
from kabusys.strategy import build_features
build_features(conn, target_date)

- DuckDB 接続（conn）は init_schema 等で確保し、prices_daily/raw_financials テーブルを参照します。

4) シグナル生成
from kabusys.strategy import generate_signals
generate_signals(conn, target_date)

- features / ai_scores / positions を参照して signals テーブルへ日付単位で置換（冪等）して書き込みます。

5) ニュース収集
from kabusys.data.news_collector import run_news_collection
run_news_collection(conn, sources=None, known_codes=None)

- デフォルトで DEFAULT_RSS_SOURCES を使用。
- known_codes を渡すと記事中の四桁コード抽出→news_symbols を行います。

6) J-Quants データ取得と保存
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
data = fetch_daily_quotes(code=None, date_from=..., date_to=...)
save_daily_quotes(conn, data)

- get_id_token() は settings.jquants_refresh_token を利用して ID トークンを取得します。
- API 呼び出しはレート制限（120 req/min）、401 自動リフレッシュ、リトライを備えます。

主要な設計・動作上の注意
- ルックアヘッドバイアス回避: 特徴量/シグナルは target_date 時点までの情報のみを用いる設計。
- 冪等性: 各テーブルへの書き込みは日付単位の置換や ON CONFLICT により冪等に実装されています。
- セキュリティ: RSS 取得は SSRF 対策、XML パースは defusedxml を使用、レスポンスサイズ制限あり。
- レジーム/リスク管理: calc_regime_multiplier により市場レジーム（bull/neutral/bear）に応じて投入資金を調整します。bear レジームでは generate_signals が BUY シグナルを抑制します。

ディレクトリ構成（主なファイル）
-----------------------------
以下は src/kabusys 以下の主要ファイル群（リポジトリに含まれる実装に基づく）:

- src/kabusys/
  - __init__.py
  - config.py
  - execution/ (未実装/プレースホルダ)
  - monitoring/ (未実装/プレースホルダ)
  - data/
    - jquants_client.py
    - news_collector.py
    - (その他: schema, calendar_management 等が想定)
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - strategy/
    - feature_engineering.py
    - signal_generator.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - backtest/
    - engine.py
    - simulator.py
    - metrics.py
    - clock.py
    - run.py
    - __init__.py
  - portfolio/ (上記)
  - backtest/ (上記)
  - research/ (上記)

開発・貢献
---------
- コードはドキュメント文字列とロギングを多用しており、モジュール単位での理解がしやすい設計です。
- 新機能追加やバグ修正の際は unit test（特にデータ処理・数値ロジック）を追加してください。
- .env.example を用意し、必須環境変数の説明を明確にすると良いです。

最後に
------
この README はコードベースの実装内容に基づいてまとめています。実際の運用では必ずテストネットや paper_trading 環境で十分に検証した上で live 環境に移行してください。自動売買はリスクを伴います — 運用は自己責任で行ってください。