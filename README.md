# KabuSys

KabuSys は日本株向けの自動売買 / 研究フレームワークです。データ取得、ファクター計算、特徴量構築、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集までをカバーするモジュール群を提供します。

本 README ではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python パッケージです：

- J-Quants 等の外部 API からのデータ収集（株価・財務・カレンダー）
- RSS ニュース収集と記事 → 銘柄紐付け
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量（features）構築と正規化
- シグナル生成（BUY / SELL）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクター制約、レジーム調整）
- バックテストフレームワーク（擬似約定、手数料・スリッページモデル、メトリクス計算）

設計面の特徴：
- DuckDB をデータバックエンドとして使用（軽量で SQL が使える）
- ルックアヘッドバイアス防止を意識したデータ設計（fetched_at の記録等）
- 冪等性（DB への upsert / ON CONFLICT 対応）
- ネットワーク耐性（API リトライ、レート制御、SSRF 対策）

---

## 機能一覧

主要モジュールと機能（抜粋）:

- kabusys.data
  - jquants_client: J-Quants API から OHLCV / 財務 / 上場情報 / カレンダーを取得・保存
  - news_collector: RSS フィード取得、記事正規化、raw_news と news_symbols への保存（SSRF 対策、トラッキングパラメータ除去）
- kabusys.research
  - factor_research: mom / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー
- kabusys.strategy
  - feature_engineering: 生ファクターの正規化（Zスコア）と features テーブルへの保存
  - signal_generator: features + ai_scores を統合して final_score を算出、BUY/SELL シグナル生成
- kabusys.portfolio
  - portfolio_builder: 候補選定、等配分・スコア加重
  - position_sizing: 株数決定（risk_based / equal / score）、単元丸め、aggregate cap
  - risk_adjustment: セクター上限適用、レジーム乗数計算
- kabusys.backtest
  - engine: バックテストの全体ループ（データコピー→シミュレータ呼出し→指標算出）
  - simulator: 擬似約定・ポートフォリオ状態管理（スリッページ・手数料モデル）
  - metrics: CAGR / Sharpe / MaxDrawdown / 勝率等の計算
  - CLI: `python -m kabusys.backtest.run`（バックテスト実行用簡易 CLI）

その他：設定管理（kabusys.config）やログ設定等。

---

## 動作環境 / 依存

- Python 3.10 以上（typing の | 演算子等を使用）
- 必要な Python パッケージ（代表例）
  - duckdb
  - defusedxml
  - （標準ライブラリを多用しているため依存は最小限に設計されています）
- 外部サービス：
  - J-Quants API（データ収集）
  - Slack（通知等を利用する場合）

プロジェクト固有の依存は実際の配布物に含まれる requirements.txt を参照してください。

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. Python 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージのインストール（requirements.txt がある場合）
   ```bash
   pip install -r requirements.txt
   ```
   ない場合は最低限 duckdb と defusedxml を入れておく：
   ```bash
   pip install duckdb defusedxml
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（優先度: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB スキーマの初期化
   - 本プロジェクトは DuckDB のスキーマ（prices_daily, raw_prices, raw_financials, features, signals, positions, ai_scores, market_regime, market_calendar, stocks, raw_news, news_symbols 等）を前提とします。
   - スキーマ初期化関数（例: `kabusys.data.schema.init_schema(path)`）を用いて DB を作成してください（schema スクリプトはリポジトリ内にある想定）。

---

## 必要な環境変数

Settings クラスで参照される主要環境変数（必須のもの）:

- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN        — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID       — Slack チャンネル ID（必須）

任意/デフォルト付き:

- KABUSYS_ENV            — "development" | "paper_trading" | "live" (デフォルト: development)
- LOG_LEVEL              — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL" (デフォルト: INFO)
- KABU_API_BASE_URL      — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite（デフォルト: data/monitoring.db）

.env の書き方の例（簡易）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表例）

以下は主要なタスクの一例です。

### バックテストを CLI で実行

DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）が用意されている前提です。

```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db path/to/kabusys.duckdb \
  --allocation-method risk_based \
  --max-positions 10
