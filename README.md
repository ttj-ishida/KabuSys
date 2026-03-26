# KabuSys

日本株向けの自動売買・研究プラットフォーム。  
DuckDB をデータ層に、J-Quants 等の外部データソースからの ETL、特徴量計算、シグナル生成、ポートフォリオ構築、バックテストおよびニュース収集までを含むモジュール群を提供します。

主な設計方針:
- ルックアヘッドバイアスの排除（常に target_date 時点の情報のみを使用）
- DuckDB を用いたローカルデータベース中心のパイプライン
- 冪等性とトランザクション保護（DB 操作は日付単位で置換等）
- 本番実行（execution / kabu API）と研究（research / backtest）を分離

---

## 機能一覧

- data/
  - J-Quants API クライアント（取得・リトライ・レート制御・DuckDB 保存）
  - ニュース収集（RSS → raw_news、銘柄抽出）
  - DB スキーマ・カレンダー管理等（init_schema 等が想定）
- research/
  - ファクター計算（momentum / volatility / value）
  - ファクター探索・IC 計算・統計要約
- strategy/
  - 特徴量生成（features テーブルへの正規化・保存）
  - シグナル生成（features + ai_scores → BUY/SELL signals）
- portfolio/
  - 候補選定・重み計算（等金額・スコア加重）
  - ポジションサイジング（risk_based / equal / score）
  - リスク調整（セクターキャップ、レジーム乗数）
- backtest/
  - ポートフォリオシミュレーター（約定・スリッページ・手数料モデル）
  - バックテストエンジン（全体ループ、signals/positions の読み書き）
  - 指標計算（CAGR、Sharpe、Max Drawdown、勝率等）
  - CLI ランナー（python -m kabusys.backtest.run）
- execution/（骨組み。kabu ステーション連携等を想定）
- monitoring/（Slack 通知等を想定）

---

## セットアップ手順

前提:
- Python 3.10+（typing 演算子 `X | Y` を使用）
- DuckDB を利用できること

1. リポジトリをクローン、仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（プロジェクトに requirements.txt がない場合の例）
   ```bash
   pip install duckdb defusedxml
   ```
   - 実環境では他に requests などが必要になる可能性があります。プロジェクトの requirements.txt / pyproject.toml があればそちらを使ってください。

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml を想定）配下の `.env` / `.env.local` を自動ロードします（ただし、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数の例は次節を参照してください。

4. DuckDB スキーマ初期化
   - 本コードベースでは `kabusys.data.schema.init_schema(path)` がスキーマ初期化関数として想定されています（実装ファイルが存在する場合はそれを呼び出してください）。
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 初期化後に J-Quants やニュース等の ETL を実行してテーブルを準備します。

---

## 環境変数一覧（重要）

必須（実行する機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（data.jquants_client）
- KABU_API_PASSWORD — kabu ステーション API パスワード（execution）
- SLACK_BOT_TOKEN — Slack 通知用トークン（monitoring）
- SLACK_CHANNEL_ID — Slack チャネル ID（monitoring）

その他（デフォルトあり）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）

.env の例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表的な操作）

### バックテスト（CLI）
DuckDB が prices_daily / features / ai_scores / market_regime / market_calendar 等を含む状態で実行します。
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --db data/kabusys.duckdb \
  --allocation-method risk_based \
  --lot-size 100
```
出力はコンソールにバックテスト指標（CAGR、Sharpe、Max Drawdown 等）。

### バックテスト（プログラムから）
```python
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
# result.history / result.trades / result.metrics を参照
```

### 特徴量生成（features テーブルへ）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {count}")
```

### シグナル生成（signals テーブルへ）
```python
from kabusys.strategy import generate_signals
count = generate_signals(conn, target_date=date(2024,1,31))
print(f"signals generated: {count}")
```

### J-Quants データ取得 & 保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.config import settings

records = fetch_daily_quotes(date_from=..., date_to=...)
saved = save_daily_quotes(conn, records)
print(f"saved {saved} price records")
```

### ニュース収集
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
new_counts = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set_of_codes)
```

---

## コア API の説明（概要）

- kabusys.config.settings
  - 環境変数をラップし、必須チェックやデフォルトの提供を行う。自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可）。

- strategy.build_features(conn, target_date)
  - research の factor 計算を呼び出し、ユニバースフィルタ・Z スコア正規化・features テーブルへの UPSERT を行う。

- strategy.generate_signals(conn, target_date, threshold=0.6, weights=None)
  - features と ai_scores を組み合わせ final_score を計算し BUY/SELL の signals を挿入。Bear レジームでは BUY を抑制。

- portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes / apply_sector_cap / calc_regime_multiplier
  - 候補選定・重み付け・株数算出・セクターキャップ・レジームによる投下資金調整。

- backtest.run_backtest(conn, start_date, end_date, ...)
  - DuckDB のコピーを作成してインメモリでバックテストを実行。ポートフォリオシミュレータ、signals の読み書き、サイジング〜約定フローをシミュレーションする。

- data.jquants_client
  - J-Quants API との通信（レート制御、リトライ、401 リフレッシュ対応）と DuckDB への保存ユーティリティを提供。

- data.news_collector
  - RSS フィードの取得・前処理・記事保存・銘柄抽出（SSRF/サイズ制限/トラッキングパラメータ削除等の安全対策あり）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージヘッダ（version 等）
- config.py — 環境変数・設定管理
- data/
  - jquants_client.py — J-Quants API クライアント & データ保存
  - news_collector.py — RSS ニュース収集・保存・銘柄抽出
  - (schema.py, calendar_management.py などを想定)
- research/
  - factor_research.py — momentum / volatility / value 計算
  - feature_exploration.py — forward returns / IC / summary
- strategy/
  - feature_engineering.py — features の構築
  - signal_generator.py — シグナル生成ロジック
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・cap・aggregate cap
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- backtest/
  - engine.py — バックテストエンジン（run_backtest）
  - simulator.py — PortfolioSimulator（約定ロジック・マークトゥマーケット)
  - metrics.py — バックテスト評価指標計算
  - run.py — CLI エントリポイント
  - clock.py — （将来用）模擬時計
- execution/ — 実トレード（kabu）連携層（骨組み）
- monitoring/ — Slack 等の監視・通知（骨組み）

各モジュールには docstring と設計注記が豊富に含まれており、仕様（StrategyModel.md / PortfolioConstruction.md / BacktestFramework.md 等）に従った実装方針が記載されています。

---

## 注意事項・運用上のヒント

- バックテスト用 DB は本番 DB と分離してください。run_backtest は本番 DB から必要な期間のデータをコピーして in-memory DuckDB にロードしますが、ETL の実行順序・データの整合性に注意が必要です。
- features / ai_scores / market_regime 等のテーブルは、シグナル生成に直接影響します。ルックアヘッドを避けるため、データの fetched_at / report_date に留意してください。
- J-Quants API の利用はレート制限が厳格に設定されています（デフォルト 120 req/min）。大量取得時はレート制御に留意してください。
- ニュース収集では SSRF 対策・受信サイズ制限等を実装していますが、フィードの信頼性や文字コード問題などに注意してください。

---

README は以上です。追加で「.env.example」のテンプレート、requirements.txt、あるいは各モジュールの詳細な API ドキュメント（引数・戻り値の型例）を生成することもできます。必要であれば作成します。