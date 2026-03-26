# KabuSys

日本株向けの自動売買 / 研究プラットフォーム（KabuSys）のコードベース用 README。

本ドキュメントはプロジェクトの概要、主な機能、セットアップ手順、使い方（主要な CLI / API の例）、およびディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株に対するアルゴリズム取引プラットフォームで、以下の機能を備えます。

- データ収集（J-Quants API 経由で日次株価・財務データ、RSS ニュース）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量エンジニアリング（正規化・クリッピングして features テーブルへ保存）
- シグナル生成（複数ファクターと AI スコアの統合、BUY/SELL 判定）
- ポートフォリオ構築（候補選定、配分、リスク調整、株数サイジング）
- バックテストフレームワーク（疑似約定モデル・メトリクス計算）
- ニュース収集・記事と銘柄の紐付け
- 環境設定管理（.env 自動読み込み等）

設計原則として「ルックアヘッドバイアスを排除」「DuckDB を中心としたローカル ETL / バックテスト」「発注層と研究層の疎結合」を採用しています。

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数管理、.env 自動ロード、環境モード（development / paper_trading / live）
- kabusys.data
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークンリフレッシュ対応）
  - news_collector: RSS 収集・正規化・DB 保存・銘柄抽出
  - （schema 等）DuckDB スキーマ初期化・ETL 用ユーティリティ（init_schema を参照）
- kabusys.research
  - factor_research: mom/volatility/value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー
- kabusys.strategy
  - feature_engineering: ファクターの正規化・features テーブル作成
  - signal_generator: final_score 計算、BUY/SELL シグナル生成、signals テーブルへの保存
- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment（セクターキャップ、レジーム乗数）
- kabusys.backtest
  - engine: バックテストループの実装（run_backtest）
  - simulator: 擬似約定・ポートフォリオ状態管理
  - metrics: バックテスト評価指標計算
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- kabusys.execution / kabusys.monitoring
  - （発注・監視用の骨組み）

---

## 前提条件 / 推奨環境

- Python 3.10 以上（構文に `X | None` 等の新しい型記法を使用）
- 必要なパッケージ（主な例）
  - duckdb
  - defusedxml
  - （その他、プロジェクトの requirements.txt があればそれを使用してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repository-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - またはプロジェクトに requirements.txt があれば:
     - pip install -r requirements.txt
   - 開発時は editable install:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（pyproject.toml または .git がある場所）に `.env` / `.env.local` を置くと自動的に読み込まれます（起動時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必須環境変数（kabusys.config.Settings 参照）
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャネルID（必須）
   - オプション:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development | paper_trading | live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

5. DuckDB スキーマの初期化
   - コード内で `from kabusys.data.schema import init_schema` を参照する実装があるため、init_schema(db_path) により必要なテーブル群を作成するスクリプトが存在する想定です（schema.py を用いて DB を初期化してください）。
   - バックテスト／研究には prices_daily / raw_financials / features / ai_scores / market_regime / market_calendar / stocks 等のテーブルが必要です。

---

## 使い方（主要な実行例）

### バックテスト（CLI）

プロジェクトに含まれるバックテストランナーを使う例：

python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --db path/to/kabusys.duckdb \
  --cash 10000000 \
  --allocation-method risk_based \
  --max-positions 10

主なオプション:
- --start / --end: バックテスト期間（YYYY-MM-DD）
- --db: DuckDB ファイルパス（事前にデータを準備）
- --cash: 初期資金（デフォルト 10,000,000）
- --slippage / --commission: スリッページ・手数料率
- --allocation-method: equal | score | risk_based

CLI は実行後に CAGR, Sharpe, Max Drawdown などを出力します。

---

### Python API の簡単な利用例

（1）DuckDB 接続の作成（schema.init_schema を利用）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

（2）J-Quants からデータ取得して保存
```python
from kabusys.data import jquants_client
records = jquants_client.fetch_daily_quotes()
saved = jquants_client.save_daily_quotes(conn, records)
```

（3）特徴量ビルド（features テーブル作成）
```python
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, target_date=date(2024, 1, 31))
```

（4）シグナル生成
```python
from kabusys.strategy import generate_signals
n = generate_signals(conn, target_date=date(2024, 1, 31))
```

（5）ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection
results = run_news_collection(conn, sources=None, known_codes={'7203','6758'})
```

（6）バックテスト関数呼び出し
```python
from kabusys.backtest.engine import run_backtest
from datetime import date
result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
# result.history, result.trades, result.metrics を参照
```

---

## .env 自動読み込み

- プロジェクトルート（.git または pyproject.toml のある場所）を起点に `.env` → `.env.local` の順で自動読み込みします。
- OS 環境変数が優先で、`.env.local` は `.env` 上書き（ただし OS 環境変数は保護されます）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 重要な DB テーブル（使用箇所の概略）

バックテストや信号生成が利用する代表的なテーブル：
- prices_daily, raw_prices
- raw_financials, features, ai_scores
- signals, positions
- market_regime, market_calendar
- stocks
- raw_news, news_symbols

（schema の init 関数でこれらを作成する想定です。バックテストや signal 生成には必要テーブル・整合したデータが事前に存在することが前提となります）

---

## ディレクトリ構成（ソースの主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
  - execution/ (発注・execution 層)
  - monitoring/ (監視用)
  - backtest/
    - engine.py
    - simulator.py
    - metrics.py
    - clock.py
    - run.py (CLI)
  - data/
    - jquants_client.py
    - news_collector.py
    - (schema.py など)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - strategy/
    - feature_engineering.py
    - signal_generator.py
    - __init__.py

---

## 開発上の注意点 / よくある質問

- Python バージョン: 型ヒントや union 型シンタックスから Python >= 3.10 を推奨します。
- Look-ahead バイアス対策: 各処理（ファクター計算 / シグナル生成 / 保存）は target_date 時点以前のデータのみを使うよう設計されています。ETL・データ収集の際にも fetched_at や取得日の扱いに注意してください。
- レート制限: J-Quants クライアントは API レート制限（120 req/min）に合わせた RateLimiter とリトライを実装しています。
- 自動 .env 読み込みはテスト時に影響する場合があるため、テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を活用してください。

---

## 貢献 / 問い合わせ

バグ報告や改善提案は Issues を立ててください。プルリクエスト歓迎です。

---

README に不足している実行用スクリプトや schema 初期化スクリプトがある場合は、プロジェクト内の `kabusys.data.schema`（init_schema）や、requirements.txt を確認してそれらを用意してください。