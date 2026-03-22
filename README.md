# KabuSys

日本株向けの自動売買・データプラットフォーム。J-Quants から市場・財務データ・カレンダーを取得して DuckDB に格納し、研究用ファクター計算、特徴量エンジニアリング、シグナル生成、バックテスト、ニュース収集などを一貫して扱うためのモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（各モジュールは target_date 時点の情報のみを使用）
- DuckDB を中心とした冪等（idempotent）で安全なデータ保存
- API 呼び出しはレート制御とリトライを実装（J-Quants クライアント）
- バックテストは本番データベースを汚さないようインメモリコピーで実行

バージョン: 0.1.0

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価・財務・市場カレンダー）
  - 差分ETL（差分取得・バックフィル・品質チェック）
  - News（RSS）取得・前処理・DB保存・銘柄抽出
- データ管理
  - DuckDB スキーマ定義と初期化（init_schema）
  - raw / processed / feature / execution 層のテーブル
- 研究 (research)
  - ファクター計算（Momentum / Volatility / Value）
  - 特徴量探索（将来リターン・IC・統計サマリー）
  - Zスコア正規化ユーティリティ
- 戦略（strategy）
  - 特徴量生成（build_features）
  - シグナル生成（generate_signals）：複数コンポーネントの重み付け合成、Bear レジーム抑制、エグジット判定（ストップロス等）
- バックテスト（backtest）
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）
  - バックテストエンジン（日次ループ、ポジション書き戻し、シグナル→約定）
  - メトリクス計算（CAGR、Sharpe、Max Drawdown、勝率、Payoff 等）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- 実行（execution）
  - 発注・約定・ポジション管理用のテーブル定義（signal_queue, orders, trades, positions 等）
- モニタリング（Slack連携等の設定想定：設定は config.Settings 経由）

---

## 要件

- Python 3.10+
- 主要依存（例）
  - duckdb
  - defusedxml
- （プロジェクトによっては追加パッケージが必要です。requirements.txt があればそれを使用してください）

例（最低限のインストール）:
```
python -m pip install "duckdb>=0.7" defusedxml
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン
```
git clone <このプロジェクトのリポジトリURL>
cd <repo>
```

2. Python 仮想環境を作成・有効化（推奨）
```
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

3. 依存パッケージをインストール
- プロジェクトに requirements.txt がある場合:
```
pip install -r requirements.txt
```
- 最低限:
```
pip install duckdb defusedxml
```

4. 環境変数 (.env) を作成
プロジェクトルートに `.env` または `.env.local` を置くことで自動読み込みされます（自動ロードはデフォルト有効）。必須のキーは Settings で参照されます。例:
```
# .env (例)
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```
- テスト等で自動ロードを無効にする場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

5. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
```
またはコマンドラインで Python を使って初期化:
```
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```
- インメモリ DB を使う場合は db_path に ":memory:" を指定できます（テスト用途）。

---

## 使い方（主要ユースケース）

以下は代表的な操作例です。各関数はモジュールから直接インポートして利用します。

1. J-Quants から株価を取得して保存（ETL の一例）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_prices_etl
from datetime import date

conn = init_schema("data/kabusys.duckdb")
# target_date は取得終了日（通常は当日）
target_date = date.today()
# run_prices_etl は (fetched_count, saved_count) を返す
fetched, saved = run_prices_etl(conn, target_date)
conn.close()
```

2. RSS ニュース収集と保存
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes を与えると記事内の4桁銘柄コード抽出→news_symbolsへ保存される
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
conn.close()
```

3. 特徴量の構築（features テーブルへ書き込み）
```python
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 31))
conn.close()
```

4. シグナル生成（features と ai_scores を参照して signals へ書き込み）
```python
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals
from datetime import date

conn = init_schema("data/kabusys.duckdb")
num_signals = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
conn.close()
```

5. バックテスト実行（CLI）
DuckDB ファイルが適切にデータを含んでいる前提で以下のように実行できます:
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```
主な引数:
- --start / --end : バックテスト期間（YYYY-MM-DD）
- --cash : 初期資金（円）
- --slippage / --commission : スリッページ率・手数料率
- --max-position-pct : 1銘柄あたりの最大比率
- --db : DuckDB ファイルパス

また、Python API としても run_backtest を呼び出せます。

6. バックテストの結果解析
run_backtest は BacktestResult を返します（history, trades, metrics）。metrics から CAGR、Sharpe、Max Drawdown 等を参照できます。

---

## 環境設定のポイント

- 必須環境変数（Settings により _require されるもの）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- デフォルト値あり:
  - KABUSYS_ENV: development | paper_trading | live（default: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（default: INFO）
  - DUCKDB_PATH, SQLITE_PATH（デフォルトは data/ 以下）
- .env 自動ロードの優先順位: OS 環境 > .env.local > .env
- 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主な構成です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（レート制御・リトライ・保存）
    - news_collector.py        # RSS 取得・前処理・保存・銘柄抽出
    - pipeline.py              # ETL パイプライン
    - schema.py                # DuckDB スキーマ定義・初期化
    - stats.py                 # Zスコア等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py       # ファクター計算（mom/vol/value）
    - feature_exploration.py   # IC/将来リターン/統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py   # features テーブル構築
    - signal_generator.py      # signals 生成ロジック
  - backtest/
    - __init__.py
    - engine.py                # バックテストエンジン（全体ループ）
    - simulator.py             # PortfolioSimulator（約定・スナップショット）
    - metrics.py               # 評価指標計算
    - run.py                   # CLI エントリポイント
    - clock.py                 # SimulatedClock（将来拡張用）
  - execution/                 # 発注・実行層（パッケージ用意）
  - monitoring/                # 監視（Slack 通知等を想定）

---

## 開発・運用上の注意

- ルックアヘッド防止: 戦略 / 研究モジュールは target_date 時点のデータのみ参照する設計です。外部から future data を渡すと意図しない結果になります。
- DuckDB スキーマは init_schema() により冪等的に作成されます。初期化時に親ディレクトリが自動生成されます。
- ETL はバックフィル（デフォルト 3 日）を行い、API の後出し修正を吸収する仕組みがあります。
- news_collector は SSRF や XML Bomb への対策を含みます（スキーム検証、ホストのプライベートIPチェック、defusedxml の使用、サイズ制限）。
- J-Quants API はレート制御（120 req/min）と自動トークンリフレッシュ、指数バックオフを実装しています。

---

## 参考：よく使う API / 関数一覧

- データベース
  - kabusys.data.schema.init_schema(db_path)
  - kabusys.data.schema.get_connection(db_path)
- ETL / データ取得
  - kabusys.data.pipeline.run_prices_etl(...)
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.save_daily_quotes(...)
- ニュース
  - kabusys.data.news_collector.fetch_rss(url, source)
  - kabusys.data.news_collector.run_news_collection(...)
- 研究 / 戦略
  - kabusys.research.calc_momentum/ calc_volatility / calc_value
  - kabusys.strategy.build_features(conn, target_date)
  - kabusys.strategy.generate_signals(conn, target_date, threshold, weights)
- バックテスト
  - kabusys.backtest.run_backtest(conn, start_date, end_date, ...)

---

必要があれば README にサンプル .env.example、詳細な API 使用例（パラメータ解説）、CI/CD のセットアップ、運用ガイド（定期 ETL スケジュール、Slack 通知の手順）などを追加できます。どの部分を詳しく書きたいか教えてください。