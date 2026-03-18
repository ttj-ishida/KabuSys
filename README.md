KabuSys — 日本株自動売買システム
================================

バージョン: 0.1.0

概要
----
KabuSys は日本株向けのデータプラットフォーム / 自動売買基盤の一部実装です。  
主に以下を目的としています。

- J-Quants API から市場データ・財務データ・カレンダーを取得して DuckDB に蓄積する ETL パイプライン
- RSS ニュース収集と記事の前処理 / 銘柄紐付け
- ファクター（モメンタム・バリュー・ボラティリティ等）計算およびリサーチ用ユーティリティ
- DuckDB スキーマ定義・監査ログ（発注→約定のトレース）・データ品質チェックの実装
- 環境設定管理（.env 自動読み込み、必須環境変数の検証）

機能一覧
--------
主な機能（実装済みモジュール）:

- 環境設定
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得と検証（kabusys.config.settings）
- データ取得 / 永続化（kabusys.data）
  - J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - 日足・財務・マーケットカレンダーの取得と DuckDB への冪等保存
  - RSS ニュース収集（SSRF 対策・gzip/サイズ制限・XML 安全パース）と raw_news 保存
  - DuckDB スキーマ初期化（raw / processed / feature / execution 層）
  - ETL パイプライン（差分更新、バックフィル、品質チェック）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - マーケットカレンダー管理（営業日判定・next/prev_trading_day 等）
  - 監査ログスキーマ（signal → order_request → executions のトレース）
- リサーチ（kabusys.research）
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン計算 / IC（Spearman） / ファクター統計サマリ
  - 統計ユーティリティ（zscore 正規化）
- ユーティリティ
  - URL 正規化・記事ID生成・銘柄コード抽出など（news_collector 内）

セットアップ手順
----------------

前提
- Python 3.10+（型注釈で | 型が使われているため）
- ネットワークアクセス（J-Quants API、RSS 等）
- J-Quants のリフレッシュトークン等の環境変数

1) 必要パッケージのインストール（例）
   pip install duckdb defusedxml

   ※プロジェクトに requirements.txt/poetry がある場合はそれに従ってください。

2) ソースをインストール（開発時）
   - プロジェクトルートで:
     pip install -e .

3) 環境変数の設定
   プロジェクトルートに .env または .env.local を置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロード無効化可）。
   必須の環境変数（kabusys.config.Settings に基づく）:

   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
   - KABU_API_PASSWORD     : kabu ステーション API パスワード（発注周りを使う場合）
   - SLACK_BOT_TOKEN       : Slack 通知用トークン（必要に応じて）
   - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID

   任意（デフォルトあり）:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
   - LOG_LEVEL (DEBUG/INFO/...) — デフォルト INFO
   - KABUSYS_DISABLE_AUTO_ENV_LOAD（=1 で自動ロード無効）
   - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（監視用 DB、デフォルト data/monitoring.db）
   - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）

4) DuckDB スキーマ初期化
   Python REPL やスクリプトで：

   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   # conn は duckdb 接続オブジェクト（duckdb.DuckDBPyConnection）

使い方（代表的な操作例）
-----------------------

- 日次 ETL を実行して市場データを取得・保存する

  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # デフォルトは今日を対象に ETL を実行
  print(result.to_dict())

- ニュース収集ジョブを実行する

  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  known_codes = {"7203", "6758", "9984"}  # 既知銘柄コードセット（任意）
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)  # ソースごとの新規保存件数

- ファクター計算 / リサーチ関数の利用例

  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  # 将来リターン - 翌日・5営業日・21営業日
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

  # IC の例（factor_col = "mom_1m", return_col = "fwd_1d"）
  ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
  summary = factor_summary(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])

- z-score 正規化ユーティリティ

  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

設定周りの注意
--------------
- .env 読み込み順: OS 環境 > .env.local > .env（.env.local は .env を上書き）
- 自動読み込みを無効にしたいとき:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- settings はプロパティベースで必須項目は未設定時に ValueError を投げます。

開発・テストのヒント
--------------------
- モジュール内の HTTP 呼び出し等は単体テストでモック可能に設計されています（例: news_collector._urlopen を差し替え）。
- ETL の差分取得は内部で最終取得日を確認して必要な範囲だけ取得します。backfill_days を指定すると直近 N 日分を再取得して API の後出し修正を吸収できます。
- DuckDB への保存関数は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を意識して実装されています。

ディレクトリ構成
----------------

（プロジェクトの src/kabusys 配下の主要ファイルとモジュール）

- src/
  - kabusys/
    - __init__.py            (version, public package)
    - config.py              (環境変数・設定管理)
    - data/
      - __init__.py
      - jquants_client.py    (J-Quants API クライアント、取得＋保存ロジック)
      - news_collector.py    (RSS 取得、前処理、DB 保存、銘柄抽出)
      - schema.py            (DuckDB スキーマ定義・初期化)
      - stats.py             (統計ユーティリティ、zscore)
      - pipeline.py          (ETL パイプライン、run_daily_etl 等)
      - features.py          (feature API エクスポート)
      - calendar_management.py (マーケットカレンダー管理)
      - audit.py             (監査ログスキーマ・初期化)
      - etl.py               (ETL API エクスポート)
      - quality.py           (データ品質チェック)
    - research/
      - __init__.py
      - feature_exploration.py (将来リターン、IC、summary、rank)
      - factor_research.py     (momentum/volatility/value の計算)
    - strategy/               (戦略関連エントリポイント — 空の __init__ を含む)
    - execution/              (発注実装など — 空の __init__ を含む)
    - monitoring/             (監視用モジュール — 空の __init__ を含む)

ドキュメント / 設計参照
---------------------
コード内に多くの設計ノート（DataPlatform.md / StrategyModel.md への言及）が記載されています。各モジュールの docstring を参照してください。

ライセンス / 貢献
-----------------
（該当情報がないため README には含めていません。プロジェクトにライセンスファイルを追加してください。）

問い合わせ
---------
不具合報告や質問はリポジトリの issue またはプロジェクトの連絡手段に従ってください。

以上。必要であれば README にサンプル .env.example、コマンドラインツールや systemd タイマーの設定例、CI/CD 設定テンプレートなどを追記します。どの追加情報が欲しいか教えてください。