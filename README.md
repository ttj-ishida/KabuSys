# KabuSys — 日本株自動売買システム

本リポジトリは日本株向けの自動売買／リサーチ基盤の実装群（ライブラリ＋バッチツール）です。  
主に以下の用途を想定しています：市場データの取得・ETL、ファクター計算、特徴量構築、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のレイヤーで構成されたモジュール群を提供します：

- Data: J-Quants API 経由で株価・財務・市場カレンダーなどを取得し DuckDB に格納する ETL 機能
- Research: ファクター計算・特徴量探索（IC・統計サマリー等）
- Strategy: 特徴量をもとに戦略シグナル（BUY/SELL）を生成
- Portfolio: 候補選定、重み付け、ポジションサイズ計算、リスク制御（セクターキャップ、レジーム乗数）
- Backtest: ポートフォリオシミュレータ、バックテストエンジン、評価メトリクス
- News: RSS フィードからニュースを収集し記事→銘柄紐付けを行うモジュール
- Execution/Monitoring: 実運用・監視に必要な層（スケルトン）

設計方針の例：
- ルックアヘッドバイアスを防ぐ（時刻情報・fetched_at を記録、target_date 以前のデータのみ参照）
- 冪等性（DB INSERT は ON CONFLICT で保護）
- ネットワーク操作は堅牢（リトライ、レートリミット、SSRF対策 等）
- バックテストは本番 DB を汚さない（インメモリにコピーして実行）

---

## 主な機能一覧

- J-Quants API クライアント（取得・保存・トークン自動リフレッシュ・ページネーション対応）
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
  - fetch_listed_info
- ニュース収集（RSS）および前処理・銘柄抽出・DB 保存
  - fetch_rss / save_raw_news / run_news_collection
- ファクター計算（momentum / volatility / value）
  - calc_momentum, calc_volatility, calc_value
- 特徴量構築
  - build_features(conn, target_date)
- シグナル生成
  - generate_signals(conn, target_date, threshold, weights)
- ポートフォリオ構築
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（risk_based / equal / score 配分）
  - apply_sector_cap（セクター集中制限）
  - calc_regime_multiplier（市場レジームに応じた乗数）
- バックテスト
  - run_backtest(...)：バックテストループ、シミュレータ、metrics 出力
  - PortfolioSimulator：擬似約定モデル、マーク・トゥ・マーケット記録
  - バックテスト CLI: python -m kabusys.backtest.run
- 研究支援
  - calc_forward_returns, calc_ic, factor_summary, rank
- 設定管理
  - 環境変数の自動読み込み（.env / .env.local）と検証（kabusys.config）

---

## セットアップ手順

※ 以下は本リポジトリをローカルで動かすための一般的な手順です。プロジェクトごとの依存関係（requirements.txt / pyproject.toml）が存在する場合はそちらに従ってください。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-dir>

2. Python 仮想環境の作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml がある場合はそれを使用）

4. 環境変数（.env）の準備
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（kabusys.config）。
   - 必須の環境変数は後述の「環境変数」を参照してください。

5. DuckDB スキーマ初期化 / データ投入
   - 実行には DuckDB のスキーマ（prices_daily, features, ai_scores, market_regime, market_calendar など）が必要です。
   - コード内の schema 初期化関数（kabusys.data.schema.init_schema）を利用してスキーマを作成してください（本 README にスキーマ定義は含まれていません）。
   - J-Quants からデータを取得して保存する場合は data/jquants_client の関数を使用してください。

---

## 環境変数

kabusys.config.Settings によって必要な環境変数が管理されます。自動読み込みは .env / .env.local（プロジェクトルート検出: .git または pyproject.toml基準）から行われます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（必須を明記）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API のリフレッシュトークン。get_id_token によって ID トークン取得に使用。
- KABU_API_PASSWORD (必須)
  - kabuステーション API 用のパスワード（execution 層で使用想定）。
- KABU_API_BASE_URL (任意、デフォルト http://localhost:18080/kabusapi)
  - kabu API のベース URL。
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト data/kabusys.duckdb)
  - DuckDB ファイルパス
- SQLITE_PATH (任意、デフォルト data/monitoring.db)
  - 監視用 SQLite パス
- KABUSYS_ENV (任意、デフォルト development)
  - 有効値: development, paper_trading, live
