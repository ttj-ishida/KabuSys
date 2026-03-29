KabuSys — 日本株自動売買 / データプラットフォーム
=================================

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買基盤のためのライブラリ群です。本コードベースは主に以下を提供します。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得（ETL）
- RSS によるニュース収集とニュースの前処理（SSRF 対策・正規化）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- マーケットレジーム判定（ETF の MA とマクロニュースの組合せ）
- 研究用途のファクター計算 / 特徴量解析ユーティリティ（モメンタム、ボラティリティ、バリュー、IC 等）
- データ品質チェック、監査ログ（トレーサビリティ）の初期化ユーティリティ
- DuckDB を使ったローカルデータベース保存（冪等性を重視）

設計ポリシー（抜粋）
- ルックアヘッドバイアス防止（内部で date.today() 等を直接参照しないよう配慮）
- DuckDB への保存は冪等（ON CONFLICT）で安全
- API 呼び出しはレート制限／リトライ／バックオフを実装
- セキュリティ対策（RSS の SSRF 対策、XML の defusedxml 利用 等）

主な機能一覧
-------------
- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 関数、トークン自動リフレッシュ、レートリミット）
  - market_calendar 管理（営業日判定、next/prev trading day 等）
  - news_collector（RSS 取得・正規化・保存）
  - quality（欠損・スパイク・重複・日付不整合チェック）
  - audit（監査ログテーブルの初期化・DB 作成ヘルパー）
  - stats（Zスコア正規化等の統計ユーティリティ）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores テーブルに保存
  - regime_detector.score_regime: ETF（1321）の200日MA乖離とマクロセンチメントを合成して market_regime を更新
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

セットアップ手順
----------------

1. Python 環境を準備
   - 推奨: Python 3.10+（型注釈に | を使用しているため）
   - 仮想環境を作成して有効化することを推奨します。

2. 依存パッケージをインストール
   - 必須（最小限）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください。）

3. 環境変数の設定（.env）
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の主なキー:
     - JQUANTS_REFRESH_TOKEN=（J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD=（kabuステーション のパスワード）
     - SLACK_BOT_TOKEN=（Slack 通知に使用する場合）
     - SLACK_CHANNEL_ID=（Slack 通知に使用する場合）
     - OPENAI_API_KEY=（OpenAI を使う場合。score_news / score_regime に必要）
   - 任意:
     - DUCKDB_PATH=data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH=data/monitoring.db（デフォルト）
     - KABUSYS_ENV=development|paper_trading|live（デフォルト development）
     - LOG_LEVEL=INFO|DEBUG|...（デフォルト INFO）

   例 (.env):
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG

4. DuckDB データベース初期化（監査ログ等）
   - 監査テーブルを作る例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - または既存の接続に対して init_audit_schema(conn) を呼び出すことも可能。

使い方（代表例）
---------------

- DuckDB に接続して ETL を実行（日次差分 ETL）:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースセンチメント（銘柄別）を算出して保存:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数にセットされていれば api_key 引数は不要
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"written scores: {written}")

- マーケットレジーム判定の実行:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))  # market_regime テーブルを更新

- 監査ログスキーマ初期化（既存 DB 接続に適用）:
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)

主な関数 / エントリポイント（一覧）
- data.pipeline.run_daily_etl(...) — 日次 ETL（カレンダー→株価→財務→品質チェック）
- data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
- data.news_collector.fetch_rss(...) — RSS 取得（SSRF 対策あり）
- ai.news_nlp.score_news(conn, target_date, api_key=None)
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
- research.factor_research.calc_momentum / calc_volatility / calc_value
- data.quality.run_all_checks(conn, ...)

運用上の注意点
-------------
- OpenAI 利用には API キー（OPENAI_API_KEY）が必要です。score_news / score_regime は API 呼び出し失敗時にフェイルセーフ（スコアを 0 にフォールバック）する設計ですが、API 利用料やレート制限に注意してください。
- J-Quants API のレート制限（120 req/min）を守るために内部でスロットリング・リトライを行っています。J-Quants の資格情報（リフレッシュトークン）は安全に管理してください。
- .env の自動ロードはプロジェクトルート（.git か pyproject.toml の存在）を基準に行います。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に対する executemany の空リスト渡しなどの互換性問題に注意しており、モジュール内で対策済みです。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py            : パッケージ定義（version）
- config.py              : 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings）
- ai/
  - __init__.py
  - news_nlp.py          : 銘柄別ニュースセンチメントの取得・DB 書込
  - regime_detector.py   : マーケットレジーム判定（ETF MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py    : J-Quants API クライアント（fetch/save, auth, rate limit）
  - pipeline.py          : ETL パイプライン（run_daily_etl 等）
  - news_collector.py    : RSS 取得・正規化・SSRF 対策
  - calendar_management.py : 市場カレンダー管理・営業日判定
  - quality.py           : データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit.py             : 監査ログテーブル定義・初期化 / init_audit_db
  - etl.py               : ETLResult のエクスポート（薄いラッパー）
  - stats.py             : 統計ユーティリティ（zscore_normalize）
- research/
  - __init__.py
  - factor_research.py   : Momentum / Value / Volatility 等の計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー

補足（設計上のポイント）
-----------------------
- ルックアヘッドバイアスに配慮して、target_date を引数で与えるパターンが多く、内部で現在時刻を直接参照しない設計です（バックテスト用途で重要）。
- 外部 API 呼び出しはリトライ・バックオフ・タイムアウトを備え、OpenAI 呼び出しはレスポンスのバリデーションを行います。
- RSS 収集部分は URL 正規化・トラッキングパラメータ除去・プライベート IP 検査・gzip サイズ検査・XML の defusedxml を使用するなど安全面を重視しています。

ライセンス / 貢献
-----------------
（このリポジトリのライセンスに関する情報をここに追記してください）

問題報告やプルリクエストは歓迎します。機能改善や互換性の確認はテスト環境（paper_trading）で十分に検証してから本番（live）へ反映してください。

-----------

必要があれば、README に具体的な .env.example、起動スクリプト例、Dockerfile、CI 設定などの追加を作成します。どの内容を優先しますか？