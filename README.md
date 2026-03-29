KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株のデータ取得（ETL）、データ品質チェック、特徴量/ファクター計算、ニュースNLP（LLM を用いたセンチメント分析）、市場レジーム判定、監査ログ等を含む研究・運用向けのライブラリ群です。DuckDB をデータプラットフォームに、J-Quants API でマーケットデータを取得し、OpenAI（gpt-4o-mini など）をニュース解析に利用する設計になっています。

主な機能
--------
- データ ETL（J-Quants からの株価・財務・カレンダー取得）: kabusys.data.pipeline.run_daily_etl
- データ品質チェック（欠損・重複・スパイク・日付不整合）: kabusys.data.quality
- ニュース収集・前処理（RSS）: kabusys.data.news_collector.fetch_rss
- ニュースの LLM ベースセンチメント（銘柄別 ai_scores 生成）: kabusys.ai.news_nlp.score_news
- 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメントの合成）: kabusys.ai.regime_detector.score_regime
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティなど）: kabusys.research.*
- 監査ログスキーマの初期化・監査 DB 管理: kabusys.data.audit.init_audit_db
- J-Quants API クライアント（ページネーション・トークン自動リフレッシュ・レート制御・保存関数）: kabusys.data.jquants_client

セットアップ（開発環境向け）
-------------------------
1. Python 環境準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（最低必要）
   - pip install duckdb openai defusedxml

   ※プロジェクトをパッケージとして整備している場合:
   - pip install -e .

   （実運用では追加で requests 等が必要になる箇所があるかもしれません。requirements.txt がある場合はそれを使用してください。）

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml を基準）に .env を配置すると自動で読み込まれます。
     - 読み込み優先順: OS 環境 > .env.local > .env
     - 自動ロードを無効化するには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID      : Slack チャネル ID（必須）
   - 任意 / デフォルト値:
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
     - KABU_API_BASE_URL — デフォルト http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

基本的な使い方（コード例）
-----------------------

- DuckDB 接続を作って ETL を実行する（日次パイプライン）:

  ```
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str("<path-to-duckdb-file>"))  # 例: settings.duckdb_path
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアを付ける（OpenAI API キーは OPENAI_API_KEY 環境変数、または api_key 引数で渡す）:

  ```
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数を使う場合 api_key=None
  print("書き込んだ銘柄数:", count)
  ```

- 市場レジームを判定して保存する:

  ```
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を参照
  ```

- 監査ログ用の DuckDB を初期化する（監査テーブル作成）:

  ```
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成されます
  ```

- カレンダー更新バッチ（J-Quants から JPX カレンダーを取得）:

  ```
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import calendar_update_job

  conn = duckdb.connect("data/kabusys.duckdb")
  saved_count = calendar_update_job(conn)
  print("保存レコード数:", saved_count)
  ```

OpenAI / API キーについて
-------------------------
- news_nlp.score_news と regime_detector.score_regime は OpenAI API キーを必要とします。
  - 引数 api_key に直接渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants にはリフレッシュトークン（JQUANTS_REFRESH_TOKEN）を用い、モジュール内で ID トークンを取得・キャッシュします。

動作上の注意 / 設計方針の抜粋
----------------------------
- ルックアヘッドバイアス対策: 多くの関数は datetime.today()/date.today() を直接参照せず、引数で target_date を受け取り、DB クエリも target_date より前のデータのみを利用する設計です。
- ETL は差分更新 + バックフィル（デフォルト3日）を行い、API の後出し修正を吸収します。
- J-Quants クライアントはレート制御（120 req/min）・リトライ・トークンリフレッシュを備えます。
- ニュース収集には SSRF 対策、XML の安全パーシング（defusedxml）、受信サイズ制限、URL 正規化（トラッキング除去）等の安全策を実装しています。
- API 呼び出し（OpenAI 等）はエラー時にフェイルセーフ（0.0 フォールバックやスキップ）を行う箇所があり、全体の処理停止を最小化します。

ディレクトリ構成（主要ファイルと役割）
------------------------------------
- src/kabusys/
  - __init__.py — パッケージ初期化、公開モジュール定義
  - config.py — 環境変数 / 設定の読み込みと検証（自動 .env ロード機能）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを銘柄ごとにまとめて OpenAI に投げ、ai_scores に書き込む
    - regime_detector.py — ETF 1321 の MA とマクロニュースの LLM センチメントを合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + 保存関数（raw_prices / raw_financials / market_calendar 等）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得・正規化・raw_news への保存ロジック
    - calendar_management.py — 市場カレンダー管理・営業日判定・calendar_update_job
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — zscore_normalize 等の汎用統計ユーティリティ
    - audit.py — 監査ログテーブル定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — モメンタム / バリュー / ボラティリティ等の計算
    - feature_exploration.py — 将来リターン計算、IC（情報係数）、統計サマリー
  - (その他) strategy / execution / monitoring 等は __all__ に想定されています（実装の拡張部分）

ログ/環境
---------
- KABUSYS_ENV: development / paper_trading / live（settings.env で検証）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。
- 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

貢献・拡張
---------
- 各モジュールは DuckDB 接続を受け取る設計なので、テストでは in-memory DB(":memory:") を使って単体テストが容易です。
- OpenAI 呼び出しやネットワークリクエストは内部でラップしてあるため、ユニットテストでは該当関数をモックして挙動を検証してください。
- 監査ログや発注機能はスキーマ定義済みで、運用側で発注ロジックやブローカー統合を実装できます。

ライセンス / 免責
-----------------
（この README にはライセンス情報は含まれていません。実際の配布時は LICENSE を追加してください。）

付録: よく使う関数（参考）
-------------------------
- ETL 実行: kabusys.data.pipeline.run_daily_etl(conn, target_date, id_token=None)
- ニューススコア: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 監査 DB 初期化: kabusys.data.audit.init_audit_db(db_path)
- カレンダー更新ジョブ: kabusys.data.calendar_management.calendar_update_job(conn)

質問・サポート
--------------
この README を読んで不明点があれば、使い方の具体的なユースケース（ローカル実行・本番デプロイ・バックテスト用データ準備など）を教えてください。使い方のスニペットや設定例をより詳細に提供します。