```

出力にバックテスト結果（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）が表示されます。

### バックテストをコードから呼ぶ

```python
from datetime import date
import duckdb
from kabusys.backtest.engine import run_backtest

conn = duckdb.connect("path/to/kabusys.duckdb")
result = run_backtest(
    conn=conn,
    start_date=date(2023,1,1),
    end_date=date(2023,12,31),
    initial_cash=10_000_000,
)
conn.close()

# result.history, result.trades, result.metrics を参照
```

### 特徴量構築（feature_engineering.build_features）

DuckDB の接続を渡して、ある日付の features を作成します。

```python
from datetime import date
import duckdb
from kabusys.strategy.feature_engineering import build_features

conn = duckdb.connect("path/to/kabusys.duckdb")
n = build_features(conn, target_date=date(2024,1,31))
print(f"{n} 銘柄を upsert しました")
conn.close()
```

### シグナル生成（strategy.signal_generator.generate_signals）

features / ai_scores / positions を参照し signals を作成します。

```python
from datetime import date
import duckdb
from kabusys.strategy.signal_generator import generate_signals

conn = duckdb.connect("path/to/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)
print(f"{count} 件のシグナルを書き込みました")
conn.close()
```

### ニュース収集（data.news_collector.run_news_collection）

RSS を取得して raw_news / news_symbols に保存します。

```python
import duckdb
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = duckdb.connect("path/to/kabusys.duckdb")
# known_codes があると記事中の銘柄コード抽出を行う
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
conn.close()
```

### J-Quants データ取得・保存

jquants_client の fetch / save 関数を使って DuckDB にデータを投入します。トークンは `JQUANTS_REFRESH_TOKEN` を利用。

例:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
import duckdb
from datetime import date

conn = duckdb.connect("path/to/kabusys.duckdb")
recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, recs)
print(f"saved {saved} rows")
conn.close()
```

---

## 自動環境読み込みの挙動

- プロジェクトルートは `__file__` から親ディレクトリを遡り `.git` または `pyproject.toml` があるディレクトリとして推定されます。
- 自動ロードの優先順位: OS 環境 > .env.local > .env
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時などに利用）。

---

## ディレクトリ構成

主なファイル・ディレクトリ（抜粋）:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/data/
  - jquants_client.py
  - news_collector.py
  - (schema / calendar_management 等の補助モジュールを想定)
- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
- src/kabusys/strategy/
  - feature_engineering.py
  - signal_generator.py
- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- src/kabusys/backtest/
  - engine.py
  - simulator.py
  - metrics.py
  - run.py  (CLI エントリ)
  - clock.py
- src/kabusys/portfolio/__init__.py
- その他: execution, monitoring 等の名前空間（実装は別ファイル/今後拡張想定）

簡単なツリー表示（要約）:
```
src/kabusys/
├─ config.py
├─ data/
│  ├─ jquants_client.py
│  └─ news_collector.py
├─ research/
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ strategy/
│  ├─ feature_engineering.py
│  └─ signal_generator.py
├─ portfolio/
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  └─ risk_adjustment.py
├─ backtest/
│  ├─ engine.py
│  ├─ simulator.py
│  ├─ metrics.py
│  └─ run.py
└─ ...
```

---

## 開発者向け Notes / 注意点

- 多くの関数は DuckDB の接続を受け取り、テーブルに対する SQL 読み書きを行います。テーブルスキーマを事前に整備してください。
- バックテストは本番 DB を直接書き換えないよう、エンジン内でインメモリ接続にコピーして実行します（_build_backtest_conn）。
- ニュース収集時は SSRF 対策やレスポンスサイズ制限、XML デフューズ処理など防御を重視した実装になっています。
- API 呼び出しはレート制限とリトライロジックを備えています。J-Quants のトークン管理は自動リフレッシュに対応します。
- コード内のログメッセージや docstring を参照することで詳細なアルゴリズム仕様（例: StrategyModel.md / PortfolioConstruction.md の参照箇所）を理解できます。

---

必要に応じて README に含めるコマンド例や .env.example のテンプレート、Schema の初期化手順（DDL / init スクリプト）を追加できます。追加したい情報があれば教えてください。