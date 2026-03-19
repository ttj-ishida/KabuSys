KabuSys
======

日本株向けの自動売買システムのコアライブラリ（データ収集・ETL・ファクター計算・シグナル生成・DB スキーマ等）。
このリポジトリはライブラリ層を提供し、実行ジョブやオーケストレーションは呼び出し側で組み合わせて利用します。

概要
----
KabuSys は以下を目的としたツール群を含みます。

- J-Quants API からの市場データ・財務データ・マーケットカレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- RSS ベースのニュース収集とテキスト前処理・銘柄抽出
- DuckDB ベースのスキーマ定義と原子性を考慮した冪等保存
- ETL パイプライン（差分取得・バックフィル・品質チェックフック）
- 研究（research）向けのファクター計算、将来リターン/IC 計算、特徴量探索ユーティリティ
- 戦略（strategy）向けの特徴量構築（正規化・フィルタ）とシグナル生成（BUY/SELL のロジック）
- マーケットカレンダーの管理ユーティリティ
- 設定管理 (.env ファイル自動読込、環境変数の管理)

主な機能一覧
--------------
- データ取得
  - J-Quants から日次株価 (OHLCV)、財務諸表、取引カレンダーのページング対応取得（jquants_client）
  - レートリミット(120 req/min)、指数バックオフ、401 時のリフレッシュ対応
- DB
  - DuckDB 用スキーマ定義・初期化（init_schema）
  - raw / processed / feature / execution 層に分かれたテーブル群（冪等保存 SQL）
- ETL
  - 差分取得ロジック（最終取得日からの差分 + backfill）
  - run_daily_etl による日次 ETL（カレンダー→株価→財務→品質チェック）
- ニュース収集
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、記事 ID の生成、raw_news への冪等保存
  - SSRF 対策、gzip サイズ制限、XML 攻撃対策（defusedxml）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリューのファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - z-score 正規化ユーティリティ
- 戦略
  - build_features: research で算出した raw factor を正規化・フィルタして features テーブルへ保存
  - generate_signals: features + ai_scores を統合し final_score を計算、BUY/SELL シグナルを signals テーブルへ保存
- その他
  - マーケットカレンダー操作（is_trading_day / next_trading_day / get_trading_days 等）
  - audit（監査）テーブル定義（signal → order → execution のトレーサビリティを想定）

セットアップ手順
----------------

1. 必要な Python バージョン
   - Python 3.9 以上を推奨（型注釈に union 型や型ヒントを使用）

2. 依存パッケージのインストール（最小）
   - duckdb
   - defusedxml
   - （必要に応じて logging 等標準ライブラリ以外の依存を追加）
   例:
     pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを使用してください）

3. リポジトリの配置
   - 任意の場所にクローン / 配置

4. 環境変数 / .env の準備
   - ルート（.git または pyproject.toml を基準）に .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（例）:
       JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
       KABU_API_PASSWORD=<kabu_station_api_password>
       SLACK_BOT_TOKEN=<slack_bot_token>
       SLACK_CHANNEL_ID=<slack_channel_id>
     任意:
       KABUSYS_ENV=development|paper_trading|live
       LOG_LEVEL=INFO
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db

   - .env の書式は shell 形式（export optional, シングル/ダブルクォート対応、コメント行 # をサポート）※config モジュールで柔軟にパースされます

5. データベース初期化
   - DuckDB ファイル（デフォルト data/kabusys.duckdb）を作成してスキーマを初期化します:
     Python REPL やスクリプトから:
       from kabusys.data.schema import init_schema
       conn = init_schema("data/kabusys.duckdb")

   - インメモリ DB を試す場合:
       conn = init_schema(":memory:")

使い方（簡単なコード例）
-----------------------

- DuckDB の初期化と日次 ETL 実行
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（初回のみ）
  conn = init_schema("data/kabusys.duckdb")

  # 日次 ETL（今日分）
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ファーチャー構築（特徴量作成）
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2025, 1, 15))
  print(f"features upserted: {count}")

