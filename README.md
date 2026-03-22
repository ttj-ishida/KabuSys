# KabuSys

日本株向けの自動売買（データ取得・特徴量生成・シグナル生成・バックテスト・ニュース収集）フレームワークです。研究用の factor 計算やバックテストエンジン、J-Quants API / RSS ニュース収集などのデータパイプラインを備え、DuckDB をデータストアとして利用します。

---

## プロジェクト概要

主な目的
- J-Quants などから市場データを取得して DuckDB に保存
- 研究（factor 計算）→ 特徴量生成 → シグナル生成 のパイプライン
- ポートフォリオシミュレーション（バックテスト）
- RSS ニュースの収集・銘柄紐付け
- 発注層（execution）や監視（monitoring）を統合できる構成を想定

設計方針の要点
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- DB への保存は冪等（ON CONFLICT 等）を重視
- ネットワークリトライ / レート制御 / SSRF 対策など堅牢性を考慮

---

## 主な機能一覧

- data/
  - J-Quants API クライアント（取得・保存・トークン自動リフレッシュ、レートリミット、リトライ）
  - RSS フィード収集・前処理・DB 保存・銘柄抽出
  - DuckDB スキーマ定義・初期化（init_schema）
  - ETL パイプライン（差分取得、品質チェックフック）
  - 汎用統計関数（Zスコア正規化など）
- research/
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、統計サマリー
- strategy/
  - 特徴量エンジニアリング（build_features）
  - シグナル生成（generate_signals） — final_score 計算、Bear フィルタ、BUY/SELL 判定
- backtest/
  - ポートフォリオシミュレータ（約定モデル：スリッページ・手数料）
  - バックテストエンジン（run_backtest）
  - メトリクス計算（CAGR, Sharpe, MaxDD, WinRate...）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- execution/, monitoring/（パッケージ公開ポイントは存在、実装は別途）

---

## セットアップ手順

前提
- Python 3.10 以上（typing に PEP 604 の | を使用）
- DuckDB を利用するための依存（duckdb）
- RSS パースに defusedxml 等

例: 仮想環境作成と必須パッケージのインストール（プロジェクトに requirements.txt があればそれを使用）
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 例: 必要依存をインストール
pip install duckdb defusedxml
# 開発時にローカル編集を反映させる場合
pip install -e .
```

環境変数（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

オプション環境変数
- KABUSYS_ENV: environment（development / paper_trading / live）、デフォルト development
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）、デフォルト INFO
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

.env の自動ロード
- パッケージはプロジェクトルート（.git または pyproject.toml）を検出して .env, .env.local を自動で読み込みます。
- 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 初期化（DuckDB スキーマ作成）

DuckDB ファイルを初期化してスキーマを作成します。":memory:" でインメモリ DB も可能です。

Python REPL またはスクリプトで:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルパスを指定
conn.close()
```

注意: init_schema は親ディレクトリを自動作成します。

---

## 使い方（代表例）

1) バックテスト（CLI）
DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar）があらかじめ用意されていることが前提です。

```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --slippage 0.001 \
  --commission 0.00055 \
  --max-position-pct 0.20 \
  --db data/kabusys.duckdb
```

戻り値として標準出力にメトリクスを表示します。内部では generate_signals を呼び出し、PortfolioSimulator を用いて約定・時価評価を行います。

2) ETL（株価 / 財務 / カレンダー 等）
ETL パイプライン関数を呼んで差分取得・保存を行います。例（概念）：

```python
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_prices_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

（上の run_prices_etl は差分取得ロジックを提供します。J-Quants API の id_token を明示的に渡すことも可能）

3) ニュース収集
RSS を取得して raw_news に保存、銘柄紐付けまで実施できます。

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使う有効コードセットを渡す（None なら抽出スキップ）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)
conn.close()
```

4) 特徴量生成 / シグナル生成（戦略パイプライン）
DuckDB 接続と target_date を渡して実行します。

```python
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features, generate_signals
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024,1,31))
m = generate_signals(conn, target_date=date(2024,1,31))
conn.close()
print("features:", n, "signals:", m)
```

5) J-Quants データ取得/保存（低レベル）
- fetch_daily_quotes / save_daily_quotes
- fetch_financial_statements / save_financial_statements
- fetch_market_calendar / save_market_calendar

トークン自動リフレッシュ・レート制御・リトライが組み込まれています。get_id_token(refresh_token) も利用可能。

---

## 主要モジュールとディレクトリ構成

（src/kabusys 以下の主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py                      # 環境変数管理・自動 .env ロード
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント（取得・保存）
    - news_collector.py             # RSS 収集・前処理・DB保存・銘柄抽出
    - pipeline.py                   # ETL パイプライン（差分取得等）
    - schema.py                     # DuckDB スキーマ定義・init_schema
    - stats.py                      # Z スコア正規化等
  - research/
    - __init__.py
    - factor_research.py            # momentum/value/volatility 計算
    - feature_exploration.py        # 将来リターン、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py        # build_features
    - signal_generator.py           # generate_signals
  - backtest/
    - __init__.py
    - engine.py                     # run_backtest（エントリ）
    - simulator.py                  # PortfolioSimulator（約定モデル）
    - metrics.py                    # バックテストメトリクス
    - run.py                        # CLI ラッパー
    - clock.py                      # SimulatedClock（将来拡張）
  - execution/                       # 発注層（パッケージ用エントリ）
  - monitoring/                      # 監視・アラート層（パッケージ用エントリ）

---

## 開発時メモ / 注意事項

- 冪等性: DB への保存は ON CONFLICT DO UPDATE / DO NOTHING 等を用いているため、再実行が安全な設計になっています。
- ルックアヘッド防止: 戦略・研究系関数は target_date 時点の情報のみを利用するよう実装されています。
- 自動 .env ロードは便利ですが、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨します。
- DuckDB のバージョンや一部の機能（例: ON DELETE CASCADE のサポート）に依存する箇所があるため、実行環境の DuckDB バージョンに注意してください。
- ネットワーク呼び出し（J-Quants, RSS）はリトライ・レート制御・SSRF 警戒が入っていますが、実運用ではさらに監視・アラートを追加してください。

---

問題や改善要望がある場合は、対象のモジュール（例: data/jquants_client.py / strategy/signal_generator.py）を参照して実装方針とログ出力を確認し、Pull Request を送ってください。