KabuSys
=======

概要
----
KabuSys は日本株のデータ取得・前処理・特徴量生成・AI ベースのニュース解析・監査ログ管理までを含む、日本株自動売買システム向けのライブラリ群です。主に以下の機能を提供します。

- J-Quants API を利用した株価・財務・マーケットカレンダーの差分 ETL（DuckDB への保存）
- ニュース収集（RSS）と LLM（OpenAI）を使った銘柄別ニュースセンチメントの算出（ai_score）
- マクロニュース + ETF（1321）の MA200 を用いた市場レジーム判定（bull/neutral/bear）
- 研究用ユーティリティ（ファクター計算・前方リターン・IC 計算・Z スコア正規化）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（信号 → 発注要求 → 約定）のスキーマ初期化機能

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API 失敗時に例外で止めない）」です。

機能一覧
--------
- ETL
  - run_daily_etl: カレンダー、株価、財務の差分取得・保存・品質チェックを実行
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別ジョブ
  - jquants_client: API 呼び出し（ページネーション、トークンリフレッシュ、レート管理、保存用関数）
- ニュース
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策、XML の安全パース）
  - ai.news_nlp.score_news: 銘柄ごとのニュースセンチメント算出・ai_scores への書き込み
- レジーム判定
  - ai.regime_detector.score_regime: MA200 乖離 + マクロセンチメントで市場レジームを算出・market_regime へ保存
- 研究（research）
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: forward returns, IC, factor summary, rank
  - data.stats.zscore_normalize: クロスセクション Z スコア正規化
- データ管理
  - data.pipeline.ETLResult: ETL 結果表現
  - data.calendar_management: 営業日判定・next/prev_trading_day 等
  - data.quality: 品質チェック群（QualityIssue を返す）
  - data.audit: 監査スキーマ初期化（init_audit_schema / init_audit_db）
- 設定
  - config.Settings: .env 自動読み込み（プロジェクトルート基準）、重要な環境変数を提供

セットアップ手順
--------------
前提
- Python 3.10 以上（型ヒントに | を使用）
- システムに internet 接続（J-Quants / OpenAI 呼び出し用）

1. リポジトリをチェックアウト
   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 必要パッケージのインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクト化されている場合は pip install -e . でローカルインストール可能です。
   requirements.txt がある場合はそれに従ってください。）

4. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env/.env.local を置けば、自動で読み込まれます（読み込み順: OS 環境 > .env.local > .env）。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

  主要な環境変数（主なもの・デフォルトを含む）
  - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
  - OPENAI_API_KEY (必須 for AI): OpenAI API キー（score_news / score_regime に未指定時参照）
  - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携がある場合）
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視ログ用 SQLite（デフォルト: data/monitoring.db）
  - PID_FILE_PATH / KILL_FLAG_PATH 等の監視系パス
  - KABUSYS_ENV: environment（development | paper_trading | live）、デフォルト development
  - LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

使い方（簡単な例）
-----------------

基本的には Python API を直接呼び出して利用します。以下は代表的なユースケースの例です。

1) DuckDB 接続を作り日次 ETL を実行する
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

2) ニュースセンチメントを計算して ai_scores に書き込む
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示するか、環境変数 OPENAI_API_KEY を設定しておく
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"書き込み銘柄数: {n_written}")

3) 市場レジーム判定を行う
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

4) 監査ログ DB を初期化する
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査テーブルにデータを保存できます

5) 研究用 API の利用例（モメンタム）
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は各銘柄ごとの dict のリスト

主要な API（抜粋）
- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.data.audit.init_audit_db(path) / init_audit_schema(conn)
- kabusys.data.calendar_management.get_trading_days(conn, start, end)
- kabusys.research.* の各種関数（calc_momentum 等）

設定の自動読み込みについて
-------------------------
- .env / .env.local の自動読み込みは config モジュール内で行われます。
- 読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env の書式は export やクォート、コメントなどをある程度サポートします。必須値が欠けていると Settings のプロパティ呼び出し時に ValueError が発生します。

ディレクトリ構成
---------------
概略（主要ファイル・ディレクトリ）:

- src/kabusys/
  - __init__.py                 : パッケージ定義、version
  - config.py                   : 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py               : ai API エクスポート（score_news）
    - news_nlp.py               : ニュース NLP（score_news 等）
    - regime_detector.py        : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py         : J-Quants API クライアント（fetch/save）
    - pipeline.py               : ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    : 市場カレンダー管理（is_trading_day 等）
    - news_collector.py         : RSS ニュース収集
    - audit.py                  : 監査ログスキーマ初期化
    - stats.py                  : 統計ユーティリティ（zscore_normalize）
    - quality.py                : データ品質チェック
    - etl.py                    : ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py        : ファクター計算（momentum/value/volatility）
    - feature_exploration.py    : forward returns / IC / summary / rank
  - monitoring/ (存在するなら監視関連モジュール)
  - execution/  (発注・実行関連モジュールがあればここ)
  - strategy/   (戦略定義関連があればここ)

注意事項 / ベストプラクティス
----------------------------
- OpenAI / J-Quants の API キーは安全に管理し、レポジトリにコミットしないでください。
- DuckDB ファイルや監査 DB の保存先ディレクトリは予め作成しておいてください（一部関数は親ディレクトリを自動作成しますが、実運用では権限等に注意）。
- score_news / score_regime は外部 API に依存するため、テスト時は _call_openai_api をパッチしてスタブ化すると安定します。
- ETL は失敗しても可能な限り他の処理を継続する設計です。result.has_errors / has_quality_errors を確認して運用判断してください。
- market_calendar が未取得の状態では営業日判定は曜日フォールバック（平日を営業日）になります。カレンダー ETL を先に実行することを推奨します。

付録: ロギング / 環境
--------------------
- LOG_LEVEL 環境変数でログレベルを制御できます（デフォルト INFO）。
- KABUSYS_ENV は development / paper_trading / live のいずれかを設定します（デフォルト development）。live の場合は実口座運用に注意してください。

その他
-----
この README はコードベースの主要機能を要約したものです。より細かい実装の挙動やパラメータの調整は各モジュールの docstring を参照してください（src/kabusys 以下の各 .py に詳細な説明があります）。

質問や追加ドキュメントが必要であれば、どの機能について詳しく知りたいか教えてください。