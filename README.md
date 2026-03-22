# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）。データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、バックテスト、ニュース収集、簡易シミュレータなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引の研究〜本番ワークフローを想定したモジュール群です。主な目的は次の通りです。

- J-Quants API からのデータ取得と DuckDB への保存（差分更新・冪等保存）
- 研究環境で計算した生ファクターを用いた特徴量生成（Z スコア正規化等）
- 正規化済み特徴量 + AI スコアの統合による売買シグナル生成（BUY/SELL）
- 日次バックテストフレームワーク（擬似約定・スリッページ・手数料を考慮）
- RSS ベースのニュース収集と銘柄紐付け
- データ品質チェックやスキーマ初期化ユーティリティ

設計上のポイント：
- ルックアヘッドバイアスの防止（target_date 時点のデータのみを使用）
- DuckDB をデータ層に採用（軽量で高速な分析用 DB）
- 冪等性（ON CONFLICT / トランザクション）を重視
- 外部 API 呼び出し（発注系）と execution 層の依存は最小限

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、リトライ、トークンリフレッシュ、rate limit 対応）
  - pipeline: 差分 ETL ロジック（raw_prices, raw_financials, market_calendar の差分更新）
  - news_collector: RSS からニュース収集・前処理・DB 保存・銘柄抽出
  - schema: DuckDB スキーマ定義と初期化（init_schema）
  - stats: 共通統計ユーティリティ（zscore 正規化 等）
- research/
  - factor_research: momentum/value/volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/
  - feature_engineering: 生ファクターの正規化、ユニバースフィルタ、features テーブルへの保存
  - signal_generator: features と ai_scores を統合して final_score を計算、BUY/SELL シグナル生成
- backtest/
  - engine: 日次ループによるバックテスト（generate_signals を呼び出し、シミュレーション実行）
  - simulator: 擬似約定・ポートフォリオ管理（スリッページ・手数料・マーク・トゥ・マーケット）
  - metrics: バックテスト評価指標（CAGR, Sharpe, MaxDD 等）
  - run.py: CLI エントリポイント（python -m kabusys.backtest.run）
- config.py: 環境変数/設定管理（.env 自動読み込み機能、Settings オブジェクト）

---

## 必要環境 / 依存関係

最小限の依存（例）:
- Python 3.9+
- duckdb
- defusedxml

インストール時は pip を使って依存を追加してください。プロジェクトには requirements.txt が付属していない想定のため、以下のように手動でインストールします。

例：
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
pip install -e .
```

（※ packaging / setup があれば `pip install -e .` でパッケージの編集インストールが可能です）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成・有効化（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージのインストール
   ```
   pip install duckdb defusedxml
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（config._find_project_root による検出）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   代表的な環境変数（.env の例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=secret
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマの初期化
   Python REPL やスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ DB も可
   conn.close()
   ```

---

## 使い方（主要ユースケース）

- バックテスト（CLI）
  - 事前に DuckDB に prices_daily, features, ai_scores, market_regime, market_calendar 等が入っていること
  - 実行例:
    ```
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2024-12-31 \
      --cash 10000000 --db data/kabusys.duckdb
    ```
  - 出力: CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades 等

- スキーマ初期化（DB 作成）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- ETL（株価差分取得など）
  - pipeline モジュールの関数を呼ぶことで差分 ETL を実行できます（例: run_prices_etl）。
  - 例（概念）:
    ```python
    from datetime import date
    import duckdb
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_prices_etl

    conn = init_schema("data/kabusys.duckdb")
    fetched, saved = run_prices_etl(conn, target_date=date.today())
    conn.close()
    ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  conn.close()
  ```

- 特徴量構築 / シグナル生成（戦略）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features, generate_signals
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  target = date(2024, 1, 4)
  n = build_features(conn, target)
  signals_count = generate_signals(conn, target)
  conn.close()
  ```

- ライブラリ API（例）
  - settings: 環境変数ラッパー（kabusys.config.settings）
  - jquants_client: fetch_* / save_* 関数
  - backtest.run_backtest(conn, start_date, end_date, ...) : プログラム的呼び出しでバックテスト実行

---

## 注意事項 / 実運用上のポイント

- J-Quants API:
  - レート制限（120 req/min）を Respect する実装が含まれていますが、キーや大量データ取得時は運用監視が必要です。
  - 401 の場合は自動でリフレッシュを試みます。refresh token の管理に注意してください。
- 環境変数の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に `.env` / `.env.local` を読み込みます。
  - テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効にできます。
- DuckDB スキーマは冪等に作成されますが、既存データと互換性のある運用を心がけてください。
- NewsCollector は外部 RSS を解析するため、SSRF / XML Bomb 対策等の実装（defusedxml、応答サイズ制限、プライベートホストチェック）を含みますが、運用時はさらに制約を設けることを推奨します。
- バックテストはあくまでヒストリカルな性能評価であり、実際の trading execution / latency / slippage は別途確認してください。

---

## 主要な公開 API（抜粋）

- kabusys.config
  - settings: 環境変数アクセサ（settings.jquants_refresh_token, settings.kabu_api_base_url, settings.env, ...）
- kabusys.data.schema
  - init_schema(db_path) -> DuckDB connection
  - get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=None, weights=None)
- kabusys.backtest
  - run_backtest(conn, start_date, end_date, ...)

---

## ディレクトリ構成

プロジェクト内の主要ファイル・ディレクトリ構成（src/kabusys を抜粋）:

- src/
  - kabusys/
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
    - execution/
      - __init__.py
    - monitoring/  (実装想定の監視関連モジュール)
    - (その他ユーティリティ類)

---

## 開発とテスト

- コードの多くは DuckDB 接続を引数に取り、外部副作用（発注 API 呼び出し等）を含みません。そのためユニットテストはインメモリ DuckDB（":memory:"）で容易に実行できます。
- config の自動 .env ロードはテストで制御可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

## ライセンス / 貢献

本 README はコードベースの概要を記載したものです。ライセンスや貢献方法はリポジトリの LICENSE / CONTRIBUTING.md を参照してください。

---

もし README に追加したい内容（例: 実際の .env.example ファイル、CI 実行例、Docker イメージ、詳細な API ドキュメントの自動生成手順など）があれば教えてください。必要に応じて追記・整形します。