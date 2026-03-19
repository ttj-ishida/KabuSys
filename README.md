# KabuSys — 日本株自動売買プラットフォーム（README）

概要
----
KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ群です。  
主な目的は以下の通りです。

- J-Quants などの外部データソースから市場データ・財務データ・ニュースを取得して DuckDB に保存する（ETL）
- 研究環境で算出した生ファクターを正規化・合成して特徴量（features）を作成する
- features と AI スコアを統合して売買シグナルを生成する（BUY / SELL）
- ニュース収集・銘柄紐付けやマーケットカレンダー管理、発注／監査ログを扱うスキーマを提供する

コードはモジュール化されており、ETL（data）、研究／ファクター計算（research）、戦略（strategy）、発注／実行（execution）等のレイヤに分かれています。

主な機能
--------
- データ取得（J-Quants クライアント）
  - 株価日足、財務諸表、マーケットカレンダー取得（ページネーション対応／レート制御／リトライ／トークン自動リフレッシュ）
- DuckDB スキーマ定義と初期化（冪等）
- ETL パイプライン（差分取得・バックフィル・品質チェックフック）
- 特徴量計算（momentum, volatility, value 等）および Z スコア正規化ユーティリティ
- シグナル生成（複数のコンポーネントスコアを重み付け統合、Bear レジーム抑制、エグジット判定）
- ニュース収集（RSS → 前処理 → raw_news 保存、銘柄コード抽出）
- マーケットカレンダー管理（営業日判定・next/prev/trading days）
- 監査ログ（signal_events / order_requests / executions などの監査テーブル定義）

セットアップ手順
----------------

前提
- Python 3.10+（typing のユニオン等を利用）
- DuckDB が利用可能（pip install duckdb）
- ネットワーク経路上で J-Quants API にアクセス可能

1. リポジトリをクローンしてインストール
   - 開発用（editable）インストール例:
     ```
     git clone <repo-url>
     cd <repo-root>
     pip install -e ".[dev]"   # requirements が extras に分かれている想定
     ```
   - 必要な依存（例）:
     - duckdb
     - defusedxml

2. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` / `.env.local` を配置すると自動で読み込まれます（ただしテスト目的等で KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可）。
   - 必須環境変数（config.Settings に基づく）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション等の API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意:
     - KABUSYS_ENV: development | paper_trading | live （既定: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
     - DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB 等（既定: data/monitoring.db）
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

3. DuckDB スキーマ初期化
   - Python からスキーマを作成します（db_path を適宜変更してください）:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - init_schema は親ディレクトリを自動作成し、テーブルをすべて冪等に作成します。

使い方（主要例）
----------------

1. 日次 ETL を実行してデータを取得・保存する
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

   - run_daily_etl は市場カレンダー、株価、財務データの差分取得と保存、オプションで品質チェックまで実行します。
   - id_token を明示的に渡すことも可能（テスト用など）。

2. 特徴量（features）を構築する
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   n = build_features(conn, target_date=date(2025, 1, 15))
   print(f"built features: {n} rows")
   ```

   - build_features は research.factor_research の出力を使ってユニバースフィルタ・正規化を行い、features テーブルへ日付単位で置換（冪等）します。

3. シグナル生成
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2025, 1, 15), threshold=0.6)
   print(f"signals written: {total}")
   ```

   - weights 引数で各コンポーネントの重みを上書きできます（自動正規化されます）。
   - Bear レジーム判定が True の場合は BUY を抑制します。

4. ニュース収集ジョブ（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   # known_codes を渡すと記事中の4桁銘柄コード抽出→news_symbols登録を行います
   known_codes = {"7203", "6758", "9984"}
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)  # {source_name: saved_count, ...}
   ```

5. カレンダー更新（夜間バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

ディレクトリ構成（主なファイル）
-----------------------------
（パッケージルート = src/kabusys）

- kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動ロードロジック、Settings）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（レート制御／リトライ／保存ヘルパ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - schema.py — DuckDB スキーマ定義 & init_schema / get_connection
    - news_collector.py — RSS 収集・前処理・保存（raw_news / news_symbols）
    - calendar_management.py — 市場カレンダー管理（営業日判定、update job）
    - features.py — zscore_normalize の再エクスポート
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログ（signal_events, order_requests, executions）
    - pipeline.py — ETL 実行ロジック（差分取得、バックフィル）
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features の作成（Zスコア正規化・ユニバースフィルタ）
    - signal_generator.py — final_score 計算、BUY/SELL シグナル生成
  - execution/
    - __init__.py
    (発注・実行層は将来の実装箇所。監査ログや signal_queue / orders / trades schema は schema.py に定義済み)

補足・設計上の注意
-----------------
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト環境等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB への書き込みは多くの箇所でトランザクションでラップされ、冪等性（ON CONFLICT や INSERT ... DO UPDATE / DO NOTHING）を意識した設計です。
- J-Quants クライアントは ID トークンの自動リフレッシュ、固定間隔のレート制御、HTTP の再試行（指数バックオフ）などを備えています。
- 研究モジュール（research/*）は本番口座や発注 API にアクセスしない設計です（データベースの prices_daily / raw_financials のみ参照）。

よくある利用フロー（例）
-----------------------
1. .env を用意して必要なトークンを設定
2. init_schema() で DB を作成
3. run_daily_etl() を定期実行してデータを蓄積（cron / Airflow 等）
4. build_features() を実行して features を作成
5. generate_signals() を実行して signals を出力
6. execution 層（将来的な broker 接続）で signals を消化して発注→約定→監査ログ保存

ライセンスや貢献方法
-------------------
（この README では省略。必要であれば LICENSE ファイルを作成してください。）

問題・バグ報告
--------------
不具合や改善提案があれば Issue を作成してください。ログ出力（LOG_LEVEL）や .env の設定値を添付いただくと調査がスムーズです。

以上。追加で README に載せたいコマンド例や CI / Docker 設定、.env.example の自動生成テンプレートが必要であればお知らせください。