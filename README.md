KabuSys — 日本株自動売買基盤（README）
概要
- KabuSys は日本株向けのデータプラットフォーム・研究・戦略・発注監査を含む自動売買基盤のコアライブラリ群です。
- 主な目的は「データ収集（J-Quants / RSS 等）」「ETL（DuckDB への格納・スキーマ管理）」「データ品質チェック」「特徴量計算・研究ユーティリティ」「監査ログ管理」を提供することです。
- 本リポジトリは発注実行（証券会社 API との実際の接続）を直接行うモジュールと分離されており、データ処理・研究ロジックは本番口座に触れない設計になっています。

主な機能
- データ取得（J-Quants API クライアント）
  - 株価日足、四半期財務、JPX カレンダー等の取得（ページネーション対応）
  - レート制御（120 req/min）、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - 取得データを DuckDB に冪等保存するユーティリティ（ON CONFLICT ...）
- ETL パイプライン
  - 差分取得（最終取得日に基づく差分・バックフィル）
  - 市場カレンダー／株価／財務の総合的な日次 ETL（run_daily_etl）
  - 品質チェック呼び出し（欠損、重複、スパイク、日付不整合）
- データスキーマ管理（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化（init_schema, init_audit_db）
- ニュース収集
  - RSS フィード収集（SSRF 対策、サイズ上限、XML セキュリティ対策）
  - 記事正規化、記事 ID 生成（URL 正規化→SHA256）、ニュースと銘柄紐付け
- 研究用ユーティリティ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算（calc_forward_returns）
  - IC（Spearman）計算、ランク変換、ファクターの統計サマリー
  - Z スコア正規化ユーティリティ
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定 までトレース可能な監査テーブル定義
  - 発注要求の冪等キー（order_request_id）など監査性を重視

セットアップ手順（開発環境）
前提
- Python 3.10 以上（型注釈に X | None を使用しているため）
必須パッケージ（最低限）
- duckdb
- defusedxml
（実行環境に応じて追加の依存が必要になることがあります。プロジェクトの requirements.txt がある場合はそちらを参照してください。）

例（venv を使う場合）:
1) 仮想環境作成・有効化
  python -m venv .venv
  source .venv/bin/activate  # Unix/macOS
  .venv\Scripts\activate     # Windows

2) 必要パッケージのインストール
  pip install duckdb defusedxml

3) パッケージのインストール（プロジェクトルートで）
  pip install -e .

環境変数
- 自動的にプロジェクトルートの .env と .env.local をロードします（優先度: OS 環境 > .env.local > .env）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
主要な環境変数（アプリケーション起動前に設定してください）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development"|"paper_trading"|"live")（デフォルト "development"）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト "INFO"）

使い方（簡易ガイド）
1) DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)

  - init_schema(":memory:") でインメモリ DB を使用可能。

2) 日次 ETL 実行（J-Quants から差分取得して保存）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

  - run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェック の順で実行します。
  - トークンを明示的に渡す場合は id_token 引数に get_id_token() の戻り値を渡せます（通常はモジュール内キャッシュを利用）。

3) ニュース収集の実行
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に使う有効な銘柄コードの集合（例: {"7203","6758",...}）
  results = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(results)  # {source_name: saved_count}

4) 研究・特徴量計算
  from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
  from datetime import date
  movers = calc_momentum(conn, date(2025, 1, 31))
  vols = calc_volatility(conn, date(2025, 1, 31))
  vals = calc_value(conn, date(2025, 1, 31))
  normalized = zscore_normalize(movers, ["mom_1m", "mom_3m", "ma200_dev"])

5) 監査ログ DB 初期化（監査専用 DB を分けたい場合）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

主要 API（抜粋）
- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.duckdb_path, settings.env 等
- kabusys.data.jquants_client
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_daily_quotes(), save_financial_statements(), save_market_calendar()
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl（個別ジョブ）
- kabusys.data.news_collector
  - fetch_rss(url, source), save_raw_news(conn, articles), run_news_collection(conn, ...)
- kabusys.data.quality
  - run_all_checks(conn, ...)
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize(records, columns)

設計上の注意点 / 運用メモ
- J-Quants API にはレート制限とリトライロジックが組み込まれていますが、長時間バッチや多数の銘柄取得を行う際は監視を行ってください。
- DuckDB に対する DDL は冪等であるため再帰的に呼び出しても安全です。なお一部の初期化関数は transactional オプションでトランザクション制御可能です（例: init_audit_schema）。
- News Collector は外部 XML を解析するため defusedxml を使用し、SSRF 対策や受信サイズ制限を実装しています。
- run_daily_etl は品質チェックの結果を ETLResult.quality_issues に格納します。重大（severity="error"）な問題があれば運用側でアラートや ETL 停止を判断してください。
- 環境変数は .env/.env.local から自動ロードされます。テストなどで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                    : 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          : J-Quants API クライアント（取得・保存）
    - news_collector.py         : RSS 収集・正規化・DB 保存
    - schema.py                 : DuckDB スキーマ定義・初期化
    - stats.py                  : 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py               : ETL パイプライン（差分取得・日次 ETL）
    - features.py               : 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py    : カレンダー更新・営業日判定ロジック
    - etl.py                    : ETL 公開型（ETLResult 再エクスポート）
    - audit.py                  : 監査ログスキーマ / 初期化
    - quality.py                : データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py    : 将来リターン・IC 計算・統計サマリー
    - factor_research.py        : momentum / volatility / value の計算
  - strategy/                    : （戦略ロジックのエントリプレースホルダ）
  - execution/                   : （発注実行ロジックのエントリプレースホルダ）
  - monitoring/                  : （監視系のエントリプレースホルダ）

ライセンス / 貢献
- 本 README 内ではライセンス情報を含めていません。実際の配付物では LICENSE ファイルを確認してください。
- コントリビューション方針・コードスタイルはプロジェクトの CONTRIBUTING.md を参照してください（存在する場合）。

最後に
- この README はコードベースの主要機能と基本的な使い方を短くまとめたものです。詳細な API 使用例や運用手順は各モジュールの docstring（ソース内コメント）とプロジェクト内ドキュメント（StrategyModel.md, DataPlatform.md 等）を参照してください。