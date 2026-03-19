KabuSys — 日本株自動売買プラットフォーム（README）
概要
- KabuSys は日本株を対象としたデータプラットフォーム兼戦略実行基盤のコアライブラリです。
- DuckDB をデータ層に使い、J-Quants API から市場データ・財務データ・カレンダーを取得し、ETL → 特徴量生成 → シグナル生成 → 発注監査のワークフローを想定したモジュール群を提供します。
- 目的: 研究（factor research）で得たファクターをパイプライン化し、ルックアヘッドバイアスに配慮した形で特徴量作成・シグナル生成・監査ログ保存まで行えるようにすること。

主な機能
- 環境設定管理
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード（プロジェクトルートを検出）。
  - 必須変数未設定時は明示的なエラー。
- データ取得 / 保存（J-Quants クライアント）
  - 株価日足（OHLCV）のページネーション対応取得、財務データ、JPXカレンダー取得。
  - API レート制御（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ。
  - DuckDB への冪等保存（ON CONFLICT / upsert 相当）。
- ETL パイプライン
  - 差分取得（DB の最終取得日を基準に自動算出）・バックフィル対応・品質チェックとの統合（quality モジュール呼び出し）。
  - 市場カレンダーの先読み（lookahead）など。
- 特徴量エンジニアリング（strategy.feature_engineering）
  - research 層で計算された raw factor を読む -> ユニバースフィルタ（最低株価・出来高） -> Z スコア正規化（クリップ） -> features テーブルへ UPSERT。
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合してコンポーネントスコアを計算し、重み付き合算で final_score を出す。
  - Bear レジーム判定による BUY 抑制、エグジット判定（ストップロス等）、signals テーブルへの置換保存（冪等）。
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理（URL 除去・正規化）、記事 ID の生成（正規化 URL の SHA-256）、raw_news 保存、銘柄抽出と news_symbols への紐付け。
  - SSRF 対策 / Gzip・サイズ制限 / defusedxml を用いた安全な XML パース。
- スキーマ管理（data.schema）
  - DuckDB 用の DDL を一括で作成する init_schema / get_connection。Raw / Processed / Feature / Execution 層を定義。
- カレンダー管理（data.calendar_management）および監査ログ（data.audit）など運用向けユーティリティ群。
- 研究向けツール（research）
  - モメンタム・ボラティリティ・バリュー計算、将来リターン計算、IC（Spearman）や統計サマリ等。

必須要件（例）
- Python 3.10+
- 依存パッケージ（本 README 作成時の主要外部依存）:
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API 等）

セットアップ手順
1. リポジトリをクローン
   - git clone <repository-url>
   - cd <repository>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （パッケージとして配布している場合）pip install -e .

4. 環境変数（.env）を用意
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 最低限設定すべき変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=CXXXXXXX
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development  # development | paper_trading | live
     - LOG_LEVEL=INFO
   - 注意: settings で必須とされる変数が未設定だと ValueError を投げます。

5. データベース初期化
   - Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を渡すとインメモリ DB が使えます（テスト用）。

基本的な使い方（サンプル）
- 日次 ETL 実行
  from datetime import date
  import kabusys
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量作成（build_features）
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date.today())
  print(f"features テーブルに書き込んだ銘柄数: {n}")

- シグナル生成（generate_signals）
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date.today(), threshold=0.60)
  print(f"生成したシグナル数: {total}")

- ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)

- カレンダー更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"保存したカレンダーレコード数: {saved}")

設定 / 注意点
- 自動 .env ロード:
  - デフォルトで .env / .env.local をプロジェクトルートから自動ロードします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。
  - プロジェクトルートは .git または pyproject.toml を探索して決定します。見つからない場合は自動ロードをスキップします。
- 環境 (KABUSYS_ENV):
  - 有効値: development, paper_trading, live。settings.env により is_dev/is_paper/is_live を参照できます。
- DB 初期化:
  - init_schema() は DDL をすべて作成します。既存テーブルはスキップされるため冪等です。
- セキュリティ:
  - news_collector は SSRF 対策・受信サイズ制限・XML デコード安全化を実装しています。RSS ソースには http/https を指定してください。
  - API トークン等は決してコミットしないでください。.env を .gitignore へ。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - news_collector.py       — RSS ニュース収集・保存
    - schema.py               — DuckDB スキーマ定義・初期化
    - stats.py                — zscore_normalize 等ユーティリティ
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  — 市場カレンダー管理 / ジョブ
    - features.py             — data 層の特徴量ユーティリティ再公開
    - audit.py                — 発注〜約定の監査ログ用 DDL/初期化
  - research/
    - __init__.py
    - factor_research.py      — momentum/volatility/value の計算
    - feature_exploration.py  — forward returns / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py  — features テーブル構築（正規化・フィルタ）
    - signal_generator.py     — final_score 計算と signals 生成
  - execution/                — 空パッケージ（発注層を想定）
  - monitoring/               — 監視／監査関連（実装は別途）
- pyproject.toml / setup.cfg 等（配布設定: リポジトリに存在する想定）

開発者向けメモ
- 型と戻り値は可能な限り標準ライブラリ型（date, datetime, dict/list）で設計されています。
- DuckDB の接続オブジェクトを明示的に渡す設計によりテストしやすくしています（:memory: での単体テスト推奨）。
- 外部 API 呼び出し部分は id_token 注入等でモックしやすく設計されています。

ライセンス・貢献
- （この README にライセンス情報が含まれていない場合、リポジトリの LICENSE を参照してください）
- バグ報告・機能追加は Issue / PR でお願いします。

以上。質問や README の追加要望（例: 具体的な .env.example ファイル内容、CI 実行手順、ユニットテストの書き方等）があれば教えてください。