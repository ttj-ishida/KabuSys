# KabuSys

日本株向けの自動売買 / 研究プラットフォームの一部を実装した Python ライブラリ群です。  
バックテスト、特徴量計算、シグナル生成、データ収集（J-Quants / RSS）など、投資戦略開発およびオートメーションに必要な主要機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の関心事にフォーカスしたモジュール群を備えています。

- データ取得・ETL（J-Quants API / RSS ニュース）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- 特徴量生成（正規化・クリップ）と保存
- シグナル生成（ファクター＋AI スコア統合、BUY / SELL 判定）
- ポートフォリオ構築（候補選定・重みづけ・サイジング・セクター制限）
- バックテストフレームワーク（擬似約定・評価指標計算）
- ニュース収集と銘柄紐付け

設計方針は「ルックアヘッドバイアスの回避」「冪等性」「明示的かつ再現可能なデータ処理」です。

---

## 主な機能一覧

- kabusys.data
  - J-Quants API クライアント（fetch / save）
  - RSS ニュース収集・保存・銘柄抽出（SSRF/サイズ制限対策あり）
- kabusys.research
  - calc_momentum / calc_volatility / calc_value（DuckDB ベースのファクター）
  - IC / forward return / 統計サマリー
- kabusys.strategy
  - build_features(conn, target_date): features テーブル生成
  - generate_signals(conn, target_date, ...): signals テーブル生成（BUY/SELL）
- kabusys.portfolio
  - select_candidates / calc_equal_weights / calc_score_weights
  - calc_position_sizes（等金額・スコア加重・リスクベース）
  - apply_sector_cap / calc_regime_multiplier（リスク調整）
- kabusys.backtest
  - run_backtest(conn, start_date, end_date, ...): 完全なバックテスト実行
  - PortfolioSimulator, DailySnapshot, TradeRecord（擬似約定と状態管理）
  - metrics（CAGR, Sharpe, MaxDD, WinRate, Payoff 等）
- 環境設定
  - .env / .env.local 自動読み込み（プロジェクトルートを探索）
  - 必須環境変数を Settings 経由で取得

---

## 動作要件 / 前提

- Python >= 3.10
- DuckDB（Python パッケージ `duckdb`）
- defusedxml（RSS の安全な XML パースに使用）
- ネットワークアクセス（J-Quants API / RSS）

必要な Python ライブラリはプロジェクト側の requirements / pyproject に定義されている想定です。手動でインストールする最低限の例:

```
pip install duckdb defusedxml
```

（パッケージ化されている場合は `pip install -e .` 等でインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン / 作業ディレクトリに配置
2. Python 3.10+ の仮想環境を作成・有効化
3. 依存パッケージをインストール
   - 例: pip install -r requirements.txt
   - または: pip install duckdb defusedxml
4. DuckDB スキーマ初期化（例: データベースファイル作成）
   - ライブラリ内の schema 初期化関数を利用できます（例: kabusys.data.schema.init_schema）
   - 例（対話例）:
     >>> from kabusys.data.schema import init_schema
     >>> conn = init_schema("data/kabusys.duckdb")
     >>> conn.close()
5. 環境変数（または .env）を用意
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

推奨の .env（例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

必須環境変数（Settings により取得・検証されます）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意/デフォルト:
- KABUSYS_ENV (development | paper_trading | live) — default development
- LOG_LEVEL (DEBUG|INFO|...) — default INFO
- DUCKDB_PATH — default data/kabusys.duckdb
- SQLITE_PATH — default data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — set to 1 to disable .env auto load

---

## 使い方（代表的なユースケース）

以下は代表的な操作例です。すべて DuckDB 接続（kabusys.data.schema.init_schema で得る conn）を前提とします。

1) バックテスト実行（CLI）
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2024-12-31 \
  --cash 10000000 --db path/to/kabusys.duckdb
```
オプションで slippage / commission / allocation-method / lot-size 等を指定可能。

2) features 作成（1日分）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
print(f"upserted features: {n}")
conn.close()
```

3) シグナル生成（1日分）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
print(f"signals written: {count}")
conn.close()
```

4) J-Quants からデータ取得 & 保存（例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print(f"saved daily quotes: {saved}")
conn.close()
```
- 認証: JQUANTS_REFRESH_TOKEN 環境変数で指定。get_id_token() による自動リフレッシュと内部キャッシュあり。

5) ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コード抽出に使うセット（None だと抽出をスキップ）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
conn.close()
```
- RSS フェッチはスキーム検証、SSRF ガード、レスポンスサイズ制限、gzip 対応などの安全策を講じています。
- 新規記事のみ raw_news に挿入され、news_symbols に銘柄紐付けを行います。

6) バックテスト API（プログラムから呼ぶ）
```python
from datetime import date
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
print(result.metrics)
conn.close()
```

---

## 注意点 / 実装に関する補足

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。テスト時等に無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants クライアントは内部でレート制限（120 req/min）を守る実装です。大量データ取得時はページネーションの扱いに注意してください。
- generate_signals() は market_regime, features, ai_scores, positions を参照して BUY/SELL を決定します。Bear レジームでは BUY が抑制される仕様があります。
- バックテストは run_backtest が DuckDB の一時 in-memory コピーを作り、そこにデータを投入して実行します（本番 DB の signals/positions を汚染しない）。
- ニュース収集では URL 正規化 → SHA-256（先頭32文字）で記事IDを作成し冪等性を担保しています。

---

## ディレクトリ構成（主要ファイル）

（この README に含まれるコードベースに基づく抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - execution/ (空 __init__ が存在)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - backtest/
    - __init__.py
    - engine.py
    - metrics.py
    - simulator.py
    - clock.py
    - run.py
  - data/
    - jquants_client.py
    - news_collector.py
    - (schema, calendar_management 等のモジュールが別途存在する想定)
  - portfolio, strategy, research, backtest, data の各モジュールが主要ロジックを提供

---

## 探索・拡張ポイント（開発者向け）

- 単元株（lot_size）の銘柄別対応: 現状は一括 lot_size パラメータ。将来的に銘柄ごとの lot_map へ拡張可能。
- 価格欠損時のフォールバック: apply_sector_cap / position_sizing 等で price が 0 のケースに対するフォールバック（前日終値など）の導入検討。
- AI スコア統合: ai_scores テーブルからの regime_score / ai_score を使った挙動のさらなるチューニング。
- ニュースの自然言語処理（エンティティ抽出、センチメント）の追加でシグナルへの影響を強化可能。

---

## ライセンス / コントリビューション

この README はコードベースの説明用テンプレートです。実際のリポジトリでは LICENSE / CONTRIBUTING ガイドラインを参照してください。

---

必要であれば、README に以下を追加できます：
- 詳細な DB スキーマ（tables / columns）
- 開発用の docker-compose / データ初期化手順
- CI / テストの実行方法

追加希望があれば教えてください。