# KabuSys

日本株向けの自動売買基盤ライブラリ（研究・データ基盤・戦略・バックテスト・擬似実行を含む）

現在のバージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのライブラリ群です。主な目的は以下です。

- J-Quants API からの市場データ取得・保存（ETL）
- DuckDB 上に構築されたデータスキーマと品質管理
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 特徴量エンジニアリングとシグナル生成（BUY / SELL）
- バックテスト用シミュレータ（擬似約定、ポートフォリオ管理、メトリクス）
- ニュース（RSS）収集と記事→銘柄紐付け
- 実運用向けの発注／実行レイヤーの基礎（スキーマ・テーブル定義）

設計方針として、ルックアヘッドバイアス回避・冪等性・テスト容易性・ネットワーク／SSRF対策等を重視しています。

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（レート制御、リトライ、トークンリフレッシュ）
  - raw_prices / raw_financials / market_calendar の保存関数
- ETL パイプライン（差分更新・品質チェック）
- DuckDB スキーマ初期化（init_schema）
- 研究モジュール
  - ファクター計算: momentum / volatility / value
  - 将来リターン計算・IC（Spearman）・統計サマリー
- 特徴量エンジニアリング（build_features）
- シグナル生成（generate_signals）
  - ファクター統合、AI スコア統合、Bear レジーム判定、BUY/SELL 生成
- バックテスト
  - ポートフォリオシミュレータ（スリッページ／手数料対応）
  - 日次ループによるシミュレーション（run_backtest）
  - メトリクス計算（CAGR, Sharpe, Max Drawdown 等）
  - CLI エントリポイント（kabusys.backtest.run）
- ニュース収集（RSS）と記事保存、銘柄抽出（SSRF対策・gzip制限・トラッキング除去）
- 環境変数管理（.env 自動読み込み機能を含む）

---

## 要件（推奨）

- Python 3.10 以上（型ヒントに PEP 604 の `X | Y` を使用）
- 主要外部ライブラリ（一例）
  - duckdb
  - defusedxml

依存はプロジェクトの requirements.txt があればそちらを使用してください。ない場合は最低限次をインストールしてください:

pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン／取得

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存インストール
   - 可能なら requirements.txt を使う:
     - pip install -r requirements.txt
   - 最低限:
     - pip install duckdb defusedxml

4. パッケージを編集可能インストール（開発時）
   - pip install -e .

5. DuckDB スキーマ初期化
   - Python から:
     - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   - これにより必要なテーブル群が作成されます（":memory:" も可）。

6. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（kabusys.config 参照）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（Settings を参照）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注系を使う場合）
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（デフォルトあり）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/...
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

---

## 使い方（代表例）

### 1) DB スキーマ初期化（再掲）
Python から:
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

### 2) ETL の実行（株価・財務・カレンダー取得）
ETL モジュールの関数を呼び出して差分取得を行えます（例は概念）:

from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_news_collection

conn = init_schema('data/kabusys.duckdb')
result = run_prices_etl(conn, target_date=date.today())
# run_financials_etl なども同様に利用可能

（注: pipeline モジュールは差分取得ロジック・品質チェックを提供します）

### 3) 特徴量生成
DuckDB 接続を渡して日次の特徴量を作成します:

from kabusys.data.schema import init_schema
from kabusys.strategy import build_features
from datetime import date

conn = init_schema('data/kabusys.duckdb')
count = build_features(conn, target_date=date(2024, 1, 15))
print(f"features upserted: {count}")

### 4) シグナル生成
features / ai_scores / positions を参照して signals を作成します:

from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema('data/kabusys.duckdb')
n = generate_signals(conn, target_date=date(2024, 1, 15))
print(f"signals generated: {n}")

### 5) バックテスト（CLI）
パッケージに付属の CLI でバックテストを実行できます:

python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2024-12-31 \
  --cash 10000000 --db data/kabusys.duckdb

出力に CAGR、Sharpe、Max Drawdown、勝率、ペイオフレシオ等が表示されます。

### 6) ニュース収集（RSS）
RSS フィードを取得して raw_news / news_symbols に保存できます:

from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema('data/kabusys.duckdb')
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
print(results)

---

## 開発メモ / 注意点

- 環境変数の自動読み込み
  - モジュール kabusys.config はプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先、.env.local は上書き）。
  - テスト時や明示的に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 冪等性
  - データ保存は可能な限り ON CONFLICT / DO UPDATE / DO NOTHING を使って冪等に設計されています。

- ルックアヘッドバイアス対策
  - 特徴量／シグナル生成では target_date 時点までの情報のみ参照するよう設計されています。
  - J-Quants 取得時には fetched_at を記録し、データがいつ利用可能になったかを追跡できます。

- セキュリティ
  - RSS 収集は SSRF 防止、gzip サイズ制限、XML パースに defusedxml を使用する等の対策があります。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - pipeline.py
  - schema.py
  - stats.py
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
  - clock.py
  - run.py
- execution/
  - __init__.py
- monitoring/  (モニタリング関係のコード（今回の抜粋では実装無し））

上記は主要モジュールの抜粋です。個別の実装は各ファイルの docstring / 関数注釈に詳細が記載されています。

---

## よくある利用フロー（例）

1. init_schema() で DB を作成
2. run_prices_etl() などでデータを取得・保存
3. build_features() で特徴量テーブルを更新
4. generate_signals() で当日シグナル生成
5. run_backtest() で戦略の履歴検証（バックテスト）
6. 実運用では signals → execution 層でオーダー送信（実装に依存）

---

## 補足

- API キーや機密情報は .env に保存し、Git 管理下には置かないでください。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に置かれます。サイズによってはバックアップ／スナップショット運用を検討してください。
- 追加の機能や詳細な運用手順（StrategyModel.md / DataPlatform.md / BacktestFramework.md 等の設計文書）がプロジェクトに付属している前提です。実装やパラメータ調整はこれらのドキュメントに従ってください。

---

必要であれば、README にサンプル .env.example や具体的なコマンド一覧（ETL / バックテスト / ローカルデバッグ用）を追記します。どの使用例を詳しく載せれば良いか教えてください。