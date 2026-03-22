# KabuSys

日本株向けの自動売買システム基盤ライブラリです。データ収集・ETL、ファクター計算、特徴量生成、シグナル生成、バックテスト、ニュース収集までを一貫してサポートするモジュール群を提供します。

主な設計方針は「ルックアヘッドバイアス排除」「冪等性」「シンプルな DuckDB ベースのデータモデル」「研究と実運用の分離」です。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件 / 必要ライブラリ
- セットアップ手順
- 環境変数 (.env) 例
- 使い方（主要ユースケース）
  - DB 初期化
  - データ ETL（J-Quants からの株価/財務/カレンダー取得）
  - 特徴量作成 / シグナル生成
  - バックテスト（CLI）
  - ニュース収集
- 重要な設定・注意点
- ディレクトリ構成（主要ファイル）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤ライブラリで、以下を主な目的として設計されています。

- J-Quants 等の外部 API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いたローカル DB スキーマ管理と ETL（冪等保存）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量の正規化・合成（features テーブル）
- シグナル生成（final_score に基づく BUY/SELL）
- バックテストエンジン（ポートフォリオシミュレータ、メトリクス）
- RSS ニュース収集と記事→銘柄の紐付け

コードベースは src/kabusys 以下にモジュール化されています。

---

## 機能一覧

- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み（プロジェクトルート検出）と必須設定の取得
- データ層（src/kabusys/data）
  - J-Quants クライアント（レート制御・リトライ・トークン自動更新）: jquants_client.py
  - RSS ニュース収集・前処理・DB保存: news_collector.py
  - DuckDB スキーマ初期化/接続管理: schema.py
  - ETL パイプライン（差分取得・保存・簡易品質チェック）: pipeline.py
  - 統計ユーティリティ（Z スコア正規化等）: stats.py
- 研究・ファクター計算（src/kabusys/research）
  - calc_momentum / calc_volatility / calc_value（prices_daily/raw_financials に基づく）
  - 将来リターン計算、IC 計算、統計サマリー
- 戦略層（src/kabusys/strategy）
  - 特徴量作成（build_features）: feature_engineering.py
  - シグナル生成（generate_signals）: signal_generator.py
- バックテスト（src/kabusys/backtest）
  - PortfolioSimulator（スリッページ・手数料考慮）: simulator.py
  - run_backtest（エンドツーエンドのバックテスト）: engine.py
  - CLI エントリーポイント: run.py
  - メトリクス算出（CAGR, Sharpe, MaxDD 等）: metrics.py
- 実行層（発注・監視）は execution/monitoring 名でプレースホルダ構成（拡張対象）

---

## 前提条件 / 必要ライブラリ

- Python 3.10+
- 必須（最低限）パッケージ
  - duckdb
  - defusedxml
- 標準ライブラリベースで実装している箇所が多いですが、J-Quants API を使う場合はネットワーク接続と有効なトークンが必要です。

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 開発時はプロジェクト直下に移動して editable install（pyproject/setup があれば）
# pip install -e .
```

（プロジェクト配布時に pyproject.toml/setup.py があれば pip install -e . を推奨）

---

## セットアップ手順

1. リポジトリを取得、仮想環境を作成して有効化
2. 必要パッケージをインストール（duckdb, defusedxml 等）
3. DuckDB スキーマを初期化（ファイル DB または :memory:）

Python REPL またはスクリプトで:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # data/ ディレクトリは自動作成されます
conn.close()
```

4. 環境変数を設定（下記の .env 例を参照）
5. J-Quants 等の API を使う場合は認証情報（リフレッシュトークン等）を設定

---

## 環境変数 (.env) 例

config.py が参照する主な環境変数は以下です。プロジェクトルートに .env や .env.local を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能）。

例: .env

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション（発注 API）
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack（通知）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（オプション）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境（development | paper_trading | live）
KABUSYS_ENV=development

# ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
LOG_LEVEL=INFO
```

必須項目:
- JQUANTS_REFRESH_TOKEN
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- KABU_API_PASSWORD

（実行する機能に応じて追加で設定が必要です）

---

## 使い方（主要ユースケース）

以下は主要ワークフローの実行例です。各操作はライブラリ関数を直接インポートして利用できます。

### DB 初期化

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# ... 使用後
conn.close()
```

### J-Quants からデータ取得と保存（ETL の単体実行例）

```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# 例: ある銘柄の株価を取得して保存
records = jq.fetch_daily_quotes(code="7203", date_from=None, date_to=None)
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)

conn.close()
```

※ 実運用では kabusys.data.pipeline の差分 ETL（run_prices_etl 等）を使って自動化します。

### ETL パイプライン（差分更新）の利用

pipeline モジュールは差分取得・保存・品質チェックを行います。使い方の一例（スクリプトから）:

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl

conn = init_schema("data/kabusys.duckdb")
result = run_prices_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

（pipeline モジュールには prices_etl, financials_etl, calendar_etl などのジョブが揃っています）

### 特徴量生成（features テーブルの作成）

DuckDB 接続を渡して指定日分の features を生成します。

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
print(f"built features: {n}")
conn.close()
```

### シグナル生成（signals テーブルへの書き込み）

features / ai_scores / positions を参照して BUY/SELL シグナルを生成します。

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals generated: {count}")
conn.close()
```

weights パラメータでファクター重みを上書きできます（辞書形式）。

### バックテスト（CLI）

バックテストは CLI から実行できます。データベースに必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar）が事前に用意されている必要があります。

```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --db data/kabusys.duckdb
```

実行後、CAGR・Sharpe・Max Drawdown・勝率等のメトリクスが標準出力に表示されます。

また、run_backtest 関数をプログラムから呼ぶこともできます。

### ニュース収集（RSS）

ニュース収集は news_collector.run_news_collection で実行できます。既知銘柄コードセットを渡すことで記事と銘柄の紐付けを行います。

```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984", ...}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
conn.close()
```

---

## 重要な設定・注意点

- 環境変数の自動読み込みは config._find_project_root() で .git/pyproject.toml を基準に行います。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- DuckDB のスキーマ初期化は init_schema() で行ってください（既存テーブルはスキップされ、冪等）。
- J-Quants API 呼び出しはレート制御とリトライを行いますが、実際の運用では API 利用制限に注意してください（デフォルト 120 req/min）。
- feature / signal の計算は「target_date 時点の情報のみ」を使うよう設計されています（ルックアヘッドバイアス防止）。
- news_collector は SSRF 対策やレスポンスサイズ制限、XML 安全パーシング（defusedxml）等の安全対策を含みます。
- 実運用（live）環境では KABUSYS_ENV を `live` に設定し、安全確認と監視を徹底してください。

---

## ディレクトリ構成（主要ファイル）

以下はソースの主要モジュール一覧（src/kabusys 以下）です。実際にはさらに細かいファイル・テスト等が存在する可能性があります。

- src/kabusys/
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
    - run.py
    - clock.py
  - execution/
    - __init__.py
  - monitoring/  (パッケージとして宣言されているが詳細未実装)
  - backtest/ (上記)
  - その他: README.md（本ファイル）など

---

README は実装の概要と使い方の簡潔なガイドです。詳細な設計仕様（StrategyModel.md / DataPlatform.md / BacktestFramework.md 等）や運用手順はプロジェクト内の設計書を参照してください。

不明点や README の追加項目（例: CI、テストの実行方法、より詳細な ETL の実行例）を希望される場合は教えてください。