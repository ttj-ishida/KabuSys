# KabuSys — 日本株自動売買プラットフォーム（README）

概要
-----
KabuSys は日本株を対象としたデータプラットフォーム兼自動売買補助ライブラリです。  
主な目的は以下の通りです。

- J-Quants API を用いた株価・財務・マーケットカレンダーなどの ETL（差分取得・保存・品質チェック）
- ニュース収集・NLP による銘柄別センチメントスコア算出（OpenAI を利用）
- 市場レジーム判定（ETF MA とマクロニュースの LLM センチメントの合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ管理
- DuckDB を中心としたローカルデータ保存と分析ユーティリティ

主な機能
---------
- データ ETL（kabusys.data.pipeline.run_daily_etl で日次パイプラインを実行）
- ニュース収集（kabusys.data.news_collector.fetch_rss）
- ニュース NLP（kabusys.ai.news_nlp.score_news：銘柄単位の ai_score を ai_scores テーブルへ保存）
- 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- ファクター計算（kabusys.research.calc_momentum / calc_value / calc_volatility）
- 統計ユーティリティ（zscore 正規化等 / kabusys.data.stats）
- データ品質チェック（kabusys.data.quality.run_all_checks）
- 監査ログスキーマ初期化（kabusys.data.audit.init_audit_db / init_audit_schema）
- J-Quants API クライアント（kabusys.data.jquants_client：取得・保存関数を含む）

セットアップ手順
----------------

1. リポジトリをクローン（例）
   ```
   git clone <repository-url>
   cd <repo>
   ```

2. Python 環境
   - 推奨: Python 3.10 以上（typing の union | などを利用）
   - 仮想環境を作ることを推奨します（venv / pyenv 等）

3. 依存パッケージのインストール
   - requirements ファイルがあればそれを利用してください。無ければ概ね以下を使います：
     ```
     pip install duckdb openai defusedxml
     ```
   - 実際の依存はプロジェクトの packaging（pyproject.toml / requirements.txt）を参照ください。

4. 環境変数の設定
   - .env/.env.local をプロジェクトルートに置くことで自動読み込みされます（kabusys.config による）。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   必須（少なくとも開発でよく使う）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
   - SLACK_BOT_TOKEN — Slack 通知を利用する場合
   - SLACK_CHANNEL_ID — Slack 通知チャネル ID
   - KABU_API_PASSWORD — kabuステーション API を使う場合
   - OPENAI_API_KEY — OpenAI を利用する NLP / レジーム判定時（score_news, score_regime）

   オプション / デフォルト:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
   - DUCKDB_PATH — デフォルト data/kabusys.duckdb
   - SQLITE_PATH — デフォルト data/monitoring.db

5. データベース初期化（監査ログ等）
   - 監査ログ用の DB を作る例:
     ```py
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # :memory: も可
     ```
   - 既存の DuckDB 接続へスキーマを追加する:
     ```py
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)
     ```

使い方（主要なユースケース）
---------------------------

- 日次 ETL を実行してデータ収集・品質チェックを行う
  ```py
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースを収集して raw_news に保存（fetch_rss は記事リストを返します。DB 保存ロジックは別に実装）
  ```py
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- OpenAI を使ってニュースセンチメントをスコアリング（ai_scores へ書き込む）
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数で設定するか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("書き込まれた銘柄数:", n_written)
  ```

- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM）
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- ファクター・研究用ユーティリティ
  ```py
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  ```

- データ品質チェックを実行
  ```py
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

開発時の注意点
---------------
- ルックアヘッドバイアス防止: 多くの関数は内部で date.today() を参照せず、引数で与えた target_date を基準に処理を行います。バックテストや履歴処理時に有用です。
- OpenAI 呼び出し: API エラー時のフォールバックやリトライロジックがありますが、テストでは _call_openai_api をパッチすることが可能です。
- J-Quants API: rate limit（120 req/min）やトークンの自動リフレッシュを考慮した実装になっています。
- .env の自動読み込み: プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を読み込みます。テスト等で無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
------------------------------

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動ロード、Settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP スコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理・営業日ロジック
    - pipeline.py — ETL パイプライン（run_daily_etl 他）
    - jquants_client.py — J-Quants API クライアント（fetch/save 関数）
    - news_collector.py — RSS ニュース収集/前処理
    - quality.py — データ品質チェック
    - stats.py — 共通統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ定義 / 初期化
    - etl.py — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー

ライセンス・貢献
----------------
- 本 README ではライセンスの記載がありません。実際のプロジェクトで使用する場合は LICENSE ファイルを確認してください。
- バグ修正や機能提案は PR を通してお願いします。互換性やテストの方針に沿った追加を歓迎します。

最後に
------
この README はリポジトリ内の主要機能を短くまとめたものです。詳細な仕様や設計原則は各モジュールのドキュメント文字列（docstring）を参照してください。質問や追加で欲しい利用例があれば教えてください。