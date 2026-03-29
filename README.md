KabuSys
=======

日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。  
ETL（J-Quants からの株価・財務・市場カレンダー取得）、ニュース収集・NLP（OpenAI）によるセンチメント評価、ファクター計算、監査ログ用スキーマなどを含み、バックテスト／運用用データ基盤と戦略研究に必要な機能を提供します。

主な特徴
--------
- J-Quants API 連携（株価日足、財務、マーケットカレンダー等）の取得・保存（Rate-limit / retry / id_token 自動更新対応）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS）とニュース前処理（SSRF対策、サイズ制限、トラッキングパラメータ除去）
- OpenAI を用いたニュース NLP（銘柄別センチメント評価）および市場レジーム判定（ETF MA + マクロニュースの LLM 評価の合成）
- 研究モジュール（ファクター計算、将来リターン、IC 計算、Z スコア正規化など）
- 監査ログ（signal / order_request / executions）用の DuckDB スキーマ初期化ユーティリティ
- データ品質チェック（欠損/スパイク/重複/日付整合性）

セットアップ手順
---------------

前提:
- Python 3.10+（型注釈に union 型等を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）
- DuckDB（Python パッケージとしてインストール）

1. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - その他プロジェクトで用いるパッケージがあれば requirements.txt を用意して pip install -r requirements.txt

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env / .env.local を置くことで自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 連携に使用する場合
     - KABU_API_PASSWORD : kabu ステーション API のパスワード
     - OPENAI_API_KEY : OpenAI を使う処理（news_nlp / regime_detector）で必要
   - 任意 / デフォルト:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL : DEBUG / INFO / ...
     - KABU_API_BASE_URL : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH : データベースファイルのパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite など（デフォルト data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース準備
   - DuckDB ファイルは settings.duckdb_path を参照します。初回は空のファイルを作成しておくか、init スキーマ用のユーティリティを使ってテーブルを作成してください。
   - 監査ログ専用 DB を初期化する例（Python）:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

使い方（代表的な API）
--------------------

すべての操作は Python からインポートして使います。主要なユースケースを簡単に示します。

1. 設定読み込み
   ```python
   from kabusys.config import settings
   db_path = settings.duckdb_path
   ```

2. DuckDB 接続
   ```python
   import duckdb
   conn = duckdb.connect(str(settings.duckdb_path))
   ```

3. 日次 ETL 実行
   - run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェックを順に実行します。
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

4. ニュースセンチメント（銘柄別）計算
   - OpenAI API キーを環境変数にセットするか api_key 引数を渡してください。
   ```python
   from kabusys.ai.news_nlp import score_news
   from datetime import date
   n = score_news(conn, target_date=date(2026,3,20))  # 戻り値は書き込んだ銘柄数
   ```

5. 市場レジーム判定
   ```python
   from kabusys.ai.regime_detector import score_regime
   from datetime import date
   score_regime(conn, target_date=date(2026,3,20))
   ```

6. ファクター計算 / 研究系
   ```python
   from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
   from datetime import date
   momentum = calc_momentum(conn, date(2026,3,20))
   volatility = calc_volatility(conn, date(2026,3,20))
   value = calc_value(conn, date(2026,3,20))
   normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
   ```

7. ニュース RSS 取得（news_collector）
   - fetch_rss は URL の検証（SSRF 対策）と最大サイズチェックを行います。
   ```python
   from kabusys.data.news_collector import fetch_rss
   articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
   ```

注意点 / テスト用フック
----------------------
- OpenAI 呼び出しは内部で _call_openai_api を通して行われます。ユニットテストではこの関数を patch して応答を差し替えることができます（kabusys.ai.news_nlp._call_openai_api、kabusys.ai.regime_detector._call_openai_api）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行われます。自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany は古いバージョンで空リストを受け付けない制約があるため、モジュール内で保護ロジックがあります。DuckDB のバージョン互換性に注意してください。

ディレクトリ構成（主なファイルと説明）
------------------------------------

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定の読み込み（.env 自動ロード、settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄ごとに集約し OpenAI でセンチメント評価、ai_scores テーブルへ書き込み
    - regime_detector.py
      - ETF(1321)の200日MA乖離 + マクロニュースの LLM センチメントを合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API の取得・保存（rate limit / retry / id_token 管理 / DuckDB 保存）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）、ETLResult 定義
    - etl.py
      - ETLResult の公開再エクスポート
    - news_collector.py
      - RSS 収集・前処理・保存ロジック（SSRF / gzip / トラッキング除去）
    - calendar_management.py
      - 市場カレンダー管理・営業日判定、calendar_update_job
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログ（signal / order_requests / executions）スキーマ初期化
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value ファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、rank、factor_summary など

その他
-----
- ログレベルは環境変数 LOG_LEVEL で制御できます（INFO デフォルト）。
- KABUSYS_ENV は動作モード（development / paper_trading / live）に使われます。is_live / is_paper / is_dev のプロパティで判定可能です。
- 本リポジトリは外部サービス（J-Quants、OpenAI、RSS）に依存するため、本番運用では API キーやネットワークの取り扱いに注意してください。
- セキュリティ対策（SSRF、XML インジェクション、レスポンスサイズ制限）に留意して実装されていますが、運用環境に合わせた追加対策を検討してください。

ライセンス・貢献
----------------
（本リポジトリのライセンス情報や貢献方法をここに追記してください。）

問い合わせ
----------
利用中の不具合や実装に関する質問はリポジトリの Issues / Pull Requests を通じてお願いします。