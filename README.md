# KabuSys

日本株向けの自動売買システム（研究・データプラットフォーム・戦略・バックテストを含む）  
このリポジトリは、データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、約定シミュレーション／バックテストの機能を持つモジュール群で構成されています。設計上の重点は以下の通りです：冪等性（ON CONFLICT）、ルックアヘッドバイアス回避、外部 API への過度な依存の回避、テスト容易性。

主な設計方針や注意点
- DuckDB をデータストアとして利用（schema.init_schema による初期化）
- J-Quants API 呼び出しは rate limit と retry を考慮
- 研究（research）コードと実運用（strategy / execution）は疎結合
- ETL / 保存処理は冪等に実装（ON CONFLICT 等）
- ローカル .env / 環境変数で設定管理

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（jquants_client）
    - 株価日足、財務データ、JPX カレンダーの取得（ページネーション／自動トークンリフレッシュ／リトライ）
    - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）
- ETL パイプライン（data.pipeline）
  - 差分更新（最終取得日ベース）、バックフィル、品質チェックフック
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、raw_news への冪等保存、銘柄抽出と紐付け
- スキーマ管理（data.schema）
  - DuckDB スキーマの定義・初期化（raw / processed / feature / execution 層）
- 統計ユーティリティ（data.stats）
  - Z スコア正規化など（research と共有）
- 研究用ファクター計算（research.factor_research）
  - Momentum、Volatility、Value 等のファクターを prices_daily/raw_financials から算出
- 特徴量作成（strategy.feature_engineering）
  - 研究で作成した raw factor の正規化、ユニバースフィルタ適用、features テーブルへの upsert
- シグナル生成（strategy.signal_generator）
  - features + ai_scores を統合して final_score を計算、BUY/SELL シグナルを signals に書き込む
- バックテストフレームワーク（backtest）
  - PortfolioSimulator（約定・手数料・スリッページモデル）、run_backtest による日次シミュレーション、評価指標計算
  - CLI エントリポイント: python -m kabusys.backtest.run
- 実行／監視用のプレースホルダ（execution / monitoring パッケージ）

---

## 前提 / 必要条件

- Python 3.10+
- 必要な Python パッケージ（最低限）:
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API / RSS）

例（最小インストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（プロジェクト化する場合は requirements.txt を用意して pip install -r で管理してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <this-repo-url>
   cd <repo-dir>
   ```

2. 仮想環境と依存ライブラリのインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   ```

3. 環境変数（.env）の準備  
   プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（自動読込を無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   重要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu API のパスワード（実行環境で必要な場合）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必要に応じて）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

   例（.env の一部）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - コマンドライン（Python ワンライナー）
     ```bash
     python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
     ```
   - またはバックテスト CLI を実行すると内部で init_schema を呼びます（--db に指定）。

---

## 使い方（よく使う操作）

ここでは代表的な操作例を示します。すべて Python スクリプト内または REPL から実行できます。

- DB 接続（DuckDB）の初期化 / 接続:
```python
from kabusys.data.schema import init_schema, get_connection
# 初回: スキーマ作成
conn = init_schema("data/kabusys.duckdb")
# 既存 DB への接続（スキーマ初期化しない）
# conn = get_connection("data/kabusys.duckdb")
```

- J-Quants から株価を差分取得して保存（ETL）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
# id_token を自前で取得して注入することも可能（テスト用）
result = run_prices_etl(conn, target_date=date.today())
print(result.prices_fetched, result.prices_saved)
```

- RSS ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
# known_codes を渡すと記事中の銘柄抽出と news_symbols 登録を試みる
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)
```

- 特徴量の構築（features テーブルへの書き込み）
```python
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブルへの書き込み）
```python
from datetime import date
from kabusys.strategy import generate_signals
n = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
print(f"signals generated: {n}")
```

- バックテスト（CLI）
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --slippage 0.001 \
  --commission 0.00055 \
  --max-position-pct 0.20 \
  --db data/kabusys.duckdb
```

