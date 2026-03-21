# KabuSys

KabuSys は日本株向けの自動売買基盤ライブラリです。データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、監査ログなどを含む3層アーキテクチャ（Raw / Processed / Feature / Execution）で設計されています。

概要
- 日本株のデータ取得・保管・加工・戦略生成を行うためのモジュール群
- DuckDB をデータストアとして利用し、冪等性（ON CONFLICT）やトランザクションに配慮
- ルックアヘッドバイアス排除、レートリミット、リトライ、SSRF対策など実運用を想定した実装
- research 層によりファクター研究やIC解析が可能

主な機能
- J-Quants API クライアント（取得・保存・トークン自動リフレッシュ・レート制御）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- ETL パイプライン
  - run_daily_etl（市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl
- DuckDB スキーマ定義と初期化（init_schema）
- ニュース収集（RSS）
  - fetch_rss, save_raw_news, extract_stock_codes, run_news_collection
  - SSRF、防御的XMLパース、トラッキングパラメータ削除、記事IDは正規化URLのSHA-256に基づく
- 研究用モジュール（research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 将来リターン・IC・統計サマリー: calc_forward_returns, calc_ic, factor_summary, rank
- 戦略層（strategy）
  - build_features: 生ファクターを統合・正規化して features テーブルへ保存
  - generate_signals: features と AIスコアを組み合わせて BUY/SELL シグナルを生成し signals テーブルへ保存
- その他ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - カレンダー管理（is_trading_day, next_trading_day, get_trading_days 等）
  - 環境変数管理（.env 自動読み込み、必須チェック）

必要要件
- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリで多くを実装しているため依存は最小限

セットアップ手順（開発環境の例）

1. リポジトリをクローン / ワークツリー作成
   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成して有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb defusedxml

   （パッケージ化されている場合は pip install -e . など）

4. 環境変数を設定（.env を推奨）
   プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（CWD に依存せずパッケージ起点で探索）。
   自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注機能を使う場合）
   - SLACK_BOT_TOKEN: Slack 通知用（必要な場合）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネルID

   任意 / 推奨
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development|paper_trading|live（デフォルト development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

   例 .env
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトで以下を実行して DB とテーブルを作成します。

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # :memory: も可
   conn.close()
   ```

基本的な使い方（例）

- 日次 ETL を実行する（J-Quants から差分取得して保存、品質チェックまで）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # 引数で target_date や id_token を渡せます
  print(result.to_dict())
  conn.close()
  ```

- 特徴量構築（strategy.build_features）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, date(2024, 1, 15))
  print(f"features upserted: {count}")
  ```

- シグナル生成（strategy.generate_signals）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, date(2024, 1, 15))
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

環境設定の注意点
- コンフィグ（kabusys.config.Settings）は環境変数から値を読み取ります。必須値が未設定だと ValueError を発生させます。
- .env ファイルの読み込み順は OS 環境 > .env.local > .env。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で抑止可能。
- LOG_LEVEL / KABUSYS_ENV の値検証が行われます（許容値以外はエラー）。

主要モジュール一覧（簡易説明）
- kabusys.config: 環境変数管理・設定取得
- kabusys.data
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - jquants_client: J-Quants API クライアント（取得・保存）
  - pipeline: ETL パイプライン（差分取得・品質チェック）
  - news_collector: RSS 収集・記事保存・銘柄紐付け
  - calendar_management: JPX カレンダー管理・営業日判定
  - stats: 統計ユーティリティ（zscore_normalize）
  - features: zscore_normalize の公開
  - audit: 監査ログ用 DDL（signal_events / order_requests / executions 等）
- kabusys.research: ファクター計算・IC・forward returns 等（研究用）
- kabusys.strategy: feature_engineering（build_features）と signal_generator（generate_signals）
- kabusys.execution: 発注・約定管理（パッケージ名のみ、詳細実装は別ファイル）

推奨運用フロー（参考）
1. DB 初期化（init_schema）
2. 夜間バッチで run_daily_etl を実行（market calendar, prices, financials）
3. 研究・検証環境で特徴量検証（research.calc_* / feature_exploration）
4. 本番では build_features → generate_signals → execution 層で発注（paper_trading/live 切替）
5. audit / orders / executions テーブルでトレーサビリティを確保

開発／テストのヒント
- 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト用の環境を注入してください。
- DuckDB の :memory: 接続を使えばテストが容易です（init_schema(":memory:") を利用）。
- ネットワーク呼び出し部分（jquants_client._request、news_collector._urlopen など）はモック可能な設計になっています。

ディレクトリ構成（主なファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - (その他 quality, etc. が存在する想定)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/  (パッケージは __all__ に含まれますがコードは別途)
    - (その他ユーティリティ・モジュール)

最後に
- README は簡潔な利用方法と参照ポイントをまとめたもので、個別の使い方や運用ルール（StrategyModel.md、DataPlatform.md、Security.md など）は各ドキュメントを参照してください。
- 実運用では API のレートやトークン管理、監査ログの保全、Slack通知やエラーハンドリング方針などの運用設計を十分に行ってください。

必要であれば、README に含めるサンプル .env.example、運用手順書、または簡易 CLI の使い方（run-etl / build-features / generate-signals 等）を追加で作成します。どれを優先しますか？