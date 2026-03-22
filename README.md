# KabuSys

日本株自動売買プラットフォーム（ライブラリ）  
このリポジトリは、データ収集・ETL・特徴量生成・シグナル生成・バックテスト・ニュース収集など一連のワークフローを含む日本株向け自動売買システムのコア実装です。

---

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API からのデータ取得 / DuckDB への永続化（idempotent 保存）
- ETL パイプライン（差分取得、品質チェック）
- 研究用ファクター計算・特徴量生成（ルックアヘッドを排除）
- シグナル生成（複数コンポーネントスコアの統合と売買ルール）
- バックテストフレームワーク（擬似約定・ポートフォリオ管理・評価指標）
- ニュース収集と銘柄紐付け（RSS、SSRF 対策、記事正規化）

設計上のポイント:
- 各種保存は冪等（ON CONFLICT / DO UPDATE / DO NOTHING）を意識
- ルックアヘッドバイアスを避けるため、target_date 時点の情報のみを使用
- API 呼び出しに対するレート制御、リトライ、トークン自動更新を実装
- 研究モジュールは発注・実行層へ依存しない（安全な解析）

---

## 主な機能一覧

- data.jquants_client: J-Quants API クライアント（レート制限、リトライ、token refresh、DuckDB 保存ユーティリティ）
- data.schema: DuckDB スキーマ定義 / 初期化
- data.pipeline: 差分 ETL（prices / financials / market_calendar）とヘルパー
- data.news_collector: RSS 取得・記事正規化・raw_news 保存・銘柄抽出
- data.stats: Z スコア正規化など統計ユーティリティ
- research.factor_research: momentum / volatility / value ファクター計算
- research.feature_exploration: 将来リターン計算、IC、ファクター統計
- strategy.feature_engineering: ファクター正規化・features テーブル更新
- strategy.signal_generator: final_score 計算、BUY/SELL シグナル生成（冪等）
- backtest.engine: バックテスト全体ループ、実データのコピー -> インメモリでシミュレーション
- backtest.simulator: 擬似約定・ポートフォリオ管理（スリッページ・手数料を考慮）
- backtest.metrics: バックテスト評価指標（CAGR, Sharpe, MaxDD, Win rate...）

---

## 前提条件

- Python 3.9+
- DuckDB
- defusedxml
- （ネットワーク/API を利用する場合）インターネット接続と J-Quants API のリフレッシュトークン

推奨インストールパッケージ（例）:
- duckdb
- defusedxml

例:
pip install duckdb defusedxml

（プロジェクトに requirements.txt / pyproject.toml がある場合はそれを利用してください）

---

## セットアップ手順

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml

3. データベーススキーマ初期化
   Python REPL やスクリプトで:
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()

   - メモリ DB を使う場合: init_schema(":memory:")

