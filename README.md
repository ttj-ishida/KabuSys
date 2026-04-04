KabuSys — 日本株自動売買プラットフォーム
====================================

概要
----
KabuSys は日本株を対象としたデータプラットフォーム兼自動売買システムの骨格ライブラリです。本リポジトリには以下の主要機能が含まれます。

- J-Quants API を用いた株価・財務・カレンダーの ETL（差分取得・保存・品質チェック）
- RSS によるニュース収集と LLM（OpenAI）を使ったニュースセンチメント解析（銘柄ごと、マクロ）
- 市場レジーム判定（MA200乖離 × マクロニュースセンチメント）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー、Forward Returns、IC 等）
- DuckDB を用いたデータ格納・監査ログスキーマの初期化
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 安全策（SSRF/リダイレクト検査、API レート制御、Look-ahead バイアス対策 など）

主な設計方針
- ルックアヘッドバイアスに注意（target_date を明示、datetime.today()/date.today() への依存を最小化）
- DuckDB を主要データストレージに採用（ETL は冪等設計）
- 外部 API 呼び出しにはリトライ・バックオフ・レート制御を実装
- LLM 呼び出しは JSON Mode を利用し、レスポンスを厳密にバリデーション

機能一覧
--------
- data.*
  - jquants_client: J-Quants からのデータ取得／DuckDB への保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline: ETL パイプライン（差分取得・保存・品質チェック） run_daily_etl
  - news_collector: RSS 収集と raw_news への登録（SSRF・サイズ検査・正規化）
  - quality: データ品質チェック（欠損・重複・スパイク・日付整合性）
  - calendar_management: 営業日判定・カレンダーバッチ更新
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログ（signal_events, order_requests, executions）スキーマ初期化 / init_audit_db
- ai.*
  - news_nlp.score_news: ニュースを銘柄別に集約して OpenAI でセンチメントを算出 → ai_scores へ書込
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime に保存
- research.*
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境を作成・有効化（任意推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   本コード中で使用している主要依存:
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリの urllib, json 等を使用）

   例:
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使用してください:
   pip install -r requirements.txt）

4. 環境変数 (.env) を準備
   プロジェクトルートの .env または .env.local に必要な設定を記載します。
   自動ロード順序: OS 環境 > .env.local > .env
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用）。

   主要な環境変数例:
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>   ← 必須（jquants_client.get_id_token で使用）
   - OPENAI_API_KEY=<your_openai_api_key>                ← LLM 呼び出しに必要
   - KABU_API_PASSWORD=<your_kabu_api_password>
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi    ← デフォルト値あり
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb                      ← デフォルト
   - SQLITE_PATH=data/monitoring.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - KABUSYS_ENV=development|paper_trading|live            ← default: development
   - LOG_LEVEL=INFO|DEBUG|...                              ← default: INFO

   .env のフォーマットは shell 形式（KEY=VALUE）。コメントや export KEY=val 形式にも対応しています。

5. データベース用ディレクトリの作成（必要に応じて）
   - mkdir -p data

使い方（主要な操作例）
--------------------

以下は Python REPL / スクリプト から呼び出す簡単な例です。事前に .env を準備し、依存をインストールしてください。

1) DuckDB 接続の作成（監査 DB 初期化）
- 監査ログ用 DB の初期化:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

2) 日次 ETL を実行（J-Quants から差分取得し保存）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(...))  # settings.duckdb_path を使うのが便利
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

3) ニュースセンチメントのスコアリング（ai.news_nlp.score_news）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026,3,20))  # OpenAI API キーは環境変数またはapi_key引数で指定
  print(f"scored {n} codes")

4) 市場レジーム判定（ai.regime_detector.score_regime）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))

5) ファクター計算（research）
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))

注意点 / 運用上のポイント
- OpenAI 呼び出し: API リトライ・レスポンスバリデーションあり。api_key を引数で注入可能（テスト性向上）。
- J-Quants: rate limit（120 req/min）・トークン自動リフレッシュ・リトライが実装済み。
- Look-ahead バイアス対策: target_date 以前のデータのみ参照する設計が徹底されています（ETL / スコアリング / リサーチ関数）。
- 自動 .env ロード: パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を検出して .env を読み込みます。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
-------------------------------

src/kabusys/
- __init__.py
- config.py                          — 環境変数 / 設定管理（自動 .env ロード・Settings）
- ai/
  - __init__.py
  - news_nlp.py                       — ニュース NLP（score_news）
  - regime_detector.py                — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                 — J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py                       — ETL パイプライン（run_daily_etl 他）
  - etl.py                            — ETLResult のエクスポート
  - news_collector.py                 — RSS 収集（SSRF 対策・正規化）
  - calendar_management.py            — 市場カレンダー管理 / 営業日ユーティリティ
  - quality.py                        — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py                          — zscore_normalize 等
  - audit.py                          — 監査ログスキーマ作成 / init_audit_db
- research/
  - __init__.py
  - factor_research.py                — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py            — calc_forward_returns / calc_ic / factor_summary / rank
- research/（パッケージ内その他）     — （ユーティリティ群）

ロギング
-------
各モジュールは標準 logging を使用します。LOG_LEVEL 環境変数でログレベルを調整してください（DEBUG, INFO, WARNING, ERROR, CRITICAL）。デフォルトは INFO。

テストとモック
--------------
- OpenAI 呼び出しやネットワーク I/O 部分は内部で専用関数を通す設計になっており、ユニットテスト時はこれらをモックして差し替え可能です（例: kabusys.ai.news_nlp._call_openai_api を patch）。

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンス、貢献方法、issue/PR の手順などを適宜追記してください）

付録: よく使う環境変数一覧（まとめ）
-----------------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (必須: news_nlp / regime_detector)
- KABU_API_PASSWORD
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (INFO|DEBUG|...)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1: 自動 .env 読み込みを無効化)

以上がプロジェクトの概要と主要な使い方です。README の補足やサンプルスクリプト（ETL の cron 化、監視・実行プロセスの例など）が必要であれば、用途に合わせて追記できます。