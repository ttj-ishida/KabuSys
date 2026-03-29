KabuSys — 日本株自動売買 / データ基盤ライブラリ
=================================================

概要
----
KabuSys は日本株のデータ基盤・リサーチ・AI支援・監査ログ・ETL を提供する Python パッケージです。  
主に次の用途を想定しています。

- J-Quants API からの株価・財務・マーケットカレンダーの取得および DuckDB への ETL
- RSS ニュース収集・前処理・銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントや市場レジーム判定
- 研究用途のファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析
- 発注関連の監査ログ（監査テーブル初期化、約定トレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

主な機能一覧
--------------
- data
  - jquants_client: J-Quants API 経由のデータ取得（差分取得、ページネーション、再試行、保存）
  - pipeline: 日次 ETL（run_daily_etl）と個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 収集、テキスト前処理、raw_news への冪等保存
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ（is_trading_day, next_trading_day 等）
  - quality: データ品質チェック（欠損、スパイク、重複、日付整合性）
  - audit: 監査ログ用テーブル定義と初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize などの統計ユーティリティ
- ai
  - news_nlp.score_news: 記事を銘柄ごとにまとめて LLM へ送りセンチメント（ai_scores）を作成
  - regime_detector.score_regime: ETF 1321 の MA200乖離 と マクロニュース LLM スコアを合成し market_regime を更新
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数読み込み・設定管理（settings オブジェクト）

セットアップ手順
----------------

1. Python 環境を用意（推奨: 3.10+）
2. パッケージ依存をインストール
   - 必要な主要依存例:
     - duckdb
     - openai
     - defusedxml
   - 例（pip）:
     - pip install duckdb openai defusedxml
   - （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを利用してください）
3. ローカルで開発する場合:
   - パッケージを editable インストール:
     - pip install -e .

環境変数 / .env
----------------
KabuSys はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探し、.env / .env.local を自動的に読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主に必要となる環境変数（必須 / 利用する機能に依存）:

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD: kabuステーション API 連携がある場合のパスワード
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャネル ID
- OPENAI_API_KEY: OpenAI API 呼び出し（news_nlp, regime_detector 等）
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視系などで使用する SQLite パス（data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live のいずれか（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

例（.env）:
    JQUANTS_REFRESH_TOKEN=xxxxx
    OPENAI_API_KEY=sk-xxxxx
    SLACK_BOT_TOKEN=xoxb-xxxxx
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

使い方（簡単な例）
-----------------

- DuckDB 接続の作成:
    import duckdb
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行:
    from kabusys.data.pipeline import run_daily_etl
    from datetime import date

    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    # ETLResult オブジェクトが返る（取得/保存件数・品質問題・エラー情報を含む）

- ニュースセンチメント（AI）:
    from kabusys.ai.news_nlp import score_news
    from datetime import date

    # OPENAI_API_KEY が環境変数に設定されていること
    n = score_news(conn, target_date=date(2026, 3, 20))
    print(f"書き込み銘柄数: {n}")

- 市場レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    from datetime import date

    score_regime(conn, target_date=date(2026, 3, 20))  # market_regime テーブルに書き込む

- 監査ログテーブル初期化:
    from kabusys.data.audit import init_audit_db, init_audit_schema
    # 監査専用 DB を作る場合
    audit_conn = init_audit_db("data/audit.duckdb")
    # 既存接続に監査スキーマを追加する場合
    init_audit_schema(conn, transactional=False)

- ファクター計算例:
    from kabusys.research.factor_research import calc_momentum
    from datetime import date

    momentum = calc_momentum(conn, target_date=date(2026,3,20))
    # momentum は dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）

- データ品質チェック:
    from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=date(2026,3,20))
    for i in issues:
        print(i)

設定オブジェクト（settings）
--------------------------
kabusys.config.settings オブジェクトを通じて各種設定へアクセスできます。主なプロパティ:

- jquants_refresh_token
- kabu_api_password
- kabu_api_base_url (デフォルト http://localhost:18080/kabusapi)
- slack_bot_token
- slack_channel_id
- duckdb_path (Path)
- sqlite_path (Path)
- env (development / paper_trading / live)
- log_level
- is_live / is_paper / is_dev

自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）基準で行われ、テスト時などに KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

ディレクトリ構成（主要ファイル）
-----------------------------

src/kabusys/
- __init__.py
- config.py                         — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                      — ニュースセンチメント（LLM）処理
  - regime_detector.py               — 市場レジーム判定（MA + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py                — J-Quants API クライアント & DuckDB 保存
  - pipeline.py                      — ETL パイプライン / run_daily_etl / ETLResult
  - etl.py                           — ETLResult の再エクスポート
  - news_collector.py                — RSS 収集・記事前処理
  - calendar_management.py           — 市場カレンダー管理・営業日ユーティリティ
  - quality.py                       — データ品質チェック
  - stats.py                         — 統計ユーティリティ（zscore_normalize）
  - audit.py                         — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py               — モメンタム/バリュー/ボラティリティ 等
  - feature_exploration.py           — 将来リターン / IC / 統計要約

注意事項・設計上のポイント
-----------------------
- Look-ahead バイアス対策: モジュールは date/target_date を引数で受け取り、内部で datetime.today()/date.today() を直接参照しない実装方針が徹底されています（再現性が高い）。
- 冪等性: DuckDB への保存は可能な限り ON CONFLICT 系で冪等に設計されています。
- フェイルセーフ: LLM API や外部 API が失敗した場合、許容可能なデフォルト（例: macro_sentiment=0）にフォールバックして処理を継続する設計が多く採用されています。
- テスト差し替え: 外部呼び出し（OpenAI/API/ネットワーク）はモック差し替えを想定した設計になっています（モジュール内の呼び出し関数を patch 可能）。

よくある操作例（コマンドラインの例）
-----------------------------------
（※ プロジェクトに CLI がある場合はそれを利用してください。ここでは Python REPL / スクリプト内利用例のみ記載しています。）

- ETL を日次で cron から回す（簡易例）:
    python -c "from datetime import date; import duckdb; from kabusys.data.pipeline import run_daily_etl; from kabusys.config import settings; conn=duckdb.connect(str(settings.duckdb_path)); print(run_daily_etl(conn, target_date=date.today()).to_dict())"

サポート / 開発
---------------
- テストや CI を行う際は自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants の実際の呼び出しは課金や API 制限（レート）に注意してください。jquants_client にはレート制御とリトライが組み込まれています。

ライセンス
---------
（ここにプロジェクトのライセンス情報を追記）

-----

この README はコード内のドキュメント文字列を元に作成しています。機能や API の詳細は各モジュールの docstring を参照してください。必要であれば、サンプルスクリプトや pyproject.toml / requirements.txt のテンプレートも追加します。