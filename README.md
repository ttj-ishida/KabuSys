# KabuSys

日本株向けの自動売買システム（研究 / データ基盤 / 戦略 / バックテスト用ライブラリ群）。

このリポジトリは、J-Quants など外部データを取り込み、特徴量作成 → シグナル生成 → 発注/シミュレーションまでを想定したモジュール群を提供します。実運用・研究双方を意識して設計されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の層で構成される株式取引基盤ライブラリです。

- data: J-Quants からのデータ取得クライアント、RSS ニュース収集、DuckDB スキーマ定義、ETL パイプライン、統計ユーティリティ
- research: ファクター計算 / 特徴量探索（IC, forward returns など）
- strategy: 特徴量の正規化・合成（features 作成）とシグナル生成
- backtest: インメモリバックテスト実行エンジン、シミュレータ、メトリクス計算、CLI
- execution / monitoring: 実運用向けの発注・監視層（骨格）

設計上のポイント:
- ルックアヘッドバイアスを避ける設計（target_date 時点のデータのみを使用）
- DuckDB を用いたローカル DB（データ層）での整合性と冪等性を重視
- ネットワーク・RSS 周りに安全策（SSRF 検査、gzip/サイズ上限、XML 疎結合）を実装

---

## 機能一覧

主要な機能（モジュール別）

- data
  - jquants_client: J-Quants API クライアント（トークンリフレッシュ・レート制限・リトライ付き）
  - news_collector: RSS 取得・前処理・raw_news 保存・銘柄抽出
  - schema: DuckDB スキーマ初期化（raw / processed / feature / execution 層のテーブル定義）
  - pipeline: ETL の差分取得ロジック、品質チェック呼び出し（ETLResult を返す）
  - stats: Zスコア正規化ユーティリティ
- research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy
  - feature_engineering.build_features: ファクターの正規化および features テーブルへのUPSERT
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナルを生成し signals テーブルへ書き込む
- backtest
  - engine.run_backtest: 本番 DB からデータをコピーして日次シミュレーションを実行。CAGR / Sharpe / MaxDD 等を計算
  - simulator.PortfolioSimulator: 擬似約定・ポートフォリオ管理（スリッページ・手数料考慮）
  - metrics.calc_metrics: バックテスト評価指標の計算
  - CLI: python -m kabusys.backtest.run で実行可能
- news_collector:
  - URL 正規化、トラッキングパラメータ除去、記事ID生成（SHA-256 トップ32）、重複排除付き保存

---

## セットアップ手順

前提
- Python 3.10 以上（型表記に X | Y を使用）
- DuckDB（Python パッケージ）
- defusedxml（RSS パースの安全化）

推奨インストール例（venv を使う）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 必須パッケージ
pip install duckdb defusedxml
# 開発時にローカルパッケージとして使う場合（setup/pyproject があれば pip install -e . を利用）
```

環境変数
- .env または OS 環境変数で設定してください（プロジェクトルートにある `.env` / `.env.local` が自動読み込みされます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client 用）
- KABU_API_PASSWORD: kabu API パスワード（発注層で使用）
- SLACK_BOT_TOKEN: Slack 通知用トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意 / デフォルト値あり
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

データベースの初期化（DuckDB スキーマ作成）:

Python REPL またはスクリプトで:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
conn.close()
```

これにより必要なテーブルがすべて作成されます（冪等）。

---

## 使い方（代表的な例）

1) バックテスト（CLI）

データベースファイルがあらかじめ prices_daily / features / ai_scores / market_regime / market_calendar などを含む状態で実行します:

```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --slippage 0.001 --commission 0.00055 \
  --max-position-pct 0.20 \
  --db data/kabusys.duckdb
```

実行後に CAGR / Sharpe / MaxDD / Win Rate / Payoff Ratio / Total Trades を表示します。

2) ETL（株価差分取得の呼び出し）

以下は pipeline から株価差分 ETL を実行する例（J-Quants トークンは settings から取得）:

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_prices_etl

# DB 初期化済みを想定
conn = init_schema("data/kabusys.duckdb")

# 対象日（通常は当日）
target = date.today()
fetched, saved = run_prices_etl(conn, target_date=target)
print("fetched:", fetched, "saved:", saved)

conn.close()
```

3) ニュース収集ジョブ

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"6758", "7203", "9984"}  # 事前に保持している有効銘柄コード集合
res = run_news_collection(conn, known_codes=known_codes)
print(res)
conn.close()
```

4) 特徴量作成とシグナル生成（戦略）

DuckDB 接続を用いて日付ごとに features を作成し、シグナル生成を行います。

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features, generate_signals

conn = init_schema("data/kabusys.duckdb")
target = date(2023, 12, 1)
n_feats = build_features(conn, target)
n_signals = generate_signals(conn, target)
conn.close()
```

5) プログラムによるバックテスト呼び出し（API）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
res = run_backtest(conn, start_date=date(2023,1,4), end_date=date(2023,12,29))
print(res.metrics)
conn.close()
```

---

## 注意点 / 運用メモ

- 自動 .env ロード: モジュール import 時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動で読み込みます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト実行時に有用）。
- J-Quants API はレート制限があるため jquants_client は固定間隔スロットルを用いています。大量取得時は時間がかかります。
- RSS 取得は外部ネットワークを使うため、SSRF 対策やレスポンスサイズ上限が実装されています。fetch_rss は HTTP/HTTPS スキーム以外を拒否します。
- バックテスト実行時、run_backtest は本番 DB から必要な期間をインメモリ DB にコピーして処理します。元の signals/positions テーブルは汚染されません。

---

## ディレクトリ構成

下記は主要ファイルの一覧（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数と設定取得ロジック
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント + 保存関数
    - news_collector.py            # RSS 収集・前処理・保存
    - pipeline.py                  # ETL パイプライン
    - schema.py                    # DuckDB スキーマ定義・初期化
    - stats.py                     # zscore_normalize 等統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py           # momentum / volatility / value 等
    - feature_exploration.py       # forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py       # build_features
    - signal_generator.py          # generate_signals
  - backtest/
    - __init__.py
    - engine.py                    # run_backtest
    - simulator.py                 # PortfolioSimulator
    - metrics.py                   # バックテスト評価指標
    - clock.py                     # SimulatedClock（将来拡張用）
    - run.py                       # CLI entry point (python -m kabusys.backtest.run)
  - execution/                      # 発注層の骨格（将来的な実装）
    - __init__.py
  - monitoring/                     # 監視用モジュール（骨格）
    - __init__.py

---

## 開発 / 貢献

- コードはモジュール単位で分離されているため、各モジュールごとのユニットテストが書きやすく構成されています。
- 外部 API 呼び出し箇所（jquants_client._request、news_collector._urlopen など）はモックしやすい設計です。
- PR の際は既存の型注釈・ログ出力・例外設計に合わせてください。

---

この README はリポジトリ内のソースコード（src/kabusys 以下）に基づいて作成しています。実運用する場合は .env.example（存在する場合）や DataSchema.md / StrategyModel.md 等の設計ドキュメントを参照してください。必要であれば README に追加したい手順や利用例を教えてください。