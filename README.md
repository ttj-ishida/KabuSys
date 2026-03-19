KabuSys — 日本株自動売買システム（README）
========================================

概要
----
KabuSys は日本株向けのデータプラットフォームおよび自動売買基盤の一部を実装した Python パッケージです。本リポジトリには以下を中心とした機能群が実装されています。

- J-Quants API からの株価・財務・市場カレンダー取得クライアント（レート制御・リトライ・トークン自動更新）
- DuckDB を用いたデータスキーマ定義・初期化
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- RSS ベースのニュース収集（SSRF対策・記事正規化・銘柄抽出）
- ファクター計算・特徴量探索（モメンタム・ボラティリティ・バリュー等）と統計ユーティリティ
- 監査ログ（発注から約定までのトレーサビリティ）

設計方針として、DuckDB によるローカルデータベースを中核に、外部 API（証券会社発注等）には直接アクセスしないモジュール（Research / Data）と、発注周りを接続する Execution / Audit 層で責務を分けています。

主な機能一覧
--------------
- data.jquants_client: J-Quants API クライアント（ページネーション・トークン自動リフレッシュ・レート制御・リトライ）
- data.schema: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- data.pipeline: 差分 ETL（prices, financials, calendar）と品質チェック（欠損・重複・スパイク・日付不整合）
- data.news_collector: RSS 取得、記事正規化、DB 保存、銘柄抽出（SSRF / Gzip / XML 攻撃対策）
- data.quality: 各種データ品質チェック（QualityIssue を返す）
- data.stats / data.features: 統計・正規化ユーティリティ（zscore_normalize）
- research.factor_research / feature_exploration: モメンタム・ボラティリティ・バリュー計算、将来リターン計算、IC（Spearman）等
- data.audit: 監査ログ（signal → order_request → execution の追跡用スキーマ）

前提条件 / 必要なソフトウェア
----------------------------
- Python 3.10 以上（コード中で "A | B" 形式の型アノテーション等を使用）
- pip
- 以下の Python パッケージを利用します（最小限）:
  - duckdb
  - defusedxml

セットアップ手順
----------------

1. 仮想環境の作成（任意）
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

2. 依存パッケージのインストール
   - pip install duckdb defusedxml

   （開発用に他パッケージがあれば requirements.txt を用意してある場合はそれに従ってください）

3. パッケージのインストール（開発モード）
   - pip install -e .

4. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（注意: 自動ロードは .git または pyproject.toml を基準にルートを探索します）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
- KABU_API_PASSWORD=xxxx (kabuステーション API 用)
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=CXXXXXXX
（オプション）
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development | paper_trading | live
- LOG_LEVEL=DEBUG | INFO | WARNING | ERROR | CRITICAL

参考 .env 例:
    JQUANTS_REFRESH_TOKEN=your_refresh_token_here
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=your_slack_token
    SLACK_CHANNEL_ID=your_channel_id
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=DEBUG

基本的な使い方（例）
-------------------

1) DuckDB スキーマ初期化
- Python スクリプトや REPL で:

    from kabusys.data import schema
    conn = schema.init_schema("data/kabusys.duckdb")
    # またはメモリ内:
    # conn = schema.init_schema(":memory:")

  init_schema は必要なテーブル／インデックスをすべて作成します（冪等）。

2) 日次 ETL 実行（J-Quants からの差分取得・品質チェック）
- run_daily_etl を用いて実行:

    from datetime import date
    from kabusys.data import schema
    from kabusys.data.pipeline import run_daily_etl

    conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema 済みを想定
    result = run_daily_etl(conn)  # target_date を省略すると今日
    print(result.to_dict())

  パラメータで id_token の注入や spike_threshold, backfill_days を指定できます。

3) RSS ニュース収集ジョブ
- news_collector.run_news_collection:

    from kabusys.data import schema
    from kabusys.data.news_collector import run_news_collection

    conn = schema.get_connection("data/kabusys.duckdb")
    known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
    results = run_news_collection(conn, known_codes=known_codes)
    print(results)  # {source_name: saved_count, ...}

  fetch_rss は SSRF 対策やサイズチェック、gzip 解凍などの安全対策を行います。

