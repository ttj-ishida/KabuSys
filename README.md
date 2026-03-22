# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
市場データ収集（J-Quants）、ETL、特徴量エンジニアリング、シグナル生成、バックテスト、ニュース収集、発注/約定（execution 層）など、アルゴリズム取引システムの主要機能を含みます。

主な設計方針:
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ使用）
- DuckDB をデータストア（ローカル）として使用
- 冪等性（ON CONFLICT / トランザクション）を重視
- 外部 API 呼び出し（発注など）は明示的に分離

---

## 機能一覧

- data/
  - J-Quants API クライアント（fetch / save）
  - RSS ニュース収集（SSRF対策・ID生成・銘柄抽出）
  - DuckDB スキーマ定義と初期化（init_schema）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - 汎用統計ユーティリティ（Zスコア正規化 等）
- research/
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（将来リターン計算・IC・統計サマリ）
- strategy/
  - 特徴量エンジニアリング（build_features：features テーブル生成）
  - シグナル生成（generate_signals：features + ai_scores → signals）
- backtest/
  - ポートフォリオシミュレータ（擬似約定・スリッページ/手数料）
  - バックテストエンジン（run_backtest）
  - メトリクス計算（CAGR, Sharpe, MaxDD, 勝率 等）
  - CLI 実行エントリ（python -m kabusys.backtest.run）
- execution/, monitoring/ （発注・監視の拡張ポイント）

---

## 必要環境 / 依存パッケージ

- Python 3.10 以上（型注釈で PEP 604 の `X | Y` を使用）
- 以下の主要パッケージ（例）
  - duckdb
  - defusedxml
- 追加で使用するパッケージがある場合は requirements.txt を用意してください。

例（最低限）
```
pip install duckdb defusedxml
```

開発時は editable install を推奨:
```
pip install -e .
```

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートに置く `.env` / `.env.local` から読み込まれます（自動ロード）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード（execution 用）
- SLACK_BOT_TOKEN       : Slack 通知用 bot token
- SLACK_CHANNEL_ID      : Slack 通知用 channel id

オプション / デフォルト:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG | INFO | ...) — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 で自動 .env ロード無効化

settings は kabusys.config.settings から参照できます。

例 .env（プロジェクトルートに置く）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があれば）pip install -r requirements.txt
4. パッケージを開発モードでインストール（任意）
   - pip install -e .
5. 環境変数を設定（.env をプロジェクトルートに作成）
6. DuckDB スキーマを初期化
   - Python REPL/スクリプトで:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - :memory: を指定するとインメモリ DB を初期化できます（テスト用）。

---

## 使い方（代表的な例）

1. DuckDB の初期化（上記参照）

2. データ収集 / 保存（例: J-Quants）
   ```
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   token = get_id_token()  # settings.jquants_refresh_token を使用
   records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
   saved = save_daily_quotes(conn, records)
   conn.close()
   ```

3. ETL パイプライン（部分的に提供。DataPlatform.md に従い run_prices_etl 等を利用）
   - data.pipeline モジュールに ETL 関数群があるため、target_date を指定して実行します。

4. 特徴量構築
   ```
   from datetime import date
   import duckdb
   from kabusys.strategy import build_features

   conn = duckdb.connect("data/kabusys.duckdb")
   n = build_features(conn, target_date=date(2024, 1, 31))
   print(f"built features: {n} rows")
   conn.close()
   ```

5. シグナル生成
   ```
   from kabusys.strategy import generate_signals
   from datetime import date
   import duckdb

   conn = duckdb.connect("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2024,1,31))
   conn.close()
   ```

6. バックテスト（CLI）
   - 事前に prices_daily, features, ai_scores, market_regime, market_calendar が DB に存在する必要があります。
   - 実行例:
     ```
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2024-12-31 \
       --cash 10000000 \
       --slippage 0.001 \
       --commission 0.00055 \
       --max-position-pct 0.20 \
       --db data/kabusys.duckdb
     ```
   - または Python API:
     ```
     from kabusys.backtest.engine import run_backtest
     from kabusys.data.schema import init_schema
     from datetime import date

     conn = init_schema("data/kabusys.duckdb")
     result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2024,12,31))
     conn.close()

     # result.history, result.trades, result.metrics を参照
     ```

7. ニュース収集
   ```
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   known_codes = {"7203", "6758", ...}  # 既知銘柄コードセット
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   conn.close()
   ```

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得・保存）
  - news_collector.py      — RSS 収集・記事保存・銘柄抽出
  - pipeline.py            — ETL パイプライン
  - schema.py              — DuckDB スキーマ定義と init_schema()
  - stats.py               — 統計ユーティリティ（zscore_normalize）
- research/
  - __init__.py
  - factor_research.py     — ファクター計算 (momentum/volatility/value)
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- strategy/
  - __init__.py
  - feature_engineering.py — features テーブル構築
  - signal_generator.py    — final_score 計算 / signals 生成
- backtest/
  - __init__.py
  - engine.py              — run_backtest の実装
  - simulator.py           — PortfolioSimulator（擬似約定）
  - metrics.py             — バックテスト評価指標
  - run.py                 — CLI エントリポイント
  - clock.py               — SimulatedClock（将来拡張用）
- execution/               — 発注・実行層（拡張）
- monitoring/              — 監視・通知（拡張）

---

## 開発 / テストに関する注意点

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml が見つかるディレクトリ）を基準に行われます。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のスキーマ初期化は idempotent（init_schema は既存テーブルを上書きしない）です。
- 外部 API（J-Quants等）呼び出しはレート制御やリトライロジックを内蔵しています。トークン周りは settings.jquants_refresh_token を利用します。
- ニュース取得は SSRF や XML Bomb 等に対する保護を組み込んでいます（defusedxml, ホスト検証, サイズ制限 等）。

---

## ライセンス・貢献

（ここにライセンス、コントリビューションガイドライン、コードスタイルや PR の流儀を記載してください。プロジェクト固有のポリシーがあれば追記してください。）

---

README に書かれている API や CLI の詳細、設計ドキュメント（StrategyModel.md、DataPlatform.md、BacktestFramework.md 等）に基づく追加仕様がプロジェクトに含まれている場合は、そちらも参照してください。必要であれば README にサンプルの .env.example や requirements.txt のテンプレートを追加できます。