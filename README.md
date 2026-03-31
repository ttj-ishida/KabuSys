KabuSys — 日本株自動売買プラットフォーム (README)
概要
- KabuSys は日本株向けのデータプラットフォーム・リサーチ・AI補助・監査ログ・ETL を統合したライブラリ群です。
- 主目的：
  - J-Quants API からのデータ取得（株価・財務・市場カレンダー）
  - DuckDB を用いたデータ保存・品質チェック・ETL パイプライン
  - ニュースの NLP スコアリング（OpenAI）および市場レジーム判定
  - 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 発注／約定を追跡する監査ログ（監査用 DB 初期化ユーティリティ）
- 内部設計の特徴：
  - Look-ahead bias を避ける設計（日時の固定参照を避け、ETL/スコアリングは明示的な target_date を使用）
  - 冪等性（DB 保存は ON CONFLICT DO UPDATE / DO NOTHING で設計）
  - フェイルセーフ（外部 API 失敗時はフォールバックやスキップ、ログ出力）
  - テスト容易性（APIキー注入、内部呼び出しをモックしやすい構造）

主な機能一覧
- 設定管理
  - kabusys.config.settings：.env / 環境変数読み込み、自動ロード（.env, .env.local）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能
- データ取得・ETL（kabusys.data）
  - jquants_client: J-Quants API 呼び出し、ページネーション、レート制御、リトライ
  - pipeline: 日次 ETL（run_daily_etl）・個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - calendar_management: 市場カレンダー管理、営業日判定、next/prev_trading_day など
  - news_collector: RSS 収集、SSRF 対策、前処理、raw_news 保存
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - audit: 監査テーブル定義・初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計（zscore_normalize）
- AI（kabusys.ai）
  - news_nlp.score_news: ニュースをまとめて OpenAI に送り、銘柄毎に ai_score を ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースセンチメントを混合して日次の市場レジーム（bull/neutral/bear）を market_regime テーブルへ保存
- 研究（kabusys.research）
  - factor_research: calc_momentum, calc_value, calc_volatility（価格/財務からの各種ファクター計算）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank（将来リターン・IC・統計要約）

セットアップ手順
1. 推奨 Python バージョン
   - Python 3.10+（型記法や組み込み typing 機能を使用）

2. 依存パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリの urllib 等を使用）
   - 例: requirements.txt を用意する場合
     - duckdb
     - openai
     - defusedxml

   インストール例:
   - pip install duckdb openai defusedxml

3. 環境変数（最低限必要なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（jquants_client が使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（設定管理用）
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - OPENAI_API_KEY: OpenAI 呼び出しに使用（news_nlp / regime_detector のデフォルト）
   - 任意・デフォルト値を上書き可能な変数:
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
     - DUCKDB_PATH（データ保存先、デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - .env 自動ロード:
     - プロジェクトルート（.git または pyproject.toml を探索）にある .env を読み込み
     - .env.local は .env を上書き
     - OS 環境変数は保護され上書きされない（ただし .env.local は上書き可能）
     - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. データベース初期化（監査ログなど）
   - 監査ログ用 DuckDB を作成してテーブルを初期化:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
     - init_audit_db は parent ディレクトリを自動作成します

使い方（簡単な例）
- 共通: settings と DuckDB 接続
  - from kabusys.config import settings
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（全体パイプライン）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- 個別 ETL
  - run_prices_etl(conn, target_date, id_token=None)
  - run_financials_etl(conn, target_date, id_token=None)
  - run_calendar_etl(conn, target_date, id_token=None)

- ニュース NLP（AI）スコアリング
  - from kabusys.ai.news_nlp import score_news
    n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
    print(f"scored {n} codes")

  - 注意点:
    - api_key を引数で渡せる（テストやマルチキー対応）
    - OpenAI のレート制限、モデルは gpt-4o-mini を想定
    - 空記事時は LLM 呼び出しを行わず 0 を返す

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 研究用関数（ファクター計算）
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    moms = calc_momentum(conn, target_date=date(2026,3,20))
    vals = calc_value(conn, target_date=date(2026,3,20))
    vols = calc_volatility(conn, target_date=date(2026,3,20))

- 統計正規化ユーティリティ
  - from kabusys.data.stats import zscore_normalize
    normed = zscore_normalize(records, ["mom_1m", "mom_3m"])

- 監査ログ初期化
  - from kabusys.data.audit import init_audit_db, init_audit_schema
    conn = init_audit_db("data/audit.duckdb")  # テーブル作成済みの接続が返る
    # あるいは既存 conn に対して
    init_audit_schema(conn, transactional=True)

重要なテーブル（コード内参照）
- raw_prices / prices_daily（株価データ）
- raw_financials（財務情報）
- market_calendar（JPX カレンダー）
- raw_news, news_symbols（ニュースと銘柄マッピング）
- ai_scores（ニュース由来の AI スコア）
- market_regime（レジーム判定結果）
- signal_events, order_requests, executions（監査ログ）

設定ファイル (.env) の例
- .env (プロジェクトルート)
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - OPENAI_API_KEY=sk-...
  - SLACK_BOT_TOKEN=xoxb-...
  - SLACK_CHANNEL_ID=C01234567
  - KABUSYS_ENV=development
  - DUCKDB_PATH=data/kabusys.duckdb

テスト／デバッグのヒント
- OpenAI 呼び出しはモジュール内の _call_openai_api をモック可能（unittest.mock.patch）
- .env 自動ロードを無効にしてテスト用の環境を明示的に設定:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py (ニュースNLPスコアリング)
    - regime_detector.py (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント + 保存関数)
    - pipeline.py (ETL パイプライン)
    - etl.py (ETLResult 再エクスポート)
    - calendar_management.py (カレンダー管理)
    - stats.py (統計ユーティリティ)
    - quality.py (データ品質チェック)
    - news_collector.py (RSS 収集・前処理)
    - audit.py (監査テーブル定義・初期化)
  - research/
    - __init__.py
    - factor_research.py (モメンタム等)
    - feature_exploration.py (forward returns / IC / summary)

設計上の注意
- 本ライブラリはデータ取得・分析・監査を目的とした内部ライブラリです。実際の自動売買で「本番」運用する際は、発注ロジック・エラーハンドリング・レート制御など追加の安全策を設けてください。
- OpenAI や J-Quants API を利用する箇所は API キーや利用料金・レート制限に注意してください。
- DuckDB の executemany における空パラメータの扱い（バージョン差異）をコード内で考慮していますが、実行環境の DuckDB バージョン差異に注意してください。

ライセンス
- (この README ではライセンス情報は含めていません。プロジェクトで採用するライセンスをここに明記してください。)

最後に
- まずは .env を用意し（または環境変数を設定）、DuckDB 接続を作成して run_daily_etl を実行することで日次データ取り込みの動作確認ができます。AI 関連は OPENAI_API_KEY を設定し、score_news / score_regime を試してください。詳細はコード内ドキュメント（docstring）を参照してください。