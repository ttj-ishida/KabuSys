# KabuSys

日本株向けの自動売買・研究プラットフォームのコアライブラリです。  
バックテスト、ファクター計算、シグナル生成、データ収集（J-Quants / RSS）、ポートフォリオ構築・サイジング、擬似約定シミュレータなどを含みます。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 市場データ（OHLCV / 財務 / カレンダー）を取得して DuckDB に保存する ETL
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- 特徴量（features）の正規化・作成
- シグナル生成（BUY / SELL）ロジック
- ポートフォリオ構築（候補選定、重み付け、サイジング、セクター制限、レジーム調整）
- バックテストエンジン（擬似約定・手数料・スリッページモデル・メトリクス）
- ニュース収集（RSS → raw_news、銘柄抽出）
- 環境変数ベースの設定管理（.env ロード機能）

このリポジトリはライブラリ（src/kabusys）として設計され、研究と運用の双方で利用できるよう分離された Pure functions / DB 操作を併用します。

---

## 主な機能一覧

- data/
  - J-Quants API クライアント（取得・リトライ・レート制限・保存）
  - RSS ニュース収集と記事→銘柄紐付け
- research/
  - ファクター計算（mom, vol, value）
  - 将来リターン・IC 計算・統計サマリー
- strategy/
  - feature_engineering.build_features(conn, target_date)
  - signal_generator.generate_signals(conn, target_date, ...)
- portfolio/
  - 候補選定・重み計算（等配分・スコア加重）
  - position_sizing.calc_position_sizes(...)
  - リスク制御（セクターキャップ、レジーム乗数）
- backtest/
  - 実行用 engine.run_backtest(...)
  - PortfolioSimulator（擬似約定）
  - メトリクス計算（CAGR, Sharpe, MaxDD, WinRate, Payoff 等）
  - CLI エントリポイント: python -m kabusys.backtest.run
- config: 環境変数を .env/.env.local から自動ロード（自動ロードは無効化可）

---

## 必要環境

- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - defusedxml

（パッケージはプロジェクトの requirements.txt / pyproject.toml を参照してください。存在しない場合は上記を pip でインストールしてください。）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはプロジェクトに requirements.txt があれば `pip install -r requirements.txt`
pip install -e .
```

---

## 環境変数（必須 / 任意）

config.Settings から以下の環境変数を参照します。プロジェクトルートの `.env` / `.env.local` を使って設定できます（自動ロードあり。無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード（execution 層使用時）
- SLACK_BOT_TOKEN — Slack 通知用（必要な場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — one of: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（テスト時等）

設定例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```
   pip install -e .
   # または明示的に
   pip install duckdb defusedxml
   ```

4. 環境変数を .env に配置（プロジェクトルート）
   - .env.example があれば参照してください。

5. DuckDB スキーマ初期化
   - データベーススキーマを作成する初期化関数（kabusys.data.schema.init_schema）を使って DB を準備します。
   - 既存 file path を指定する場合は Settings.duckdb_path を変更するか init_schema にパスを渡します。

（注）schema 初期化や ETL の手順は別ドキュメント / スクリプトで管理されている前提です。プロジェクトに含まれている data/schema モジュールを参照してください。

---

## 使い方（主要ワークフロー）

1. データ取得（J-Quants）
   - API からデータを取得して DuckDB に保存します（fetch_* → save_*）。
   - 例（概念）:
     ```python
     from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
     from kabusys.data.jquants_client import get_id_token

     token = get_id_token()  # settings からリフレッシュトークンを使い取得
     records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
     conn = init_schema("data/kabusys.duckdb")
     save_daily_quotes(conn, records)
     conn.close()
     ```

2. 特徴量作成（features）
   - DuckDB 接続と target_date を渡して build_features を実行すると features テーブルへ書き込みます。
     ```python
     from kabusys.strategy import build_features
     conn = init_schema("data/kabusys.duckdb")
     build_features(conn, target_date=date(2024, 1, 15))
     conn.close()
     ```

3. シグナル生成
   - generate_signals(conn, target_date, threshold=?, weights=?)
     ```python
     from kabusys.strategy import generate_signals
     count = generate_signals(conn, target_date=date(2024,1,15))
     ```

4. バックテスト（CLI / プログラム）
   - CLI:
     ```
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --db data/kabusys.duckdb \
       --cash 10000000 --allocation-method risk_based
     ```
   - プログラム:
     ```python
     from kabusys.backtest.engine import run_backtest
     conn = init_schema("data/kabusys.duckdb")
     result = run_backtest(conn, start_date, end_date, initial_cash=1e7)
     conn.close()
     # result.history, result.trades, result.metrics を利用
     ```

5. ニュース収集
   - run_news_collection(conn, sources=None, known_codes=set_of_codes)
     ```python
     from kabusys.data.news_collector import run_news_collection
     conn = init_schema("data/kabusys.duckdb")
     run_news_collection(conn, known_codes=set_of_valid_codes)
     ```

---

## 主要 API（抜粋）

- kabusys.config.settings — 環境設定取得
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, save_daily_quotes, fetch_financial_statements, save_financial_statements, fetch_market_calendar, save_market_calendar, fetch_listed_info
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=?, weights=?)
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.backtest
  - run_backtest(conn, start_date, end_date, ...)

---

## ディレクトリ構成

（ソースツリーの主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - jquants_client.py
      - news_collector.py
      - (schema, calendar_management 等の補助モジュール)
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - strategy/
      - feature_engineering.py
      - signal_generator.py
      - __init__.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - backtest/
      - engine.py
      - simulator.py
      - metrics.py
      - run.py
      - clock.py
      - __init__.py
    - execution/
      - __init__.py  (実際の発注ロジックはここに実装予定)
    - monitoring/
      - (監視 / 通知 関連モジュール)
    - research/
    - (その他補助モジュール)

---

## 開発上の注意点 / 実装ポリシー

- ルックアヘッドバイアス回避
  - ファクター計算・シグナル生成は target_date 時点の情報のみ使用する設計です。
- 冪等性
  - データ保存は可能な限り ON CONFLICT / INSERT ... RETURNING 等で重複を回避する実装になっています。
- エラーハンドリング
  - J-Quants クライアントはリトライ・指数バックオフ・401 の自動リフレッシュ等を備えています。
- テスト容易性
  - config の自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能です（ユニットテスト向け）。

---

## よくある問い（FAQ）

- Q: Python のバージョンは？
  - A: 3.10 以上を想定（型アノテーションで | を使用）。
- Q: DB の初期スキーマはどこで作る？
  - A: kabusys.data.schema の init_schema を使用して DuckDB ファイルを初期化してください（プロジェクトに schema 定義があります）。
- Q: すぐ動かせるサンプルは？
  - A: バックテスト runner（python -m kabusys.backtest.run）が実行例として利用できます。事前に prices_daily / features / ai_scores / market_regime / market_calendar を DB に用意する必要があります。

---

## 貢献・ライセンス

- この README に書かれている以外の運用手順（ETL スクリプト・schema の詳細・CI）はプロジェクトの他ファイルや運用ドキュメントを参照してください。  
- ライセンス情報はリポジトリの LICENSE を参照してください。

---

README は開発/運用の入り口としての最小セットを記載しています。必要であれば、セットアップ手順の詳細（schema 初期化コマンド、サンプル .env.example、requirements.txt の内容、CI 手順など）を追記します。どの箇所を詳しく書きたいか教えてください。