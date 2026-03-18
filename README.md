KabuSys
======

日本株向けの自動売買 / データ基盤ライブラリです。  
DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）、J-Quants からのデータ取得、RSS ニュース収集、研究用途のファクター計算・特徴量探索、ETL パイプライン、監査ログ等のユーティリティを含みます。

主な特徴
--------

- DuckDB ベースのスキーマ定義と初期化（冪等）
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ニュース収集（SSRF 対策・トラッキング除去・冪等保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用モジュール（モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン・IC・統計サマリー）
- 監査ログ（シグナル→発注→約定フローのトレーサビリティ用テーブル群）
- 環境変数ベースの設定管理（.env / .env.local 自動読み込み、無効化フラグあり）

要求環境
--------

- Python 3.10+
- 必要なライブラリ（主要なもの）:
  - duckdb
  - defusedxml
- （標準ライブラリの urllib / logging / datetime 等も使用）

インストール（開発用）
---------------------

1. Python 仮想環境を作成・有効化してください（例: venv）。
2. 必要ライブラリをインストールします（例）:

   pip install duckdb defusedxml

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意している想定です）

環境変数（.env）
----------------

KabuSys はプロジェクトルートにある .env / .env.local を自動で読み込みます（OS 環境変数が優先）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須の環境変数（最低限）

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード（発注実装時に使用）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意（デフォルトあり）

- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL   : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動 .env ロードを無効化

簡単な .env の例:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

セットアップ手順（初期化）
------------------------

1. DuckDB スキーマを作成（初回のみ）

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   - ":memory:" を渡すとメモリ DB が使えます。
   - 親ディレクトリがなければ自動作成されます。

2. 監査ログ用スキーマを追加する（必要に応じて）

   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn, transactional=True)

使い方（主要ユースケース）
------------------------

1) 日次 ETL を実行する

- ETL パイプラインの実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）:

  from datetime import date
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- run_daily_etl は品質チェックやエラーをサマリで返します（ETLResult）。

2) J-Quants データの取得と保存（個別利用）

- 株価日足を取得して保存:

  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)

- 財務データ / カレンダーの取得にも同様の関数があります（fetch_financial_statements / fetch_market_calendar / save_*）。

- jquants_client はレート制限・リトライ・401 自動リフレッシュを備えています。トークンは settings.jquants_refresh_token から取得されます。

3) RSS ニュース収集ジョブ

- 全ソースから収集して DB に保存し、銘柄紐付けまで行う:

  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, sources=None, known_codes=set(['7203','6758']), timeout=30)
  # results -> {source_name: saved_count}

- fetch_rss / save_raw_news / save_news_symbols を個別に使うこともできます。SSRF 対策や受信サイズ上限、トラッキング除去等が組み込まれています。

4) 研究（Research）モジュール

- ファクター計算・特徴量探索等:

  from kabusys.research import calc_momentum, calc_value, calc_volatility
  from kabusys.research import calc_forward_returns, calc_ic, factor_summary, rank
  from kabusys.data.stats import zscore_normalize

  # 例: DuckDB 接続 conn と日付 target_date を渡してそれぞれを計算
  mom = calc_momentum(conn, target_date)
  vol = calc_volatility(conn, target_date)
  val = calc_value(conn, target_date)
  fwd = calc_forward_returns(conn, target_date)
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")

- zscore_normalize でクロスセクション正規化が可能です。

5) データ品質チェック

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=..., reference_date=...)
  for issue in issues:
      print(issue)

設定取得（Settings）
-------------------

環境変数は kabusys.config.Settings でラップされています。使用例:

from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
print(settings.env, settings.is_live, settings.is_paper, settings.is_dev)

自動 .env ロード挙動:
- プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して決定します。  
- 読み込み順: OS 環境変数 > .env.local > .env  
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます（テスト用等）。

注意点 / 設計上のポイント
-----------------------

- J-Quants の API レート制限（120 req/min）に合わせて固定間隔スロットリングを行います。再試行や 401 時のトークンリフレッシュ、Retry-After ヘッダ優先などに対応しています。
- DuckDB への保存は ON CONFLICT を使った冪等処理です（重複挿入耐性）。
- ニュース収集は SSRF 対策、gzip サイズ検査、XML の安全パース（defusedxml）など安全面に配慮しています。
- 研究・データ処理モジュールは外部依存を抑え、標準ライブラリのみで実装されている箇所があります（テスト・検証が容易）。
- audit モジュールはシグナル→発注→約定を UUID ベースで追跡可能にする設計です（UTC タイムスタンプ等の制約あり）。

ディレクトリ構成
-----------------

src/kabusys/
- __init__.py
- config.py                 # 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py       # J-Quants API クライアント（fetch/save）
  - news_collector.py       # RSS ニュース収集・保存
  - schema.py               # DuckDB スキーマ定義・初期化
  - stats.py                # 統計ユーティリティ（zscore_normalize）
  - pipeline.py             # ETL パイプライン（run_daily_etl 等）
  - features.py             # 特徴量公開インターフェース（再エクスポート）
  - calendar_management.py  # 市場カレンダー管理（営業日判定・更新ジョブ）
  - audit.py                # 監査ログ用スキーマ（signal/order/execution）
  - etl.py                  # ETL 公開インターフェース（ETLResult 再エクスポート）
  - quality.py              # データ品質チェック
- research/
  - __init__.py             # 研究用ユーティリティの公開
  - factor_research.py      # Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py  # 将来リターン / IC / サマリー等
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

（上記は本リポジトリ内の主要モジュール一覧です。実際のプロジェクトでは追加モジュール・スクリプトがある場合があります）

開発上のヒント
---------------

- 単体テストや CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を有効にして環境変数の読み込みを制御すると良いです。
- DuckDB はインメモリ（":memory:"）でも利用可能なのでテストでの初期化が高速です。
- jquants_client の _request は urllib を直接使っているため、テスト時は urllib.request.urlopen / _urlopen 等をモックしてください。
- news_collector._urlopen を差し替えることでネットワーク実行部分を容易にモックできます。

ライセンス
---------

（ここにはプロジェクトのライセンス情報を記載してください — 例: MIT, Apache-2.0 等）

お問い合わせ / 贡献
-------------------

バグ報告や機能提案は issue を立ててください。Pull Request は歓迎します。

以上。README に含めてほしい追加情報（例: 実際のコマンド例、CI 設定、より詳細な API リファレンス等）があれば教えてください。