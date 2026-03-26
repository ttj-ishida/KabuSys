# KabuSys

KabuSys は日本株の自動売買システム向けライブラリおよびバックテストフレームワークです。データ取得（J-Quants）、ファクター計算、シグナル生成、ポートフォリオ構築、バックテストシミュレータ、ニュース収集などの主要機能を備えています。

---

## プロジェクト概要

- 日本株（J-Quants 等のデータソース）を用いた量的投資システムのコアロジックを提供します。
- モジュール設計により、データ取得、研究（research）、戦略（strategy）、ポートフォリオ構築、実取引実行（execution）、監視（monitoring）、バックテストを分離しています。
- DuckDB をメタデータ／時系列データベースとして利用することを前提とした設計です。
- Look-ahead バイアス回避、冪等性、レートリミット・リトライ、SSRF 防御など運用上の堅牢性を考慮しています。

---

## 主な機能一覧

- データ取得
  - J-Quants API クライアント（トークン自動リフレッシュ、レート制御、リトライ）
  - 市場カレンダー・日次株価・財務データの取得と DuckDB への保存
- ニュース収集
  - RSS フィードからニュースを収集し、前処理・ID 生成・銘柄紐付けを行って DuckDB に保存
  - SSRF / Gzip Bomb / トラッキングパラメータの除去など安全対策実装
- 研究（research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量生成（feature_engineering）
  - 生ファクターの正規化（Zスコア、クリップ）と features テーブルへのアップサート
- シグナル生成（signal_generator）
  - features と AI スコアを統合して final_score を算出、BUY/SELL シグナル生成（Bear レジーム抑制等）
- ポートフォリオ構築
  - 候補選定、等配分／スコア重み、リスクベースのサイジング、セクター上限適用
- バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）、バックテストループ、各種評価指標（CAGR、Sharpe、MaxDD、勝率、Payoff）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- 実行／監視（骨子）
  - execution / monitoring 用のパッケージエクスポート（詳細な実装は拡張想定）

---

## 動作環境・依存

- Python 3.9+（コードは 3.10+ の書き方も含むため、3.9 以上を推奨）
- 必要ライブラリ（主なもの）
  - duckdb
  - defusedxml
- そのほか標準ライブラリ（urllib, datetime, logging 等）を使用

（プロジェクトの requirements.txt / pyproject.toml がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン、プロジェクトルートへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   # またはプロジェクトに pyproject/requirements があればそれに従う
   ```

4. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .   # setup.cfg/pyproject がある場合
   ```

5. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると、自動で読み込まれます（自動読み込みはデフォルトで有効）。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（実行する機能に応じて必要）
     - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
     - KABU_API_PASSWORD: kabuステーション API パスワード（実取引用）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知（必要な場合）
   - その他（オプション）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...
     - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH: デフォルト "data/monitoring.db"

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須：実運用時）
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須：通知利用時）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須：通知利用時）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（default: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")
- LOG_LEVEL — ログレベル ("INFO" など)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env の自動読み込みを無効化

.env のパースはシェル形式（export を含む行も可）に対応し、コメントやクォートを適切に扱います。

---

## 使い方（代表例）

### 1) バックテスト（CLI）

DuckDB に prices_daily / features / ai_scores / market_regime / market_calendar 等が整っていることが前提です。

```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2024-12-31 \
  --cash 10000000 \
  --db path/to/kabusys.duckdb
```

主なオプション：
- --start / --end : バックテスト期間（YYYY-MM-DD）
- --cash : 初期資金（JPY）
- --slippage / --commission : スリッページ・手数料率
- --allocation-method : equal | score | risk_based
- --max-positions / --max-utilization / --lot-size など

実行後に CAGR 等のメトリクスが出力されます。

### 2) Python API からバックテストを呼ぶ

```python
import duckdb
from datetime import date
from kabusys.backtest.engine import run_backtest

conn = duckdb.connect("path/to/kabusys.duckdb")
result = run_backtest(
    conn=conn,
    start_date=date(2023, 1, 1),
    end_date=date(2023, 12, 31),
    initial_cash=10_000_000,
)
# result.history / result.trades / result.metrics を利用
conn.close()
```

### 3) 特徴量生成（features テーブルのアップデート）

build_features を使い、DuckDB 接続と target_date を渡して実行します。

```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("path/to/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 31))
print(f"upserted {count} features")
conn.close()
```

### 4) シグナル生成

```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("path/to/kabusys.duckdb")
num_signals = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"generated {num_signals} signals")
conn.close()
```

### 5) データ取得（J-Quants）例

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
import duckdb
from datetime import date

# fetch
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# save to DuckDB
conn = duckdb.connect("path/to/kabusys.duckdb")
save_daily_quotes(conn, records)
conn.close()
```

### 6) ニュース収集（RSS）例

```python
from kabusys.data.news_collector import run_news_collection
import duckdb

conn = duckdb.connect("path/to/kabusys.duckdb")
results = run_news_collection(conn)  # DEFAULT_RSS_SOURCES を使用
print(results)  # {source_name: saved_count}
conn.close()
```

---

## ディレクトリ構成（主要ファイルの説明）

（ルート: src/kabusys/ 以下にモジュールが置かれます）

- kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み、Settings クラス）
  - data/
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py — RSS ベースのニュース収集・前処理・DB 保存
    - (その他: calendar_management, schema など 想定)
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー等ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - strategy/
    - feature_engineering.py — 生ファクター -> features テーブル（Zスコア等）
    - signal_generator.py — features + ai_scores -> BUY/SELL シグナル
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定（リスクベース等）、単元丸め、合算スケールダウン
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - backtest/
    - engine.py — バックテストのメインループ・補助関数
    - simulator.py — ポートフォリオシミュレータ・約定モデル
    - metrics.py — バックテスト評価指標の計算
    - run.py — CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py — シミュレーション用の時計（将来拡張用）
  - portfolio/、execution/、monitoring/ — 実運用向けの骨子（拡張用）
  - backtest/__init__.py, research/__init__.py, strategy/__init__.py, portfolio/__init__.py — パブリック API エクスポート

---

## 注意点 / 運用上のヒント

- Look-ahead バイアス対策:
  - ファクター計算・シグナル生成はいずれも target_date 時点の情報のみを使用するよう設計されています。
  - バックテスト用に DuckDB に取り込むデータは「その時点で利用可能であったデータ」を意識して準備してください（fetched_at 等の管理）。
- 環境ごとの挙動:
  - KABUSYS_ENV により is_live / is_paper / is_dev ロジックが切り替わります。実取引時は慎重に設定してください。
- 自動 .env ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml がある場所）を探索して .env/.env.local を自動で読み込みます。テストや CI で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB スキーマ:
  - 本リポジトリのコードは特定のテーブルスキーマを前提としています（prices_daily, features, ai_scores, positions, signals, market_regime, raw_prices, raw_financials, raw_news, news_symbols, stocks, market_calendar など）。スキーマ初期化ロジック（kabusys.data.schema.init_schema）が提供されている想定です。

---

以上が README の要約です。必要であれば次の内容も追記できます：
- 具体的な .env.example（テンプレート）
- DuckDB スキーマ定義サンプル（init_schema の内容）
- CI / テスト実行手順
- 実運用（kabuステーション連携、Slack 通知）に関する詳細手順

どの追加情報が必要か教えてください。