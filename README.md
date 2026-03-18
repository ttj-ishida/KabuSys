# KabuSys

日本株向け自動売買データ基盤・補助ライブラリ

概要
- KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。
- 主にデータ取得（J-Quants）、ニュース収集（RSS）、ETL パイプライン、DuckDB スキーマ定義、データ品質チェック、監査ログ（発注〜約定トレース）などを提供します。
- 小〜中規模のバックエンドバッチ処理や戦略の前処理層として利用できます。

特徴（主な機能）
- J-Quants クライアント
  - 日足（OHLCV）、四半期財務（BS/PL）、JPX カレンダーを取得
  - API レート制御（120 req/min）
  - 再試行（指数バックオフ、最大 3 回）、HTTP 408/429/5xx をリトライ対象
  - 401 を検出した場合はリフレッシュトークンで自動再発行して 1 回リトライ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead bias を防止
  - DuckDB へ冪等保存（ON CONFLICT ... DO UPDATE）
- ニュース収集（RSS）
  - 複数 RSS ソースから記事を収集し raw_news に保存
  - URL 正規化（トラッキングパラメータ除去）→ SHA-256 の先頭 32 文字で記事 ID 生成（冪等性）
  - XML の安全パーシング（defusedxml）
  - SSRF 対策（スキーム検証・プライベート IP ブロック・リダイレクト検査）
  - レスポンスサイズ上限・Gzip 展開後サイズチェック（メモリ DoS 対策）
  - 銘柄コード抽出（本文＋タイトルから 4 桁コード抽出）
- DuckDB スキーマ（Data 層）
  - Raw / Processed / Feature / Execution / Audit を想定した包括的なテーブル定義
  - インデックス、外部キー、制約を含む設計
  - 初期化 API（init_schema / init_audit_db）
- ETL パイプライン
  - 差分更新（最終取得日を確認して未取得分のみ取得）
  - backfill（指定日数分さかのぼって再取得）で API 後出し修正を吸収
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - run_daily_etl により日次 ETL を一括実行
- 監査（Audit）
  - シグナル→発注要求→約定を UUID で連鎖して完全にトレース可能に記録
  - order_request_id を冪等キーとして二重発注防止
- データ品質チェック
  - 欠損（OHLC）、主キー重複、前日比スパイク、将来日付・非営業日の検出
  - QualityIssue オブジェクトで問題を集約（呼び出し元が重大度に応じて対処）

前提（推奨）
- Python 3.10+
- 主要依存: duckdb, defusedxml
  - その他は標準ライブラリで実装されています。

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone <repo>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ配布があれば pip install -e . でも可）
4. 環境変数（.env）を用意
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込みます。
   - 自動読み込みを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

推奨する .env（例）
- .env.example の内容を参考に作成してください。最低限必要なキーは以下です。
  - JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
  - KABU_API_PASSWORD=your_password
  - SLACK_BOT_TOKEN=xoxb-...
  - SLACK_CHANNEL_ID=C0123456789
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - KABUSYS_ENV=development   # 有効値: development, paper_trading, live
  - LOG_LEVEL=INFO

設定の読み込みルール（自動ロード）
- 優先順位: OS 環境変数 > .env.local > .env
- プロジェクトルートは .git または pyproject.toml を起点に探索（カレントワーキングディレクトリに依存しない）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化

使い方（簡単なサンプル）
- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
- 監査 DB 初期化（監査専用 DB）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
- J-Quants トークン取得（内部で settings.jquants_refresh_token を参照）
  - from kabusys.data.jquants_client import get_id_token
  - id_token = get_id_token()
- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # 戻り値は ETLResult（取得件数・品質問題等）
- 個別 ETL（株価）
  - from kabusys.data.pipeline import run_prices_etl
  - fetched, saved = run_prices_etl(conn, target_date=date(2025,1,1))
- ニュース収集
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  - new_counts = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
  - run_news_collection は各ソースごとに独立してエラーハンドリングします
- 品質チェック単体実行
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=None)
  - issues は QualityIssue のリスト（severity により呼び出し元で判定）

主要 API（要点）
- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.duckdb_path, settings.env, settings.log_level 等
- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続
  - get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token()
- kabusys.data.news_collector
  - fetch_rss(url, source) -> list[NewsArticle]
  - save_raw_news(conn, articles) -> list of inserted ids
  - run_news_collection(conn, sources, known_codes)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- kabusys.data.audit
  - init_audit_schema(conn) / init_audit_db(path)
- kabusys.data.quality
  - check_missing_data / check_duplicates / check_spike / check_date_consistency / run_all_checks

運用上の注意
- 環境（KABUSYS_ENV）は "development", "paper_trading", "live" のいずれかで、settings.is_live / is_paper / is_dev を使って判定できます。
- J-Quants のレート制限（120 req/min）と再試行ロジックに依存しているため、大量同時呼び出しはレートリミットに影響します。モジュールは内部で固定間隔スロットリングを行います。
- DuckDB は単一ファイル DB であり並列書き込みに制限があるため、複数プロセスからの同時書き込みは設計によって調整してください。
- ニュース収集は外部 URL を扱うため SSRF 等に注意し、コード中でも複数の防御策（スキーム検査、プライベート IP 検査、リダイレクト検査、受信サイズ制限、defusedxml）を実装しています。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - calendar_management.py
      - schema.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

README に含める補足情報
- 自動で .env をロードする仕組みは、プロジェクトルート（.git または pyproject.toml）を基準に探索して .env / .env.local を読み込みます。テストや CI で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログレベルは LOG_LEVEL 環境変数で変更できます（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
- DuckDB の初期化（init_schema）は冪等で、既存テーブルは上書きされずスキップされます。

問い合わせ / 貢献
- バグ報告や改善提案はリポジトリの Issue に作成してください。
- コントリビューション時はコードスタイル・テストを追記してください（本リポジトリの CONTRIBUTING を準備することを推奨）。

以上が KabuSys の概要と基本的な使い方です。必要であれば、具体的なコード例（スクリプト実行例、systemd / cron 用のバッチ例、CI 用のテスト例）を追記します。どの部分の詳細が必要か教えてください。