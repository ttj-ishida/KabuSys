KabuSys — 日本株自動売買基盤
==========================

概要
----
KabuSys は日本株のデータ取得・品質管理・ファクター研究・ニュースベースのAIスコアリング・市場レジーム判定・監査ログ管理を含む自動売買/リサーチ基盤のライブラリ群です。J-Quants API からのデータ取得、DuckDB を用いたローカルデータベース管理、OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価などの機能を提供します。

主な特徴
--------
- J-Quants との堅牢な連携（認証・ページネーション・レート制御・リトライ）
- DuckDB を使った差分ETLパイプライン（株価、財務、カレンダー）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS、SSRF対策、トラッキング除去）と LLM による銘柄別センチメント計算（score_news）
- マクロ＋テクニカルを統合した市場レジーム判定（score_regime）
- 研究用ユーティリティ（ファクター計算、前方リターン、IC 等）
- 監査ログ（signal / order_request / executions）テーブルの初期化ユーティリティ
- .env 自動読み込み（プロジェクトルート検出）と環境設定ラッパー

セットアップ
-----------

前提
- Python 3.10 以上
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）

インストール（開発用）
- 仮想環境を作成して依存をインストールしてください（例は pip）。
  - 必要な主要ライブラリ:
    - duckdb
    - openai
    - defusedxml
  - 例:
    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    pip install -U pip
    pip install duckdb openai defusedxml

パッケージを開発モードでインストールする場合:
    pip install -e .

環境変数 / .env
- 設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます。
- 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト等で利用）。
- 重要な環境変数:
  - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
  - OPENAI_API_KEY (必須 for AI 機能): OpenAI API キー（score_news / score_regime で利用）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必要な場合）
  - KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知に必要
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（監視DB 等）パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

例 (.env)
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

使い方（主要機能の例）
---------------------

基本的な DuckDB 接続
    import duckdb
    from kabusys.config import settings
    conn = duckdb.connect(str(settings.duckdb_path))

日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）
    from kabusys.data.pipeline import run_daily_etl
    from datetime import date
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

ニュースセンチメントの計算（AI）
- score_news は raw_news / news_symbols / ai_scores を使用し、OpenAI に問い合わせて ai_scores に書き込みます。
    from kabusys.ai.news_nlp import score_news
    from datetime import date
    # OPENAI_API_KEY が環境変数にある場合 api_key=None で可
    n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
    print(f"wrote {n_written} scores")

市場レジームの判定（テクニカル + マクロ）
    from kabusys.ai.regime_detector import score_regime
    from datetime import date
    res = score_regime(conn, target_date=date(2026,3,20), api_key=None)
    # DB の market_regime テーブルへ書き込まれます

監査ログテーブルを初期化する（約定追跡用）
    from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")
    # または既存 conn に init_audit_schema を呼ぶことも可能:
    from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)

J-Quants クライアント
- データ取得関数:
  - jquants_client.fetch_daily_quotes(...)
  - jquants_client.fetch_financial_statements(...)
  - jquants_client.fetch_market_calendar(...)
- DuckDB への保存:
  - jquants_client.save_daily_quotes(conn, records)
  - jquants_client.save_financial_statements(conn, records)
  - jquants_client.save_market_calendar(conn, records)
- 自動的に rate limit とリトライ、401 のトークンリフレッシュを扱います。

データ品質チェック
    from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=date(2026,3,20))
    for i in issues:
        print(i)

研究用ユーティリティ
- ファクター計算:
    from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
    mom = calc_momentum(conn, date(2026,3,20))
- 前方リターン・IC・要約:
    from kabusys.research import calc_forward_returns, calc_ic, factor_summary

ニュース収集
- RSS から raw_news に保存するワークフローを提供（news_collector.fetch_rss を使用して記事を取得）。
- SSRF / Gzip bomb / トラッキングパラメータ対策が組み込まれています。

自動環境変数読み込み
- kabusys.config はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env / .env.local を自動で読み込みます。
- OS 環境変数が優先され、.env.local は上書き（override=True）されます。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                — ニュースの LLM センチメント評価（score_news）
  - regime_detector.py         — マクロ + MA200 による市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py     — 市場カレンダー管理・営業日判定
  - etl.py                     — ETL インターフェース（ETLResult）
  - pipeline.py                — ETL パイプライン実装（run_daily_etl 等）
  - stats.py                   — 統計ユーティリティ（zscore_normalize）
  - quality.py                 — データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit.py                   — 監査ログテーブル定義・初期化
  - jquants_client.py          — J-Quants API クライアント（取得 + 保存）
  - news_collector.py          — RSS 収集（SSRF/サイズ制限/正規化）
- research/
  - __init__.py
  - factor_research.py         — ファクター計算（momentum/value/volatility）
  - feature_exploration.py     — forward returns / IC / summary / rank

注意点 / 設計方針（抜粋）
-----------------------
- ルックアヘッドバイアス対策: 日付計算・DB クエリで常に対象日より未来のデータを参照しない設計。
- フェイルセーフ: API 失敗時は例外で止めずに安全側のデフォルト（例: マクロセンチメント = 0）で続行する箇所がある。
- 冪等性: ETL の保存は ON CONFLICT DO UPDATE、監査ログは order_request_id を冪等キーとして扱う。
- セキュリティ: news_collector は SSRF 防止、XML 脆弱性対策（defusedxml）、レスポンスサイズ制限を実施。

開発 / 貢献
-----------
バグ修正や機能提案は Pull Request を歓迎します。テストはユニットテストを想定しており、外部 API 呼び出しはモックして実行してください。

補足
----
- OpenAI 呼び出しを行う関数はテスト時に差し替え可能（モジュール内の _call_openai_api をモック）。
- DuckDB のバージョンや挙動によるパラメータバインドの違いに配慮した実装（executemany の空リスト回避等）を行っています。

以上が本リポジトリの簡易 README です。具体的な利用ケース（バッチ設定、cron、監視、Slack 通知連携等）や .env.example のテンプレートが必要であれば追って追加します。