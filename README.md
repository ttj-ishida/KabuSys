KabuSys — 日本株自動売買プラットフォーム（README）
=====================================

概要
----
KabuSys は日本株向けのデータプラットフォーム兼リサーチ／自動売買基盤の一部です。
主に以下を目的としたモジュール群を提供します。

- J-Quants API を用いた株価／財務／マーケットカレンダーの差分 ETL
- ニュースの収集・NLP（LLM）による銘柄センチメント付与
- マーケット・レジーム判定（ETF + マクロセンチメントの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック、マーケットカレンダー管理
- 監査ログ（signal → order → execution のトレーサビリティ）初期化ユーティリティ

このリポジトリはモジュール群（kabusys パッケージ）を提供し、DuckDB を内部データ格納として想定しています。

主な機能一覧
--------------
- ETL（kabusys.data.pipeline）
  - run_daily_etl: カレンダー・株価・財務の差分取得と品質チェックを一括実行
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得・前処理・raw_news への保存補助ロジック
- ニュース NLP（kabusys.ai.news_nlp）
  - score_news: 指定ウィンドウのニュースを銘柄ごとに集約し、OpenAI でセンチメント付与 → ai_scores へ保存
- レジーム判定（kabusys.ai.regime_detector）
  - score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime を更新
- 研究モジュール（kabusys.research）
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary 等
- データ品質（kabusys.data.quality）
  - 欠損・重複・スパイク・日付不整合検出
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 監査ログ初期化（kabusys.data.audit）
  - init_audit_schema / init_audit_db（監査テーブルとインデックスを冪等に作成）

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <this-repo-url>
   - cd <repo>

2. Python 環境（推奨: venv）を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -e .              # パッケージとしてインストール（セットアップツールが用意されている想定）
   - または最低限:
     pip install duckdb openai defusedxml

   必要に応じて他の依存（logging 等は標準ライブラリ）を追加してください。

4. 環境変数 / .env の準備
   - プロジェクトルート（.git か pyproject.toml 配下）に .env ファイルを置くと自動で読み込まれます。
   - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です（テスト等で利用）。
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime で必要）
     - KABU_API_PASSWORD      : kabu ステーション API パスワード（使用する場合）
     - KABUSYS_ENV            : development | paper_trading | live（デフォルト development）
     - LOG_LEVEL              : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
     - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH            : 監視用 SQLite（デフォルト data/monitoring.db）
   - .env の読み込みルール:
     - OS 環境変数 > .env.local > .env の順でマージ
     - .env 解析はシェルスタイル（export KEY=val / quotes / inline comment 処理あり）

使い方（主要な API 例）
-----------------------

以下は簡単な使用例です。実行前に必須の環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）を設定してください。

- DuckDB 接続を作る（デフォルトパスを使う）
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのセンチメント付与（score_news）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使う
  print(f"written: {n_written}")

- 市場レジーム判定（score_regime）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB 初期化
  from pathlib import Path
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db(Path("data/audit.duckdb"))

- RSS フィードを取得する（ニュースコレクタの一部ユーティリティ）
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])

- J-Quants クライアント直接利用例
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  rows = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))

設定（config）について
---------------------
- settings オブジェクト: kabusys.config.settings を通じて各種設定へアクセスできます。
  例: settings.duckdb_path, settings.sqlite_path, settings.is_live, settings.log_level, settings.jquants_refresh_token など。
- 環境値がないと必須項目は ValueError を送出します（例: JQUANTS_REFRESH_TOKEN）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/
  kabusys/
    __init__.py                 # パッケージ初期化（バージョン等）
    config.py                   # .env / 環境変数読み込みと Settings
    ai/
      __init__.py
      news_nlp.py               # ニュース NLU / score_news
      regime_detector.py        # レジーム判定 score_regime
    data/
      __init__.py
      jquants_client.py         # J-Quants API クライアント、保存関数
      pipeline.py               # ETL パイプライン（run_daily_etl 等）
      calendar_management.py    # マーケットカレンダー管理
      news_collector.py         # RSS 収集ユーティリティ
      quality.py                # データ品質チェック
      stats.py                  # z-score 等汎用統計
      etl.py                    # ETLResult の再エクスポート
      audit.py                  # 監査ログテーブル初期化
    research/
      __init__.py
      factor_research.py        # calc_momentum / calc_value / calc_volatility
      feature_exploration.py    # forward returns, IC, factor_summary, rank
    research/（...）
    ai/（...）
    monitoring/（未掲示の監視モジュールが想定される）
    execution/（未掲示の注文実行モジュールが想定される）
その他:
  pyproject.toml / setup.cfg 等（プロジェクトルート）

開発メモ・設計上の注意点
------------------------
- Look-ahead bias 回避
  - モジュールは内部で datetime.today() 等（ランタイムの現在時刻）に依存しない設計が意識されています。
  - ETL / scoring 関数は target_date を明示するインターフェースを採用しています。

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読込します。
  - テストや意図的に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI 呼び出し
  - OpenAI のレスポンスは JSON モードを想定していますが、パース失敗時はフェイルセーフ（0.0 や空スコア）で続行する設計です。
  - API キーは api_key 引数で注入可能（テスト容易性のため）。

- DuckDB 互換性
  - 一部実装は DuckDB の executemany の制約（空リストバインド不可など）を考慮しています。

トラブルシューティング
----------------------
- 環境変数未設定で ValueError が出る場合は .env を作成して必要変数を設定してください。
- OpenAI や J-Quants の接続エラーはリトライロジックを持ちますが、ネットワーク/認証が正しいか確認してください。
- DuckDB ファイルの親ディレクトリは自動作成されますが、権限周りでエラーが出る場合はパスと書込権限を確認してください。

ライセンス・貢献
----------------
- この README の配布対象に関するライセンス情報はリポジトリ内の該当ファイル（LICENSE）を参照してください（本READMEでは記載なし）。

お問い合わせ・貢献
------------------
- バグ報告、機能提案、プルリクエストは GitHub の Issue / Pull Request を通じてお願いします。

以上。README の補足やサンプルコードの追加、CI / テスト手順の記載などが必要でしたらお知らせください。