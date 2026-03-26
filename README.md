# KabuSys

日本株向け自動売買 / 研究フレームワーク（軽量なバックテスト、データETL、シグナル生成モジュール群）

---

## 概要

KabuSys は日本株投資戦略の研究からバックテスト、運用までをサポートする Python パッケージです。  
主な設計方針は以下の通りです。

- 研究（ファクター計算）と実運用（シグナル → 発注）を分離
- DuckDB を中心としたローカル DB によるデータ管理
- J-Quants 等外部データソースからの ETL を想定（レート制限・リトライ・トークン更新対応）
- バックテストはメモリ内シミュレータで再現性の高い評価を提供

現在の実装には、ファクター計算、特徴量構築、シグナル生成、ポートフォリオ構築、ポジションサイジング、バックステストエンジン、ニュース収集などの主要コンポーネントが含まれます。

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（価格、財務、上場銘柄、カレンダー）
  - RSS ベースのニュース収集（SSRF 対策、トラッキング除去、記事ID 重複排除）
  - DuckDB への冪等保存ユーティリティ
- 研究用モジュール
  - ファクター計算（Momentum / Volatility / Value / Liquidity）
  - ファクター探索（IC 計算、将来リターン計算、統計サマリー）
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング
  - ファクター正規化・ユニバースフィルタ・features テーブルへの UPSERT
- シグナル生成
  - ファクター + AI スコア統合による final_score 算出
  - BUY / SELL シグナルの生成（Bear レジーム抑制、ストップロス等）
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重/リスクベースのポジションサイジング
  - セクター集中制限（sector cap）、レジーム乗数
- バックテスト
  - インメモリ DuckDB によるバックテスト用データ準備
  - 日次ループのシミュレーション（スリッページ・手数料モデル、部分約定）
  - バックテストメトリクス（CAGR、Sharpe、MaxDD、勝率、Payoff 等）
  - CLI 実行エントリポイント（python -m kabusys.backtest.run）
- ユーティリティ
  - 環境設定管理（.env 自動読み込み / 必須検査）
  - RSS 前処理（URL 除去 / 正規化 / 日時パース）
  - セキュリティ対策（SSRF, gzip/サイズ制限, defusedxml）

---

## 必要要件

- Python 3.10+
- 主要依存ライブラリ（最低限）
  - duckdb
  - defusedxml

（その他、実行する機能に応じて標準ライブラリ以外の追加パッケージが必要になる場合があります）

---

## インストール

開発環境での利用例:

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   pip install -e .
   ```

注意: 実プロジェクトでは requirements.txt / poetry / pyproject.toml を用意して依存管理することを推奨します。

---

## 環境変数と設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（優先順位: OS 環境変数 > .env.local > .env）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:

- J-Quants / データ
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabu ステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- Slack 通知
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- 実行モード / ログ
  - KABUSYS_ENV (development | paper_trading | live)  デフォルト: development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) デフォルト: INFO

設定は `from kabusys.config import settings` でアクセスできます（プロパティとして提供）。

---

## セットアップ手順（DB 初期化 / データ投入の流れ）

このプロジェクトは DuckDB を中心に動作します。運用には事前にスキーマ作成とデータ投入が必要です（schema 初期化関数は `kabusys.data.schema.init_schema` を想定しています）。

概略手順:

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   （init_schema が存在しない場合は、プロジェクトのスキーマ定義に従ってテーブルを作成するスクリプトを用意してください）

2. J-Quants からデータ取得（例）
   ```python
   from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
   from kabusys.config import settings

   token = get_id_token()
   records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
   save_daily_quotes(conn, records)
   ```

3. 上場銘柄・カレンダー・財務データ等も同様に取得して保存

4. features の構築（研究 → features テーブル）
   ```python
   from kabusys.strategy.feature_engineering import build_features
   build_features(conn, target_date)
   ```

5. AI スコアや positions を適宜用意する（シグナル生成で参照）

---

## 使い方（主要ユースケース）

### バックテストの実行（CLI）

duckdb を初期化し、prices_daily / features / ai_scores / market_regime / market_calendar などが準備できていることを前提に実行します。

例:
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --db data/kabusys.duckdb \
  --allocation-method risk_based \
  --max-positions 10 \
  --lot-size 100
```

出力例（要約）:
- CAGR, Sharpe Ratio, Max Drawdown, Win Rate, Payoff Ratio, Total Trades

### 特徴量構築（コード例）

features を計算して DB に保存する:
```python
from datetime import date
import duckdb
from kabusys.strategy.feature_engineering import build_features
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 31))
print(f"upserted {count} features")
conn.close()
```

### シグナル生成（コード例）

features と ai_scores をもとにシグナルを作成:
```python
from datetime import date
from kabusys.strategy.signal_generator import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"generated {n} signals")
conn.close()
```

### ニュース収集ジョブ（RSS）

RSS を取得して raw_news に保存:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", ...}  # stocks の code セット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
conn.close()
```

---

## 重要な設計上の注意点

- バックテストでは「ルックアヘッドバイアス」を避けるため、常に target_date 時点で利用可能なデータだけを使う設計になっています。
- J-Quants API へのリクエストはレート制限（120 req/min）に従うよう内部でスロットリングしています。
- XML パースには defusedxml を使用して XML Bomb 等の脅威に対処しています。
- RSS 取得には SSRF 対策（リダイレクト先の検査、プライベートアドレス拒否）とサイズ上限があります。

---

## 主要ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数・設定管理
  - data/
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS ニュース収集・保存ロジック
    - (schema.py を想定) — DuckDB スキーマ初期化・DDL（プロジェクトに実装する必要あり）
  - research/
    - factor_research.py — Momentum/Volatility/Value 等ファクター計算
    - feature_exploration.py — IC / 将来リターン / 統計サマリー
  - strategy/
    - feature_engineering.py — features の構築（正規化・フィルタ）
    - signal_generator.py — final_score 計算と BUY/SELL シグナル生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 株数計算（等配分・スコア配分・リスクベース）
    - risk_adjustment.py — セクター上限・レジーム乗数
  - backtest/
    - engine.py — バックテスト全体ループ
    - simulator.py — 擬似約定・ポートフォリオ管理
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI エントリポイント
  - portfolio/..., execution/, monitoring/ — 実取引・監視に関するプレースホルダ（実装拡張可能）

---

## よくある質問 / トラブルシューティング

- .env の自動読み込みが邪魔なとき:
  - テストや一時的に無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のスキーマやテーブルが無いとき:
  - `kabusys.data.schema.init_schema`（プロジェクトで提供）を使って初期化してください。存在しない場合はプロジェクトのスキーマ定義を実装してください。
- J-Quants の認証エラー:
  - `JQUANTS_REFRESH_TOKEN` が正しく設定されているか確認。401 受信時はモジュール側で自動リフレッシュを試みます。

---

## 貢献 / 拡張のヒント

- stocks テーブルに銘柄別単元（lot_size）を追加すると、position_sizing の lot_map 拡張が容易になります。
- ニュースの NLP 処理（言語モデルを用いた記事スコア化）は ai_scores テーブルとの連携ポイントです。
- execution 層を実装し、kabuステーション API 経由で自動発注する際はテスト用のペーパートレードモード（KABUSYS_ENV=paper_trading）を活用してください。

---

この README は現状のコードベース（主要モジュール）を元に作成しています。実運用・デプロイ時はスキーマ定義、運用用設定ファイル、依存管理ファイル（requirements.txt / pyproject.toml）を整備してください。