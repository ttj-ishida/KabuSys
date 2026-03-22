# KabuSys

日本株のデータプラットフォームと自動売買／バックテスト基盤のライブラリ群です。  
データ取得（J‑Quants）、ETL、特徴量生成、シグナル生成、バックテストシミュレータ、ニュース収集などを含みます。

## プロジェクト概要
KabuSys は日本株の自動売買システムを構成するためのライブラリ群です。  
主に以下を提供します：
- J‑Quants API からの株価・財務・カレンダー取得と DuckDB への保存
- ETL パイプライン（差分取得、品質チェック）
- 研究用ファクター計算（momentum / value / volatility 等）
- 特徴量の正規化と features テーブルへの保存
- シグナル生成ロジック（final_score の計算、BUY/SELL 判定）
- バックテストエンジン（擬似約定、ポートフォリオ管理、評価指標）
- ニュース収集（RSS → raw_news、記事と銘柄の紐付け）
- DuckDB スキーマ初期化ユーティリティ

設計上の要点：
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- 冪等性（DB 書き込みは ON CONFLICT / トランザクションで安全に）
- 外部ライブラリ依存を最小化（標準ライブラリ + 必要最小限のライブラリ）
- テストしやすい設計（ID トークン注入、モック可能な I/O）

## 主な機能一覧
- data/
  - jquants_client: J‑Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - schema: DuckDB のスキーマ定義と初期化（init_schema）
  - pipeline: ETL ジョブ（差分更新、品質チェックフック）
  - news_collector: RSS 収集、記事正規化、銘柄抽出、DB 保存
  - stats: Zスコア正規化などの統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/
  - feature_engineering: 生ファクターを正規化して features テーブルへ保存
  - signal_generator: features + ai_scores を統合して BUY/SELL シグナルを生成
- backtest/
  - engine: 日次ループを回すバックテストエンジン（run_backtest）
  - simulator: 擬似約定・ポートフォリオ管理（PortfolioSimulator）
  - metrics: バックテスト評価指標計算（CAGR, Sharpe 等）
  - run: CLI エントリ（python -m kabusys.backtest.run）
- config: 環境変数管理（.env 自動読み込み、必須値チェック）
- execution / monitoring: 発注・モニタリング層のプレースホルダ

## セットアップ手順

前提
- Python 3.9+（typing の一部に | 型アノテーションを使用しています。環境に合わせて調整してください）
- DuckDB を使用します（ローカルファイルまたは :memory:）

1. リポジトリをクローン／配置
   - 開発環境では開発用インストールを使うと便利です:
     ```
     pip install -e .
     ```
   - 最低限の必須パッケージ（例）:
     ```
     pip install duckdb defusedxml
     ```
     ※ 実際の依存関係はプロジェクトの requirements に合わせてください。

2. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（config.py）。
   - 自動読み込みを無効化する場合は環境変数を設定:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（config.Settings 参照）:
     - JQUANTS_REFRESH_TOKEN (必須) — J‑Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - KABU_API_BASE_URL (任意) — デフォルト "http://localhost:18080/kabusapi"
     - SLACK_BOT_TOKEN (必須) — Slack 通知用
     - SLACK_CHANNEL_ID (必須)
     - DUCKDB_PATH (任意) — デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH (任意) — デフォルト "data/monitoring.db"
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
   - サンプル .env:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

3. DuckDB スキーマ初期化
   - Python REPL やスクリプトで実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```

4. （任意）J‑Quants 用の認証
   - settings.jquants_refresh_token に値があれば jquants_client が自動でトークンを発行します。
   - テスト時には get_id_token に直接トークンを渡して使用可能。

## 使い方（代表的な例）

- バックテスト（CLI）
  - 事前に DB に必要なテーブルとデータ（prices_daily, features, ai_scores, market_regime, market_calendar）を用意してください。
  - 実行例:
    ```
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 \
      --slippage 0.001 \
      --commission 0.00055 \
      --max-position-pct 0.2 \
      --db data/kabusys.duckdb
    ```
  - 出力にバックテストメトリクス（CAGR, Sharpe, Max Drawdown, Trades 等）が表示されます。

- DuckDB スキーマ初期化（プログラムから）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  # ... ETL / バックテストで conn を渡す ...
  conn.close()
  ```

- ETL（差分株価取得）の実行（例）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # target_date は通常今日または当該営業日
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  conn.close()
  ```

- 特徴量構築（features テーブルへ）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 31))
  conn.close()
  ```

- シグナル生成
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  total_signals = generate_signals(conn, target_date=date(2024, 1, 31))
  conn.close()
  ```

- ニュース収集ジョブ（RSS → raw_news）
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = duckdb.connect("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  conn.close()
  # results は source_name: 新規保存件数 の辞書
  ```

- J‑Quants から日足取得と保存
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  from datetime import date

  id_token = None  # None の場合モジュールキャッシュで取得（settings.jquants_refresh_token 必須）
  records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  conn = duckdb.connect("data/kabusys.duckdb")
  saved = jq.save_daily_quotes(conn, records)
  conn.close()
  ```

- バックテスト入出力（プログラム API）
  ```python
  from kabusys.backtest.engine import run_backtest
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  # result.history, result.trades, result.metrics を利用
  conn.close()
  ```

## 主要な API / 関数一覧（抜粋）
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
- kabusys.data.pipeline.run_prices_etl / run_news_collection
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic
- kabusys.strategy.build_features / generate_signals
- kabusys.backtest.run_backtest（および CLI）

## 環境変数の自動読み込みについて
- config.py はプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から `.env` と `.env.local` を自動読み込みします。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にするには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

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
  - clock.py
  - run.py
- execution/
  - __init__.py
- monitoring/
  - (監視用モジュール用プレースホルダ)
- backtest/（上記）

（上記は主要モジュールを抜粋した構成です。詳細はソースツリーを参照してください。）

## 注意事項 / 実運用上のポイント
- DB のバックアップや運用時のアクセス権管理は自身で整備してください（DuckDB はファイルベースです）。
- J‑Quants の API レート制限（120 req/min）に準拠していますが、大規模取得時は自身でもレートに注意してください。
- AI スコアや発注周りの実稼働連携（kabuステーション、Slack 等）は秘密情報（トークン）の取り扱いに注意してください。
- 本パッケージは研究・バックテスト基盤を主眼としており、実取引に使う場合は十分な検証とリスク管理を行ってください。

---

問題報告や機能追加の提案があれば、該当ファイルの該当関数・ドキュメントとともに Issue を作成してください。