# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、ファクター計算、特徴量生成、シグナル生成、バックテスト、ニュース収集、バックエンドの DuckDB スキーマなどを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とするモジュール群を提供します。

- J-Quants API からのデータ取得（価格・財務・カレンダー）
- データ品質チェックおよび ETL パイプライン
- ファクター計算（Momentum / Value / Volatility / Liquidity 等）
- 特徴量正規化と features テーブルへの格納
- AI スコアと統合した売買シグナル生成（BUY / SELL）
- バックテスト用のシミュレータと評価指標計算
- RSS ベースのニュース収集と銘柄紐付け
- DuckDB ベースのスキーマを提供し、冪等にデータを保存

設計方針の例:
- ルックアヘッドバイアスを避けるため、target_date 時点のデータのみを使用
- DuckDB でのトランザクションを活用し原子性・冪等性を保証
- ネットワーク呼び出しに対してレート制限・リトライ・認証リフレッシュを実装

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env ファイル / 環境変数の自動ロード、必須設定の取得
  - 設定プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（ページネーション、リトライ、レート制限、保存関数）
  - news_collector: RSS フィードからニュース収集、正規化、raw_news / news_symbols 保存
  - schema: DuckDB スキーマ定義・初期化（init_schema）
  - stats: zscore_normalize 等の統計ユーティリティ
  - pipeline: 差分ETL と品質チェックのための ETL ユーティリティ（run_prices_etl 等）
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー
- kabusys.strategy
  - feature_engineering.build_features: raw ファクターを正規化して features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナル生成・保存
- kabusys.backtest
  - engine.run_backtest: DuckDB をコピーして日次ループでシミュレーションを実行
  - simulator.PortfolioSimulator: 擬似約定・スリッページ・手数料モデル
  - metrics.calc_metrics: CAGR, Sharpe, Max Drawdown 等の計算
  - CLI: python -m kabusys.backtest.run
- kabusys.data.news_collector:
  - RSS の安全な取得、XML 攻撃対策（defusedxml）、SSRF 対策、記事ID生成、銘柄抽出

---

## 必須環境・依存

（実プロジェクトでは pyproject.toml / requirements.txt を参照してください。ここでは主要な依存を記載します）

- Python 3.9+
- duckdb
- defusedxml

標準ライブラリの urllib, logging, datetime 等も使用しています。

---

## セットアップ手順

1. リポジトリをクローン

   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境を作成・有効化（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows (PowerShell / CMD)

3. 必要パッケージをインストール

   pip install duckdb defusedxml

   （本来は requirements.txt / pyproject.toml からインストールしてください）

4. パッケージをインストール（ローカル開発用）

   pip install -e .

5. 環境変数 / .env を用意

   プロジェクトルートに `.env` や `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可）。

   最低限必要な環境変数（Settings から抜粋）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意/デフォルト:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

6. DuckDB スキーマ初期化

   Python REPL またはスクリプトで:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()

   もしくは ":memory:" でインメモリ DB を初期化できます（バックテスト用等）。

---

## 使い方（簡単なワークフロー例）

1. データ取得（J-Quants から価格・財務・カレンダーを差分取得して保存）

   - pipeline モジュールの run_prices_etl / run_financials_etl 等を利用して差分 ETL を実行します。
   - 例（概念）:
     from kabusys.data.pipeline import run_prices_etl
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     run_prices_etl(conn, target_date=date.today())
     conn.close()

   ※ pipeline モジュールは差分判定・バックフィル等のロジックを提供します（コードベース参照）。

2. 特徴量作成

   データが揃ったら features を構築します（target_date 単位で冪等処理）。

   from kabusys.strategy import build_features
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   cnt = build_features(conn, target_date=date(2024,1,31))
   conn.close()

3. シグナル生成

   features と ai_scores（任意）を基にシグナルを生成して `signals` テーブルへ保存します。

   from kabusys.strategy import generate_signals
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2024,1,31))
   conn.close()

   generate_signals はデフォルト閾値 0.60、デフォルト重みを使用します。weights を渡して重みを調整可能です。

4. バックテスト実行（CLI）

   DuckDB に必要テーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）が入っている前提で以下を実行します。

   python -m kabusys.backtest.run \
     --start 2023-01-01 --end 2023-12-31 \
     --cash 10000000 --db data/kabusys.duckdb

   実行後、CAGR / Sharpe / Max Drawdown / Win Rate / Payoff Ratio / Total Trades を出力します。

5. ニュース収集

   RSS ソースから収集して保存する:

   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
   conn.close()

   保存済み記事は raw_news / raw_news.id をベースに news_symbols と紐付けられます。

---

## 主要 API（抜粋）

- kabusys.data.schema.init_schema(db_path)
  - DuckDB の全テーブルを作成して接続を返す（冪等）

- kabusys.data.jquants_client.get_id_token(refresh_token=None)
  - J-Quants の ID トークン取得（自動リフレッシュサポート）

- kabusys.data.jquants_client.fetch_daily_quotes(...), save_daily_quotes(conn, records)
  - 取得と DuckDB への保存（冪等）

- kabusys.strategy.build_features(conn, target_date)
  - features テーブルへ正規化済み特徴量を書き込む（冪等）

- kabusys.strategy.generate_signals(conn, target_date, threshold=0.6, weights=None)
  - signals テーブルへ BUY/SELL シグナルを書き込む（冪等）

- kabusys.backtest.run_backtest(conn, start_date, end_date, ...)
  - 指定期間でバックテストを実行し結果（history, trades, metrics）を返す

- kabusys.data.news_collector.fetch_rss(url, source), save_raw_news(conn, articles)
  - RSS の取得および raw_news 保存

---

## 注意点 / 運用上の補足

- 環境変数は .env/.env.local または OS 環境から読み込まれます。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- J-Quants API はレート制限（120 req/min）や 401 リフレッシュ、408/429/5xx に対するリトライロジックを備えています。大量取得時は制限に注意してください。
- features / signals / positions 等は日付単位で DELETE→INSERT の置換を行い冪等性を保っています（トランザクションを使用）。
- DuckDB スキーマは ON DELETE CASCADE など一部の制約が DuckDB のバージョン依存で未実装のため、運用側での順序付き削除等の管理が必要な場合があります（コード内コメント参照）。
- ニュース収集では SSRF 対策や XML 脆弱性対策を実装しています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - pipeline.py
  - schema.py
  - stats.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- strategy/
  - __init__.py
  - feature_engineering.py
  - signal_generator.py
- backtest/
  - __init__.py
  - engine.py
  - simulator.py
  - metrics.py
  - run.py
  - clock.py
- execution/            # 発注関連モジュール（パッケージ化済み）
- monitoring/           # 監視・アラート用モジュール（パッケージ化済み）

---

## 開発者向けヒント

- DuckDB を素早く初期化して単体機能を試すには init_schema(":memory:") を利用すると便利です。
- logging の設定はアプリケーション側で行います（バックテスト CLI は basicConfig を設定）。
- 単体テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って環境変数の自動ロードによる副作用を避け、必要な設定はテスト側で注入してください。
- jquants_client の HTTP 呼び出しは urllib を直接使用しているため、ユニットテストでは urllib.request.urlopen または kabusys.data.news_collector._urlopen 等をモックして制御してください。

---

もし README に追加したい実行例（具体的な CLI 実行例、.env.example のテンプレート、よくあるトラブルシュート等）があれば教えてください。必要に応じて追記します。