- LOG_LEVEL (任意、デフォルト INFO)
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

未設定の必須変数にアクセスすると ValueError が発生します。

---

## 使い方

以下に主要なユースケースの実行例を示します。

1) バックテスト（コマンドライン）

DuckDB に必要なテーブルが事前に用意されていることが前提です（prices_daily, features, ai_scores, market_regime, market_calendar）。

例:
- python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db path/to/kabusys.duckdb

オプション:
- --slippage, --commission, --max-position-pct, --allocation-method, --max-utilization, --max-positions, --risk-pct, --stop-loss-pct, --lot-size など

2) ライブラリ API（スクリプト内利用例）

- 特徴量構築:
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("path/to/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 31))
  conn.close()

- シグナル生成:
  from kabusys.strategy import generate_signals
  n_signals = generate_signals(conn, target_date=date(2024,1,31))

- ニュース収集ジョブ:
  from kabusys.data.news_collector import run_news_collection
  result = run_news_collection(conn, sources=None, known_codes=set_of_codes)

- J-Quants データ取得と保存:
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=..., date_to=...)
  save_daily_quotes(conn, records)

- バックテスト API 呼び出し:
  from kabusys.backtest.engine import run_backtest
  res = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)

3) PortfolioSimulator（単体テスト等での使用）

  from kabusys.backtest.simulator import PortfolioSimulator
  sim = PortfolioSimulator(initial_cash=1_000_000)
  # signals = [{"code":"7203","side":"buy","shares":100}, ...]
  sim.execute_orders(signals, open_prices, slippage_rate=0.001, commission_rate=0.00055, trading_day=date(2024,1,2), lot_size=100)
  sim.mark_to_market(date(2024,1,2), close_prices)
  history = sim.history
  trades = sim.trades

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 配下の主なモジュール一覧）

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数・設定管理
  - data/
    - jquants_client.py           -- J-Quants API クライアント & DuckDB 保存
    - news_collector.py           -- RSS ニュース収集・前処理・DB 保存
    - (schema.py 等が存在している想定) -- DB スキーマ初期化
  - research/
    - factor_research.py          -- モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py      -- IC / 将来リターン / 統計サマリー
  - strategy/
    - feature_engineering.py      -- features テーブル構築（正規化・クリップ・UPSERT）
    - signal_generator.py         -- final_score 計算・BUY/SELL 判定・signals 書き込み
  - portfolio/
    - portfolio_builder.py        -- 候補選定・重み計算
    - position_sizing.py          -- 株数計算（risk_based / equal / score）
    - risk_adjustment.py          -- セクターキャップ・レジーム乗数
  - backtest/
    - engine.py                   -- バックテストループ、run_backtest
    - simulator.py                -- PortfolioSimulator（擬似約定）
    - metrics.py                  -- 評価指標計算
    - run.py                      -- CLI エントリポイント
    - clock.py                    -- SimulatedClock（将来拡張用）
  - portfolio/ __init__ .py
  - strategy/ __init__ .py
  - research/ __init__ .py
  - backtest/ __init__ .py
  - その他: execution/, monitoring/ フォルダ（実運用の実装予定・スケルトン）

---

## 開発メモ / 注意点

- データの「時点情報」(fetched_at, date の扱い) を厳密に管理し、バックテストでは target_date 時点で入手可能なデータのみを使うことを意図しています。
- J-Quants API: レート制限（120 req/min）や 401 自動リフレッシュ、リトライロジックを実装済みです。
- ニュース収集: SSRF 対策、gzip 上限、XML パース例外の保護を実装しています。
- バックテスト: 本番 DB を汚さないため、必要なテーブルをインメモリ DuckDB にコピーして実行します。run_backtest は多くのパラメータで挙動を制御できます。
- セキュリティ: URL の正規化やホストのプライベート判定等、外部データ取り込みの安全性に配慮しています。

---

## 貢献 / ライセンス

- 開発・提案・バグ報告は Pull Request または Issue で受け付けてください。
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（本 README では指定していません）。

---

README は以上です。実行時の具体的なスキーマ定義や依存パッケージのロック（requirements.txt / pyproject.toml）が存在する場合はそちらに従ってセットアップしてください。必要であれば、README に実際の DB スキーマ抜粋やよくあるトラブルシュート（例: .env 設定テンプレート）を追加します。