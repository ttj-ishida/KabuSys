# KabuSys

日本株向けの自動売買システム用ライブラリ／ツール群です。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集、DuckDB スキーマ管理などを包含するモジュール群を提供します。

---

## 概要

KabuSys は以下のレイヤーで構成されたシステムを対象とした Python パッケージです。

- データ取得／保存（J-Quants API 経由、DuckDB 保存）
- データ品質チェック・ETL パイプライン
- 研究向けファクター計算（research）
- 特徴量構築（feature engineering）
- シグナル生成（戦略）
- バックテストフレームワーク（シミュレーション、評価指標）
- ニュース収集（RSS ベース）
- DuckDB スキーマ定義・初期化

目的は「ルックアヘッドバイアスを避けつつ、再現可能で冪等なデータ処理・シグナル生成、検証を行うこと」です。

---

## 主な機能

- J-Quants API クライアント（トークン自動リフレッシュ、レートリミット、リトライ）
- DuckDB ベースのスキーマ定義・初期化（init_schema）
- ETL（差分取得、バックフィル、品質チェック）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量正規化（Zスコア）と features テーブルへの保存（冪等）
- シグナル生成（final_score の計算、BUY/SELL の日次置換保存）
- バックテストエンジン（擬似約定、スリッページ、手数料、評価指標）
- ニュース収集（RSS 取得、前処理、銘柄抽出、DB 保存）
- 各モジュールは DB に直接発注を行わない設計（execution 層は分離）

---

## 要件

- Python 3.10 以上（型注釈に | 演算子を使用）
- DuckDB（Python パッケージ: duckdb）
- defusedxml（RSS の安全なパースに使用）
- 標準ライブラリの urllib, datetime, logging 等

必要パッケージ（例）
pip install duckdb defusedxml

プロジェクトをパッケージとして使う場合は setuptools/pip のセットアップを用意してください（このリポジトリはソース配置想定）。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を用意
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用）

3. DuckDB スキーマを初期化（デフォルトファイルパスは data/kabusys.duckdb）
   - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（設定は後述）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途）。

---

## 環境変数（必須・主要）

以下は Settings クラスが参照する主要な環境変数です（不足時は ValueError を送出するものがあります）。

必須
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
- KABU_API_PASSWORD：kabuステーション API パスワード
- SLACK_BOT_TOKEN：Slack 通知用ボットトークン
- SLACK_CHANNEL_ID：Slack チャンネル ID

任意（デフォルトあり）
- KABU_API_BASE_URL：kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV：実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL：ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD：1 を設定すると自動で .env を読み込まない

サンプル .env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO

（実運用時は機密情報を平文で置かない運用方針を検討してください）

---

## 使い方（例）

以下は主要コンポーネントの使い方・実行例です。

1) DuckDB スキーマの初期化
```bash
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```

2) J-Quants からデータ取得（ETL の一部）
- ETL パイプラインから差分取得を行うために data.pipeline モジュールの関数群を使用します（run_prices_etl 等）。
- 例（スクリプト内で）:
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl

conn = init_schema('data/kabusys.duckdb')
target = date.today()
# run_prices_etl の呼び出しで差分取得・保存を実行（id_token 注入可能）
fetched, saved = run_prices_etl(conn, target)
```
（run_prices_etl は差分算出 / backfill を行い、jquants_client を経由して保存します）

3) ニュース収集
- RSS フィードから raw_news を収集して保存します。
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema('data/kabusys.duckdb')
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
```

4) 特徴量作成（feature engineering）
- DuckDB 接続と基準日を渡して features を構築します。
```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema('data/kabusys.duckdb')
count = build_features(conn, date(2024, 1, 31))
```

5) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema('data/kabusys.duckdb')
n = generate_signals(conn, date(2024, 1, 31), threshold=0.6)
```

6) バックテスト（CLI）
- パッケージにはバックテスト実行用のエントリポイントがあります。
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```
- または Python API 経由:
```python
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema('data/kabusys.duckdb')
res = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
print(res.metrics)
```

7) テスト用ヒント
- ローカルテスト等で自動 .env 読み込みを無効にしたいとき:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## モジュール概要 / ディレクトリ構成

主要なソースは src/kabusys 以下にあります。主なファイル・モジュールの一覧と役割は次の通りです。

- kabusys/
  - __init__.py
  - config.py — 環境変数読み込みと Settings 定義（自動 .env ロード機能）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS ニュース収集と保存
    - pipeline.py — ETL パイプライン（差分取得・品質チェックの起点）
    - schema.py — DuckDB スキーマ定義・init_schema / get_connection
    - stats.py — Z スコア正規化などの統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（Momentum / Volatility / Value）
    - feature_exploration.py — IC / forward returns / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル構築（正規化・フィルタ）
    - signal_generator.py — final_score 計算と signals テーブル生成
  - backtest/
    - __init__.py
    - engine.py — run_backtest（バックテスト全体ループ）
    - simulator.py — PortfolioSimulator（擬似約定・時価評価）
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI エントリポイント
    - clock.py — SimulatedClock（将来拡張向け）
  - execution/ — 発注／実行レイヤ（空のパッケージプレースホルダ）
  - monitoring/ — 監視用モジュール（配置場所）
  - その他：各ユーティリティ・ログ機能等

（上位ディレクトリ構成はソースに基づく概略です。細部は実ファイルを参照してください）

---

## 注意事項 / 運用メモ

- DuckDB スキーマは init_schema() で冪等に作成します。既存 DB を破壊しないので安心して実行できます。
- J-Quants API はレート制限（120 req/min）に注意してください。jquants_client は内部でスロットリングを実装しています。
- セキュリティ：RSS の取得では SSRF 対策、defusedxml による XML パース保護、受信サイズ制限などを実装しています。運用時は追加のネットワーク制約（プロキシ等）に注意してください。
- 本パッケージは「データ処理・シグナル生成・バックテスト」を提供しますが、実際の発注（ブローカーAPI連携）を行う場合は別途 execution 層や安全対策が必要です。
- KABUSYS_ENV によって挙動や安全策を切り替えられます（development / paper_trading / live）。

---

もし README に追記したい実行例（具体的な ETL スケジュール例、CI 設定、デプロイ手順）や、各モジュールの詳細な API ドキュメント（関数単位の使用例）が必要であれば教えてください。