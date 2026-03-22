# KabuSys

KabuSys は日本株向けの自動売買 / 研究プラットフォームです。  
DuckDB をデータ層に用い、J-Quants や RSS などからデータを収集・加工し、特徴量生成、シグナル生成、バックテスト、ニュース収集などの機能を備えます。

主な設計方針：
- ルックアヘッドバイアスを避ける（取得時刻 / fetched_at の記録、target_date ベースの計算）
- DuckDB によるローカル一貫データ管理（冪等保存・トランザクション）
- 研究（research）と本番（execution）を分離
- エラー耐性・リトライ・レート制御・SSRF 等のセキュリティ考慮

バージョン: 0.1.0

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足 / 財務データ / マーケットカレンダー）
  - RSS ベースのニュース収集（SSRF対策・トラッキング除去）
  - DuckDB スキーマの初期化・冪等保存（ON CONFLICT を使用）
- データ ETL パイプライン
  - 差分更新・バックフィル・品質チェックの仕組み（pipeline モジュール）
- 研究（research）
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン計算・IC（Spearman）・ファクター統計サマリ
  - Z スコア正規化ユーティリティ
- 戦略（strategy）
  - 特徴量作成（feature_engineering.build_features）
  - シグナル生成（signal_generator.generate_signals）
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）
    - Bear レジーム抑制、BUY/SELL の判定、signals テーブルへの書き込み
- バックテスト（backtest）
  - PortfolioSimulator（擬似約定、スリッページ・手数料モデル）
  - run_backtest（本番 DB をインメモリへコピーして日次ループをシミュレート）
  - メトリクス計算（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- 実行層・監視（execution / monitoring）
  - 発注・約定・ポジションのためのスキーマ（orders / trades / positions 等）
  - Slack 通知用設定（設定値は environment 経由）

---

## セットアップ

前提
- Python 3.10 以上（typing の構文で | を使用）
- pip が利用可能
- 推奨パッケージ（最低限）
  - duckdb
  - defusedxml

例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabu ステーション API のパスワード（execution 層で使用）
- SLACK_BOT_TOKEN : Slack Bot トークン（通知用）
- SLACK_CHANNEL_ID : Slack チャンネル ID

オプション
- KABUSYS_ENV : 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL : ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env の自動読み込みを無効化

.env の自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動で読み込みます。
- テスト等で自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

DB 初期化（DuckDB スキーマ作成）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ DB
conn.close()
```

必要な Python モジュールがプロジェクトに含まれていない場合は上記のように pip でインストールしてください。

---

## 使い方（代表的なワークフロー）

1. DuckDB の初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2. データ収集（手動の例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.config import settings
# 例: 当日までの差分を取得
records = fetch_daily_quotes(date_from=None, date_to=None)  # 引数を適宜指定
n = save_daily_quotes(conn, records)
```

3. ETL パイプライン（差分更新・バックフィル）
pipeline モジュールには run_prices_etl 等の関数があります。簡単な呼び出し例：
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
# target_date: 取得/処理の終了日（通常は当日）
fetched, saved = run_prices_etl(conn, target_date=date.today())
```
（pipeline は品質チェックやバックフィルを考慮して差分取得を行います）

4. 特徴量作成
```python
from datetime import date
from kabusys.strategy import build_features
cnt = build_features(conn, target_date=date.today())
```

5. シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
generated = generate_signals(conn, target_date=date.today())
```

6. バックテスト（CLI）
`kabusys.backtest.run` の CLI を使ってバックテストを実行できます。バックテストは本番 DB から必要データをインメモリへコピーして実行します。

例:
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --slippage 0.001 \
  --commission 0.00055 \
  --max-position-pct 0.20 \
  --db data/kabusys.duckdb
```

実行後、CAGR や Sharpe、Max Drawdown、勝率などが標準出力に表示されます。

7. ニュース収集（RSS）
news_collector モジュールで RSS を取得して raw_news / news_symbols に保存できます。既定の RSS ソースは DEFAULT_RSS_SOURCES に定義されています。
```python
from kabusys.data.news_collector import run_news_collection
results = run_news_collection(conn, known_codes={"7203", "6758", ...})
```

---

## 重要な API / モジュール一覧（抜粋）

- kabusys.config.settings
  - 環境変数アクセス（jquants_refresh_token / kabu_api_password / slack_bot_token など）
- kabusys.data.schema
  - init_schema(db_path) : DuckDB のスキーマ初期化
  - get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.pipeline
  - ETL の差分更新関数（run_prices_etl 等）
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic 等
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)
- kabusys.backtest
  - run_backtest(conn, start_date, end_date, ...)
  - CLI: python -m kabusys.backtest.run
- kabusys.data.news_collector
  - fetch_rss / save_raw_news / run_news_collection

---

## 開発者向けヒント

- テストで .env 自動読み込みを無効にする:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定
- settings から設定を取得:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```
- ログレベルは LOG_LEVEL 環境変数で制御（INFO/DEBUG 等）
- DuckDB は ":memory:" を渡すことでインメモリ DB を作成できます（テスト用途に便利）
- jquants_client はリトライ・トークン自動リフレッシュ・レート制御を実装しています。テストでは get_id_token や _urlopen 等をモックすることで外部依存を切り離せます。

---

## ディレクトリ構成（主要ファイル）

概観（src/kabusys/*）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - backtest/
    - __init__.py
    - engine.py
    - simulator.py
    - metrics.py
    - run.py
    - clock.py
  - execution/               (発注・監視ロジック用のプレースホルダ)
    - __init__.py
  - monitoring/              (監視関連モジュール: sqlite 等の格納想定)
    - (未記載ファイルがあればここ)
  - その他: pipeline / ETL / テスト用ユーティリティなど

各モジュールは README 内の「機能一覧」で述べた役割に対応しています。詳細は各ソースコードの docstring を参照してください。

---

## ライセンス / 注意事項

- 本プロジェクトは研究用途・実運用用途での利用を想定しています。実際に資金を投入する場合は十分な検証とリスク管理を行ってください。
- API キーやシークレットは必ず安全に管理し、リポジトリに直接コミットしないでください。
- J-Quants や外部 API の利用規約・レート制限に従ってください。

---

この README はコードベースから主要な使い方と設計意図を抜粋した概要です。細かい使い方や追加オプションは各モジュールの docstring（ソース内コメント）を参照してください。必要であれば、導入手順をさらに詳細化した手順書やサンプルスクリプトを用意します。