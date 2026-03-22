# KabuSys

日本株向けの自動売買 / バックテスト / データパイプラインライブラリです。  
DuckDB をデータ層に用い、J-Quants や RSS からデータを取得して特徴量作成、シグナル生成、バックテストを行うことを想定したモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアス回避（target_date 時点のデータのみを参照）
- DuckDB を用いた冪等なデータ保存（ON CONFLICT / トランザクション）
- ネットワーク処理は堅牢性（レート制御・リトライ・SSRF 対策）を重視

---

## 機能一覧

- data
  - J-Quants API クライアント（株価・財務・市場カレンダーの取得）と保存機能
  - RSS ニュース収集と記事→銘柄紐付け（SSRF 対策、前処理、重複排除）
  - DuckDB スキーマ定義 / 初期化（init_schema）
  - ETL パイプライン（差分取得、品質チェックなど）
  - 汎用統計ユーティリティ（Z スコア正規化）
- research
  - ファクター計算（Momentum / Volatility / Value）
  - 特徴量探索（将来リターン計算、IC 計算、要約統計）
- strategy
  - 特徴量エンジニアリング（build_features：raw factor → features テーブル）
  - シグナル生成（generate_signals：features と ai_scores を統合して BUY/SELL を生成）
- backtest
  - ポートフォリオシミュレーション（擬似約定・スリッページ・手数料モデル）
  - バックテストエンジン（run_backtest：DB からデータをコピーして日次ループを実行）
  - 評価指標計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- news_collector：RSS 収集 → raw_news / news_symbols 保存
- その他：
  - 設定管理（環境変数の自動読み込み / Settings）

---

## 動作環境 / 依存関係

推奨 Python バージョン：Python 3.10 以上（型注釈で | 演算子を使用しています）  
主な依存パッケージ（例）：
- duckdb
- defusedxml

インストール例（仮の requirements）:
pip install duckdb defusedxml

（プロジェクトに requirements.txt を追加する場合は上記を含めてください）

---

## 環境変数（.env）

プロジェクトは .env / .env.local をプロジェクトルートから自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。必須の環境変数：

- JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD      — kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       — Slack チャンネル ID（必須）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            — 環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL              — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

例 (.env)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. Python（3.10+）をインストール
2. 仮想環境を作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
3. 必要パッケージをインストール
   pip install duckdb defusedxml
4. プロジェクトルートに .env を作成し必要な環境変数を設定
5. DuckDB スキーマを初期化
   - Python REPL で:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()

---

## 使い方（主要な例）

- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
  conn.close()

- J-Quants から株価を取得して保存（簡易例）
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from datetime import date
  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  conn.close()

- RSS ニュース収集
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  conn.close()

- 特徴量作成（features テーブルへ保存）
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema
  from datetime import date
  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024,2,28))
  conn.close()

- シグナル生成（signals テーブルへ保存）
  from kabusys.strategy import generate_signals
  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024,2,28))
  conn.close()

- バックテスト（CLI）
  python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
  オプション:
    --cash 初期資金（JPY、デフォルト 10000000）
    --slippage スリッページ率（デフォルト 0.001）
    --commission 手数料率（デフォルト 0.00055）
    --max-position-pct 1銘柄あたりの最大比率（デフォルト 0.20）

- バックテストをプログラムから実行
  from kabusys.backtest.engine import run_backtest
  from kabusys.data.schema import init_schema
  from datetime import date
  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  print(result.metrics)
  conn.close()

---

## 主要テーブル（概要）

- raw_prices, raw_financials, raw_news, raw_executions
- prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- features, ai_scores, market_regime
- signals, signal_queue, orders, trades, positions, portfolio_performance

（スキーマは kabusys.data.schema 内の DDL を参照してください）

---

## ディレクトリ構成

概要的なツリー（主要ファイル）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント / 保存
    - news_collector.py             — RSS 収集・保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義 / init_schema
    - stats.py                      — z-score 正規化等
    - pipeline.py                   — ETL パイプライン（差分取得等）
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Volatility / Value 計算
    - feature_exploration.py        — 将来リターン / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py        — build_features
    - signal_generator.py           — generate_signals
  - backtest/
    - __init__.py
    - engine.py                     — run_backtest（エンジン）
    - simulator.py                  — PortfolioSimulator 等
    - metrics.py                    — 評価指標計算
    - run.py                        — CLI 起動スクリプト
    - clock.py
    - (その他)
  - execution/                       — （発注/実行周り、現状空のパッケージ）
  - monitoring/                      — （監視系、モジュールあり）

---

## 開発メモ / 注意点

- Settings は .env を自動で読み込みますが、CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして自動読み込みを無効化できます。
- DuckDB の初期化は init_schema() を必ず一度実行してください（テーブル未作成だと多くの処理が失敗します）。
- ネットワーク呼び出し（J-Quants / RSS）は堅牢に実装されていますが、API レート制限や認証情報が必要です。J-Quants のトークンは JQUANTS_REFRESH_TOKEN に設定してください。
- news_collector は外部ネットワークを扱うため SSRF / Gzip bomb / XML Bomb 等の防御を実装しています。テストではネットワーク呼び出しをモックしてください。
- 本リポジトリのコードは各モジュールの docstring に設計仕様（StrategyModel.md / DataPlatform.md など）を参照する旨が記載されています。これらのドキュメントが別ファイルで提供されている前提です。

---

## サンプルワークフロー

1. DB 初期化: init_schema("data/kabusys.duckdb")
2. データ取得:
   - jq.fetch_market_calendar / save_market_calendar
   - pipeline.run_prices_etl（差分取得）
   - jq.save_financial_statements
   - run_news_collection（RSS）
3. 特徴量作成: build_features(conn, target_date)
4. シグナル生成: generate_signals(conn, target_date)
5. バックテスト: run_backtest(...)

---

この README はコードベースの要点をまとめたものです。詳細は各モジュール（src/kabusys/**）内の docstring / 関数ドキュメントを参照してください。必要であれば、セットアップ用の requirements.txt、Dockerfile、CI ワークフロー、さらに詳しい操作例を追記できます。