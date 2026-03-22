# KabuSys

日本株向けの自動売買システム（ライブラリ）です。データ収集（J-Quants）、ETL、ファクター計算、特徴量生成、シグナル生成、バックテスト、ニュース収集、擬似約定シミュレータなどを含む一連のコンポーネントを提供します。

---

## プロジェクト概要

KabuSys は以下の機能を分離したモジュール群として実装しています。

- データ取得・保存（J-Quants API クライアント、RSS ニュース収集）
- DuckDB ベースのデータスキーマ / ETL パイプライン
- 研究用ファクター計算（momentum / volatility / value）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）
- シグナル生成（最終スコア計算、BUY/SELL 判定）
- バックテストフレームワーク（シミュレータ、メトリクス）
- ニュース -> 銘柄紐付け、保存ロジック

設計上のポイント:
- ルックアヘッドバイアスを防ぐため、target_date 時点の情報のみで計算
- DuckDB によるローカル DB を中心とした処理（:memory: も利用可）
- API 呼び出しに対してリトライ・レート制御を実装
- DB 書き込みは可能な限り冪等（ON CONFLICT やトランザクション）に

---

## 主な機能一覧

- データ（data/）
  - J-Quants からの OHLCV・財務データ・市場カレンダー取得 + 保存（jquants_client）
  - RSS フィード収集・記事保存・銘柄抽出（news_collector）
  - DuckDB スキーマ定義・初期化（schema）
  - ETL パイプライン（pipeline）
  - 共通統計ユーティリティ（stats）

- 研究（research/）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算・ファクター統計サマリー

- 戦略（strategy/）
  - 特徴量生成（build_features）
  - シグナル生成（generate_signals）

- バックテスト（backtest/）
  - ポートフォリオシミュレータ（擬似約定・手数料・スリッページ）
  - バックテストエンジン（run_backtest）
  - メトリクス計算（CAGR, Sharpe, MaxDD 等）
  - CLI ランナー（python -m kabusys.backtest.run）

---

## 必要条件

- Python 3.9+
- duckdb
- defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージをローカル開発モードでインストールする場合
pip install -e .
```

（プロジェクト配布時に `pyproject.toml` / requirements を参照してください）

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` により読み込まれます。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テスト用）。

必須の主な環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — 通知先の Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト `development`
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト `INFO`
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite（デフォルト: `data/monitoring.db`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（1 など）

設定値は `kabusys.config.settings` から取得できます。例:
```py
from kabusys.config import settings
token = settings.jquants_refresh_token
```

---

## セットアップ手順（初期 DB 作成等）

1. リポジトリをクローンして依存をインストール
2. 環境変数を準備（`.env` を作成）
3. DuckDB スキーマ初期化:

```py
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
conn.close()
```

- メモリ DB を使う場合は `":memory:"` を指定できます。
- `init_schema` は冪等なので何度呼んでも問題ありません。

---

## 使い方（主要な操作例）

以下は代表的な API / コマンドの使用例です。

1) 特徴量の作成（features テーブルに保存）
```py
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {n}")
conn.close()
```

2) シグナル生成（signals テーブルへ書き込み）
```py
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals written: {count}")
conn.close()
```

3) バックテスト（CLI）
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --db data/kabusys.duckdb \
  --cash 10000000
```

4) バックテスト（プログラムから呼び出し）
```py
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
res = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
print(res.metrics)
conn.close()
```

5) J-Quants データ取得・保存（例）
```py
from kabusys.data import jquants_client as jq
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

6) ニュース収集（RSS）と銘柄紐付け
```py
from kabusys.data.news_collector import run_news_collection
# known_codes は有効銘柄コード集合（抽出のため）
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
```

7) ETL パイプライン（差分 ETL）
- `kabusys.data.pipeline` モジュールに `run_prices_etl`, `run_news_collection` 等の関数があります。差分取得や品質チェックを行います（詳細はコード内 docstring を参照）。

---

## ディレクトリ構成

主要なファイル・モジュール構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定読み込み
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得・保存）
    - news_collector.py              — RSS 収集・記事保存・銘柄抽出
    - schema.py                      — DuckDB スキーマ定義 / init_schema
    - stats.py                       — zscore_normalize 等の統計ユーティリティ
    - pipeline.py                    — ETL パイプライン実装
  - research/
    - __init__.py
    - factor_research.py             — momentum / value / volatility の計算
    - feature_exploration.py         — IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py         — build_features（正規化・ユニバースフィルタ）
    - signal_generator.py            — generate_signals（final_score 計算・BUY/SELL）
  - backtest/
    - __init__.py
    - engine.py                      — run_backtest（バックテスト全体ループ）
    - simulator.py                   — PortfolioSimulator（擬似約定）
    - metrics.py                     — バックテスト評価指標計算
    - run.py                         — CLI エントリポイント
    - clock.py
  - execution/                        — （発注関連：現状空 or 実装箇所）
  - monitoring/                       — （監視・メトリクス用：現状空 or 実装箇所）

---

## ログ / デバッグ

- 各モジュールは標準の logging を使用します。`LOG_LEVEL` 環境変数でログレベルを制御できます（デフォルト `INFO`）。
- バックテスト CLI は実行時に基本的なログ出力を行います。

---

## よくある注意点

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に行われます。テスト時など自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。
- J-Quants API のレート制御は実装されていますが、大量取得時は API 制限に注意してください。
- DuckDB のスキーマは init_schema() で一括作成します。既存テーブルがあれば変更を加えません（冪等）。
- news_collector は外部ネットワークを使用します。SSRF 対策・レスポンスサイズ制限等の安全策が実装されていますが、運用環境でのアクセス権限には注意してください。

---

## 開発・貢献

バグ報告や機能追加の提案は Issue を立ててください。コードは PEP8 準拠を目指していますが、モジュール内部の docstring を参照して使い方を確認してください。

---

必要があれば README にサンプルデータ作成手順や CI/テストの実行方法、より詳細な ETL・運用手順を追記できます。どの部分を拡張したいか教えてください。