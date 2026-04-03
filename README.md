KabuSys
======

日本株向けのデータパイプライン・リサーチ・AIスコアリング・監査・ETL を含む自動売買（研究）向けライブラリ群です。  
（パッケージ名: kabusys）

この README はこのリポジトリに含まれる主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成をまとめたものです。

概要
----
KabuSys は以下を主目的としたモジュール群です。

- J-Quants API から日次株価・財務・カレンダー等を差分取得・保存する ETL
- ニュースの収集と OpenAI によるニュースセンチメント（銘柄毎 / マクロ）スコアリング
- 市場レジーム判定（ETF の MA200 乖離 × マクロセンチメント合成）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（信号→発注→約定の追跡）用スキーマの初期化ユーティリティ

設計方針のハイライト
- ルックアヘッドバイアス防止: datetime.today() を直接参照しない等の配慮
- DuckDB を中心としたローカル DB ベース（ETL の保存・検査・監査）
- OpenAI / J-Quants など外部 API 呼び出しにはリトライ・バックオフ・フェイルセーフ実装
- 冪等性を考慮した DB 書き込み（ON CONFLICT / DELETE→INSERT など）

主な機能一覧
--------------
- データ ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）
- ニュース収集・前処理
  - RSS 取得・正規化・raw_news 保存（kabusys.data.news_collector）
- ニュース NLP（OpenAI）
  - 銘柄別センチメントスコアリング: score_news (kabusys.ai.news_nlp)
  - マクロセンチメント + MA200 による市場レジーム判定: score_regime (kabusys.ai.regime_detector)
- 研究・ファクター計算
  - calc_momentum / calc_value / calc_volatility（kabusys.research.factor_research）
  - 将来リターン・IC・統計サマリ等（kabusys.research.feature_exploration）
  - zscore_normalize 等の汎用統計ユーティリティ（kabusys.data.stats）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出
- 監査ログ初期化
  - init_audit_schema / init_audit_db（kabusys.data.audit）
- 設定管理
  - 環境変数 / .env 自動読み込み・Settings オブジェクト（kabusys.config）

前提・必須ソフトウェア
--------------------
- Python 3.10 以上（ソース内で X | Y 型注釈等を使用）
- 必要な Python パッケージ（代表）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の依存はコード参照にて追加してください）

セットアップ手順
----------------

1. リポジトリをクローンし、仮想環境を作成・有効化
   - 例:
     python -m venv .venv
     source .venv/bin/activate   # macOS / Linux
     .venv\Scripts\activate      # Windows (PowerShell)

2. インストール（ローカル開発用）
   - pip install -e . でパッケージをeditableにするか、必要パッケージを個別にインストール
   - 代表的な依存のインストール例:
     pip install duckdb openai defusedxml

   （requirements.txt がある場合は pip install -r requirements.txt を使用してください）

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env または .env.local を配置すると自動で読み込まれます（kabusys.config が自動ロード）。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   代表的な環境変数（.env に設定する例）:
   - JQUANTS_REFRESH_TOKEN=...(必須: J-Quants のリフレッシュトークン)
   - OPENAI_API_KEY=...(OpenAI API キー。score_news / score_regime の引数で上書き可能)
   - KABU_API_PASSWORD=...(kabuステーション API のパスワード)
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - KILL_FLAG_CLEAR_ON_START=0
   - CPU_THRESHOLD_PCT=90.0
   - MEMORY_THRESHOLD_PCT=85.0
   - DISK_THRESHOLD_PCT=90.0
   - KABUSYS_ENV=development  # valid: development, paper_trading, live
   - LOG_LEVEL=INFO

   注意: Settings は必須変数（JQUANTS_REFRESH_TOKEN 等）を参照すると ValueError を出すため、必要な値は設定してください。

基本的な使い方（コード例）
------------------------

以下は Python REPL などからの利用例です。適宜 import して利用します。

- Settings（設定）を参照する
  from kabusys.config import settings
  print(settings.duckdb_path)        # DUCKDB パス
  print(settings.jquants_refresh_token)  # 必須（未設定なら例外）

