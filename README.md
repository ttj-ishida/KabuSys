KabuSys
=======

概要
----
KabuSys は日本株のデータ取得・前処理・研究・AIベースのニュースセンチメント判定・監視・監査ログを含む、日本株自動売買プラットフォーム向けのライブラリ群です。  
主に以下用途を想定しています。

- J-Quants からのデータ ETL（株価日足、財務、マーケットカレンダー）
- ニュース収集と LLM（OpenAI）によるセンチメントスコア付与
- 日次 ETL パイプラインとデータ品質チェック
- ファクター計算・特徴量探索（研究用）
- 市場レジーム判定（MA と マクロニュースの合成）
- オーディット（監査）用テーブルの初期化と管理
- DuckDB を中心としたローカルデータ保存

主要機能
--------
- データ ETL
  - run_daily_etl による日次差分 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - jquants_client: J-Quants API からの安全な取得・レート制御・リトライ・保存関数
- ニュースと AI
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策、トラッキング除去）
  - news_nlp.score_news: OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出・ai_scores へ保存
  - regime_detector.score_regime: ETF(1321) の MA200 とマクロニュースから市場レジームを判定
- 研究（Research）
  - calc_momentum, calc_value, calc_volatility（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量解析・統計）
  - zscore_normalize（共通統計ユーティリティ）
- データ品質・カレンダー
  - quality モジュールで欠損・重複・スパイク・日付不整合検査
  - calendar_management で営業日判定・calendar 更新バッチ
- 監査ログ（Audit）
  - init_audit_schema / init_audit_db による監査テーブル初期化（signal / order_request / executions 等）
- 設定管理
  - config.Settings: 環境変数 / .env 読み込み、主要パスや閾値の取得

セットアップ
-----------
前提
- Python 3.10 以上を推奨（型ヒントに | 演算子を使用）
- DuckDB、OpenAI SDK、defusedxml などの依存パッケージが必要

インストール（開発用）
- リポジトリルートで（パッケージ化済みであれば pip install でも可）:
  pip install -e .[dev]
（requirements の管理は本リポジトリに含まれる設定に従ってください。最低限 duckdb, openai, defusedxml が必要です）

環境変数 / .env
- プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（CWD に依存せず __file__ を起点に探索）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 主要な環境変数:

  - JQUANTS_REFRESH_TOKEN (必須)  
    J-Quants のリフレッシュトークン（ETL 実行に必須）

  - KABU_API_PASSWORD (必須)  
    kabu ステーション API のパスワード（発注等に使用）

  - KABU_API_BASE_URL (任意)  
    kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

  - OPENAI_API_KEY (必要に応じて)  
    OpenAI API キー（news_nlp.score_news / regime_detector.score_regime 等で使用）。api_key を関数引数で渡すことも可能。

  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)  
    LINE 通知用トークン

  - DUCKDB_PATH (任意)  
    DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）

  - SQLITE_PATH (任意)  
    監視用 SQLite パス（デフォルト: data/monitoring.db）

  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT  
    実行監視・停止等の設定

  - KABUSYS_ENV (development | paper_trading | live)  
    実行環境

  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

注意: config._parse_env_line はシングル/ダブルクォート、export プレフィックス、インラインコメント等に柔軟に対応します。

使い方（簡単なコード例）
--------------------

1) 設定と DuckDB 接続を作る
- 一例:
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())

3) ニュースセンチメントで ai_scores を生成する
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # OpenAI API キーは OPENAI_API_KEY 環境変数または api_key 引数で渡す
  n = score_news(conn, target_date=date(2026,3,20))
  print(f"written {n} scores")

4) 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))  # OpenAI API キーは環境変数か引数

5) 監査ログ DB 初期化
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db(settings.duckdb_path)  # ファイルを作成して監査テーブルを初期化

6) 研究用ファクター計算例
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  rows = calc_momentum(conn, target_date=date(2026,3,20))
  # rows: list of dict にファクターが格納される

主要な API（抜粋）
- kabusys.config.settings: 各種設定プロパティ
- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.news_collector.fetch_rss
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.research.*: calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary
- kabusys.data.quality.run_all_checks(conn, ...)

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                    -- 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                -- ニュースセンチメント（LLM 呼び出し、バッチ処理）
  - regime_detector.py        -- 市場レジーム判定（MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py         -- J-Quants API クライアント（取得・保存）
  - pipeline.py               -- ETL パイプライン（run_daily_etl 等）
  - etl.py                    -- ETLResult 再エクスポート
  - news_collector.py         -- RSS 取得と前処理
  - calendar_management.py    -- 市場カレンダー管理・判定ユーティリティ
  - stats.py                  -- zscore_normalize 等統計ユーティリティ
  - quality.py                -- データ品質チェック
  - audit.py                  -- 監査テーブル定義 / 初期化
- research/
  - __init__.py
  - factor_research.py        -- モメンタム / ボラティリティ / バリュー
  - feature_exploration.py    -- 将来リターン、IC、統計サマリー
- monitoring/, strategy/, execution/  (パッケージ配下で利用される想定のサブ機能群)

設計上の注意点
-------------
- Look-ahead bias に配慮して、ほとんどの関数は内部で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取ります。
- DuckDB を中心に設計されており、ETL は冪等（ON CONFLICT DO UPDATE）で保存します。
- OpenAI 呼び出しは JSON Mode を利用し、応答検証とリトライ（429/ネットワーク/5xx）を実装しています。APIキーは環境変数または関数引数で注入してください。
- news_collector は SSRF 対策・受信サイズ制限・XML パースの安全化（defusedxml）等の安全策を講じています。

トラブルシューティング
---------------------
- 環境変数が足りない場合、config.Settings は ValueError を投げます（必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
- OpenAI API 呼び出し失敗時は多くの処理が安全側（スコア 0.0 を採用、あるいは処理をスキップ）で継続する設計です。ログを確認してください。
- DuckDB への executemany に空リストを渡すと失敗するバージョン対策がコード内にあります（空チェック済み）。

貢献
----
バグ修正・機能改善は Pull Request を歓迎します。変更の際はユニットテスト（可能なら）を追加してください。

ライセンス
----------
（この README ではライセンス記載がありません。リポジトリの LICENSE を参照してください。）

付録: よく使う例（まとめ）
- ETL 実行:
  from kabusys.config import settings
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect(str(settings.duckdb_path))
  run_daily_etl(conn)

- ニューススコア:
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date=date(2026,3,20))

- レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))

以上が本プロジェクトの概要・セットアップ・使い方のガイドです。具体的な使い方や CI/デプロイに関する追加情報はリポジトリ内のドキュメント（DataPlatform.md 等）やソースコメントを参照してください。