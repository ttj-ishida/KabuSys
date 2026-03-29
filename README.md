KabuSys
=======

日本株向けのデータプラットフォーム & 自動売買補助ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどを一貫して扱えるモジュール群を提供します。

主な用途
- J-Quants API から株価 / 財務 / 市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と OpenAI を用いた銘柄別センチメント（ai_scores）算出
- 市場レジーム判定（ETF + マクロニュース × LLM）
- 研究用ファクター計算（Momentum / Volatility / Value 等）と特徴量解析ユーティリティ
- データ品質チェック / 市場カレンダー管理
- 発注フローの監査ログテーブル初期化ユーティリティ（監査 / トレーサビリティ）

機能一覧
- data.jquants_client: J-Quants API 呼び出し、取得データの DuckDB への冪等保存
- data.pipeline: 日次 ETL 実行（run_daily_etl）と個別 ETL ジョブ（prices/financials/calendar）
- data.news_collector: RSS 取得・正規化・raw_news への保存（SSRF 対策、トラッキング除去など）
- ai.news_nlp: OpenAI を用いた銘柄別ニュースセンチメント評価（score_news）
- ai.regime_detector: ETF（1321）200日移動平均乖離 + マクロニュース（LLM）を組み合わせた市場レジーム判定（score_regime）
- research: ファクター計算（calc_momentum / calc_volatility / calc_value）や特徴量解析（forward returns / IC / summary）
- data.quality: データ品質チェック群（欠損、重複、スパイク、日付不整合）
- data.audit: 発注〜約定の監査テーブル定義・初期化（init_audit_schema / init_audit_db）
- config: 環境変数読み込み・検証（.env 自動ロード機能、settings オブジェクト）

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに setuptools / poetry 等のパッケージ管理がある場合は適宜 pip install -e .）
   - 追加で必要な実行環境（sqlite3 等）は OS 標準で足ります
4. 環境変数設定（.env）
   - プロジェクトルート（pyproject.toml や .git のあるディレクトリ）に .env を置くと自動で読み込まれます
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 必要な環境変数（概観）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL     : kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN       : Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID      : Slack チャネル ID（必須）
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime の呼び出し時に環境参照）
   - DUCKDB_PATH           : DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite (monitoring) パス（省略時: data/monitoring.db）
   - KABUSYS_ENV           : 実行環境 ("development" / "paper_trading" / "live")（デフォルト "development"）
   - LOG_LEVEL             : ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")（デフォルト "INFO"）

例: .env（最小）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C0123456
    DUCKDB_PATH=data/kabusys.duckdb

使い方（代表的な API/コマンド）
- DuckDB 接続を作って ETL を実行する（サンプル）
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメントを算出（OpenAI API キーは環境変数 OPENAI_API_KEY、あるいは api_key 引数で指定）
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"ai_scores written for {written} codes")

- 市場レジームスコアを算出して書き込む
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20))
    # market_regime テーブルに書き込まれます

- 監査ログ用の DB 初期化
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # テーブル／インデックスが作成される

- 設定（settings）の参照
    from kabusys.config import settings
    print(settings.duckdb_path)
    print(settings.is_live)

注意点 / 運用上のポイント
- Look-ahead bias 防止設計が随所に組み込まれています（関数は内部で date.today() を盲目的に参照しない等）。
- OpenAI 呼び出しや J-Quants 呼び出しはリトライ・フォールバックロジックを備えていますが、API キー未設定時は ValueError を送出します。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を探索します。テスト時などで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の一部操作（executemany に空リスト渡す等）はバージョン依存の注意があるため、コード側で配慮されています。DuckDB は推奨バージョンを合わせてください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント（score_news）
    - regime_detector.py             — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント & DuckDB 保存関数
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult の公開（再エクスポート）
    - news_collector.py              — RSS 収集（fetch_rss 等）
    - calendar_management.py         — マーケットカレンダー管理（is_trading_day 等）
    - quality.py                     — データ品質チェック群
    - stats.py                       — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py             — Momentum/Value/Volatility ファクター
    - feature_exploration.py         — 将来リターン、IC、summary、rank
- setup / packaging: pyproject.toml 等（プロジェクトルートに配置想定）

主要 DB テーブル（コード参照）
- raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, signal_events, order_requests, executions, など

開発・テスト時の便利情報
- 自動 .env ロードを無効化:
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しをユニットテストで差し替える場合、各モジュールの _call_openai_api を mock.patch して置き換える設計になっています。
- news_collector は defusedxml を使用して XML 攻撃対策を行っています。

ライセンス / 貢献
- 本 README ではライセンスやコントリビュート手順を記載していません。必要に応じてプロジェクトの LICENSE / CONTRIBUTING ドキュメントを参照してください。

以上。必要があればセットアップ用の requirements.txt、サンプル .env.example、簡易起動スクリプト (例: run_etl.py) の雛形を併せて作成します。どれを作成しましょうか？