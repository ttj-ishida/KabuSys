KabuSys
=======

KabuSys は日本株のデータ取得・特徴量作成・シグナル生成・発注トレーサビリティを想定した、自動売買プラットフォームのコアライブラリ群です。本リポジトリは主に以下を提供します。

- J-Quants API からのデータ取得（株価・財務・市場カレンダー）
- DuckDB を用いたデータスキーマと永続化（冪等保存）
- ETL パイプライン（差分更新、バックフィル、品質チェック呼び出し）
- ニュース収集（RSS → raw_news、銘柄抽出）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量エンジニアリング（Z スコア正規化・ユニバースフィルタ）
- シグナル生成（最終スコア算出、BUY/SELL 判定、SELL の優先）
- マーケットカレンダー管理（営業日判定）
- 監査ログ / 発注フローのためのスキーマ（audit）

バージョン
----------
パッケージバージョン: 0.1.0（src/kabusys/__init__.py）

主な機能一覧
-------------
- data/jquants_client:
  - J-Quants API 呼び出し、ページネーション対応、トークン自動リフレッシュ、リトライ & レートリミット
  - save_* 関数で DuckDB に冪等保存
- data/schema:
  - DuckDB のスキーマ作成（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) で初期化
- data/pipeline:
  - run_daily_etl：カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別 ETL
- data/news_collector:
  - RSS 取得（SSRF 対策、gzip/サイズ制限、XML 安全パーサ）
  - raw_news / news_symbols への保存（重複排除、記事 ID は正規化 URL の SHA-256）
- data/calendar_management:
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job による夜間カレンダー更新
- research:
  - calc_momentum / calc_volatility / calc_value：prices_daily / raw_financials を使ったファクター計算
  - calc_forward_returns / calc_ic / factor_summary：ファクター探索・評価ツール
- strategy:
  - build_features：研究から得た raw factor を正規化して features テーブルへ UPSERT
  - generate_signals：features / ai_scores / positions を参照して BUY/SELL シグナルを生成
- data/stats:
  - zscore_normalize：クロスセクション Z スコア正規化ユーティリティ
- config:
  - .env 自動読み込み（プロジェクトルート検出）と Settings オブジェクトで環境変数管理

システム要件 / 依存
-------------------
- Python 3.10 以降（型注釈に | を使用）
- 依存パッケージ（最低限）:
  - duckdb
  - defusedxml

インストール（開発環境の例）
---------------------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml

3. （任意）プロジェクトを編集可能モードでインストールする場合:
   - pip install -e .

環境変数 / .env
----------------
config.Settings が以下の環境変数を参照します。プロジェクトルートに .env / .env.local を置くことで自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須（アプリケーションの用途による）:
- JQUANTS_REFRESH_TOKEN  : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API のパスワード
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack 通知先チャンネル ID

オプション / デフォルト値:
- KABUS_API_BASE_URL     : デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH            : デフォルト "data/kabusys.duckdb"
- SQLITE_PATH            : デフォルト "data/monitoring.db"
- KABUSYS_ENV            : development / paper_trading / live（デフォルト development）
- LOG_LEVEL              : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

セットアップ手順（初期 DB の作成）
---------------------------------
1. Python REPL またはスクリプトで DuckDB スキーマを初期化します:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   init_schema は data/ ディレクトリが無ければ自動作成します。":memory:" を渡すとインメモリ DB になります。

基本的な使い方（例）
-------------------

1) 日次 ETL を実行（J-Quants からデータ取得 → 保存 → 品質チェック）
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema, get_connection
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())

2) 特徴量作成（build_features）
   from datetime import date
   from kabusys.strategy import build_features
   conn = get_connection("data/kabusys.duckdb")
   n = build_features(conn, target_date=date.today())
   print(f"features upserted: {n}")

3) シグナル生成（generate_signals）
   from datetime import date
   from kabusys.strategy import generate_signals
   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals generated: {total}")

4) ニュース収集ジョブ（RSS → raw_news → news_symbols）
   from kabusys.data.news_collector import run_news_collection
   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)

5) カレンダー更新（夜間バッチ）
   from kabusys.data.calendar_management import calendar_update_job
   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")

注意事項・設計上のポイント
------------------------
- 自動読み込みされる .env はプロジェクトルート（.git または pyproject.toml のある親）から探索されます。テストで自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- J-Quants API 呼び出しには内部でレートリミットと再試行ロジックが組み込まれており、401 時はトークンの自動リフレッシュを試みます。
- DB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実装されています。
- ルックアヘッドバイアス防止のため、特徴量・シグナル生成は target_date 時点で入手可能なデータのみを用いる設計方針です。
- production/live モードでの発注処理は execution 層・発注 API の実装と結合する必要があります（本コードベースは発注スキーマと監査テーブルを提供しますが、ブローカー連携ロジックは別実装）。

ディレクトリ構成
----------------
以下は主要ファイル／モジュールのツリー（src/kabusys 以下）。実際のリポジトリはこの構成に従っています。

- src/kabusys/
  - __init__.py                (パッケージ定義, __version__ = "0.1.0")
  - config.py                  (環境変数 / Settings)
  - data/
    - __init__.py
    - jquants_client.py        (J-Quants API クライアント + 保存)
    - news_collector.py        (RSS 収集・前処理・保存)
    - schema.py                (DuckDB スキーマ定義 & init_schema)
    - stats.py                 (zscore_normalize 等の統計ユーティリティ)
    - pipeline.py              (ETL パイプライン)
    - features.py              (data.stats 再エクスポート)
    - calendar_management.py   (market_calendar 管理・営業日判定)
    - audit.py                 (監査ログ用 DDL)
    - (その他: quality.py など想定)
  - research/
    - __init__.py
    - factor_research.py       (calc_momentum / calc_volatility / calc_value)
    - feature_exploration.py   (calc_forward_returns / calc_ic / factor_summary)
  - strategy/
    - __init__.py
    - feature_engineering.py   (build_features)
    - signal_generator.py      (generate_signals)
  - execution/
    - __init__.py              (発注層のエントリ置き場（実装は追加）)
  - monitoring/                (モニタリング用モジュール置き場（未詳細実装）)

ロギング
--------
- 各モジュールは標準 logging を使用します。LOG_LEVEL 環境変数でログレベルを制御できます。
- エラーハンドリングは ETL 等で個別ステップが例外を出しても他ステップを続行する設計（Fail-Fast ではない）です。run_daily_etl は結果オブジェクトに発生したエラーを集約します。

スケジューリング / 運用
-----------------------
- 日次 ETL / カレンダー更新 / シグナル生成は cron や Airflow / systemd タイマー等で定期実行する想定です。
- production での発注連携時は必ず paper_trading 環境で十分な検証を行ってから live 環境へ移行してください（KABUSYS_ENV により is_live/is_paper/is_dev フラグが切り替わります）。

貢献 / テスト
--------------
- 現状 README はコード構成と主要な使い方をまとめたものです。ユニットテスト・CI 設定は別途追加してください。
- Pull Request の際は関連するモジュールの単体テストとドキュメント更新をお願いします。

ライセンス
----------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（このテンプレートには含まれていません）。

補足
----
- 実際に API キーや本番資金が絡む処理を行う場合は、秘匿情報の管理・権限管理・発注の二重チェック等、運用面の安全対策を必須で組み込んでください。
- 本 README はコードベース（src/kabusys/*.py）を参照して作成しています。各関数 / クラスの詳細は該当モジュールの docstring を参照してください。

--- 
必要であれば、セットアップのための example .env.template、cron / systemd ユニット例、run の簡易スクリプトなどのサンプルを追記します。どれを優先して作成しますか？