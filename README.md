KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。  
J-Quants からのデータ取得・ETL、ニュース収集・NLP（OpenAI）、研究用ファクター計算、監査ログ／発注監視など、アルゴリズム運用に必要な基盤機能群を提供します。  
（本リポジトリはライブラリ実装であり、実際のブローカー発注やフロントエンドは含みません。）

主な特徴
--------
- J-Quants API からの差分取得（株価・財務・上場情報・カレンダー）と DuckDB への冪等保存
- ニュース RSS 収集（SSRF 対策、URL 正規化）と raw_news テーブル保存
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（銘柄別 ai_score）とマクロセンチメントによる市場レジーム判定
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）と統計ユーティリティ（Z スコア正規化、IC 計算）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order_request / executions テーブル）と監査 DB 初期化ユーティリティ
- 設定は .env または環境変数で管理（自動ロード機構あり）

セットアップ
-----------

前提
- Python >= 3.10 を推奨
- 必要なライブラリ（最低限）
  - duckdb
  - openai
  - defusedxml

仮想環境作成例
- Unix/macOS:
  python -m venv .venv
  source .venv/bin/activate
- Windows (PowerShell):
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1

パッケージ依存インストール（例）
- pip install duckdb openai defusedxml

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください。）

環境変数
- 自動でプロジェクトルートの .env → .env.local を読み込みます（CWD ではなくソースツリーを基準に探索）。
- 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（最低限設定が必要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須。jquants_client.get_id_token で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（実行・注文周りで利用）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
- （任意）
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知系
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等の監視設定
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

参考 .env（例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=your_openai_api_key
- KABU_API_PASSWORD=your_kabu_password
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

使い方（簡易ガイド）
-------------------

共通：設定の読み込み
- 設定は kabusys.config.settings 経由で参照できます。

例: Python REPL / スクリプトから
- DuckDB 接続を作成して日次 ETL を実行する

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを計算して ai_scores に書き込む

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数で設定しておくか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")

- 市場レジームをスコアリングする（ma200 + マクロニュース + LLM）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  res = score_regime(conn, target_date=date(2026, 3, 20))
  print("done", res)

- 研究用ファクター計算の例

  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は dict のリストとして返る
  print(len(records))

- 監査ログ DB 初期化（独立 DB にする例）

  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit は監査用 DuckDB 接続（テーブル作成済み）

主要 API / 関数一覧（代表）
- ETL:
  - data.pipeline.run_daily_etl(...)
  - data.pipeline.run_prices_etl(...)
  - data.pipeline.run_financials_etl(...)
  - data.pipeline.run_calendar_etl(...)
- J-Quants クライアント:
  - data.jquants_client.fetch_daily_quotes(...)
  - data.jquants_client.save_daily_quotes(...)
  - data.jquants_client.get_id_token(...)
- ニュース:
  - data.news_collector.fetch_rss(...)
  - ai.news_nlp.score_news(...)
  - ai.regime_detector.score_regime(...)
- 研究 / リサーチ:
  - research.factor_research.calc_momentum(...)
  - research.factor_research.calc_value(...)
  - research.factor_research.calc_volatility(...)
  - research.feature_exploration.calc_forward_returns(...)
  - research.feature_exploration.calc_ic(...)
- データ品質:
  - data.quality.run_all_checks(...)
- 監査／発注:
  - data.audit.init_audit_schema(...)
  - data.audit.init_audit_db(...)

ディレクトリ構成
----------------
（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースセンチメント（OpenAI 連携）
    - regime_detector.py     -- 市場レジーム判定（ETF + マクロ）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント + DuckDB 保存ロジック
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETL 型再エクスポート（ETLResult）
    - news_collector.py      -- RSS 取得と前処理
    - calendar_management.py -- 市場カレンダー管理、営業日判定
    - quality.py             -- データ品質チェック
    - stats.py               -- 統計ユーティリティ（z-score 正規化）
    - audit.py               -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     -- ファクター計算（momentum / value / volatility）
    - feature_exploration.py -- 将来リターン / IC / 統計サマリー

設計上の注意点 / ベストプラクティス
-----------------------------------
- ルックアヘッドバイアス対策
  - 多くの関数は date.today() を直接参照せず、target_date を明示的に渡す設計になっています。バッチ処理やバックテストで必ず target_date を指定してください。
- OpenAI / J-Quants 呼び出し
  - API 呼び出しはリトライやフェイルセーフを備えていますが、API レートやコストには注意してください（特に OpenAI の大規模モデル）。
- DuckDB
  - データを永続化する DuckDB ファイルのパスは settings.duckdb_path で管理します。初回実行時にディレクトリを作成する必要があります（audit.init_audit_db は自動で親ディレクトリを作成します）。
- テスト時の環境制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます。テストで環境を制御したい場合に有用です。

ライセンス / 貢献
-----------------
（この README にライセンス情報は含めていません。リポジトリの LICENSE を参照してください。）  

問題報告や機能要望は Issue を立ててください。プルリクエスト歓迎します。

補足
----
- 実運用での発注/約定処理はリスクを伴います。実口座での使用前に十分な検証を実施してください。  
- OpenAI や J-Quants の API キー／トークンは安全に管理し、不要な公開を避けてください。