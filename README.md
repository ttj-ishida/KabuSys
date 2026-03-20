KabuSys — 日本株自動売買プラットフォーム
================================

概要
----
KabuSys は日本株向けのデータプラットフォームとシグナル生成／ETL パイプラインを提供するライブラリです。  
主に以下を目的としています。

- J-Quants API からマーケットデータ・財務データ・カレンダーを取得して DuckDB に蓄積
- ニュース（RSS）収集とテキスト前処理・銘柄紐付け
- 研究（research）で作成した生ファクターを整形して特徴量を生成
- 正規化済み特徴量と AI スコアを統合し売買シグナルを生成
- 発注 / 実行 層の監査ログ・スキーマを提供

バージョン: 0.1.0

主な機能
--------
- 環境変数ベースの設定管理（自動で .env/.env.local を読み込み可能）
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（市場カレンダー、株価、財務データの差分取得／保存）
- 特徴量エンジニアリング（研究で作成したファクターの正規化・フィルタ）
- シグナル生成（複数コンポーネントの重み付け合成、BUY/SELL 判定、エグジット判定）
- RSS ベースのニュース収集（SSRF/サイズ制限/XML 脆弱性対策、銘柄抽出）
- 統計ユーティリティ（Z スコア正規化、IC 計算、要約統計）

前提 / 必要環境
--------------
- Python 3.10+（typing における | None 構文を使用）
- duckdb
- defusedxml
- （標準ライブラリで多くを実装しています）

セットアップ手順
----------------

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   最小限の依存：
   ```
   pip install duckdb defusedxml
   ```
   （パッケージ化されている場合は `pip install -e .` を行ってください）

4. 環境変数設定
   ルートに .env（または .env.local）を置くと自動読み込みします（自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必須環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id

   オプション:
   - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL (デフォルト: INFO)
   - DUCKDB_PATH=data/kabusys.duckdb (デフォルト)
   - SQLITE_PATH=data/monitoring.db

   .env の簡易例:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

使い方（主要な操作例）
--------------------

※ すべての操作は Python スクリプト／REPL から行えます。以下は簡単な利用例です。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # ファイルを作成して全テーブルを作る
   ```

   メモリ DB を使う場合:
   ```python
   conn = init_schema(":memory:")
   ```

2. 日次 ETL を実行（市場カレンダー・株価・財務データ）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   result = run_daily_etl(conn)  # デフォルトは今日（営業日に調整）
   print(result.to_dict())
   ```

3. ニュース収集ジョブ（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 既知の上場銘柄コードセット
   res = run_news_collection(conn, known_codes=known_codes)
   print(res)  # {source_name: 新規保存件数, ...}
   ```

4. 特徴量ビルド（戦略用 features テーブル作成）
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   n = build_features(conn, target_date=date(2025, 3, 1))
   print(f"upserted features: {n}")
   ```

5. シグナル生成
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2025, 3, 1))
   print(f"signals generated: {total}")
   ```

主要モジュール / API
-------------------
- kabusys.config
  - settings: 環境変数から各種設定を取得
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy
  - build_features, generate_signals

ディレクトリ構成
---------------
リポジトリの主要なファイル／ディレクトリ（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - pipeline.py
    - schema.py
    - stats.py
    - features.py
    - calendar_management.py
    - audit.py
    - (その他 data 関連モジュール)
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
  - monitoring/
    - (監視 / ロギング等のモジュール想定)

開発上の注意点 / トラブルシュート
--------------------------------
- 環境変数が足りない場合、settings のプロパティ（例: jquants_refresh_token）が ValueError を投げます。必須変数を .env に設定してください。
- J-Quants API はレート制限があります。jquants_client は内部でスロットルとリトライを実装していますが、大量リクエスト時は注意してください。
- DuckDB のファイルパスの親ディレクトリが存在しない場合は init_schema が自動で作成します。
- RSS フェッチは SSRF 対策やファイルサイズ上限（10MB）等の防御を行っています。フィードに問題があると取得をスキップする場合があります。
- Python バージョンは 3.10 以上を推奨（| を用いた型注釈を使用）。

ライセンス
--------
（この README ではライセンス表記を省略しています。リポジトリの LICENSE を参照してください。）

付録: よく使うワンライナー
------------------------
- スキーマ初期化（CLI から）
  ```
  python -c "from kabusys.data.schema import init_schema; from kabusys.config import settings; init_schema(settings.duckdb_path)"
  ```

- 日次 ETL（CLI から）
  ```
  python -c "from kabusys.data.schema import init_schema; from kabusys.config import settings; from kabusys.data.pipeline import run_daily_etl; conn=init_schema(settings.duckdb_path); print(run_daily_etl(conn).to_dict())"
  ```

必要に応じて、README に追加したい内容（例: CI / テスト手順・詳細な設定項目・運用手順）があれば教えてください。