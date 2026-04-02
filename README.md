KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買補助ライブラリ群です。  
主に以下の機能を備え、バックテスト／リサーチ／ETL／監査ログ／ニュース NLP／市場レジーム判定／J-Quants 連携を想定しています。

- J-Quants API からの株価・財務・カレンダーの差分取得と DuckDB への冪等保存（ETL）
- ニュース収集（RSS）→ raw_news 保存・銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロセンチメントの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、Zスコア正規化）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal→order_request→execution のトレースを永続化）
- Kabusys 用の環境設定ローダ（.env 自動読み込み／環境変数経由）

機能一覧（抜粋）
----------------
- ETL
  - run_daily_etl: 市場カレンダー / 株価（raw_prices）/ 財務（raw_financials）を差分取得して保存
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別ETLジョブ
- Data
  - jquants_client: J-Quants API クライアント（認証・ページネーション・リトライ・保存関数）
  - news_collector: RSS 収集（SSRF対策・トラッキング除去・前処理）
  - quality: データ品質チェック（QualityIssue を返す）
  - audit: 監査ログ（DDL / 初期化 / init_audit_db）
  - calendar_management: 営業日判定・next/prev_trading_day・calendar_update_job
  - stats: zscore_normalize
- AI
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを取得し ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離と LLM マクロセンチメントを合成して market_regime を更新
- Research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

セットアップ手順
----------------

前提
- Python 3.10 以上（Union 型表記や Path | None を利用）
- DuckDB を使用（Python パッケージ duckdb）
- OpenAI SDK（openai）を使用（AI モジュール）
- defusedxml（RSS パースの安全対策）

推奨手順（UNIX 系の例）
1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <repo>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （必要に応じて他のユーティリティを追加してください。プロジェクトに requirements.txt がある場合はそれを使ってください。）

4. 開発インストール（パッケージをプロジェクト内で利用したい場合）
   - pip install -e .

環境変数 / .env
----------------
kabusys/config.py が .env ファイルをプロジェクトルートから自動読み込みします（優先度: OS env > .env.local > .env）。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（必須を含む）
- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
- KABU_API_PASSWORD (必須) : kabu ステーション API のパスワード（実行モジュールで使用）
- SLACK_BOT_TOKEN (必須) : Slack 通知用（該当機能を使う場合）
- SLACK_CHANNEL_ID (必須) : Slack チャンネル ID
- OPENAI_API_KEY (必須 for AI) : OpenAI API キー（score_news / score_regime で代替可能）
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT （監視設定）

簡単な .env 例（プロジェクトルートに置く）
(必ず実運用では秘密情報を安全に管理してください)
    JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
    OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    KABUSYS_ENV=development

使い方（よく使う API 例）
------------------------

基本的な DuckDB 接続と ETL 実行（例）
    import duckdb
    from datetime import date
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

監査データベース初期化
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn を使って発注ログ等を記録できる

ニュース収集（RSS）の呼び出し例（単体）
    from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
    for a in articles:
        print(a["id"], a["title"], a["datetime"])

ニュースセンチメントスコア付け
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    from kabusys.config import settings
    import duckdb

    conn = duckdb.connect(str(settings.duckdb_path))
    count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を環境に設定しておく
    print("scored:", count)

市場レジーム判定
    from kabusys.ai.regime_detector import score_regime
    from kabusys.config import settings
    import duckdb
    from datetime import date

    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を設定

研究 / ファクター計算
    from kabusys.research.factor_research import calc_momentum
    import duckdb
    from datetime import date

    conn = duckdb.connect("data/kabusys.duckdb")
    momentum = calc_momentum(conn, date(2026,3,20))
    # momentum は date/code をキーとした dict のリスト

データ品質チェック
    from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=date(2026,3,20))
    for i in issues:
        print(i.check_name, i.severity, i.detail)

注意点 / 設計方針（抜粋）
-----------------------
- ルックアヘッドバイアス対策: AI・ETL・research モジュールは date 引数を明示的に受け取り、内部で datetime.today() / date.today() を参照しないように設計されています（バックテスト利用を想定）。
- 冪等性: J-Quants からの保存処理は ON CONFLICT / DO UPDATE や INSERT/DELETE の組合せで冪等に保存されます。
- API リトライ・レート制御: J-Quants の呼び出しは内部で固定レート制御（120 req/min）とリトライを備えています。OpenAI 呼び出しはリトライ・バックオフの実装があります。
- セキュリティ: news_collector は SSRF 対策（リダイレクト検査・プライベートホスト除外）、defusedxml を使った XML パースを行います。
- フェイルセーフ: AI API 等の外部障害時はスコアを 0.0 として継続する設計（例: regime_detector/news_nlp）。

ディレクトリ構成
----------------
（主要ファイル・サブパッケージのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / .env 自動読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースセンチメント解析 / score_news
    - regime_detector.py     -- 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント + save_* 関数
    - pipeline.py            -- ETL パイプライン / run_daily_etl
    - etl.py                 -- ETLResult 再エクスポート
    - news_collector.py      -- RSS 取得・前処理
    - quality.py             -- データ品質チェック
    - stats.py               -- zscore_normalize 等
    - audit.py               -- 監査ログスキーマ / init_audit_db
    - calendar_management.py -- カレンダー & 営業日判定
  - research/
    - __init__.py
    - factor_research.py     -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py -- calc_forward_returns / calc_ic / factor_summary / rank
  - ai/ (上記)
  - research/ (上記)
  - その他モジュール（strategy / execution / monitoring 等のプレースホルダが __all__ に含まれています）

運用上のヒント
---------------
- 本番環境では KABUSYS_ENV=live を設定し、ログレベル等を適切に設定してください。
- 秘密情報（API キー等）は環境変数管理ツールやシークレットストアで管理し、リポジトリに含めないでください。
- DuckDB ファイルと監査 DB のバックアップ・スナップショット運用を検討してください。
- OpenAI API 呼び出しはコストが発生します。スコア処理のバッチ化／頻度を制御してください。

ライセンス / 貢献
-----------------
（ここにライセンス情報やコントリビューションガイドを追記してください）

補足
----
この README はコードのコメント・実装に基づいて作成しています。実行前にプロジェクト固有の追加依存・セットアップ（requirements.txt、pyproject.toml、DB スキーマ初期化スクリプト等）を必ず確認してください。必要であれば README に追記しますので、追加で記載したい情報（例: 具体的な依存パッケージ一覧やデプロイ手順）があれば教えてください。