# KabuSys

日本株向けの自動売買・研究プラットフォーム（バックテスト・データETL・シグナル生成など）。

---

## プロジェクト概要

KabuSys は、J-Quants や RSS 等からデータを収集し、DuckDB に保存してファクター計算、特徴量生成、シグナル生成、ポートフォリオ構築、バックテストを行うためのモジュール群です。実トレード用の実行層や Slack 通知などの設定が組み込まれており、研究→本番のワークフローを意識した設計になっています。

主な設計方針：
- ルックアヘッドバイアス防止（計算は target_date 時点のデータのみ使用）
- 冪等性（DB 書き込みは置換／ON CONFLICT を使用）
- バックテストと本番で同一ロジックを共有できるよう純粋関数中心の実装

---

## 主な機能（モジュール別）

- kabusys.config
  - .env ファイルや環境変数から設定を読み込む。自動ロード機能あり。
- kabusys.data
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - news_collector: RSS 収集と raw_news / news_symbols への保存（SSRF 対策・前処理）
- kabusys.research
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - feature_exploration: IC 計算など研究用ユーティリティ
- kabusys.strategy
  - feature_engineering.build_features: raw ファクターを正規化して features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナルを生成
- kabusys.portfolio
  - portfolio_builder: 候補選定・スコア重み付け等
  - position_sizing: 株数算出（risk_based / equal / score）
  - risk_adjustment: セクターキャップ、レジーム乗数
- kabusys.backtest
  - engine.run_backtest: バックテストのメインループ（擬似約定・マーク・ポートフォリオ構築）
  - simulator.PortfolioSimulator: 擬似約定ロジック（スリッページ・手数料モデル）
  - metrics: バックテスト評価指標の計算
  - run.py: CLI エントリポイント（python -m kabusys.backtest.run ...）

---

## 前提 / 要求環境

- Python 3.10 以上（typing の新構文や型ヒントを使用）
- DuckDB（Python パッケージ: duckdb）
- defusedxml（news_collector で XML パースに使用）
- その他標準ライブラリ（urllib, logging, datetime 等）

依存パッケージ例（簡易）:
- duckdb
- defusedxml

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## 必要な環境変数（主なもの）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` で管理できます。必須の例：

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（省略時は http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）

.env 例（最小）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順（ローカル開発向け）

1. Python 3.10+ を用意する
2. 仮想環境を作成してアクティベート
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されているなら）pip install -e .
4. プロジェクトルートに `.env` を作成し、必要な環境変数を設定する（.env.example を参照）
5. DuckDB スキーマを初期化する（プロジェクト内のスキーマ初期化関数を利用）
   - 例:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

（schema モジュールはこのリポジトリの他のファイルに含まれている前提です）

---

## 使い方

### バックテスト（CLI）

用意した DuckDB ファイル（prices_daily, features, ai_scores, market_regime, market_calendar 等を前もって投入）に対して CLI でバックテストを実行できます。

例:
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --db path/to/kabusys.duckdb \
  --allocation-method risk_based \
  --lot-size 100

主なオプション:
- --start / --end: 日付（YYYY-MM-DD）
- --cash: 初期資金
- --slippage / --commission: スリッページ・手数料率
- --allocation-method: equal | score | risk_based
- --max-positions / --max-utilization など多数（詳細はヘルプ参照）

### プログラムから呼び出す例

- DuckDB 接続初期化:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- ファクター正規化（features 作成）:
  from datetime import date
  from kabusys.strategy.feature_engineering import build_features
  build_features(conn, target_date=date(2024, 1, 31))

- シグナル生成:
  from kabusys.strategy.signal_generator import generate_signals
  generate_signals(conn, target_date=date(2024, 1, 31))

- J-Quants から日足取得と保存:
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
  save_daily_quotes(conn, records)

- RSS ニュース収集:
  from kabusys.data.news_collector import run_news_collection
  run_news_collection(conn, sources=None, known_codes=set_of_codes)

- バックテスト API:
  from kabusys.backtest.engine import run_backtest
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)

戻り値には履歴、トレード記録、評価指標（CAGR, Sharpe, MaxDD など）が含まれます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - jquants_client.py
  - news_collector.py
  - (schema.py, calendar_management.py などがプロジェクト内に存在する想定)
- research/
  - factor_research.py
  - feature_exploration.py
- strategy/
  - feature_engineering.py
  - signal_generator.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- backtest/
  - engine.py
  - simulator.py
  - metrics.py
  - run.py
- execution/ (空のパッケージプレースホルダ)
- monitoring/ (監視関連の実装を収める想定)

（実際のリポジトリにはさらに細かいモジュールや補助ユーティリティが含まれます）

---

## 開発・運用上の注意点

- 環境変数は .env/.env.local にて管理可能。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを抑止できます（テスト時に便利）。
- DuckDB のスキーマ（tables）を事前に準備しておく必要があります（prices_daily, raw_prices, features, signals, positions, ai_scores, market_regime, market_calendar, stocks, raw_news, news_symbols 等）。
- J-Quants API 呼び出しはレート制限（120 req/min）とリトライを組み込んでいますが、長時間の大量取得時は運用ルールに注意してください。
- news_collector は SSRF 対策や送受信サイズ制限を実装していますが、外部ソースを追加する際は慎重に検証してください。
- バックテストは DuckDB のデータを一部コピーしてインメモリ DB を作成します（本番 DB を汚さない設計）。

---

## ライセンス / 貢献

リポジトリ上の LICENSE や CONTRIBUTING.md を参照してください（存在する場合）。バグ報告・機能提案は Issue を立ててください。

---

この README はコードベースの主要機能と基本的な使い方をまとめたものです。詳細な API やスキーマ定義、運用手順はプロジェクト内のドキュメント（例: PortfolioConstruction.md, StrategyModel.md, DataPlatform.md, BacktestFramework.md）を参照してください。