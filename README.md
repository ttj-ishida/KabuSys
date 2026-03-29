KabuSys — 日本株自動売買／データ基盤ライブラリ
===================================

概要
----
KabuSys は日本株向けの自動売買・データ基盤のための Python ライブラリ群です。本リポジトリは以下の主要機能を提供します。

- J-Quants API を使った市場データの差分 ETL（株価日足・財務・市場カレンダー）
- ニュース収集（RSS）と LLM（OpenAI）を使ったニュースセンチメント評価
- 市場レジーム判定（ETF の MA 乖離 + マクロニュースセンチメントの合成）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ 等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution）用スキーマの初期化ユーティリティ
- 環境変数（.env/.env.local）自動ロード、設定ラッパー

主なユースケースは、データパイプライン（ETL）と研究（リサーチ）、および市場情報に基づく戦略評価です。実際の発注ロジック・ブローカー連携は別層（execution 等）で実装可能です。

機能一覧
--------
- ETL（data.pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- J-Quants API クライアント（data.jquants_client）
  - fetch / save の冪等実装、リトライ・レート制御、トークン自動リフレッシュ
- ニュース収集（data.news_collector.fetch_rss）と前処理（URL 正規化・SSRF 防御）
- ニュース NLP（ai.news_nlp.score_news）
  - gpt-4o-mini を用いた銘柄ごとのセンチメント評価、バッチ送信、レスポンス検証
- 市場レジーム判定（ai.regime_detector.score_regime）
  - ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成
- 研究用ユーティリティ（research.*）
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic など
- データ品質チェック（data.quality.run_all_checks）
- 監査ログスキーマ初期化（data.audit.init_audit_db / init_audit_schema）
- 設定管理（config.Settings）
  - 環境変数をラップ、.env/.env.local の自動読み込み（プロジェクトルート検出）

セットアップ手順
----------------

前提
- Python 3.10 以上（PEP 604 の型記法や型ヒントを使用）
- system のネットワークアクセス（J-Quants / OpenAI / RSS 取得など）

1) リポジトリをクローンして開発用インストール（src レイアウトを想定）
   - プロジェクトルートで:
     - pip install -e .   （パッケージ化されている場合）
     - もしくは必要なライブラリを手動でインストール:

       pip install duckdb openai defusedxml

   主要依存:
   - duckdb
   - openai (OpenAI Python SDK)
   - defusedxml

2) 環境変数設定
   プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   必須の環境変数（用途に応じて設定）:
   - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（ETL 用）
   - KABU_API_PASSWORD     : kabuステーション API パスワード（注文実行層）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャネル ID
   - OPENAI_API_KEY        : OpenAI API キー（ai.news_nlp / ai.regime_detector 用）
   例（.env）:
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678

3) データベース
   デフォルトの DuckDB/SQLite パスは設定により変えられます（settings.duckdb_path / settings.sqlite_path）。
   デフォルト:
   - DuckDB: data/kabusys.duckdb
   - SQLite (monitoring 用): data/monitoring.db

使い方（簡単な例）
-----------------

※ ここでは Python REPL / スクリプトから呼ぶ例を示します。実運用ではジョブスケジューラやワーカーから呼び出してください。

1) 設定を参照する
   from kabusys.config import settings
   print(settings.duckdb_path)
   print(settings.env)

2) DuckDB 接続を作り ETL を実行（日次 ETL）
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())

3) ニュースセンチメントスコア（LLM を使う）
   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect(str(settings.duckdb_path))
   n_written = score_news(conn, target_date=date(2026, 3, 20))
   print(f"ai_scores に書き込んだ銘柄数: {n_written}")

   - score_news は OPENAI_API_KEY を参照（api_key 引数でも可）。
   - LLM 呼び出しは失敗耐性（リトライ・フォールバック）を持ちますが、API クォータに注意してください。

4) 市場レジーム判定
   from kabusys.ai.regime_detector import score_regime
   conn = duckdb.connect(str(settings.duckdb_path))
   score_regime(conn, target_date=date(2026,3,20))  # OpenAI API キーは環境変数または引数で指定

5) 監査ログ DB 初期化（監査専用 DB を作る）
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
   # これで監査用テーブル(signal_events / order_requests / executions) が作成される

注意点
- LLM 呼び出し（OpenAI）は API キーと利用料金が必要です。開発環境ではキーの管理に注意してください。
- J-Quants API の呼び出しには rate limit（120 req/min）があり、モジュールは固定間隔スロットリングで制御しています。
- .env の自動読み込みはプロジェクトルート（.git or pyproject.toml が存在するディレクトリ）を基準に行われます。CWD に依存しない設計です。

ディレクトリ構成
----------------

src/kabusys/
- __init__.py
- config.py                 : 環境変数・設定管理（.env 自動ロード、settings）
- ai/
  - __init__.py
  - news_nlp.py             : ニュースセンチメントスコアリング（OpenAI）
  - regime_detector.py      : 市場レジーム判定（MA + マクロセンチメント合成）
- data/
  - __init__.py
  - calendar_management.py  : 市場カレンダーの管理（営業日判定、next/prev）
  - pipeline.py             : ETL パイプライン（run_daily_etl 等）
  - jquants_client.py       : J-Quants API クライアント（fetch/save 等）
  - news_collector.py       : RSS 収集・前処理（SSRF 対策等）
  - quality.py              : データ品質チェック
  - stats.py                : 共通統計ユーティリティ（zscore_normalize）
  - audit.py                : 監査ログスキーマ初期化
  - etl.py                  : ETLResult 型のエクスポート
- research/
  - __init__.py
  - factor_research.py      : ファクター計算（momentum/value/volatility）
  - feature_exploration.py  : 将来リターン・IC・統計サマリー等
- research/... (各種研究ユーティリティ)
- その他（strategy / execution / monitoring 等はパッケージ公開対象に含める設計）

開発・テスト
-------------
- 自動ロードされる .env をテスト時に無効化したい場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- モジュール内の外部呼び出し（OpenAI やネットワーク）にはモックを注入できるよう設計されています（ユニットテストでの patch が想定されています）。

貢献・ライセンス
------------------
（リポジトリに LICENSE / CONTRIBUTING があれば参照してください。ここでは省略。）

付記
----
この README はソースコードの docstring と実装から生成しています。実運用前に .env の作成、必要な API キー・トークンの取得、DuckDB の初期スキーマ作成（必要に応じて SQL 定義を用意）を行ってください。質問や補足が必要であれば、どの機能についてもっと詳しく知りたいか教えてください。