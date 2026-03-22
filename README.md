# KabuSys

日本株向けの自動売買システム用ライブラリ / フレームワーク。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集、及び擬似約定シミュレータなどを含むモジュール群で構成されています。

主な用途は研究環境でのファクター検討から、本番向けのシグナル生成・バックテストまでのワークフローをサポートすることです。

---

## 目次
- プロジェクト概要
- 機能一覧
- 動作要件
- 環境変数 (設定)
- セットアップ手順
- 使い方（主要ワークフローの例）
  - DB初期化
  - バックテスト実行（CLI）
  - 特徴量構築 / シグナル生成（プログラム呼び出し）
  - ETL（株価・財務・カレンダー）実行
  - ニュース収集ジョブ
  - 研究用ユーティリティ
- ディレクトリ構成
- 補足 / 開発メモ

---

## プロジェクト概要
KabuSys は日本株向けのアルゴリズム売買パイプラインを想定した Python パッケージです。主なコンポーネントは次の通りです。
- データ取得（J-Quants API クライアント）
- DuckDB によるスキーマ定義・保存
- ETL パイプライン（差分更新・品質チェック）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）
- シグナル生成（最終スコア算出・BUY/SELL 判定）
- バックテストエンジン（シミュレータ・評価指標）
- ニュース収集（RSS → raw_news、記事から銘柄抽出）
- 実運用のための設定管理（.env 自動読み込み等）

設計方針としては「ルックアヘッドバイアスを避ける」「DuckDB をデータレイヤに使用する」「各処理は冪等（idempotent）」を重視しています。

---

## 機能一覧
- jquants_client: J-Quants API との通信（レートリミット・自動リトライ・トークンリフレッシュ対応）
- data.schema: DuckDB のスキーマ定義と初期化（raw / processed / feature / execution 層）
- data.pipeline: 差分 ETL（prices / financials / market_calendar）と補助関数
- data.news_collector: RSS からニュース収集、記事正規化、銘柄抽出、DB 保存
- data.stats: クロスセクションの Z スコア正規化ユーティリティ
- research: ファクター計算(calc_momentum / calc_volatility / calc_value)、将来リターン、IC 計算など
- strategy:
  - feature_engineering.build_features: raw ファクターを統合して features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナルを生成
- backtest:
  - engine.run_backtest: 日次ループに基づくバックテスト（擬似約定、ポジション管理、メトリクス算出）
  - simulator.PortfolioSimulator: 約定ロジック（スリッページ・手数料モデル）
  - metrics.calc_metrics: CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio 等
  - CLI: python -m kabusys.backtest.run
- その他: 設定管理（kabusys.config）と .env 自動読み込み

---

## 動作要件（概略）
必須パッケージ（最低限）:
- Python 3.10+（コードは型注釈に Python 3.10 の構文を利用）
- duckdb
- defusedxml

ネットワークアクセス:
- J-Quants API へのアクセス（API トークンが必要）
- RSS フィード等の HTTP(S) アクセス

（実際のプロジェクトでは requirements.txt / pyproject.toml で管理してください）

---

## 環境変数 (主な設定項目)
kabusys.config.Settings が参照する主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
- KABU_API_PASSWORD：kabu ステーション API のパスワード（execution 層で使用）
- SLACK_BOT_TOKEN：Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID：通知先 Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV：環境 ("development" | "paper_trading" | "live")。デフォルト "development"
- LOG_LEVEL：ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")。デフォルト "INFO"
- DUCKDB_PATH：DuckDB のファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH：監視用 SQLite（デフォルト "data/monitoring.db"）

自動 .env 読み込み:
- プロジェクトルートにある `.env` と `.env.local` が自動でロードされます（OS 環境変数優先）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必要な環境変数が不足していると Settings のアクセス時に ValueError が発生します。

---

## セットアップ手順（開発環境）
1. リポジトリをクローンして仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject.toml / requirements.txt がある場合はそれに従ってください）

3. 開発インストール（任意）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を作成して、上記の必須変数を設定してください。
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xxxx
     SLACK_CHANNEL_ID=CHANNEL_ID

5. DuckDB スキーマ初期化（後述）

---

## DB 初期化
DuckDB のスキーマを初期化するには Python から次のように呼びます。

例:
```python
from kabusys.data.schema import init_schema

# ファイル DB を作る場合
conn = init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = init_schema(":memory:")
conn.close()
```

init_schema() はテーブル定義を冪等に適用します（既存テーブルは壊しません）。親ディレクトリが無ければ自動作成されます。

---

## 使い方（主要ワークフローの例）