4) 研究用ファクター計算
- research モジュールからファクター計算関数を呼ぶ:

    from datetime import date
    import duckdb
    from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, zscore_normalize

    conn = duckdb.connect("data/kabusys.duckdb")
    target = date(2024, 1, 31)

    mom = calc_momentum(conn, target)
    vol = calc_volatility(conn, target)
    val = calc_value(conn, target)

    # 将来リターンを計算
    fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

    # IC（相関）計算例
    ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
    print("IC:", ic)

    # Z-score 正規化
    mom_z = zscore_normalize(mom, ["mom_1m", "ma200_dev"])

各モジュールの概要（要点）
-------------------------
- data.jquants_client
  - _RateLimiter による 120 req/min のスロットリング
  - リトライ（指数バックオフ、最大 3 回）、401 の場合はトークン自動リフレッシュ
  - fetch_* 系でページネーション対応
  - save_* 系は DuckDB 側で ON CONFLICT を使った冪等保存を行う

- data.schema
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - init_schema(db_path) でまとめて作成。get_connection は既存 DB への接続のみ。

- data.pipeline
  - run_daily_etl はカレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック の順で実行
  - 差分更新、バックフィル日により後出し修正を吸収する設計

- data.news_collector
  - RSS を安全に取得して raw_news に保存、記事ID を正規化 URL から SHA-256 (先頭32文字) で生成
  - SSRF 対策、レスポンスサイズ上限、gzip 対応、XML デコード攻撃対策を実装

- data.quality
  - 欠損データ、重複、スパイク（前日比閾値）、日付整合性のチェックを行い QualityIssue リストを返す

- research.*
  - DuckDB 内の prices_daily / raw_financials のみを参照し、将来リターン・ファクター計算を行う（外部発注 API に触れない）

設定・動作上の注意点
-------------------
- 自動で .env をロードする挙動:
  - プロジェクトルート（.git や pyproject.toml）を基準に .env / .env.local を読み込みます。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - テスト時や明示的に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれかでなければなりません。
- LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれかのみ許容されます。
- DuckDB 初期化前に親ディレクトリがない場合は自動作成されます。

ディレクトリ構成（主なファイル）
--------------------------------
- src/kabusys/
  - __init__.py (パッケージルート)
  - config.py (環境変数管理・settings)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント)
    - news_collector.py (RSS ニュース収集)
    - schema.py (DuckDB スキーマと init_schema)
    - pipeline.py (ETL パイプライン)
    - calendar_management.py (市場カレンダー管理)
    - stats.py (統計ユーティリティ)
    - features.py (特徴量公開インターフェース)
    - quality.py (データ品質チェック)
    - audit.py (監査ログスキーマ)
    - etl.py (ETLResult の公開)
  - research/
    - __init__.py
    - factor_research.py (モメンタム・ボラティリティ・バリュー)
    - feature_exploration.py (将来リターン・IC・統計要約)
  - strategy/ (戦略層、空の __init__ は拡張を想定)
  - execution/ (発注関連、拡張用)
  - monitoring/ (監視用、拡張用)

開発・貢献
----------
- コードはモジュールごとに責務が分かれています。DuckDB のスキーマや SQL を変更する場合は互換性（既存データの冪等性）に注意してください。
- 大きな変更（DDL 変更など）はマイグレーション手順を用意することを推奨します。
- テストを追加する際は、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境の影響を切ってください。

ライセンス
----------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（本 README には記載していません）。

問い合わせ
----------
- 実装方針や利用方法に関する質問は ISSUE を立ててください。

以上が本コードベースの概要と導入手順です。必要があれば具体的なユースケース（例: バックフィル戦略、監査ログのクエリ例、ETL スケジューリング例）について追記します。どの例が欲しいか教えてください。