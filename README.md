# KabuSys

日本株自動売買システム向けのライブラリ群（データ取得・ETL・特徴量計算・シグナル生成・バックテストなど）です。  
このリポジトリは、J-Quants などの外部データソースからデータを取得して DuckDB に保存し、研究・戦略・バックテストを一貫して実行できるように設計されています。

主な特徴
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ対応）
- RSS ニュース収集（SSRF対策、トラッキングパラメータ除去、記事→銘柄紐付け）
- DuckDB スキーマ定義と初期化ユーティリティ（冪等）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ）
- シグナル生成（複数コンポーネントスコアの統合、Bear レジーム抑制、売買シグナルの冪等保存）
- バックテストフレームワーク（ポートフォリオシミュレータ、スリッページ／手数料モデル、メトリクス算出）
- ニュース収集→raw_news / news_symbols への保存、記事IDは正規化URLのSHA-256ハッシュ（先頭32文字）

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援するライブラリ群です。  
主にデータ基盤（Raw → Processed → Feature → Execution 層）を DuckDB に構築し、研究用ファクター計算・特徴量作成・シグナル生成・バックテストを提供します。設計は以下を重視しています。

- ルックアヘッドバイアスの排除（target_date 時点のデータのみ使用）
- 冪等性（DB への保存は ON CONFLICT 等で上書き/スキップ）
- ネットワーク安全性（API レート制御、RSS の SSRF 対策等）
- テスト容易性（トークン注入、in-memory DuckDB を利用したバックテスト等）

---

## 機能一覧

- data/
  - J-Quants API クライアント（fetch/save）
  - RSS ニュース収集と記事→銘柄抽出
  - DuckDB スキーマ初期化（init_schema）
  - ETL パイプライン（差分取得、バックフィル）
  - 統計ユーティリティ（Zスコア正規化 など）
- research/
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（forward returns, IC, 統計サマリー）
- strategy/
  - 特徴量作成（build_features）
  - シグナル生成（generate_signals）
- backtest/
  - ポートフォリオシミュレータ（売買約定の擬似化）
  - バックテストエンジン（run_backtest）
  - メトリクス計算（CAGR, Sharpe, Max Drawdown, Win Rate 等）
  - CLI 実行ラッパー（python -m kabusys.backtest.run）
- config.py
  - 環境変数読み込み（.env/.env.local の自動読み込みをサポート）
  - settings オブジェクト経由で設定を取得

---

## セットアップ手順

前提
- Python 3.10 以上（コードは PEP 604 の型記法（|）を使用）
- DuckDB を利用（ローカルファイルまたは in-memory）
- ネットワーク接続は J-Quants API / RSS 取得用に必要

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate

2. 必要パッケージのインストール
   - 最低限:
     - duckdb
     - defusedxml
   - 例:
     pip install duckdb defusedxml

   （プロジェクトに requirements.txt があればそれを利用してください）

3. 環境変数の設定
   - 必須（Settings で参照される環境変数）:
     - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
     - KABU_API_PASSWORD: kabu API のパスワード（発注系を使う場合）
     - SLACK_BOT_TOKEN: Slack 通知用（必要な場合）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必要な場合）
   - 省略可能（デフォルト値あり）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト development）
     - LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db
   - .env 自動読み込み:
     - パッケージはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）にある `.env` / `.env.local` を自動的に読み込みます
     - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   - またはインメモリ:
     from kabusys.data.schema import init_schema
     conn = init_schema(":memory:")

---

## 使い方

以下は代表的な実行方法とサンプルコードです。

1) DuckDB スキーマ初期化（再掲）
- ファイル DB を初期化
  ```bash
  python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
  ```

2) J-Quants から株価を取得して保存（Python スクリプト例）
```python
from datetime import date
import duckdb
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
conn.close()
```

3) ニュース収集の実行例
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203","6758","9984"}  # 事前に用意した有効銘柄コード集合
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
conn.close()
```

4) 特徴量作成（build_features）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024,12,01))
print("features upserted:", count)
conn.close()
```

5) シグナル生成（generate_signals）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date(2024,12,01), threshold=0.6)
print("signals written:", n)
conn.close()
```

6) バックテスト（CLI）
- 付属の CLI を利用してバックテストを実行できます。DB は事前に prices_daily、features、ai_scores、market_regime、market_calendar が入っている必要があります。
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```
- 実行例（オプション）
  - --slippage, --commission, --max-position-pct でシミュレーションパラメータを指定可能

7) ETL パイプライン（run_prices_etl / run_prices_etl など）
- kabusys.data.pipeline モジュールに差分取得・バックフィルを行う関数があり、init_schema で初期化した conn を渡して使用します（詳細は pipeline モジュールの実装を参照）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須 for execution) — kabu API パスワード
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル（例: INFO）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動読み込みを無効化

設定値は kabusys.config.settings 経由で取得できます:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
```

---

## 注意点 / 実運用上の留意事項

- J-Quants API のレート制限（120 req/min）を守る設計になっていますが、大量リクエスト時は API 制限に注意してください。
- RSS の取得は SSRF 対策や受信サイズ制限（10MB）などを実装していますが、外部フィードについては運用時に信頼できるソースのみを登録してください。
- DB のスキーマは DuckDB のバージョンに依存する SQL 機能（外部キーの挙動等）に留意してください。実装のコメントにもあるように DuckDB バージョンによる差異を考慮しています。
- production 環境では KABUSYS_ENV を適切に設定し、Live運用時には発注・監視ロジックの安全性を十分検証してください。

---

## ディレクトリ構成

下は主要なモジュールと簡単な説明です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・settings オブジェクト
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント、fetch/save 関数
    - news_collector.py — RSS 取得・記事正規化・保存・銘柄抽出
    - schema.py — DuckDB スキーマ定義 / init_schema
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL 差分更新 / backfill / 品質チェック（部分実装）
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value 計算
    - feature_exploration.py — forward return, IC, summary
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features（正規化・ユニバースフィルタ）
    - signal_generator.py — generate_signals（最終スコア計算、BUY/SELL生成）
  - backtest/
    - __init__.py
    - engine.py — run_backtest（全体ループ）
    - simulator.py — PortfolioSimulator（約定ロジックの擬似化）
    - metrics.py — バックテストメトリクス計算
    - run.py — CLI エントリポイント
    - clock.py — SimulatedClock（将来拡張用）
  - execution/
    - __init__.py
    - （発注系は別途実装・統合が想定される）
  - monitoring/
    - （監視系の DB / ロギング・Slack 通知統合などを想定）

---

必要に応じて README を拡張します。例えば:
- 詳しい ETL の実行フロー（run_prices_etl の使い方や引数説明）
- CI / テストの実行方法
- 実運用でのデプロイ手順（systemd / cron / Airflow 等）
ご希望があれば、対象セクションを追加して README を更新します。