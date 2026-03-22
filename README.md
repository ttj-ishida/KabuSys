# KabuSys

日本株の自動売買・研究プラットフォーム (KabuSys) の README。  
このリポジトリはデータ取得・前処理、ファクター計算、シグナル生成、バックテスト、ニュース収集などを含むモジュール群で構成されています。

- 対象言語: Python 3.10+
- 主な外部依存: duckdb, defusedxml（その他標準ライブラリで実装されたユーティリティ多数）

---

## プロジェクト概要

KabuSys は日本株を対象とした、研究〜本番までを想定した自動売買システムのコードベースです。  
主要機能は下記のレイヤに分かれます。

- Data layer: J-Quants API などからのデータ取得（株価、財務、マーケットカレンダー）、RSS ニュース収集、DuckDB スキーマ定義／ETL
- Research layer: ファクター計算、特徴量探索、統計ユーティリティ
- Strategy layer: 特徴量を用いた正規化・統合（features構築）、最終スコア計算とシグナル生成
- Backtest layer: ポートフォリオシミュレータ、バックテストエンジン、メトリクス計算
- Execution layer: 発注周り（骨格: 信号キュー、orders、trades、positions 等のテーブル定義。実際の API 実装は別途）

設計上の要点:
- DuckDB を DB として採用し、スキーマは冪等に作成可能
- ルックアヘッドバイアス防止（計算は target_date 時点のデータのみ使用）
- J-Quants API 呼び出しはレート制御、リトライ、トークン自動リフレッシュ等を備える
- ニュース収集は SSRF / XML Bomb 等の攻撃に対する防御を実装

---

## 機能一覧

主なモジュールと機能（抜粋）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート：.git または pyproject.toml を基準）
  - 必須環境変数チェックなど
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存用ユーティリティ）
  - news_collector: RSS からニュース取得・前処理・DB 保存
  - schema: DuckDB のスキーマ定義 & init_schema()
  - pipeline: ETL ロジック（差分取得・品質チェックの起点）
  - stats: z-score 正規化など統計ユーティリティ
- kabusys.research
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、ファクター統計
- kabusys.strategy
  - feature_engineering.build_features(conn, target_date)
  - signal_generator.generate_signals(conn, target_date, ...)
- kabusys.backtest
  - engine.run_backtest(conn, start_date, end_date, ...)
  - simulator.PortfolioSimulator（擬似約定、スリッページ/手数料モデル）
  - metrics.calc_metrics（CAGR・Sharpe 等）
  - run.py: CLI からのバックテスト実行エントリポイント

---

## セットアップ

必要条件:
- Python 3.10+
- pip

推奨インストール手順（開発環境想定）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに setup.py / pyproject.toml があれば pip install -e .）

3. DuckDB 用ディレクトリ作成（必要に応じて）
   - mkdir -p data

環境変数:
このプロジェクトはいくつかの必須環境変数を参照します。開発ではプロジェクトルートの `.env` / `.env.local` を使えます（kabusys.config が自動で読み込みます）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（実行する機能により変化しますが、主要なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（データ取得に必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注周り）
- SLACK_BOT_TOKEN — Slack 通知用
- SLACK_CHANNEL_ID — Slack チャネル ID

任意／既定値あり:
- KABUSYS_ENV — development|paper_trading|live（デフォルト: development）
- LOG_LEVEL — DEBUG|INFO|...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

サンプル .env（最低限の例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 初期化（DuckDB スキーマ）

Python REPL などから初期スキーマを作成できます:

```python
from kabusys.data.schema import init_schema

# ファイル DB を作る例
conn = init_schema("data/kabusys.duckdb")
# 終了時に close
conn.close()

# インメモリ DB
mem_conn = init_schema(":memory:")
```

この関数は全テーブルを冪等に作成します。

---

## 使い方（主要ワークフロー & サンプル）

以下は代表的な操作例です。

1) データ取得（J-Quants から株価／財務／カレンダーを取得し保存）

```python
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data import jquants_client as jq

conn = init_schema("data/kabusys.duckdb")
# 例: ある期間の株価を取得して保存
recs = jq.fetch_daily_quotes(date_from=<date1>, date_to=<date2>)
saved = jq.save_daily_quotes(conn, recs)
print("saved:", saved)
conn.close()
```

2) ニュース収集（RSS → raw_news 保存 → 銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", ...}  # 事前に有効コードセットを用意
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
conn.close()
```

3) 特徴量構築（features テーブルへ書き込み）

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
print("built features:", n)
conn.close()
```

4) シグナル生成（features + ai_scores + positions を参照して signals に書込）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 31))
print("signals generated:", count)
conn.close()
```

5) バックテスト（CLI またはプログラムから）

CLI 例:
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```

プログラムから:
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
res = run_backtest(conn, start_date=date(2023,1,4), end_date=date(2023,12,29))
print(res.metrics)
conn.close()
```

6) ETL パイプライン（差分取得）：pipeline モジュールに差分更新や品質チェックのユーティリティがあります。例:

```python
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
# run_prices_etl は id_token 引数を受け取るため、jq.get_id_token() 等で取得したトークンを渡せます
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

（実際の ETL は環境・運用方針によりジョブ化して実行してください）

---

## 主要ディレクトリ構成

（src/kabusys 以下の代表ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント & save_* 関数
    - news_collector.py              — RSS ニュース収集・保存
    - schema.py                      — DuckDB スキーマ定義 & init_schema
    - pipeline.py                    — ETL パイプライン・差分取得ユーティリティ
    - stats.py                       — zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py             — momentum / value / volatility 等
    - feature_exploration.py         — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py         — features の構築
    - signal_generator.py            — final_score 計算と signals 生成
  - backtest/
    - __init__.py
    - engine.py                      — run_backtest の本体
    - simulator.py                   — PortfolioSimulator（擬似約定）
    - metrics.py                     — バックテスト評価指標
    - run.py                         — CLI entrypoint
    - clock.py
  - execution/                       — 発注周り（パッケージ用の骨格）
  - monitoring/                      — 監視・メトリクス関連（DB または外部連携用）
  - research/                        — 研究用ユーティリティ（factor_research 等）

---

## 注意点 / 補足

- Python バージョン: 本コードは型ヒントや新しい構文（| 型合成）を使用しているため Python 3.10 以上を想定しています。
- DB 初期化: 初回は必ず init_schema() を呼んでスキーマを作成してください。
- 自動環境読み込み: kabusys.config はプロジェクトルートにある `.env` / `.env.local` を自動で読み込みます。CWD に依存せず __file__ を基点にプロジェクトルートを検出します。テストなどで無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- セキュリティ: news_collector は SSRF 等の対策を実装していますが、運用時は外部 URL の許可リストやプロキシ制御等を追加検討してください。
- J-Quants API: API のレート制限・認証・リトライロジックを実装していますが、実運用ではトークン管理・ログ監査・例外監視を整備してください。
- Execution 層: 実際の注文送信（kabuステーション等）を行う実装は別途必要です。本リポジトリは DB とロジック、シミュレータを中心に整備しています。

---

必要に応じて README を拡張できます（開発者向けセットアップ手順、CI、テスト、運用手順、データ品質チェック一覧など）。追加したい項目があれば教えてください。