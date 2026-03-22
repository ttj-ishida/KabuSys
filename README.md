# KabuSys

KabuSys は日本株の自動売買プラットフォームのコアライブラリです。データ収集（J-Quants、RSS）、ETL、ファクター計算、特徴量生成、シグナル生成、バックテスト、および発注/ポジション管理の基盤機能を備えています。開発・ペーパートレード・実運用の各モードを想定した設計になっています。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（各処理は target_date 時点の情報のみを使用）
- DuckDB をデータストアとして使用（軽量かつ高速な列指向 DB）
- 冪等性を重視（DB への保存は ON CONFLICT / トランザクションで保護）
- 外部 API 呼び出しはレート制御・リトライ・トークン自動更新を含む堅牢な実装

---

## 機能一覧

- データ収集
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
    - レート制御（120 req/min）、リトライ、トークン自動リフレッシュ対応
  - RSS ニュース収集（安全対策：SSRF/プライベートホストチェック、XML の安全パース）
- ETL パイプライン
  - 差分取得、バックフィル対応、品質チェックのフック
- データスキーマ
  - Raw / Processed / Feature / Execution 層の DuckDB スキーマ初期化機能
- 研究・解析
  - ファクター計算（Momentum / Value / Volatility / Liquidity）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - Z スコア正規化ユーティリティ
- 特徴量生成・シグナル作成
  - features テーブル構築（Z スコア正規化・ユニバースフィルタ）
  - features + ai_scores を統合して final_score を算出、BUY/SELL シグナル生成
  - Bear レジームでの BUY 抑制、エグジット判定（ストップロス等）
- バックテストフレームワーク
  - インメモリ DuckDB を用いた安全なバックテスト実行
  - 約定/スリッページ/手数料モデルを備えた PortfolioSimulator
  - バックテスト評価指標（CAGR, Sharpe, MaxDD, WinRate, Payoff 等）
  - CLI エントリポイントでバッチ実行可能
- ニュース処理
  - RSS 取得 → raw_news 保存 → 銘柄抽出（記事内の4桁コード抽出）→ news_symbols 保存

---

## セットアップ手順

前提
- Python 3.10+（型ヒンティングに Path|None などを使用）
- DuckDB（Python パッケージとして pip install duckdb）
- defusedxml（RSS パースの安全化）
- その他必要パッケージ（標準ライブラリ以外は requirements.txt に列挙することを推奨）

例（仮想環境）:
```bash
git clone <repository-url>
cd <repository>
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# 必要なパッケージをインストール（プロジェクトの requirements.txt がある場合）
pip install duckdb defusedxml
# 開発インストール（あれば）
pip install -e .
```

環境変数（必須）：
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード（execution 層で使用）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（monitoring 用）
- SLACK_CHANNEL_ID: Slack チャネル ID

オプション：
- DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: デフォルト "data/monitoring.db"
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.env ファイルの自動読み込み：
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）にある .env, .env.local を自動で読み込みます。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

DB スキーマ初期化（DuckDB）:
```bash
python - <<'PY'
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
print("schema initialized")
PY
```

---

## 使い方

以下は代表的な操作の例です。

1) DuckDB スキーマ初期化（上記参照）

2) データ取得（株価/財務/カレンダー）と保存（ETL の一部）
- ETL はモジュール関数を通じて呼び出します（例: run_prices_etl 等）。
- 単純な株価差分 ETL の例:
```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_prices_etl

conn = init_schema("data/kabusys.duckdb")
res = run_prices_etl(conn, target_date=date.today())
print(res)
conn.close()
```
注: run_prices_etl は API トークン注入などの引数があり、実運用ではログや例外処理を追加してください。

3) ニュース収集
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes を渡すと記事と銘柄の紐付けを行う
result = run_news_collection(conn, known_codes={"7203","6758"})
print(result)
conn.close()
```

4) 特徴量（features）構築
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024,1,31))
print(f"features upserted: {count}")
conn.close()
```

5) シグナル生成
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date(2024,1,31))
print(f"signals written: {n}")
conn.close()
```

6) バックテスト（CLI）
リポジトリにはバックテスト用の CLI エントリポイントがあります。
DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）が準備されている必要があります。

```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --db data/kabusys.duckdb
```

7) バックテストをプログラムから実行
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
res = run_backtest(conn, start_date=date(2023,1,4), end_date=date(2023,12,29))
print(res.metrics)
conn.close()
```

注意点:
- functions は多くが DuckDB 接続を受け取る設計です。接続の開閉・トランザクションは呼び出し側で管理してください。
- 設定不足時は Config.Settings が ValueError を投げます（必須環境変数のチェック）。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主なモジュールと役割です（src/kabusys 配下）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数と Settings 管理（.env 自動ロード、必須キーの検証）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント / 保存ユーティリティ
    - news_collector.py
      - RSS 取得、記事前処理、raw_news / news_symbols 保存
    - pipeline.py
      - ETL 管理（差分取得、バックフィル、品質チェックフック）
    - schema.py
      - DuckDB スキーマの定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Value / Volatility / Liquidity の各ファクター計算
    - feature_exploration.py
      - IC・将来リターン・ファクター統計
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features テーブル構築（正規化・ユニバースフィルタ）
    - signal_generator.py
      - final_score 計算と BUY/SELL シグナル生成
  - backtest/
    - __init__.py
    - engine.py
      - run_backtest（インメモリ移し替え・日次ループ）
    - simulator.py
      - PortfolioSimulator（約定ロジック・スリッページ・手数料）
    - metrics.py
      - バックテスト評価指標計算
    - run.py
      - CLI エントリポイント
    - clock.py
      - 将来拡張向けの模擬時計
  - execution/
    - __init__.py
    - （発注/キュー/監視の実装を想定）
  - monitoring/
    - （Slack 通知などの監視機能を想定）

---

## 設定（環境変数／.env）

推奨: プロジェクトルートに `.env.example` を配置して、そこから `.env` を作成してください。パッケージは起動時にプロジェクトルートを探索して `.env`（次いで `.env.local`）を自動で読み込みます。

主要なキー（要約）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須 for kabu API)
- SLACK_BOT_TOKEN (必須 for monitoring)
- SLACK_CHANNEL_ID (必須 for monitoring)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development/paper_trading/live)
- LOG_LEVEL (INFO など)

自動読み込みを無効にする:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 開発・拡張メモ

- DB スキーマは schema.py に集約されています。新しいテーブルを追加する際は _ALL_DDL と _INDEXES を更新してください。
- ETL の差分ロジック、backfill のポリシーは pipeline.py にあり、プロダクションでは API のレートやバックフィル設定を調整してください。
- シグナル生成・特徴量生成は戦略ロジックのコアです。重みや閾値は generate_signals / _DEFAULT_WEIGHTS / _DEFAULT_THRESHOLD を通じて簡単に調整できます。
- ニュース収集は外部データの危険性（SSRF、XML Bomb、巨大レスポンス）に対処する実装になっています。独自 RSS を追加する場合は DEFAULT_RSS_SOURCES を拡張してください。
- execution/monitoring は具体的なブローカー API（kabuステーション等）や通知チャネルに合わせて実装の追加を行ってください。

---

以上が README の概要です。必要であれば、セットアップ手順（requirements.txt、Dockerfile、スクリプト例）や各モジュールの API リファレンスを追記できます。どの部分を詳細化したいか教えてください。