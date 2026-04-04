KabuSys — 日本株自動売買プラットフォーム
======================================

概要
----
KabuSys は日本株向けのデータプラットフォーム、リサーチ、AI ベースのニュースセンチメント評価、監査ログ、ETL パイプラインを備えた自動売買支援ライブラリです。J-Quants API からの市場データ取得、DuckDB を用いた永続化、OpenAI を使ったニュース NLP による銘柄スコアリング、ETF を用いた市場レジーム判定などの機能を持ちます。

主な用途例:
- 日次 ETL（株価・財務・カレンダー）の自動取得と品質チェック
- ニュース記事のセンチメント解析 → 銘柄ごとの ai_score 作成
- マーケットレジーム（bull / neutral / bear）判定
- 監査ログ（signal → order_request → execution のトレーサビリティ）初期化
- 研究用途のファクター計算・特徴量解析（IC、フォワードリターン等）

機能一覧
--------
- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート探索）
  - 必須環境変数の取得ユーティリティ
- データ ETL（kabusys.data.pipeline）
  - J-Quants から差分取得（株価、財務、カレンダー）
  - DuckDB への冪等保存（ON CONFLICT / upsert）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次パイプライン run_daily_etl
- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制限、リトライ、トークン自動リフレッシュ対応
  - fetch / save の高水準 API（daily_quotes, financials, calendar 等）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF対策、トラッキングパラメータ除去、XML の安全処理）
  - raw_news / news_symbols への冪等保存
- AI（kabusys.ai）
  - ニュース NLP（score_news）: OpenAI (gpt-4o-mini) を用いた銘柄ごとのセンチメント評価
  - マーケットレジーム判定（score_regime）: ETF 1321 の MA200 乖離 + マクロニュースセンチメント合成
  - API 呼び出しは堅牢なリトライ・パース・フェイルセーフ実装
- 研究モジュール（kabusys.research）
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
  - 共通統計ユーティリティ（zscore_normalize）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のテーブル定義
  - init_audit_schema / init_audit_db による初期化（UTC タイムゾーン固定）

前提・必要条件
--------------
- Python 3.10+
- ネットワークアクセス（J-Quants / OpenAI）
- DuckDB（Python パッケージ duckdb）
- OpenAI SDK（openai）
- defusedxml（RSS パースの安全化）
- （任意）LINE Messaging API トークン（通知用途）

セットアップ手順
---------------
1. リポジトリをクローン / ワークディレクトリへ
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - (推奨) requirements.txt があれば:
     - pip install -r requirements.txt
   - 最低限の主要パッケージ:
     - pip install duckdb openai defusedxml

   ※ パッケージ名やバージョンはプロジェクト要件に合わせて調整してください。

4. 環境変数 / .env を準備
   - プロジェクトルート（pyproject.toml または .git のあるディレクトリ）を基準に .env/.env.local を自動ロードします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効にできます）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=あなたの_jquants_リフレッシュトークン
     - KABU_API_PASSWORD=kabuステーションAPIパスワード
     - OPENAI_API_KEY=あなたのOpenAI APIキー
     - LINE_CHANNEL_ACCESS_TOKEN=（任意）LINE 通知トークン
     - LINE_USER_ID=（任意）通知先ユーザーID
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - KABUSYS_ENV=development  # development / paper_trading / live
     - LOG_LEVEL=INFO

   例 (.env.example):
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=xxxx
     KABU_API_PASSWORD=xxxx
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

使い方（基本例）
----------------

- DuckDB 接続を作って ETL を実行する（Python REPL / スクリプト）:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを計算して ai_scores に書き込む:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} codes")

  ※ OpenAI API キーを関数引数 api_key に渡すか環境変数 OPENAI_API_KEY を設定してください。

- 市場レジームを計算して market_regime に書き込む:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用 DB を初期化する:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 既に接続済みの conn に対して init_audit_schema(conn) も呼べます

環境変数関連の注意
-------------------
- 自動 .env ロード順序: OS 環境 > .env.local > .env
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 必須値（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は settings プロパティ経由で取得し、未設定時は ValueError を送出します
- KABUSYS_ENV は development / paper_trading / live のいずれかである必要があります

主要な API（関数・エントリポイント）
----------------------------------
- kabusys.config.settings — 環境設定アクセス
- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL（カレンダー → 株価 → 財務 → 品質）
- kabusys.data.jquants_client.fetch_* / save_* — J-Quants 取得・保存ユーティリティ
- kabusys.data.news_collector.fetch_rss(...) — RSS 取得ユーティリティ
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None) — ニュース NLP スコア
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジーム判定
- kabusys.data.audit.init_audit_schema / init_audit_db — 監査ログ初期化
- kabusys.research.* — 研究用ファクター計算・統計ユーティリティ

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                      # 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                  # ニュース NLP（OpenAI）
  - regime_detector.py           # マーケットレジーム判定
- data/
  - __init__.py
  - jquants_client.py            # J-Quants API クライアント（fetch/save）
  - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
  - etl.py                       # ETL 結果型再エクスポート
  - news_collector.py            # RSS 収集
  - audit.py                     # 監査ログスキーマ初期化
  - calendar_management.py       # 市場カレンダー管理（営業日判定等）
  - quality.py                   # データ品質チェック
  - stats.py                     # 統計ユーティリティ（zscore_normalize）
- research/
  - __init__.py
  - factor_research.py           # モメンタム / ボラティリティ / バリュー
  - feature_exploration.py       # forward returns / IC / summary / rank
- monitoring/ (未提示コードの想定モジュール)
- execution/ (未提示コードの想定モジュール)
- strategy/ (未提示コードの想定モジュール)

設計・運用上のポイント
---------------------
- Look-ahead bias を防ぐため、モジュール群は内部で datetime.today()/date.today() をむやみに参照せず、ターゲット日（target_date）を明示的に渡す設計です。
- OpenAI / J-Quants 呼び出しはリトライ・バックオフ・エラーハンドリングを備え、失敗時は安全側（0 スコアやスキップ）にフォールバックします。
- DuckDB への書き込みは原則冪等（ON CONFLICT / upsert）により再実行可能。
- ニュース収集では SSRF 対策・XML の毒性対策（defusedxml）・受信サイズ制限などセキュリティに配慮しています。

よくある質問（FAQ）
------------------
Q: OpenAI のレスポンスが不正な JSON を返したら？
A: モジュールは JSON パース失敗時に警告を出して該当チャンクをスキップまたは macro_sentiment=0 にフォールバックします。ログを確認して必要ならリトライしてください。

Q: .env が自動で読み込まれない
A: プロジェクトルートの特定は __file__ から親ディレクトリを辿り .git または pyproject.toml を探します。CI 環境などで自動読込を避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: DuckDB スキーマはどこで初期化する？
A: 各機能（ETL / 監査ログ）に初期化関数があります。監査ログは kabusys.data.audit.init_audit_db を使うとスキーマ作成まで実行します。ETL 側で必要なテーブル定義を別途用意してください（schema 初期化ユーティリティはプロジェクトに存在する想定です）。

貢献・ライセンス
----------------
この README にライセンス情報は含まれていません。プロジェクトルートの LICENSE ファイルを参照してください。バグ報告や機能提案は issue を立ててください。

最後に
------
この README はコードベースの主要機能と使い方の概要をまとめたものです。詳細な API 仕様や運用手順は該当モジュールの docstring（ソース内コメント）をご参照ください。必要であれば、README に含めるサンプルスクリプトや運用時の systemd / cron ジョブ例なども作成できます。どの箇所を詳しくしたいか教えてください。