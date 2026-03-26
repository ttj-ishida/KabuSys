# KabuSys

KabuSys は日本株向けの自動売買・研究パイプラインを実装した Python ライブラリです。データ取得（J-Quants）、特徴量構築、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集など、実運用や研究に必要な主要コンポーネントをモジュール化しています。

---

## プロジェクト概要

主な設計方針・特徴：
- DuckDB を用いたデータ管理（prices_daily / features / ai_scores / market_regime などを前提）
- ルックアヘッドバイアスに配慮した時点ベースの処理（target_date 以前のみ参照）
- J-Quants API クライアント（レート制限・リトライ・トークンリフレッシュ対応）
- ニュース収集（RSS）と記事 → 銘柄コード紐付け機能（SSRF対策・XML安全パース）
- バックテストエンジン（疑似約定・スリッページ・手数料モデル、評価指標）
- 統計／リサーチ機能（ファクター計算、IC・フォワードリターン等）
- 環境変数による設定管理（.env 自動読み込み、プロジェクトルート検出）

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数読み込み・設定取得（J-Quants トークン、kabu API パスワード、Slack トークン、DB パス等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector: RSS 取得・前処理・raw_news/save/news_symbols への保存
  - （schema 等、DuckDB スキーマ初期化を想定するモジュールを参照）
- kabusys.strategy
  - feature_engineering.build_features(conn, target_date)
  - signal_generator.generate_signals(conn, target_date, ...)
- kabusys.portfolio
  - portfolio_builder.select_candidates / calc_equal_weights / calc_score_weights
  - position_sizing.calc_position_sizes
  - risk_adjustment.apply_sector_cap / calc_regime_multiplier
- kabusys.backtest
  - engine.run_backtest(conn, start_date, end_date, ...)
  - simulator.PortfolioSimulator（疑似約定・時価評価）
  - metrics.calc_metrics（CAGR, Sharpe, MaxDD, WinRate, Payoff, TotalTrades）
  - CLI エントリポイント: python -m kabusys.backtest.run
- kabusys.research
  - factor_research.calc_momentum/calc_volatility/calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary

---

## セットアップ手順

前提
- Python >= 3.10（モダンな型アノテーションと union 型 `|` を使用）
- 仮想環境の利用を推奨

1. リポジトリをクローン（あるいは本パッケージのルートに移動）
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .\.venv\Scripts\activate    (Windows)

3. 必要パッケージをインストール（代表的な依存）
   - pip install duckdb defusedxml
   - 必要に応じて開発用に pip install -e .（setup がある場合）

4. 環境変数設定（.env を推奨）
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を配置すると自動で読み込まれます。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（settings から参照されるキー）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API 用パスワード
- SLACK_BOT_TOKEN — Slack Bot トークン
- SLACK_CHANNEL_ID — Slack 送信先チャネル ID

任意（デフォルト値あり）
- KABUS_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — {development, paper_trading, live}（デフォルト: development）
- LOG_LEVEL — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）

例: .env
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（実行例）

1. バックテスト（CLI）
   - 前提: DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar, stocks 等）が準備されていること
   - 実行例:
     - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db path/to/kabusys.duckdb
   - 主要オプション:
     - --cash, --slippage, --commission, --max-position-pct, --allocation-method (equal|score|risk_based), --risk-pct, --stop-loss-pct, --lot-size など

2. DuckDB 接続を使った Python API の例
   - スキーマ初期化:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("path/to/kabusys.duckdb")
   - 特徴量構築:
     - from kabusys.strategy import build_features
     - build_features(conn, target_date=<datetime.date object>)
   - シグナル生成:
     - from kabusys.strategy import generate_signals
     - generate_signals(conn, target_date=<date>, threshold=0.6)
   - J-Quants から株価取得して保存:
     - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
     - recs = fetch_daily_quotes(date_from=..., date_to=...)
     - save_daily_quotes(conn, recs)
   - ニュース収集（RSS）実行例:
     - from kabusys.data.news_collector import run_news_collection
     - run_news_collection(conn, sources=None, known_codes=set_of_codes)

3. ライブラリとしての利用（例: バックテスト API）
   - from kabusys.backtest.engine import run_backtest
   - result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000, allocation_method="risk_based", ...)

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 以下に配置されています）

- src/kabusys/
  - __init__.py  — パッケージ定義（バージョン）
  - config.py    — 環境変数 / 設定管理
  - data/
    - jquants_client.py     — J-Quants API クライアント（取得/保存）
    - news_collector.py     — RSS ニュース取得・前処理・DB 保存
    - (schema.py, calendar_management.py 等は参照される想定)
  - strategy/
    - feature_engineering.py — ファクター正規化・features への upsert
    - signal_generator.py    — final_score 計算・signals テーブルへ保存
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算・集約キャップ
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — momentum / volatility / value の計算
    - feature_exploration.py — forward returns / IC / summary
  - backtest/
    - engine.py              — バックテストの中核ループ
    - simulator.py           — 擬似約定・履歴管理
    - metrics.py             — バックテスト評価指標
    - run.py                 — CLI エントリポイント
    - clock.py               — (将来用) 模擬時計
  - execution/               — 実運用の注文送信層（空パッケージ）
  - portfolio/               — 上記ポートフォリオ関連
  - monitoring/              — 監視関連（未展開）

---

## 注意点・運用上の補足

- Look-ahead バイアス防止：
  - 各種計算は target_date 時点までのデータに限定しており、バックテストやシグナル生成のループでは未来データを参照しないよう設計されています。
- 自動 .env 読み込み：
  - config モジュールはプロジェクトルート（.git / pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- J-Quants API：
  - rate limit（120 req/min）に合わせた内部 RateLimiter、リトライ・トークンリフレッシュロジックを実装しています。大量取得時は間隔に注意してください。
- DuckDB スキーマ：
  - 本コードは複数のテーブル（prices_daily / raw_prices / features / ai_scores / positions / signals / raw_news / news_symbols / stocks / market_regime / market_calendar 等）を前提に動作します。schema 初期化・ETL は別モジュール（data.schema 等）で実装される想定です。

---

## 開発・拡張のヒント

- 新しいファクターやシグナル重みは strategy モジュールに追加し、generate_signals の weights パラメータで上書き可能です。
- 単元（lot_size）や手数料モデルは simulator / position_sizing で調整できます。
- news_collector は拡張性を考慮しており、追加 RSS ソースやより精巧な記事→銘柄抽出ロジックを実装可能です。
- バックテストの出力（BacktestResult）を用いれば、結果を可視化するダッシュボードやレポート生成パイプラインを構築できます。

---

必要であれば README に含める具体的な .env.example、CLI のさらなる使用例、あるいは開発用セットアップ（Makefile / pre-commit / tox など）のテンプレートも作成できます。どうしますか？