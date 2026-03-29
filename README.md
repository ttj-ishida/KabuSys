KabuSys — 日本株自動売買 / データプラットフォーム
=======================================

概要
----
KabuSys は日本株向けのデータパイプライン・リサーチ・AI評価・監査ログ・ETL などを含む
内部ライブラリ群です。本リポジトリは主に以下の用途を想定しています。

- J-Quants API からの株価 / 財務 / マーケットカレンダーの差分取得（ETL）
- ニュース収集・NLP（OpenAI を使った銘柄別センチメント算出）
- 市場レジーム判定（ETF + マクロニュースの LLM スコアの合成）
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注〜約定までの監査ログ（監査テーブルの初期化 / ユーティリティ）

主要機能
-------
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: カレンダー / 株価 / 財務の差分取得・保存・品質チェックを一括実行
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系で DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（kabusys.data.news_collector）
  - RSS 収集、URL 正規化、SSRF ガード、raw_news への保存用ユーティリティ
- AI スコアリング（kabusys.ai）
  - score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に保存
  - score_regime: ETF（1321）200 日 MA とマクロニュース LLM を合成して market_regime に保存
- 研究ユーティリティ（kabusys.research）
  - calc_momentum / calc_volatility / calc_value 等、ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合の検出、QualityIssue レポート
- 監査ログ（kabusys.data.audit）
  - 監査テーブルの DDL / 初期化関数（init_audit_schema / init_audit_db）
- 環境設定（kabusys.config）
  - .env 自動ロード（プロジェクトルート検出）と必須設定チェック

動作要件
--------
- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

セットアップ手順
---------------
1. ソースをクローン
   - 任意の場所へクローンしてください。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必須パッケージのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （開発時にパッケージとして使うなら）pip install -e .

   ※ requirements.txt は本リポジトリに含まれていないため、環境に応じて追加で依存を入れてください。

4. 環境変数／.env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動で読み込まれます。
   - 読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   代表的な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
   - SLACK_BOT_TOKEN        : （通知用）Slack ボットトークン（プロジェクトで使用する場合）
   - SLACK_CHANNEL_ID       : Slack チャネル ID
   - KABU_API_PASSWORD      : kabuステーション API パスワード（実行系で必要な場合）
   - OPENAI_API_KEY         : OpenAI API キー（AI スコアリング用）
   - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH            : 監視 DB 等の SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV            : development / paper_trading / live
   - LOG_LEVEL              : DEBUG/INFO/WARNING/ERROR/CRITICAL

   注意: Settings クラス経由で必須変数は _require() によりチェックされます。README に従って .env.example を作り必須値を設定してください。

基本的な使い方（コード例）
--------------------

- DuckDB 接続を作り日次 ETL を実行する例

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

  - run_daily_etl は ETLResult を返します。ETL は内部で calendar / prices / financials を差分取得して保存し、品質チェックを実行します。

- OpenAI を使ってニューススコアを生成（score_news）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数に設定されていれば api_key を省略可能
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定（score_regime）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

  - 内部で ETF 1321 の 200 日移動平均乖離とマクロ記事の LLM スコアを重み付け合成して market_regime テーブルに書き込みます。
  - OpenAI API キーは引数 api_key、または環境変数 OPENAI_API_KEY を使用します。

- 監査ログ DB を初期化する

  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # 以後 conn を使って監査ログテーブルへ書き込み可能

- ニュース RSS を取得する（ニュースコレクタのユーティリティ）

  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  src_url = DEFAULT_RSS_SOURCES["yahoo_finance"]
  articles = fetch_rss(src_url, source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])

追加の注意点
------------
- OpenAI 呼び出しは gpt-4o-mini（設定）を想定しています。API の課金やレート管理は利用者側で行ってください。
- J-Quants API 呼び出しは内部で rate limiter を設けていますが、API キーの管理・課金は利用者責任です。
- ルックアヘッドバイアス防止のため、モジュール内の日付ロジックは基本的に target_date を明示的に受け取り、datetime.today()/date.today() の参照を避ける設計になっています（ただし一部 helper 関数は date.today() を使います）。
- DuckDB のバージョン差異や executemany の挙動に注意（コード内に互換性対策が盛り込まれています）。

ディレクトリ構成
----------------
以下は主要ファイルの抜粋的なツリーです（src/kabusys をルートとする）:

- src/kabusys/
  - __init__.py
  - config.py                          # .env 読み込み / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       # ニュースセンチメント（score_news）
    - regime_detector.py                # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                 # J-Quants API クライアント + save_* 関数
    - pipeline.py                       # ETL パイプライン（run_daily_etl 等）
    - etl.py                            # ETL 入口の再エクスポート（ETLResult）
    - news_collector.py                 # RSS 収集ユーティリティ
    - calendar_management.py            # 市場カレンダー管理 / 営業日判定
    - stats.py                          # 統計ユーティリティ（z-score）
    - quality.py                        # データ品質チェック
    - audit.py                          # 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py                # ファクター計算（momentum/value/volatility）
    - feature_exploration.py            # 将来リターン / IC / 統計サマリー

ドキュメント / 設計参照
---------------------
- 各モジュールの docstring に設計意図・処理フロー・フォールバック挙動・リトライポリシー等のコメントを記載しています。モジュール内のトップコメントを参照してください。

貢献 / テスト
--------------
- 現時点で公式なテストスイートは含まれていません。ユニットテストを追加する場合は各モジュールの外部 API（ネットワーク呼び出し）をモックすることを推奨します（コード中に判替え用の関数や patch を想定した設計箇所があります）。

ライセンス
---------
- 本 README ではライセンス情報を含めていません。配布元リポジトリの LICENSE を参照してください。

お問い合わせ
--------------
- 実運用・機密情報（APIキー・取引パスワード等）は決して公開リポジトリに含めないでください。開発・運用に関する質問はリポジトリの issue / メンテナーへお問い合わせください。

以上。