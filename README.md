KabuSys
=======

日本株向けのデータプラットフォーム & 自動売買補助ライブラリです。  
ETL（J-Quants からの株価/財務/カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、研究用のファクター計算、監査ログ（発注/約定トレーサビリティ）などを含みます。

バージョン
---------
現在のパッケージバージョン: 0.1.0

主な特徴
--------
- J-Quants API による差分 ETL（株価、財務、JPX カレンダー）と DuckDB への冪等保存
- RSS によるニュース収集（SSRF 対策・トラッキング除去・gzip/サイズ制限）
- OpenAI (gpt-4o-mini) を利用したニュースセンチメント（銘柄ごと）スコアリング
- マクロニュース + ETF の MA200 乖離を組み合わせた市場レジーム判定（bull/neutral/bear）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ（Z スコア正規化、IC 計算 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）と初期化ユーティリティ
- 設定は環境変数 / .env で管理（自動ロード機構あり）

必要な環境変数（主なもの）
-------------------------
最低限設定が必要な環境変数（一部）:
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（発注等を使う場合）
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI を使う場合に必要

設定は .env ファイルで管理することを想定しています（パッケージ起動時にプロジェクトルートの .env → .env.local を自動読み込み）。  
自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順
----------------

1. リポジトリをクローン / パッケージを配置
   - 一般的な構成は src/kabusys 下にモジュール群が配置されています。

2. Python 環境作成（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   最低限必要なパッケージ（例）:
   - duckdb
   - openai
   - defusedxml

   例:
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

4. .env を用意
   プロジェクトルートに .env（および任意で .env.local）を作成します。例:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   SLACK_BOT_TOKEN=your_slack_token
   SLACK_CHANNEL_ID=your_channel_id
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

5. DB ディレクトリの準備
   デフォルトの DuckDB ファイルは data/kabusys.duckdb（settings.duckdb_path で取得）です。必要に応じて親ディレクトリを作成してください（モジュール側でも mkdir されることがありますが、念のため）。

使い方（代表的な操作例）
----------------------

以下は Python スクリプト／REPL から呼ぶ例です。import 先はパッケージの public API を参照してください。

- 設定を取得する
  from kabusys.config import settings
  settings.jquants_refresh_token  # 必須トークンなど

- DuckDB 接続を作成する
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースのセンチメントをスコアリングして ai_scores に保存する
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None の場合は環境変数 OPENAI_API_KEY を使用
  print(f"scored {count} codes")

- 市場レジームを判定して market_regime に保存する
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査ログ DB（別ファイル）を初期化する
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も使用可

- 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))

設計・運用上の注意
-----------------
- ルックアヘッドバイアス対策: 多くの処理は内部で date 引数を受け取り、現在時刻や date.today() に依存しない設計です（バックテストでの公平性確保）。
- OpenAI 呼び出し: API の失敗時はフェイルセーフとしてスコアを 0 にする / 処理をスキップする挙動を多くの場所で採っています。テストでは _call_openai_api をモックできます。
- .env 自動読み込み: パッケージ初期化時にプロジェクトルート（.git または pyproject.toml）を探索して .env → .env.local を読み込みます。テスト時などで無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB executemany の制約（古いバージョン）に配慮した実装があります。DuckDB のバージョンに依存する挙動に注意してください。
- J-Quants API はレート制限があります（120 req/min）。jquants_client は簡易 RateLimiter を内蔵し、トークンリフレッシュ・再試行を行います。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースセンチメント（OpenAI）処理
    - regime_detector.py            -- マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント / 保存ロジック
    - pipeline.py                   -- ETL パイプライン / run_daily_etl 等
    - etl.py                        -- ETLResult の公開（再エクスポート）
    - news_collector.py             -- RSS 収集・正規化
    - calendar_management.py        -- 市場カレンダー管理 / 営業日ロジック
    - quality.py                    -- データ品質チェック
    - stats.py                      -- Zスコア等統計ユーティリティ
    - audit.py                      -- 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py            -- モメンタム／バリュー／ボラティリティ等
    - feature_exploration.py        -- 将来リターン・IC・統計サマリー
  - monitoring/                      -- （監視系モジュールがここに入る想定）
  - strategy/                        -- （戦略ロジックがここに入る想定）
  - execution/                       -- （発注・ブローカー連携がここに入る想定）

開発上のヒント
---------------
- OpenAI の呼び出し部分（news_nlp._call_openai_api / regime_detector._call_openai_api）はテストでモックしやすいように分離されています。ユニットテストではこれらを差し替えて determinisitc なテストを作成してください。
- settings は kabusys.config.settings で単一のインスタンスとして提供されます。テストで環境変数を差し替える場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか、os.environ を直接操作してください。
- ETL の各ステップ（run_prices_etl, run_financials_etl, run_calendar_etl）は個別に実行できるため、デバッグ時は個別実行で問題を切り分けてください。

ライセンス
---------
リポジトリに記載のライセンスに従ってください（ここでは省略しています）。

問い合わせ / 貢献
------------------
バグ報告や機能提案は issue を立ててください。プルリク歓迎です。コードスタイルやテストは一貫性を保つよう心がけてください。

以上。必要があれば README に含める追加の使い方（例スクリプト、Docker / CI 設定、requirements.txt の具体例など）を追記します。