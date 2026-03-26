# KabuSys

日本株向けの自動売買 / 研究フレームワーク（DuckDB ベース）。  
バックテスト、特徴量計算、シグナル生成、データ収集（J-Quants / RSS）などのモジュールを備え、研究→バックテスト→実運用（別途 execution 層を実装）へつながる設計になっています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- 株価・財務データの取得と DuckDB への保存（J-Quants API 経由）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量の正規化・保存（features テーブル）
- シグナル生成（final_score に基づく BUY/SELL 判定）
- バックテストフレームワーク（擬似約定・ポートフォリオ管理・メトリクス算出）
- ニュース収集（RSS → raw_news、記事と銘柄の紐付け）
- ポートフォリオ構築ロジック（候補選定、配分、リスク調整、サイジング）

設計上のポイント:
- DuckDB をデータ層に採用（高速な分析向け）
- ルックアヘッドバイアス防止の配慮（取得時刻記録、target_date ベースの処理）
- 冪等性・トランザクション制御を重視した実装
- ネットワーク周り・RSS に対するセキュリティ考慮（SSRF 対策、XML 脆弱性対策、サイズ制限 等）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存関数、トークンリフレッシュ、レート制限、リトライ）
  - news_collector: RSS 取得・前処理・raw_news 保存・銘柄抽出
- research/
  - factor_research: momentum / volatility / value 等のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration: IC・将来リターン・統計サマリー等の研究ユーティリティ
- strategy/
  - feature_engineering.build_features: ファクターの正規化と features テーブルへの UPSERT
  - signal_generator.generate_signals: features + ai_scores を統合して BUY / SELL シグナルを作成し signals テーブルへ保存
- portfolio/
  - portfolio_builder: 候補選定・重み付け
  - position_sizing: 株数決定（risk_based / equal / score）
  - risk_adjustment: セクターキャップ・レジーム乗数
- backtest/
  - engine.run_backtest: バックテストループ（擬似約定・ポートフォリオ管理・シグナル生成呼び出し）
  - simulator.PortfolioSimulator: 擬似約定ロジック、マーク・トゥ・マーケット、トレード記録
  - metrics.calc_metrics: バックテスト評価指標（CAGR, Sharpe, MaxDD 等）
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- config:
  - 環境変数管理（.env/.env.local の自動読み込み、必須キーチェック）

---

## 要件 (推奨)

- Python 3.10+
  - (型注釈で | を使っているため 3.10 以上を想定)
- 必要なサードパーティ:
  - duckdb
  - defusedxml
- 標準ライブラリのみで動く箇所も多いですが、RSS の安全パーシングに defusedxml を使っています。

インストール例:
```bash
python -m pip install -U pip
python -m pip install duckdb defusedxml
# リポジトリを編集可能インストールする場合（プロジェクトに pyproject.toml がある想定）
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 環境を用意（venv 等推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   ```

3. 環境変数 (.env) を用意  
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（CWD ではなくファイル位置からプロジェクトルートを探索します）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必要な環境変数（サンプル）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API (実運用)
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack (通知等)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789

   # DB パス（任意の場所）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 動作環境: development | paper_trading | live
   KABUSYS_ENV=development

   # ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化  
   パッケージ内にスキーマ初期化関数（例: `kabusys.data.schema.init_schema`）があり、DuckDB ファイルを開く際に必要なテーブルを作成できる想定です（このリポジトリに schema 実装がある場合）。
   サンプル:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ作成
   conn.close()
   ```
   （schema の実装に従って prices_daily / features / signals 等のテーブルを作成してください）

---

## 使い方

以下は代表的な利用例です。

1) バックテスト（CLI）
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb \
  --allocation-method risk_based --max-positions 10 --lot-size 100
```
出力は最終的なバックテストメトリクス（CAGR, Sharpe, Max Drawdown 等）。

2) 特徴量構築（スクリプトから）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 01, 31))
print(f"upserted features: {n}")
conn.close()
```

3) シグナル生成（スクリプトから）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 01, 31))
print(f"signals written: {count}")
conn.close()
```

4) J-Quants から取得して保存（例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
token = get_id_token()  # settings に JQUANTS_REFRESH_TOKEN が必要
records = fetch_daily_quotes(date_from=..., date_to=...)
saved = save_daily_quotes(conn, records)
conn.close()
```

5) ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄抽出のための既知コードセット（例: stocks テーブルから取得）
# ここでは None を渡すと銘柄紐付けをスキップ
results = run_news_collection(conn, sources=None, known_codes=None)
print(results)
conn.close()
```

6) バックテスト API（プログラムから）
```python
from datetime import date
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
res = run_backtest(conn, start_date=date(2022,1,1), end_date=date(2022,12,31))
print(res.metrics)
conn.close()
```

---

## 環境変数の取り扱い

- パッケージ起動時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、`.env` → `.env.local` の順で自動読み込みを行います（既存の OS 環境変数は上書きされませんが `.env.local` は上書き可能）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で便利です）。

必須となる環境変数例（実運用では必ず設定する）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

（欠損すると Settings が例外を投げます）

---

## ディレクトリ構成（主要ファイル抜粋）

src/kabusys/
- __init__.py
- config.py
- data/
  - jquants_client.py
  - news_collector.py
  - (schema.py 等が存在する想定)
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
  - __init__.py
- backtest/
  - engine.py
  - simulator.py
  - metrics.py
  - run.py
  - clock.py
- execution/ (エントリポイントや API 連携層を実装する場所)
- monitoring/ (監視・アラート用モジュールを想定)

--- 

## 開発メモ / 注意点

- Python 3.10+ を推奨（型注釈の構文等）
- DuckDB のスキーマ（tables）を適切に作成してから各処理を実行してください（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_regime, stocks, market_calendar, raw_news, news_symbols 等）。
- バックテストは本番 DB（ファイル）から必要な期間のデータを抽出してインメモリで実行します（元の signals/positions を汚染しません）。
- news_collector は RSS の XML を扱うため defusedxml を使用しています。RSS の外部アクセスに対して SSRF・Gzip bomb 等の防御を実装していますが、運用時は適切なネットワークポリシーを設定してください。
- J-Quants API の制限（120 req/min）や 401 リフレッシュの挙動に注意してください（実装済み）。

---

この README はリポジトリ内の実装に基づく利用手順の概要です。より詳細な設計仕様（PortfolioConstruction.md / StrategyModel.md / DataPlatform.md / BacktestFramework.md 等）がプロジェクト内にある場合はそちらも参照してください。質問や補足があれば教えてください。