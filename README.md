# KabuSys

KabuSys は日本株向けの自動売買フレームワークです。データ収集（J-Quants / RSS）、特徴量計算、シグナル生成、ポートフォリオ構築、バックテスト、ニュース集約までを含む一連のモジュールを提供します。研究（research）と本番（execution/monitoring）を分離した設計で、DuckDB をデータストアとして想定しています。

---

## 主な特徴

- J-Quants API 経由の株価・財務データ取得（レート制御・リトライ・トークン自動更新対応）
- RSS からのニュース収集と記事→銘柄の紐付け機能（SSRF 対策・トラッキング除去・重複排除）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ / 流動性）
- 特徴量正規化（Zスコアクリップ）と features テーブルへの格納処理
- シグナル生成（ファクター + AI スコア統合、Bear レジーム抑制、EXIT 条件）
- ポートフォリオ構築（候補選定、等配分／スコア配分／リスクベース配分、セクターキャップ）
- バックテストフレームワーク（擬似約定、スリッページ・手数料モデル、評価指標）
- 冪等性・トランザクション制御を考慮した DB 書き込み処理

---

## 依存関係（最低限）

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - defusedxml

（このリポジトリ内で外部モジュールを利用しているため、上記以外のパッケージが必要になることがあります。pyproject.toml / requirements.txt がある場合はそちらを参照してください。）

---

## セットアップ手順

1. リポジトリをクローン：
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）：
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール：
   ```bash
   pip install -U pip
   pip install duckdb defusedxml
   # 開発インストール（パッケージ化されている場合）
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると、自動で読み込まれます。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。

   推奨の最低限環境変数（.env の例）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_refresh_token

   # kabuステーション API（必要な場合）
   KABU_API_PASSWORD=your_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack 通知
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス（任意。デフォルト: data/kabusys.duckdb）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境 / ログ
   KABUSYS_ENV=development   # development / paper_trading / live
   LOG_LEVEL=INFO
   ```

   `kabusys.config.Settings` で要求される必須キー:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   ※不足すると起動 / 実行時に ValueError が発生します。

5. DuckDB スキーマ初期化
   - スキーマ初期化関数（例: `kabusys.data.schema.init_schema`）を使って DB を作成してください（schema 定義スクリプトは別途用意されている想定）。  
   例:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

6. データ取得（例）
   - J-Quants から株価や財務データを取得して DuckDB に保存する処理は `kabusys.data.jquants_client` 内にある関数を利用します。
   - ニュース収集は `kabusys.data.news_collector.run_news_collection(conn, ...)` を利用します。

---

## 使い方（主要コマンド・API）

### バックテストの実行（CLI）
バックテスト用のエントリポイントが用意されています。

例（コマンドライン）:
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2024-12-31 \
  --cash 10000000 \
  --db data/kabusys.duckdb \
  --allocation-method risk_based \
  --max-positions 10 \
  --lot-size 100
```

このスクリプトは DuckDB に事前に prices_daily, features, ai_scores, market_regime, market_calendar 等が投入されていることを前提とします。

### ライブラリ API の例

- 特徴量構築（features へ UPSERT）
```python
from datetime import date
import duckdb
from kabusys.strategy.feature_engineering import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 10))
print(f"upserted {n} features")
```

- シグナル生成（signals テーブルへ書き込み）
```python
from kabusys.strategy.signal_generator import generate_signals
count = generate_signals(conn, target_date=date(2024, 1, 10))
print(f"generated {count} signals")
```

- バックテスト実行（プログラムから）
```python
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
res = run_backtest(conn, start_date=date(2023, 1, 4), end_date=date(2023, 12, 29))
print(res.metrics)
```

- ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
results = run_news_collection(conn, sources=None, known_codes=None)
print(results)
```

---

## 主要モジュールと責務（要約）

- kabusys.config
  - .env / 環境変数の自動読み込みと設定オブジェクト（Settings）

- kabusys.data
  - jquants_client.py : J-Quants API クライアント（レート制御・リトライ・保存関数）
  - news_collector.py : RSS 収集と raw_news / news_symbols への保存
  - （その他）schema / calendar_management 等（スキーマ初期化・営業日取得など）

- kabusys.research
  - factor_research.py : モメンタム / バリュー / ボラティリティ 等のファクター計算
  - feature_exploration.py : IC / 将来リターン計算 / 統計サマリー

- kabusys.strategy
  - feature_engineering.py : ファクターの正規化と features テーブルへの書き込み
  - signal_generator.py : final_score 計算、BUY/SELL シグナル生成、signals テーブルへ書き込み

- kabusys.portfolio
  - portfolio_builder.py : 候補抽出・重み計算（等配分 / スコア配分）
  - position_sizing.py : 株数決定、aggregate cap、単元丸め
  - risk_adjustment.py : セクターキャップ・レジーム乗数

- kabusys.backtest
  - engine.py : バックテスト全体のループと運用ロジック
  - simulator.py : 擬似約定・ポートフォリオ状態管理（PortfolioSimulator）
  - metrics.py : バックテスト評価指標計算
  - run.py : CLI ラッパー

- kabusys.execution / monitoring
  - 実行層・監視のプレースホルダー（実運用用コードを配置）

---

## ディレクトリ構成

（リポジトリ内の主要ファイルを抜粋したツリー）
```
src/
  kabusys/
    __init__.py
    config.py
    data/
      jquants_client.py
      news_collector.py
      ... (schema, calendar_management など)
    research/
      factor_research.py
      feature_exploration.py
      __init__.py
    strategy/
      feature_engineering.py
      signal_generator.py
      __init__.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py
    backtest/
      engine.py
      simulator.py
      metrics.py
      run.py
      clock.py
      __init__.py
    execution/
      __init__.py
    monitoring/
      ... (監視用コード)
```

各ファイルは README 内の「主要モジュールと責務」に記載した役割を持ちます。詳しい実装や追加のユーティリティは各モジュールの docstring を参照してください。

---

## 開発メモ / 注意点

- Python バージョンは 3.10 以上を強く推奨（PEP 604 の union 型記法などを利用）。
- 環境変数は .env / .env.local をプロジェクトルートから自動読み込みします。`.env.local` は `.env` の値を上書きできます（OS 環境変数は上書きされません）。
- KABUSYS_ENV の有効値: "development", "paper_trading", "live"。設定ミスは起動時に ValueError が出ます。
- J-Quants の API 呼び出しはレート制限（120 req/min）に基づいた固定間隔スロットリングとリトライを備えています。認証は refresh_token → id_token フローで自動更新されます。
- ニュース収集は SSRF 対策、gzip 展開サイズ検査、XML パースの安全化（defusedxml）を行っています。
- バックテストは DuckDB 内のスナップショット（インメモリコピー）を使って本番データを汚染しない設計です。

---

## 貢献・問い合わせ

- バグ報告や機能要望は issue を立ててください。
- 新しい機能を追加する場合は、対応するユニットテストと docstring（挙動説明）を追加してください。

---

README はここまでです。必要があれば、README に含める具体的な .env.example ファイルや schema 初期化手順、サンプルデータ取得スクリプトのテンプレートを追加で生成します。どの情報を追記しますか？