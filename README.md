# KabuSys

日本株向けの自動売買 / 研究プラットフォームのコアライブラリです。本リポジトリはデータ取得・ファクター計算・シグナル生成・ポートフォリオ構築・バックテストやニュース収集など、アルゴリズムトレーディングに必要な主要コンポーネントを含みます。

---

## 概要

KabuSys は次の目的を持つ Python パッケージです。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- ファクター（モメンタム、ボラティリティ、バリュー等）の計算および正規化
- AI スコア等を統合したシグナル生成（BUY / SELL）
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制限）
- バックテストフレームワーク（擬似約定、スリッページ・手数料モデル、評価指標）
- ニュース収集（RSS）と銘柄コード抽出
- 環境変数 / 設定管理

設計方針として、ルックアヘッドバイアス回避・冪等性（DB 操作）・テスト容易性・ネットワーク安全対策（RSS の SSRF 対策等）に配慮しています。

---

## 主な機能一覧

- config
  - .env/.env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得ユーティリティ
- data
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークン自動更新）
  - news_collector: RSS 収集、前処理、DB 保存、銘柄抽出（SSRF 対策、gzip 上限等）
- research
  - factor_research: momentum / volatility / value 等のファクター計算（DuckDB を使用）
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy
  - feature_engineering: 生ファクターの正規化・features テーブルへの保存
  - signal_generator: features と ai_scores を統合して BUY/SELL を生成し signals テーブルへ保存
- portfolio
  - portfolio_builder: 候補選定・配分重み（等配分・スコア配分）
  - position_sizing: 株数決定（risk_based / equal / score）、単元丸め、aggregate cap
  - risk_adjustment: セクター上限適用、レジーム乗数
- backtest
  - engine: バックテストループ（シグナル生成 → 擬似約定 → マークトゥマーケット → サイジング）
  - simulator: PortfolioSimulator（擬似約定・履歴・約定記録）
  - metrics: バックテスト評価指標（CAGR、Sharpe、MaxDD、勝率等）
  - run: CLI エントリポイント（start/end/params 指定可能）
- monitoring / execution
  - 基盤用の名前空間（実運用連携や監視用処理を置く想定）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化

   - 例（venv）:
     ```
     python -m venv .venv
     source .venv/bin/activate   # macOS / Linux
     .venv\Scripts\activate      # Windows
     ```

2. 必要パッケージをインストール

   最低限必要な外部依存（本リポジトリに requirements.txt がない場合の例）:
   ```
   pip install duckdb defusedxml
   ```

   実運用ではさらに requests 等が必要になる場合があります（本コードは urllib を使用）。

3. プロジェクトルートに .env を作成

   config モジュールはプロジェクトルート（.git または pyproject.toml を有するディレクトリ）を自動検出して `.env` / `.env.local` を読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例（.env の最小例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ準備

   バックテストや各処理は DuckDB の特定テーブル（prices_daily, features, ai_scores, market_regime, market_calendar, stocks, positions, signals, raw_prices, raw_financials, raw_news, news_symbols など）を期待します。`kabusys.data.schema.init_schema()` を利用してスキーマを初期化するユーティリティ（別ファイル）を呼ぶか、事前に DB を用意してください。

---

## 使い方

### 1) バックテスト（CLI）

バックテスト用のエントリポイントが用意されています（python -m kabusys.backtest.run）。

例:
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --db path/to/kabusys.duckdb
```

指定可能な主なオプション:
- --start / --end : 期間（YYYY-MM-DD）
- --cash : 初期資金（円）
- --slippage / --commission : スリッページ・手数料率
- --allocation-method : equal | score | risk_based
- --max-positions / --lot-size / --risk-pct / --stop-loss-pct
- --db : DuckDB ファイルパス（必須）

バックテスト実行後、CAGR や Sharpe、Max Drawdown、勝率、約定履歴等が標準出力に表示されます。

### 2) Python API の利用例

DuckDB 接続（init_schema を想定）を作成してモジュール関数を呼ぶことができます。

- features のビルド:
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 31))
conn.close()
print("upserted features:", count)
```

- シグナル生成:
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
n = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
conn.close()
print("generated signals:", n)
```

- ニュース収集（RSS）ジョブ:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
res = run_news_collection(conn)  # DEFAULT_RSS_SOURCES を使用
conn.close()
print(res)  # {source_name: saved_count, ...}
```

### 3) J-Quants からのデータ取得と保存

jquants_client によりページネーション・リトライ・トークンリフレッシュを伴う取得が可能です。取得 → save_* 系関数で DuckDB に保存します。

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
conn.close()
print("saved rows:", saved)
```

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, default: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, default: data/kabusys.duckdb)
- SQLITE_PATH (任意, default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) (任意, default: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) (任意, default: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます。

config.Settings クラス経由で安全に取得できます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## 開発時の注意 / 実装上のポイント

- DuckDB を中心に設計しており、バックテストでは本番 DB をコピーして in-memory DuckDB を作成し検証します（データの汚染を防ぐ）。
- feature_engineering / signal_generator / portfolio の関数はできるだけ純粋関数（副作用が少ない）で設計され、テストが容易です。
- jquants_client はレート制限・リトライ・401→トークンリフレッシュのロジックを実装しています。ページネーション間で id_token をキャッシュ共有します。
- news_collector は RSS の安全性（SSRF、gzip/サイズ上限、XML 攻撃対策）を考慮して実装されています。
- バックテストでは SELL を優先して約定し、BUY は残余資金で部分約定する設計です。単元（lot_size）の丸め処理や aggregate cap（利用可能現金の上限）も考慮します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - jquants_client.py
      - news_collector.py
      - (schema.py, stats.py, calendar_management.py 等の補助モジュールを想定)
    - research/
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - feature_engineering.py
      - signal_generator.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - backtest/
      - engine.py
      - simulator.py
      - metrics.py
      - run.py
      - clock.py
    - execution/        (発注層 — 実装は別途)
    - monitoring/      (監視 / メトリクス収集用 namespace)
    - portfolio/__init__.py
    - research/__init__.py
    - strategy/__init__.py
    - backtest/__init__.py

---

## よくある質問（FAQ）

Q: バックテスト用の DB はどう用意する？
- A: prices_daily・raw_prices・raw_financials・features・ai_scores・market_regime・market_calendar・stocks などのテーブルが必要です。`kabusys.data.schema.init_schema()` でスキーマを作り、外部データ（J-Quants 等）を取り込んでください。

Q: .env の自動読み込みを止めたい
- A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化できます（テスト用途など）。

Q: 実運用（live）で安全に使うには？
- A: KABUSYS_ENV を `live` に設定すると settings.is_live が True になりますが、実際の発注・エグゼキューション層（execution）や監視（monitoring）を適切に実装・監査したうえで運用してください。本パッケージはエンジン・アルゴリズム基盤を提供しますが、実マーケットに接続する場合は充分な安全対策が必要です。

---

以上がリポジトリの概観と基本的な利用方法です。さらに詳細な設計（StrategyModel.md / PortfolioConstruction.md / BacktestFramework.md 等）に基づく実装方針やスキーマ定義は別ドキュメントを参照してください。必要であれば README を追加で拡張してコマンド例やスキーマ定義、API リファレンスを付け加えます。