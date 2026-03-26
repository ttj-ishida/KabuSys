# KabuSys

日本株向けの自動売買・バックテストフレームワーク（KabuSys）  
このリポジトリは、データ取得・特徴量エンジニアリング・シグナル生成・ポートフォリオ構築・バックテスト・ニュース収集までを含むモジュール群を提供します。

## プロジェクト概要
KabuSys は以下を想定したモジュール化されたシステムです。

- J-Quants 等の外部データソースからデータを取得して DuckDB に保存する ETL
- 研究環境での因子計算（momentum / volatility / value 等）
- 特徴量正規化と features テーブル作成
- AI スコア等を組み合わせた売買シグナル生成（BUY / SELL）
- セクター集中制御・リスク調整・資金配分・株数決定
- ポートフォリオ擬似約定シミュレータとバックテストエンジン
- RSS ベースのニュース収集と銘柄抽出

設計方針として、ルックアヘッドバイアスの回避、冪等性（DB INSERT の ON CONFLICT 処理等）、各モジュールの DB 依存の明確化（研究モジュールは DB のみ参照、実行層は外部 API を介す）を重視しています。

## 機能一覧
主な機能（モジュール）:

- kabusys.config
  - .env または環境変数から設定をロード。自動ロードはプロジェクトルートを検出して行う（無効化可）。
- kabusys.data.jquants_client
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動更新）。
  - 日足・財務データ・上場銘柄情報・マーケットカレンダーの取得と DuckDB への保存関数。
- kabusys.data.news_collector
  - RSS 取得、前処理、raw_news 保存、記事と銘柄コードの紐付け。
- kabusys.research
  - factor_research: momentum / volatility / value 等の計算。
  - feature_exploration: 将来リターン・IC・要約統計。
- kabusys.strategy
  - feature_engineering.build_features: features テーブル構築（Zスコア正規化、フィルタ等）。
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL を生成。
- kabusys.portfolio
  - portfolio_builder: 候補選定 / 重み計算（等金額 / スコア加重）。
  - position_sizing: 株数計算（risk_based / equal / score）、aggregate cap 処理、単元丸め。
  - risk_adjustment: セクター上限適用、レジーム乗数計算。
- kabusys.backtest
  - engine.run_backtest: バックテスト全体ループ（データの in-memory コピー、シミュレータ呼出し、指標計算）。
  - simulator: 擬似約定、日次スナップショット、TradeRecord 管理。
  - metrics: CAGR, Sharpe, MaxDD, 勝率等の算出。
  - CLI: python -m kabusys.backtest.run（コマンドライン実行可能）。

## セットアップ手順

前提
- Python 3.10+（typing の | 記法を使用しているため）
- DuckDB を利用するためネイティブライブラリが必要（pip でインストール可能）

推奨インストール手順（プロジェクトルートで実行）:

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（最低限）
   - pip install --upgrade pip
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt があればそれを使用してください。ここでは主要依存を列挙しています）

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. 環境変数 / .env の準備  
   プロジェクトは .env / .env.local を自動的に読み込みます（プロジェクトルート検出時）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   必須環境変数（Settings で必須とされるもの）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   オプション（デフォルトは Settings 内に記載）:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト "development"
   - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
   - DUCKDB_PATH / SQLITE_PATH のデフォルトパスはそれぞれ data/kabusys.duckdb, data/monitoring.db

## 使い方

いくつかの代表的な操作例を示します。

- DuckDB スキーマ初期化（スキーマ初期化関数は data.schema に実装されている想定）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ファイル作成＋スキーマ初期化
  ```

- J-Quants から日足データを取得して保存
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.jquants_client import get_id_token

  token = get_id_token()  # settings.jquants_refresh_token を用いて取得
  recs = fetch_daily_quotes(id_token=token, date_from=None, date_to=None)
  saved = save_daily_quotes(conn, recs)
  ```

- 特徴量（features）構築
  ```python
  from kabusys.strategy import build_features
  from datetime import date
  cnt = build_features(conn, target_date=date(2024, 01, 31))
  print(f"features upserted: {cnt}")
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date
  cnt = generate_signals(conn, target_date=date(2024, 01, 31), threshold=0.6)
  print(f"signals generated: {cnt}")
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", ...}  # stocks テーブルや外部ソースから取得する想定
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- バックテスト（CLI）
  DuckDB ファイルに必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar, stocks 等）が事前に存在している必要があります。

  コマンド例:
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```

  オプション:
  - --allocation-method: equal | score | risk_based
  - --slippage: スリッページ率（デフォルト 0.001）
  - --commission: 手数料率（デフォルト 0.00055）
  - --max-positions, --max-utilization, --risk-pct, --stop-loss-pct, --lot-size 等

- Python API でバックテストを実行
  ```python
  from kabusys.backtest.engine import run_backtest
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  print(result.metrics)
  ```

注意点:
- バックテストは本番データベースを直接書き換えないよう、内部で in-memory の DuckDB に必要なデータをコピーして実行します（_build_backtest_conn）。
- generate_signals / build_features は target_date より後方の情報を参照しないよう設計されています（ルックアヘッド防止）。
- 実行環境・本番接続での live trading 実装は別途 execution 層が必要（本コードベースは戦略・データ・バックテスト中心）。

## ディレクトリ構成（主なファイル）
以下は src/kabusys 以下の主要ファイルと簡単な説明です。

- kabusys/
  - __init__.py (パッケージ定義、バージョン)
  - config.py (環境変数 / 設定管理)
  - execution/ (発注・実行関連のための空パッケージプレースホルダ)
  - portfolio/
    - portfolio_builder.py (候補選定、等分・スコア加重)
    - position_sizing.py (株数決定・aggregate cap)
    - risk_adjustment.py (セクターキャップ、レジーム乗数)
    - __init__.py (公開 API)
  - strategy/
    - feature_engineering.py (features テーブル構築)
    - signal_generator.py (BUY/SELL シグナル生成)
    - __init__.py
  - research/
    - factor_research.py (momentum/volatility/value 計算)
    - feature_exploration.py (forward returns / IC / summary)
    - __init__.py
  - backtest/
    - engine.py (バックテストエンジン)
    - simulator.py (擬似約定・ポートフォリオ状態)
    - metrics.py (バックテスト評価指標)
    - run.py (CLI エントリ)
    - clock.py (模擬時計)
    - __init__.py
  - data/
    - jquants_client.py (J-Quants API クライアント + 保存関数)
    - news_collector.py (RSS 取得・保存・銘柄抽出)
    - (schema.py, calendar_management.py 等は参照されるがここには示されていません)
  - backtest のサブモジュールやその他ユーティリティが存在します。

各モジュールはソース内 docstring と関数コメントで挙動・前提（参照するテーブル・戻り値の形式）を詳細に記載しています。実際に利用する際は docstring を参照してください。

---

この README はリポジトリ内のコード（docstring と設定）に基づいて作成しています。実際の運用やデプロイでは、テスト用データや本番 API の挙動・権限管理、Slack・kabuステーション等の外部連携設定に十分注意してください。