### 1) バックテスト（CLI）
付属の CLI でバックテストが実行できます。必要な DuckDB ファイルは事前にデータ（prices_daily, features, ai_scores, market_regime, market_calendar 等）で埋めておく必要があります。

例:
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```

利用可能オプション:
- --start, --end: 日付 (YYYY-MM-DD)
- --cash: 初期資金（デフォルト 10,000,000）
- --slippage, --commission: スリッページ / 手数料率
- --max-position-pct: 1 銘柄あたりの最大比率（デフォルト 0.20）
- --db: DuckDB ファイルパス（必須）

### 2) 特徴量構築（feature_engineering）
DuckDB 接続と target_date を渡して features テーブルへ書き込みます。

例:
```python
import duckdb
from datetime import date
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 2, 14))
print(f"upserted {count} features")
conn.close()
```

内部で research の calc_momentum / calc_volatility / calc_value を呼び、ユニバースフィルタ・Zスコア正規化・±3 クリップ等を行います。

### 3) シグナル生成（signal_generator）
features と ai_scores、positions を参照して BUY / SELL シグナルを signals テーブルへ書き込みます。

例:
```python
from kabusys.strategy import generate_signals
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date(2024, 2, 14), threshold=0.6)
print(f"generated {n} signals")
conn.close()
```

weights を引数で指定することでファクターの重み付けを調整できます。Bear レジーム検出時は BUY を抑制します。

### 4) ETL（株価 / 財務 / カレンダー差分取得）
data.pipeline モジュールから個別 ETL ジョブを呼べます（J-Quants の id_token を注入可）。

概念:
- get_last_price_date / get_last_financial_date 等で差分範囲を決め、
- jquants_client.fetch_* → save_* を使って DuckDB へ冪等保存します。

例（概念的）:
```python
from kabusys.data.pipeline import run_prices_etl
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
conn.close()
```

（実際の run_prices_etl 関数は date_from/backfill_days 等を受け取ります）

### 5) ニュース収集
RSS ソースを使って記事を取得・保存・銘柄紐付けします。

例:
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# known_codes: 銘柄抽出に用いる有効な4桁コード集合
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
conn.close()
```

fetch_rss は SSRF 対策やレスポンス上限の保護、gzip 解凍チェックなどを備えています。保存は raw_news / news_symbols の冪等操作で行います。

### 6) 研究用ユーティリティ
research モジュールは将来リターン計算、IC（Spearman ρ）、factor_summary、rank などを提供します。DuckDB 接続を渡して prices_daily を参照して計算します。

例:
```python
from kabusys.research import calc_forward_returns, calc_ic
# conn: duckdb connection
fwd = calc_forward_returns(conn, target_date=date(2024,2,14))
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

---

## ディレクトリ構成（概要）
（src/kabusys 以下の主要ファイル・モジュールを抜粋）
- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード等）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py      — RSS ニュース取得・前処理・DB 保存
    - pipeline.py            — ETL パイプライン（差分更新等）
    - schema.py              — DuckDB スキーマ定義・初期化
    - stats.py               — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features（ファクター統合・正規化）
    - signal_generator.py    — generate_signals（最終スコア・BUY/SELL）
  - backtest/
    - __init__.py
    - engine.py              — run_backtest（バックテスト全体ループ）
    - simulator.py           — PortfolioSimulator（約定・マークトゥマーケット）
    - metrics.py             — バックテスト評価指標計算
    - run.py                 — CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py               — SimulatedClock（将来拡張用）
  - execution/               — （発注・実行ロジック用のスペース）
  - monitoring/              — （監視・アラート用）

各モジュールは可能な限り DuckDB 接続や外部トークンを引数で注入できるように設計されており、テストやモックが容易です。

---

## 補足 / 開発メモ
- 設定 (Settings) は実行時に環境変数を参照します。必須変数が未設定の場合はアクセス時に ValueError が上がります。
- .env のパースはシェル風（export KEY=val やクォート、コメント処理）に対応しています。
- J-Quants クライアントはレートリミット、401 トークンリフレッシュ、リトライ（指数バックオフ）を組み込んでいます。
- NewsCollector は SSRF や XML Bom、gzip の巨大解凍（Gzip Bomb）対策などを行っています。
- DuckDB スキーマは外部キーやインデックスを定義していますが、DuckDB のバージョンにより一部制約（ON DELETE CASCADE 等）が未サポートである旨の注記があります。
- 各データ保存関数は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING 等）に実装されています。

---

必要があれば、README に含める具体的な .env.example のテンプレートや、CI 用の実行例、詳細な API 使用例（関数ごとのサンプル）を追加で作成します。どの項目を優先して補完しますか？