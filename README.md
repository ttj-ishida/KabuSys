# KabuSys

KabuSys は日本株向けの自動売買・リサーチ基盤です。DuckDB を中心としたデータパイプライン、ファクター計算、シグナル生成、ポートフォリオ構築、バックテストシミュレータを含みます。J-Quants や RSS ニュース等のデータ取得機能や、冪等な DB 保存ロジック、バックテスト用の精密な約定モデルを備えています。

---

## 主な特徴 (Features)

- データ取得・ETL
  - J-Quants API クライアント（ページネーション・トークン自動リフレッシュ・レート制御・リトライ）
  - RSS ニュース収集（SSRF対策・トラッキング除去・記事ID生成）
  - DuckDB への冪等保存 (ON CONFLICT / INSERT ... DO UPDATE/DO NOTHING)

- 研究・特徴量
  - Momentum / Volatility / Value などのファクター計算（DuckDB SQL＋Python）
  - Zスコア正規化・ユニバースフィルタ・features テーブルへの UPSERT

- 戦略・シグナル生成
  - 正規化済み特徴量と AI スコアの統合による final_score 計算
  - Bear レジーム抑制、BUY/SELL シグナル生成、signals テーブルへの冪等書込

- ポートフォリオ構築
  - 候補選定、等金額/スコア加重、リスクベースのサイジング
  - セクター集中制限、レジーム乗数、単元丸め、集約キャップ処理

- バックテスト
  - 約定モデル（スリッページ・手数料・部分約定）
  - 日次スナップショット記録、トレード履歴
  - 各種メトリクス（CAGR、Sharpe、MaxDD、WinRate、Payoff）
  - CLI での実行可能なバックテストランナー

---

## 動作環境と前提

- Python 3.10 以上（型ヒントで `X | None` を使用）
- 必要な外部ライブラリ（主なもの）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）を行う場合は適切な API トークンとネットワーク環境が必要

（プロジェクトには pyproject.toml / requirements.txt がある想定で、実際のパッケージ依存は環境に合わせて追加してください。）

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストールします（最低限の例）:

   ```bash
   pip install "duckdb" "defusedxml"
   ```

   もしプロジェクトに packaging ファイルがあれば:

   ```bash
   pip install -e .
   # または
   pip install -r requirements.txt
   ```

3. 環境変数（.env）を設定します。
   プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと、自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   .env の例:

   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB paths (任意)
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 動作モード
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマの初期化  
   アプリ内のスキーマ初期化関数を使って DB ファイルを作成してください（実装は `kabusys.data.schema.init_schema` を参照）。

   例:

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

   ※ バックテストを実行するには prices_daily / features / ai_scores / market_regime / market_calendar 等が事前に投入されている必要があります。

---

## 使い方

以下は代表的な操作の例です。

- バックテスト（CLI）

  `src/kabusys/backtest/run.py` がエントリポイントになっています。モジュールとして実行します。

  ```bash
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb \
    --allocation-method risk_based --lot-size 100
  ```

  オプション:
  - --start/--end: 日付（YYYY-MM-DD）
  - --cash: 初期資金（JPY）
  - --slippage / --commission: スリッページ・手数料率
  - --allocation-method: equal | score | risk_based
  - --max-positions / --max-utilization / --risk-pct / --stop-loss-pct 等はヘルプを参照

- ファクター構築（programmatic）

  features を構築する関数を呼び出して DuckDB に書き込みます。

  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy.feature_engineering import build_features
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 31))
  print("upserted:", count)
  conn.close()
  ```

- シグナル生成（programmatic）

  ```python
  from kabusys.strategy.signal_generator import generate_signals
  from kabusys.data.schema import init_schema
  import duckdb
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  n_signals = generate_signals(conn, target_date=date(2024, 1, 31))
  print("signals:", n_signals)
  conn.close()
  ```

- J-Quants から日足取得 & 保存

  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
  saved = save_daily_quotes(conn, records)
  print("saved raw prices:", saved)
  conn.close()
  ```

- ニュース収集の実行

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn)
  print(results)  # {source_name: 新規保存数}
  conn.close()
  ```

---

## 主要モジュールとファイル構成

（リポジトリ内 `src/kabusys` 配下の主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロード・Settings クラス
  - data/
    - jquants_client.py — J-Quants API クライアント、保存関数
    - news_collector.py — RSS 収集・記事保存・銘柄抽出
    - (schema.py 等は DB スキーマ関連)
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計要約
  - strategy/
    - feature_engineering.py — features の作成 / 正規化
    - signal_generator.py — final_score 計算・BUY/SELL シグナル生成
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数決定（risk_based / equal / score）
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - backtest/
    - engine.py — バックテスト全体ループ（run_backtest）
    - simulator.py — 約定モデル・ポートフォリオシミュレータ
    - metrics.py — バックテストメトリクス
    - run.py — CLI エントリポイント
  - execution/ (実売買 API との連携用スペース)
  - monitoring/ (監視・アラート用コード格納想定)

この README にある内容はコード内のドキュメント（docstring）に基づいてまとめています。各モジュールの関数や引数についてはソースコード中の docstring を参照してください。

---

## 開発上の注意点

- Look-ahead bias（先見バイアス）防止の設計を意識しており、各処理は target_date 時点で利用可能なデータのみを使用する方針です。
- DB への挿入は冪等性を重視していますが、バックテストに使用する DB を作成・投入する際は事前に prices_daily / features / ai_scores / market_regime / market_calendar 等の整備が必要です。
- 設定値は環境変数から取得されます。自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

必要があれば、README に含める具体的な .env.example のテンプレートや、要件ファイル（requirements.txt）の候補リスト、DB スキーマ定義（schema.py の抜粋）なども作成します。どの情報を優先して追加しますか？