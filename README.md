KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォーム兼研究・自動売買支援ライブラリです。  
主な機能は以下のとおりです。

- J-Quants API を用いた株価・財務・カレンダーの差分ETL（DuckDB への保存）
- ニュース収集・前処理（RSS）と LLM を用いたニュース・センチメント評価
- 市場レジーム判定（MA200 とマクロニュースの組合せ）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、IC 等）
- 監査ログ（signal → order_request → execution のトレース用テーブル）初期化ユーティリティ
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- kabuステーション等への発注・監視ロジック（発注周りのモジュールは別途実装）

設計方針の特徴:
- Look-ahead bias を避けるため、内部で datetime.today()/date.today() を不用意に参照しない
- DuckDB をメインの永続化層として扱い、ETL/保存は冪等（ON CONFLICT）で実装
- 外部API呼び出しはリトライ・バックオフ・フェイルセーフを備える

主な機能一覧
--------------
- データ収集 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl (kabusys.data.pipeline)
  - J-Quants クライアント：fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar (kabusys.data.jquants_client)
- ニュース処理 / AI
  - RSS 取得・前処理・保存支援 (kabusys.data.news_collector)
  - ニュースセンチメント: score_news (kabusys.ai.news_nlp)
  - 市場レジーム判定: score_regime (kabusys.ai.regime_detector)
- 研究用ユーティリティ
  - ファクター計算: calc_momentum, calc_value, calc_volatility (kabusys.research.factor_research)
  - 将来リターン / IC / 統計: calc_forward_returns, calc_ic, factor_summary, rank (kabusys.research.feature_exploration)
  - Zスコア正規化: zscore_normalize (kabusys.data.stats)
- データ品質 / カレンダー
  - market_calendar 管理、営業日判定 (kabusys.data.calendar_management)
  - データ品質チェック一括実行 run_all_checks (kabusys.data.quality)
- 監査ログ（監査テーブルの初期化）
  - init_audit_schema / init_audit_db (kabusys.data.audit)
- 環境設定
  - settings（環境変数 / .env の読み込み）(kabusys.config)

前提条件 / 必須ソフトウェア
-------------------------
- Python 3.10+
- 必須 Python パッケージ（少なくとも以下をインストールしてください）:
  - duckdb
  - openai
  - defusedxml

インストール（開発環境）
-----------------------
1. リポジトリをクローン
   - git clone <repo-url>
2. 現在のソースを開発モードでインストール
   - python -m pip install -e .
3. 必要パッケージを個別にインストール（まだであれば）
   - python -m pip install duckdb openai defusedxml

環境変数 / .env
----------------
プロジェクトは .env または環境変数から設定を読み込みます（kabusys.config）。自動読み込みはデフォルトで有効です。無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

代表的な環境変数（.env の例）

JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
OPENAI_API_KEY=あなたの_openai_api_key
KABU_API_PASSWORD=kabu_station_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 任意（デフォルト）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO

使い方（簡単な例）
-----------------

1) Settings と DuckDB 接続の準備

    from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL の実行（J-Quants からデータ取得して保存・品質チェック）

    from kabusys.data.pipeline import run_daily_etl
    from datetime import date
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

3) ニュースセンチメントのスコアリング

    from kabusys.ai.news_nlp import score_news
    from datetime import date
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"scored {n_written} codes")

- score_news は API キーを引数 api_key で明示的に渡すか、環境変数 OPENAI_API_KEY を参照します。

4) 市場レジーム判定

    from kabusys.ai.regime_detector import score_regime
    from datetime import date
    score_regime(conn, target_date=date(2026, 3, 20))
    # market_regime テーブルに書き込まれます

5) 監査ログ（audit DB）初期化

    from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")
    # init_audit_schema は transactional 引数で BEGIN/COMMIT を指定可能

6) ニュース RSS の取得（保存はアプリ側で行う）

    from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
    for a in articles:
        print(a["id"], a["datetime"], a["title"])

注意点 / 設計上の挙動
-------------------
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行います。テストや意図的な挙動制御には KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- 環境 KABUSYS_ENV は development / paper_trading / live のいずれかで、live の場合は本番向けの挙動を行う想定です（本番発注周りは慎重に扱ってください）。
- OpenAI 呼び出しはリトライ / フェイルセーフを備えていますが、API鍵の管理・コストに注意してください。
- ETL やスキーマ変更は冪等になるよう設計されています（ON CONFLICT 等）。ただし DB バックアップは必ず取得してください。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- __init__.py
  - パッケージメタ情報（__version__）とサブパッケージ公開

- config.py
  - 環境変数 / .env 読み込み、Settings クラス（設定の集中管理）

- ai/
  - __init__.py
  - news_nlp.py        : ニュースを LLM で評価して ai_scores に書き込むロジック
  - regime_detector.py : MA200 とマクロニュースを合成して market_regime を算出

- data/
  - __init__.py
  - jquants_client.py  : J-Quants API クライアント（取得・保存関数）
  - pipeline.py        : ETL パイプライン（run_daily_etl 等）
  - etl.py             : ETL 結果データ型の再エクスポート
  - news_collector.py  : RSS 取得と前処理ユーティリティ
  - calendar_management.py : 市場カレンダー管理（営業日判定など）
  - quality.py         : データ品質チェック
  - stats.py           : 汎用統計ユーティリティ（zscore_normalize）
  - audit.py           : 監査ログ（テーブル定義・初期化）
  - (その他): jquants_client 内に保存系関数やユーティリティ

- research/
  - __init__.py
  - factor_research.py : Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py : 将来リターン / IC / 統計サマリ等

テーブル（想定される主要スキーマ）
----------------------------------
各モジュールは以下のようなテーブルを想定しています（詳細はコード内 SQL を参照してください）。

- raw_prices / prices_daily (株価)
- raw_financials (財務データ)
- market_calendar (JPX カレンダー)
- raw_news, news_symbols, ai_scores (ニュース・紐付け・AIスコア)
- market_regime (レジーム判定結果)
- signal_events, order_requests, executions (監査ログ用テーブル)

追加情報 / 開発者向けメモ
------------------------
- テストやモック：
  - AI 呼び出しやネットワーク関連は内部関数をモックしてテストしやすく設計しています（例: kabusys.ai.news_nlp._call_openai_api を patch 等）。
- ロギング：
  - LOG_LEVEL 環境変数で制御できます。設定は Settings.log_level を通して検証されます。
- セキュリティ：
  - RSS の取得では SSRF・XML Bomb 対策（defusedxml、リダイレクト先検査、プライベートIPブロック）を行っています。

貢献
----
機能追加・バグ修正の PR を歓迎します。変更を加える際はユニットテスト・静的解析（flake8 等）を追加してください。

免責
----
本プロジェクトは投資アドバイスを提供するものではありません。本コードを利用した取引による損失について一切の責任を負いません。実行・本番投入は自己責任で行ってください。

--- 

必要であれば README に実例（より詳細な .env.example、DuckDB スキーマ定義、運用手順、サンプルスクリプト）を追記します。どの部分を詳しく記述しますか？