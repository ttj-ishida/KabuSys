KabuSys
======

KabuSys は日本株の研究・データ基盤・シグナル生成・監査ログと、
AI を用いたニュースセンチメントや市場レジーム判定を組み合わせた
自動売買／リサーチ基盤のコアライブラリです。

この README ではプロジェクト概要、主な機能、セットアップ手順、簡単な使い方、
およびディレクトリ構成を日本語でまとめます。

プロジェクト概要
--------------
KabuSys は以下の主要コンポーネントを含む Python パッケージです。

- データ ETL（J-Quants から株価・財務・カレンダーを差分取得して DuckDB に保存）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー管理（営業日判定、next/prev trading day 等）
- ニュース収集（RSS → raw_news、SSRF対策・前処理）
- AI スコアリング（OpenAI を用いたニュースセンチメント / マクロセンチメント）
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- リサーチ用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- 監査ログ（signal / order_request / execution を保存する監査スキーマ）
- J-Quants API クライアント（認証、ページネーション、レートリミット、保存用ユーティリティ）

設計上の特徴:
- DuckDB を永続ストレージに利用（軽量で高速な分析向け DB）
- Look-ahead bias を避けるため日付の扱いに注意（多くの関数が target_date を受け取る）
- API 呼び出しはリトライやバックオフ、エラーハンドリングを備える
- ニュース収集では SSRF 対策や XML の安全なパース（defusedxml）を実装
- OpenAI 呼び出しは JSON mode を使う想定でレスポンス検証を厳格化

主な機能一覧
--------------
- data
  - jquants_client: J-Quants API 取得／保存（daily_quotes, financials, market_calendar, listed_info）
  - pipeline: 日次 ETL（run_daily_etl）と個別 ETL（run_prices_etl 等）
  - quality: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - news_collector: RSS 取得（fetch_rss）、前処理、raw_news 保存ロジック（SSRF 対策込み）
  - calendar_management: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize（クロスセクションの Z スコア）
- ai
  - news_nlp.score_news: ニュースを銘柄別に集約して OpenAI でセンチメントを付与し ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime に書き込む
- research
  - factor_research: calc_momentum / calc_value / calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（統計解析・IC 計算）
- 設定管理
  - config.Settings: 環境変数からの設定読み込み（.env 自動読み込みの仕組みを備える）

セットアップ手順
----------------

前提
- Python 3.9+（コード中で typing の新しい機能を使用）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（OpenAI API を使う場合）
- defusedxml（RSS パースの安全対策）
- ネットワーク環境（J-Quants / OpenAI への通信）

例: 仮想環境を作って依存を入れる
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

- 必要パッケージをインストール（例）
  - pip install duckdb openai defusedxml

（プロジェクトが pip パッケージ化されている場合は）
  - pip install -e .

環境変数 / .env（主なキー）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須、ETL 用）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に使用）
- KABU_API_PASSWORD: kabu API のパスワード（実行/注文関連）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH 等の監視設定
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

.env の自動読み込みについて
- パッケージはプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロードします。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

初期 DB（監査ログ）作成例
- Python REPL やスクリプトで実行:
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
  - これにより必要なテーブルとインデックスが作成されます。

使い方（代表的な例）
-------------------

基本的な DuckDB 接続例
- Python で DuckDB 接続を作って各 API を呼ぶ方法:

  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

日次 ETL（J-Quants からデータ取得）
- run_daily_etl を用いて一括 ETL を実行:

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- 補足:
  - run_daily_etl はカレンダー → 株価 → 財務 → 品質チェック の順で実行します。
  - id_token を明示的に渡したい場合は run_daily_etl(..., id_token="...") としてください。

ニュースセンチメント付与（OpenAI 必須）
- news_nlp.score_news の例:

  from kabusys.ai.news_nlp import score_news
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が設定されているか、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {written} ai scores")

市場レジーム判定（MA + マクロセンチメント）
- regime_detector.score_regime の例:

  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  # market_regime テーブルに書き込まれます

監査ログ初期化
- 監査ログスキーマの初期化（別 DB にする例）:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

リサーチ API（ファクター計算）
- calc_momentum / calc_volatility / calc_value の呼び出し例:

  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は dict のリスト。zscore_normalize 等で正規化可能。

注意点 / 運用時のポイント
- OpenAI API 呼び出しはコストとレート制限に注意して運用してください。
- J-Quants の API はレート制限（120 req/min）や認証の有効期限があるため
  get_id_token や _request のリトライ・リフレッシュの挙動を理解してください。
- ETL の target_date は外部から明示的に与えるのが望ましく、内部で datetime.today() に依存する処理は設計上最小化されています（バックテストの Look-ahead を避けるため）。
- ニュース収集は RSS ソースの品質／文字コード等によるパース失敗があり得ます。fetch_rss はエラーをログに吐きつつ安全に処理します。

ディレクトリ構成
----------------

以下は主要ソースファイルの構成（省略あり）。パッケージは src/kabusys 以下にあります。

- src/
  - kabusys/
    - __init__.py
    - config.py                     # 環境変数・.env 自動読み込み
    - ai/
      - __init__.py
      - news_nlp.py                 # ニュースを銘柄別に OpenAI でスコアリング
      - regime_detector.py          # MA200 とマクロセンチメントの合成でレジーム判定
    - data/
      - __init__.py
      - jquants_client.py           # J-Quants API クライアント + DuckDB 保存
      - pipeline.py                 # ETL パイプライン run_daily_etl 等
      - quality.py                  # データ品質チェック
      - news_collector.py           # RSS 収集（SSRF 対策・前処理）
      - calendar_management.py      # 市場カレンダー / 営業日判定
      - audit.py                    # 監査ログスキーマ初期化
      - stats.py                    # zscore_normalize 等
      - etl.py                      # ETL 用型・ラッパー（ETLResult など）
    - research/
      - __init__.py
      - factor_research.py          # calc_momentum / calc_value / calc_volatility
      - feature_exploration.py      # calc_forward_returns / calc_ic / factor_summary / rank
    - ai/                          # （上記）
    - research/                    # （上記）
    - ...（他モジュール）

例: 主要な設定キー（config.Settings）:
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL,
  LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, DUCKDB_PATH, SQLITE_PATH,
  PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT,
  MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL

開発・貢献
-----------
- コードの品質維持のためロギング・例外処理・再試行・タイムアウト等に配慮しています。
- ユニットテストや CI の導入を推奨します（テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと .env の自動読み込みを抑止できます）。
- OpenAI や J-Quants 呼び出しは外部サービス依存のため、ユニットテストでは呼び出し関数をモックする設計（モジュール内の _call_openai_api 等を patch する想定）です。

付録: よく使う関数一覧（抜粋）
- data.pipeline.run_daily_etl(conn, target_date, ...)
- data.jquants_client.fetch_daily_quotes / save_daily_quotes
- data.news_collector.fetch_rss(url, source)
- ai.news_nlp.score_news(conn, target_date, api_key=None)
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
- data.audit.init_audit_db(path) / init_audit_schema(conn)
- research.factor_research.calc_momentum/ calc_value/ calc_volatility

以上が KabuSys の概要と基本的な利用手順です。具体的な利用やデプロイの要件（ジョブスケジューラ、永続ストレージのパス、OpenAI/J-Quants の運用ポリシー等）は運用環境に合わせて設定・拡張してください。追加で README に記載したいサンプルコードや CI 導入手順があれば指示してください。