- DuckDB 接続の作成
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL（run_daily_etl）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（銘柄別）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, target_date=date(2026,3,20))  # ai_scores テーブルへ書き込み

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))  # market_regime テーブルへ書き込み

- 監査ログ DB 初期化（監査専用の DuckDB を作る）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")  # 初期化済み接続返却

- 研究用ファクター計算（例: モメンタム）
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  recs = calc_momentum(conn, date(2026,3,20))
  # recs は [{'date': ..., 'code': 'XXXX', 'mom_1m': ..., ...}, ...]

注意点・運用上のポイント
-----------------------
- .env の自動ロードはプロジェクトルートを .git または pyproject.toml で検出します。パッケージ配布後も動作するように __file__ を起点に探索します。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは API キーの設定が必要です。score_news/score_regime は api_key 引数で上書き可能。
- J-Quants API 呼び出しでは内部で id_token の自動リフレッシュ・レート制御が行われます。JQUANTS_REFRESH_TOKEN の設定が必要です。
- DuckDB の executemany に空リストを渡すとバージョン依存でエラーになることがあるため、コード側で空チェックされています（実装済み）。
- 日付の扱いはすべて date / naive datetime（UTC基準の変換を必要に応じて行う設計）に統一されています。バックテスト等でのルックアヘッドバイアスに注意してください。

ディレクトリ構成
----------------

src/
  kabusys/
    __init__.py                -- パッケージ初期化、__version__
    config.py                  -- .env / 環境変数管理 (settings)
    ai/
      __init__.py              -- ai パブリック API エクスポート
      news_nlp.py              -- 銘柄別ニューススコアリング（score_news）
      regime_detector.py       -- 市場レジーム判定（score_regime）
    data/
      __init__.py
      jquants_client.py        -- J-Quants API クライアント（fetch/save）
      pipeline.py              -- ETL パイプラインと run_daily_etl 等
      etl.py                   -- ETLResult の再エクスポート
      news_collector.py        -- RSS 収集・前処理
      quality.py               -- データ品質チェック
      stats.py                 -- 汎用統計ユーティリティ（zscore_normalize）
      calendar_management.py   -- 市場カレンダー管理（is_trading_day 等）
      audit.py                 -- 監査ログスキーマ初期化
    research/
      __init__.py
      factor_research.py       -- モメンタム / バリュー / ボラティリティ計算
      feature_exploration.py   -- 将来リターン / IC / 統計サマリ
    monitoring/                 -- （発注監視や実行モジュール等が入る想定）
    strategy/                   -- （戦略定義 / モデルが入る想定）
    execution/                  -- （注文実行・ブローカ連携が入る想定）
    data/ (上記の data パッケージと混同しないよう注意)

主な公開 API（抜粋）
- kabusys.config.settings                -- 設定オブジェクト
- kabusys.data.pipeline.run_daily_etl    -- 日次 ETL 実行
- kabusys.ai.news_nlp.score_news         -- ニューススコアリング
- kabusys.ai.regime_detector.score_regime-- 市場レジーム判定
- kabusys.data.audit.init_audit_db       -- 監査 DB 初期化
- kabusys.research.*                     -- ファクター・統計関連

貢献・テスト
--------------
- ローカルでの開発は virtualenv を使い、パッケージを editable にインストールして作業してください（pip install -e .）。
- 外部 API（J-Quants / OpenAI）を実際に呼ぶためのキーは環境変数または関数引数で注入できます。ユニットテストでは外部呼び出しをモックすることを推奨します（コード中にモック用の差し替え箇所が想定されています）。

ライセンス・その他
------------------
- 本 README はリポジトリ内のコードに基づいて作成されています。実運用時は各 API（J-Quants / OpenAI / kabuステーション 等）の利用規約に従ってください。

以上。必要があれば README にサンプル .env.example（テンプレート）や具体的な CLI / サービス起動方法を追記します。どの形式で追加したいか教えてください。