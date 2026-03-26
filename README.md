# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。データ取得・ファクター計算・シグナル生成・ポートフォリオ構築・バックテストまでを含むモジュール群を提供します。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要ユースケース）
- 環境変数（.env）/設定
- ディレクトリ構成（主要ファイルと責務）
- 開発・寄稿に関する注意

---

## プロジェクト概要

KabuSys は日本株を対象とした研究〜運用のためのモジュール群です。設計上の特徴は以下のとおりです。

- DuckDB を用いたオンプレ／ローカル DB をデータ層に想定
- J-Quants API からのデータ取得（価格・財務・市場カレンダー等）をサポート
- 研究（factor 計算 / exploration）と本番（signal → execution / monitoring）を分離
- バックテストフレームワークを同梱（スリッページ・手数料モデル付き）
- ニュース収集（RSS）モジュールで raw_news 保存と銘柄紐付けを実装
- 環境変数 / .env ファイルの自動読み込み機能あり（配布後も安全に動作するよう設計）

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants クライアント（fetch/save）
  - RSS ニュース収集（fetch_rss / save_raw_news / run_news_collection）
- 研究（research）
  - ファクター計算: momentum, volatility, value
  - 特徴量探索: forward returns, IC, summary
  - Z スコア正規化ユーティリティ連携
- 戦略（strategy）
  - features ビルド（build_features）
  - シグナル生成（generate_signals）: ファクター＋AIスコア統合、BUY/SELL の判定
- ポートフォリオ構築（portfolio）
  - 候補選定（select_candidates）
  - 重み計算（等配分 / スコア加重）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（calc_position_sizes）: risk_based / equal / score
- バックテスト（backtest）
  - エンジン（run_backtest）: DB からデータをコピーしてインメモリで実行
  - シミュレータ（PortfolioSimulator）：擬似約定・履歴管理
  - メトリクス計算（CAGR, Sharpe, MaxDD, Win Rate, Payoff など）
  - CLI 実行用エントリポイント（python -m kabusys.backtest.run）
- 実運用支援
  - 設定管理モジュール（kabusys.config.Settings）
  - Slack 通知等のための設定キー（SLACK_*）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈のユニオン演算子等を用いているため）
- DuckDB と defusedxml 等の依存ライブラリ

1. リポジトリをクローン / ソース配置
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要なパッケージをインストール
   - 最小例:
     - pip install duckdb defusedxml
   - もし pyproject.toml / requirements.txt があればそれに従ってインストールしてください。
4. パッケージを開発モードでインストール（任意）
   - pip install -e .

注意: DuckDB を使用するため、DuckDB の Python パッケージをインストールしてください。

---

## 環境変数（.env） / 設定

kabusys.config.Settings を通じて環境変数を参照します。プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（必須は README 内で明示）:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須) — kabu API のパスワード
  - KABU_API_BASE_URL — API ベース URL（デフォルト http://localhost:18080/kabusapi）
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- 実行設定
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト development）
  - LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト INFO）

例 (.env.example):
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

Settings を使う例:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

---

## 使い方（主要ユースケース）

1) バックテスト（CLI）

DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar, stocks など）が用意されていることを前提に CLI で実行:

```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2024-12-31 \
  --cash 10000000 --db path/to/kabusys.duckdb
```

主なオプション:
- --start / --end: バックテスト期間
- --cash: 初期資金
- --slippage / --commission: スリッページ / 手数料率
- --allocation-method: equal | score | risk_based
- --max-positions, --lot-size, など多数 (run.py のヘルプ参照)

2) バックテストをプログラムから呼ぶ

```python
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest
from datetime import date

conn = init_schema("path/to/kabusys.duckdb")
try:
    result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
finally:
    conn.close()

print(result.metrics)
```

3) 特徴量の構築（features テーブルへ書き込む）

build_features を呼び出すには DuckDB 接続（kabusys.data.schema.init_schema で作成）を渡します:

```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from datetime import date
conn = init_schema("path/to/kabusys.duckdb")
count = build_features(conn, target_date=date(2024,1,31))
print(f"upserted {count} features")
```

4) シグナル生成（generate_signals）

features / ai_scores / positions テーブルを参照して signals テーブルへ出力します:

```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("path/to/kabusys.duckdb")
n = generate_signals(conn, target_date=date(2024,1,31))
print(f"generated {n} signals")
```

5) J-Quants データ取得と保存

J-Quants クライアントを使ってデータを取得し DuckDB に保存できます。save_* 関数は冪等（ON CONFLICT）です。

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("path/to/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
save_daily_quotes(conn, records)
```

6) ニュース収集

RSS を収集して raw_news / news_symbols に保存します。

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
```

---

## ディレクトリ構成（主要モジュールと説明）

（パッケージルート: src/kabusys/）

- __init__.py
  - パッケージエントリ（__version__ 等）
- config.py
  - 環境変数読み込み / Settings クラス（自動 .env 読み込みロジック含む）
- data/
  - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存ユーティリティ）
  - news_collector.py — RSS 取得と raw_news 保存、銘柄抽出・紐付け
  - …（schema / calendar_management 等、README で参照されるがここに含まれる想定）
- research/
  - factor_research.py — momentum / volatility / value の計算
  - feature_exploration.py — forward returns, IC, factor summary
- strategy/
  - feature_engineering.py — research のファクターを正規化して features テーブルへ
  - signal_generator.py — final_score 計算、BUY/SELL 判定、signals への書き込み
- portfolio/
  - portfolio_builder.py — 候補選定・配列のソート
  - position_sizing.py — 株数算出（risk_based / equal / score）
  - risk_adjustment.py — セクターキャップ / レジーム乗数
- backtest/
  - engine.py — run_backtest（DB コピー、ループ、発注・評価）
  - simulator.py — PortfolioSimulator（擬似約定、履歴記録）
  - metrics.py — バックテスト評価指標計算
  - run.py — CLI エントリポイント
- research/、monitoring/、execution/ 等のサブパッケージが存在し、各々の責務を分離

（ファイル間で DuckDB 接続を受け渡す設計になっており、DB スキーマ初期化は kabusys.data.schema.init_schema を利用する想定です。）

---

## 開発上の注意・設計上のポイント

- データ保存関数は冪等（ON CONFLICT）で実装しているため再実行が安全です。
- J-Quants クライアントはレート制限（120 req/min）に合わせた内部 RateLimiter とリトライロジックを備えています。401 エラー時のトークン自動リフレッシュも実装済みです。
- news_collector は SSRF 対策・gzip サイズ検査・XML ディフェンスなど複数の安全対策を施しています。
- バックテストは本番 DB を直接汚染しないよう、データをインメモリ DuckDB にコピーして実行します。
- 設定読み込みは .env（→ .env.local）を自動読み込みしますが、OS 環境変数が常に優先されます。テスト時などで自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってください。

---

必要に応じて README のサンプルやチュートリアル（データの初期投入・schema の作成・実運用の runbook 等）を追加できます。追加してほしいセクション（例: schema 定義、依存パッケージの完全リスト、例の DB 初期化手順）があれば教えてください。