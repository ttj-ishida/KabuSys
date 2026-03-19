KabuSys — 日本株自動売買プラットフォーム（README）
概要
本リポジトリは「KabuSys」と呼ばれる日本株向けの自動売買・データ基盤ライブラリです。  
主に以下を目的としたモジュール群を提供します。

- J-Quants API からの市場データ取得と DuckDB への永続化（ETL）
- ニュース（RSS）収集と記事 → 銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 特徴量計算（モメンタム・バリュー・ボラティリティ等）と調査用ユーティリティ
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）スキーマ定義
- マーケットカレンダー管理（JPX 祝日・半日・SQ 判定）

この README では、機能概要、セットアップ手順、使い方例、ディレクトリ構成を日本語でまとめます。

主な機能一覧
- data/jquants_client
  - J-Quants API クライアント（レートリミット制御、リトライ、トークン自動更新、ページネーション対応）
  - 日足（OHLCV）、財務諸表、マーケットカレンダーの取得・保存関数
- data/schema, data/audit
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit 層）
  - スキーマ初期化ユーティリティ（init_schema, init_audit_schema, init_audit_db）
- data/pipeline
  - 差分 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - バックフィル・品質チェックの組み合わせて実行
- data/news_collector
  - RSS フィードの安全な取得（SSRF 対策、gzip サイズ制限、XML 危険検査）
  - 記事正規化、ID 生成、raw_news への冪等保存、銘柄抽出・紐付け
- data/quality
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
  - data.stats の zscore_normalize を再利用
- data/calendar_management
  - 営業日判定・次/前営業日・期間内営業日取得、夜間カレンダー更新ジョブ
- audit
  - signal_events / order_requests / executions テーブルによる完全な監査ログ

セットアップ手順
前提
- Python 3.9+（typing の Union/Annotated 等に依存するため）を推奨
- DuckDB を使用するため、pip で duckdb をインストール
- ネットワークアクセスが必要（J-Quants API / RSS）

1) 仮想環境（推奨）
- python -m venv .venv
- source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2) 依存パッケージのインストール
- pip install -U pip
- 必要ライブラリ例:
  - duckdb
  - defusedxml
  - さらに開発用途で logging 等（標準ライブラリ）
- 例:
  - pip install duckdb defusedxml

3) 開発モードでインストール（プロジェクトルートに setup.py / pyproject.toml がある場合）
- python -m pip install -e .

4) 環境変数の設定
プロジェクトは .env / .env.local / OS 環境変数から設定を読み込みます（kabusys.config）。ルートに .git または pyproject.toml がある場合、自動で .env を読み込みます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須環境変数（Settings 参照）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（発注関連）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（監視通知など）
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意（デフォルト有り）
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV: development / paper_trading / live（default: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（default: INFO）

.env の例（プロジェクトルートに .env を置く）
- JQUANTS_REFRESH_TOKEN=your_refresh_token
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- KABU_API_PASSWORD=your_password
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development

使い方（代表的なコード例）
以下は最小限の利用例（Python スクリプト or REPL）です。

1) DuckDB スキーマ初期化
- from kabusys.data import schema
- conn = schema.init_schema("data/kabusys.duckdb")
- conn を使って以降の ETL / 保存処理を行う

2) 日次 ETL を実行（J-Quants トークンは settings から取得）
- from kabusys.data.pipeline import run_daily_etl
- from kabusys.data.schema import init_schema
- conn = init_schema("data/kabusys.duckdb")
- result = run_daily_etl(conn)  # target_date を渡すことも可
- print(result.to_dict())  # ETL のサマリ

3) 特定データの取得 & 保存（例: 日足直接取得して保存）
- from kabusys.data import jquants_client as jq
- recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
- saved = jq.save_daily_quotes(conn, recs)
- print("saved", saved)

4) ニュース収集ジョブ実行
- from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
- results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
- print(results)

5) 研究・ファクター計算（DuckDB 接続を渡して実行）
- from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
- mom = calc_momentum(conn, target_date)
- vol = calc_volatility(conn, target_date)
- fwd = calc_forward_returns(conn, target_date)
- ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")

注意点 / 運用上のヒント
- J-Quants API はレート制限（120 req/min）を守る必要あり。クライアントは固定間隔スロットリングとリトライを実装済みです。
- ETL は冪等設計（ON CONFLICT DO UPDATE / DO NOTHING）になっていますが、初期化時はスキーマを作成してから実行してください（init_schema を使用）。
- news_collector は SSRF / gzip bomb / XML bomb 対策を実装しています。RSS ソースは DEFAULT_RSS_SOURCES をカスタマイズしてください。
- 設定は .env / .env.local → OS 環境変数 の順で上書きされます（.env.local は .env を上書き）。OS 環境変数の保護のため .env.local に重要情報を置く運用などが可能です。
- 自動で .env を読み込む仕組みはプロジェクトルート（.git または pyproject.toml）を基準に探索します。CI などで自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV によって is_live/is_paper/is_dev が切り替わります。発注等を行うモジュールは本番モード（live）での動作に注意してください。

ディレクトリ構成（主要ファイル）
（src/kabusys をルートにした主要モジュール一覧）

- kabusys/
  - __init__.py (パッケージメタ情報)
  - config.py (環境変数・設定管理)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント・保存ユーティリティ)
    - news_collector.py (RSS 取得・正規化・DB 保存)
    - schema.py (DuckDB スキーマ定義 & init_schema/get_connection)
    - pipeline.py (ETL パイプライン: run_daily_etl 等)
    - features.py (特徴量ユーティリティ公開)
    - stats.py (zscore 正規化 等)
    - calendar_management.py (マーケットカレンダー更新・営業日判定)
    - audit.py (監査ログ用スキーマ・初期化)
    - quality.py (データ品質チェック)
    - etl.py (ETLResult 再エクスポート)
  - research/
    - __init__.py (公開 API: calc_momentum 等)
    - feature_exploration.py (将来リターン、IC、summary)
    - factor_research.py (mom/value/vol 計算)
  - strategy/ (戦略層 placeholder)
  - execution/ (発注実装 placeholder)
  - monitoring/ (監視系 placeholder)

開発・貢献
- テスト: 各モジュールは外部依存（ネットワーク）を注入可能に設計されています（例: id_token 注入、_urlopen のモック化など）。ユニットテストを書く際は外部呼び出しをモックしてください。
- スタイル: ロギングを多用し、例外は上位で捕捉して運用側でハンドリングする設計ポリシーです。
- ドキュメント: 各モジュールヘッダに設計方針・注意点が記述されています。機能拡張時はヘッダの設計方針も更新してください。

ライセンス・免責
- 本文書はコードベースの README です。実際に取引を行う場合は自己責任でバックテスト・リスク管理・法令順守を行ってください。

補足（よく使う関数）
- schema.init_schema(db_path) — DuckDB スキーマ初期化
- data.jquants_client.fetch_daily_quotes / save_daily_quotes
- data.pipeline.run_daily_etl(conn, target_date=None, ...)
- data.news_collector.run_news_collection(conn, sources, known_codes)
- research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic

必要であれば、README にサンプル .env.example、CI 用ジョブ定義、より詳しい API 使用例（関数呼び出しサンプル）を追加できます。追加希望があれば教えてください。