4. 環境変数設定（.env ファイルをプロジェクトルートに置くと自動で読み込まれます）
   重要なキー:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (省略可、デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (省略可、デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO

   自動ロードを無効化したい場合:
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例 .env（参考）
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要ワークフロー）

以下は代表的な操作例です。

- DB 初期化（既出）
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- J-Quants からデータ取得・保存
  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()
  records = jq.fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)

- ETL（株価）差分取得（pipeline のヘルパーを利用）
  from kabusys.data.pipeline import run_prices_etl
  result = run_prices_etl(conn, target_date=date.today(), id_token=None)

- 特徴量作成（features テーブルへ）
  from kabusys.strategy import build_features
  build_features(conn, target_date)

- シグナル生成（signals テーブルへ）
  from kabusys.strategy import generate_signals
  generate_signals(conn, target_date)

- ニュース収集と銘柄紐付け
  from kabusys.data.news_collector import run_news_collection
  # known_codes は有効な銘柄コードの集合（extract_stock_codes 用）
  run_news_collection(conn, sources=None, known_codes=known_codes_set)

- バックテスト実行（CLI）
  python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

  オプション:
  --cash, --slippage, --commission, --max-position-pct

- バックテストを Python API から実行
  from kabusys.backtest.engine import run_backtest
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  # result.history, result.trades, result.metrics を参照

注意:
- research モジュール（factor_research / feature_exploration）は DuckDB 上の prices_daily / raw_financials 等を読み取り、外部 API や発注は行いません（安全な研究用）。
- generate_signals / build_features は target_date 単位で日付の置換（削除→挿入）を行い冪等性を保ちます。

---

## よく使う API（抜粋）

- init_schema(db_path) -> DuckDB 接続（スキーマ初期化）
- jquants_client.get_id_token(refresh_token=None) -> id token
- jquants_client.fetch_daily_quotes(...) -> レコードリスト
- jquants_client.save_daily_quotes(conn, records) -> 保存件数
- pipeline.run_prices_etl(conn, target_date, id_token=None) -> (fetched, saved)
- strategy.build_features(conn, target_date) -> upsert 件数
- strategy.generate_signals(conn, target_date, threshold=0.6) -> シグナル総数
- backtest.run_backtest(conn, start_date, end_date, ...) -> BacktestResult

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                             — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py                    — J-Quants API クライアント + 保存
  - news_collector.py                    — RSS 取得・前処理・保存・銘柄抽出
  - pipeline.py                          — ETL パイプライン
  - schema.py                            — DuckDB スキーマ / init_schema
  - stats.py                             — zscore_normalize 等ユーティリティ
- research/
  - __init__.py
  - factor_research.py                   — momentum / volatility / value
  - feature_exploration.py               — forward returns, IC, summary
- strategy/
  - __init__.py
  - feature_engineering.py               — features 作成
  - signal_generator.py                  — final_score, BUY/SELL シグナル生成
- backtest/
  - __init__.py
  - engine.py                            — run_backtest, データコピー, ループ
  - simulator.py                         — PortfolioSimulator（約定ロジック）
  - metrics.py                           — バックテスト評価指標計算
  - run.py                               — CLI エントリポイント
  - clock.py                             — SimulatedClock（将来用）
- execution/                              — 発注 / 実行関連（空 __init__.py）
- monitoring/                             — 監視関連（置き場）
- otherモジュール...

（上記は主要ファイルの要約です。実際のファイル一覧はリポジトリを参照してください。）

---

## 運用上の注意 / 設計メモ

- 環境設定読み込み:
  - プロジェクトルート（.git または pyproject.toml を探索）にある .env / .env.local を自動で読み込みます。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- J-Quants API:
  - レート制限（120 req/min）を守るため固定間隔スロットリング実装あり
  - 408/429/5xx に対するリトライ、401 時はトークン自動更新を試みる

- News Collector:
  - SSRF 対策、リダイレクト先検査、受信サイズ上限、defusedxml による安全な XML パースを採用

- 冪等性:
  - DB 保存は可能な限り ON CONFLICT 句や INSERT ... DO NOTHING を使用して冪等性を担保

- ルックアヘッドバイアス防止:
  - feature / signal / research の各計算は target_date 時点もしくは target_date 以前のデータのみを使用

---

## 参考例: 簡単なスクリプト

特徴量作成 → シグナル生成 → バックテスト用 DB への反映（疑似例）:

from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features, generate_signals
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
target = date(2024, 1, 4)

# 特徴量作成
build_features(conn, target)

# シグナル生成
generate_signals(conn, target)

# バックテスト（期間を指定）
res = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2024,1,31))
print(res.metrics)

---

## コントリビュート / 開発

- コード規約、ユニットテスト、CI を整備することが推奨されます。
- データベース操作やネットワーク I/O 部分はモック可能な実装にしているため、単体テストが容易です（例: news_collector._urlopen をモックする等）。

---

不明点や README に追加したい利用例（例: デプロイ手順、Docker 化、監視・アラート設定など）があれば教えてください。README を用途に合わせて拡張します。