- シグナル生成
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 1, 15))
  print(f"signals generated: {total}")

- ニュース収集ジョブ（RSS）
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # sources: {source_name: rss_url} を渡せる。known_codes は銘柄抽出に用いるコード集合（例: set(["7203","6758"])）
  results = run_news_collection(conn, sources=None, known_codes=None)
  print(results)

- J-Quants からのデータ取得（低レベル）
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  # DuckDB に保存する:
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  saved = jq.save_daily_quotes(conn, records)

注意点・運用上のヒント
---------------------
- 自動環境読み込み:
  - config モジュールはプロジェクトルートを .git または pyproject.toml で検出し、.env / .env.local を自動的にロードします。テストなどで自動読込を抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- レート制御:
  - J-Quants API はレート制限を守るため _RateLimiter を使っています。大規模なバックフィルやパラレル化の際は注意してください。

- 冪等性:
  - save_* 関数は ON CONFLICT や INSERT ... RETURNING によって冪等性を保つ設計です。ジョブを再実行しても重複保存は避けられるようになっています。

- DuckDB ファイルの場所:
  - settings.duckdb_path のデフォルトは data/kabusys.duckdb。適切なパスを環境変数 DUCKDB_PATH で上書きしてください。親ディレクトリがなければ自動生成されますが、権限等には注意してください。

- システム環境モード:
  - KABUSYS_ENV は development / paper_trading / live を許容します。live では実際の発注等を行う想定のため慎重に運用してください。

- ロギング:
  - LOG_LEVEL 環境変数でログレベルを制御します（DEBUG, INFO, ...）。ライブラリは logging.getLogger(__name__) を利用しているため、呼び出し側でハンドラを設定してください。

ディレクトリ構成
----------------

src/kabusys/
- __init__.py
- config.py
  - 環境変数/ .env 自動読み込み、settings オブジェクト提供
- data/
  - __init__.py
  - jquants_client.py      : J-Quants API クライアント（取得・保存）
  - news_collector.py     : RSS ベースのニュース収集・保存
  - schema.py             : DuckDB スキーマ定義と init_schema / get_connection
  - stats.py              : z-score 等の統計ユーティリティ
  - pipeline.py           : ETL パイプライン（run_daily_etl 等）
  - features.py           : features 用公開ユーティリティ（再エクスポート）
  - calendar_management.py: マーケットカレンダー操作・更新ジョブ
  - audit.py              : 監査ログ（signal / order / execution）DDL（未完の箇所あり）
- research/
  - __init__.py
  - factor_research.py    : momentum/volatility/value のファクター計算
  - feature_exploration.py: 将来リターン / IC / ファクター統計
- strategy/
  - __init__.py
  - feature_engineering.py: features テーブルの構築（正規化・ユニバースフィルタ等）
  - signal_generator.py    : final_score 計算と BUY/SELL シグナル生成
- execution/
  - __init__.py
  - （発注 / Broker 接続層はこの下に実装を想定）
- monitoring/
  - （監視・メトリクス周りのモジュールを想定）

各ファイルには docstring と実装方針・設計方針が記載されており、コード単体で動作の意図が把握できるようになっています。

拡張・組み込みのヒント
-----------------------
- 実運用では strategy → execution（発注）層を実装して signals テーブルをトリガーに注文を作成し、orders/executions/trades を更新する必要があります。
- AI スコア / ニューススコアは ai_scores テーブルに格納される前提で signal_generator は動作します。外部モデルを使う場合は ai_scores を更新するモジュールを用意してください。
- 品質チェック（quality モジュール）は pipeline.run_daily_etl から呼ばれます。品質ルールを拡張してアラートや自動ロールバックを統合可能です。

問い合わせ / 貢献
-----------------
- リポジトリに issue を作成してください。設計方針・API 変更提案・バグ報告歓迎します。

免責
----
- 本ライブラリは投資助言を目的とするものではありません。live モードでの利用は自己責任で行ってください。