- バックテスト（プログラムから）
```python
from datetime import date
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
print(result.metrics)
```

---

## よく使う API（主要関数）

- data.schema.init_schema(db_path)
  - DuckDB スキーマを作成して接続を返す

- data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - save_daily_quotes(conn, records)
  - fetch_financial_statements(...)
  - save_financial_statements(conn, records)
  - fetch_market_calendar(...)
  - save_market_calendar(conn, records)

- data.pipeline.run_prices_etl(conn, target_date, ...)
  - 差分 ETL を実行して結果を ETLResult で返す

- data.news_collector.run_news_collection(conn, sources, known_codes)
  - RSS 収集から raw_news / news_symbols まで一括で実行

- research.calc_momentum / calc_volatility / calc_value
  - ファクター計算（prices_daily / raw_financials を参照）

- strategy.build_features(conn, target_date)
  - features テーブルへ書き込み

- strategy.generate_signals(conn, target_date, threshold=0.6, weights=None)
  - signals テーブルへ書き込み（BUY/SELL）

- backtest.run_backtest(conn, start_date, end_date, initial_cash=..., ...)
  - バックテストの実行（戻り値: BacktestResult）

---

## ディレクトリ構成（概要）

（ルートは src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数 / 設定管理（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（フェッチ／保存）
    - news_collector.py       — RSS 収集・前処理・DB 保存
    - pipeline.py             — ETL 差分パイプライン
    - schema.py               — DuckDB スキーマ定義 / init_schema
    - stats.py                — 統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py      — Momentum/Volatility/Value 計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ等
  - strategy/
    - __init__.py
    - feature_engineering.py  — raw factor を正規化して features テーブルへ
    - signal_generator.py     — final_score 計算・BUY/SELL シグナル生成
  - backtest/
    - __init__.py
    - engine.py               — run_backtest（全体ループ）
    - simulator.py            — PortfolioSimulator（約定ロジック）
    - metrics.py              — バックテスト評価指標計算
    - clock.py                — SimulatedClock（将来拡張用）
    - run.py                  — CLI エントリポイント (@ module)
  - execution/                — 発注／ステータス管理（プレースホルダ）
    - __init__.py
  - monitoring/               — 監視・通知（プレースホルダ）
    - __init__.py

---

## 設定（環境変数の詳細）

主な環境変数と意味（config.py を参照）：

- JQUANTS_REFRESH_TOKEN (必須)：J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須 for kabu 使用時)：kabu API のパスワード
- KABU_API_BASE_URL：kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID：通知用
- DUCKDB_PATH：DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite
- KABUSYS_ENV：development, paper_trading, live（デフォルト development）
- LOG_LEVEL：ログレベル（INFO デフォルト）
- KABUSYS_DISABLE_AUTO_ENV_LOAD：1 を設定すると自動で .env を読み込まない

config.Settings はプロパティとして上記を提供しています（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## 開発・貢献

- コードはモジュール毎に単体でテストしやすい設計（外部接続は注入可能）
- 新しい ETL/フェッチ処理を追加する場合は data.schema のスキーマと整合性を保ってください
- ローカルでのテストは in-memory DuckDB（init_schema(":memory:")）を利用可能

---

## 注意事項 / 運用上のポイント

- J-Quants API のレート制限（120 req/min）やエラーハンドリングを組み込んでいますが、運用時にさらに制御が必要な場合があります。
- production（live）環境では KABUSYS_ENV を `live` に設定し、発注モジュールの安全確認を行ってください。
- signals → execution → orders → trades のフローは DB を介して分離されています。実運用で発注する場合は execution 層の実装と安全チェックが必須です。
- DuckDB ファイルは定期バックアップを推奨します（データ量に応じたスナップショット戦略を検討してください）。

---

README はここまでです。必要であれば以下の点を追記できます：
- 具体的な .env.example（テンプレート）
- CI / テスト実行方法
- より詳しい設計ドキュメント（StrategyModel.md / DataPlatform.md の要約）