KabuSys
=======

日本株向けの自動売買・データ基盤ライブラリです。J-Quants や RSS などから市場データ／ニュースを収集し、DuckDB に保存して
ETL／品質チェック／監査ログのサポートを行います。取引実行や監視用の基盤モジュール群を含む設計です。

主な目的
- 日本株の株価（OHLCV）、財務データ、JPX マーケットカレンダーを自動で取得・保存する
- RSS からニュース記事を収集し、銘柄コードとの紐付けを行う
- DuckDB にスキーマを定義して冪等的にデータを保存する（ON CONFLICT 対応）
- ETL（差分更新、バックフィル）、データ品質チェック、監査ログ（トレーサビリティ）を提供する

特徴 / 設計方針
- J-Quants API 呼び出しはレート制限（120 req/min）に従う（モジュール内 RateLimiter）
- HTTP リトライ（指数バックオフ、最大 3 回）、401 時のトークン自動リフレッシュ対応
- 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を低減
- DuckDB への保存は冪等（INSERT ... ON CONFLICT DO UPDATE / DO NOTHING）
- RSS 収集は SSRF・XML Bomb 等を考慮した安全実装（defusedxml、リダイレクト検査、受信サイズ制限）
- データ品質チェック（欠損・スパイク・重複・日付不整合）を実行可能
- 監査ログ用スキーマ（signal → order_request → execution のトレーサビリティ）を提供

機能一覧
- 環境設定読み込み・検証（kabusys.config.Settings）
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数の取得とバリデーション（JQUANTS_REFRESH_TOKEN 等）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）・四半期財務・マーケットカレンダーの取得（ページネーション対応）
  - ID トークン取得とキャッシュ、自動リフレッシュ
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
- RSS ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、記事ID生成（正規化URL の SHA-256 先頭32文字）
  - raw_news 保存、news_symbols 紐付け、銘柄コード抽出
  - SSRF 対策（スキーム検査、プライベートIPブロック）、圧縮・サイズチェック
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL とインデックス定義
  - init_schema() / get_connection()
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日からの差分・バックフィル）、日次 ETL 実行 run_daily_etl()
  - 品質チェックの組み込み（kabusys.data.quality）
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・次/前営業日の取得、カレンダーの夜間更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のテーブルとインデックス
  - init_audit_schema() / init_audit_db()

前提（推奨）
- Python 3.10+
- 依存パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリ以外の追加があれば requirements.txt に記載してください）

セットアップ手順
- リポジトリをクローンし、Python 仮想環境を作成して依存をインストールします（例）。
  1. Python 仮想環境を作成・アクティベート
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
  2. 必要なパッケージをインストール
     - pip install duckdb defusedxml
     - （実プロジェクトでは requirements.txt / pyproject.toml を参照してください）
- 環境変数 / .env
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動検出して .env を読み込みます。
  - 読み込み順序（優先度）: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用途など）。
  - 主な環境変数（必須・任意）:
    - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
    - KABU_API_PASSWORD (必須) — kabu API 用パスワード
    - SLACK_BOT_TOKEN (必須)
    - SLACK_CHANNEL_ID (必須)
    - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
    - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
    - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
    - KABUSYS_ENV (任意, development|paper_trading|live, デフォルト: development)
    - LOG_LEVEL (任意, DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)
  - .env のパースは export プレフィックス・クォート・コメントに対応します（詳しくは kabusys.config の実装参照）。

使い方（基本例）
- 設定取得
  - from kabusys.config import settings
  - settings.jquants_refresh_token や settings.duckdb_path でアクセスできます。
- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)  # ファイルの親ディレクトリを自動作成
- 監査DB 初期化（監査ログ専用 DB を使う場合）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
- 日次 ETL 実行（株価・財務・カレンダーを取得して品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=None)  # target_date を指定するとその日を基準に実行
  - result は ETLResult オブジェクト（fetched/saved/quality_issues/errors を含む）
- 単体 ETL ジョブ
  - run_prices_etl / run_financials_etl / run_calendar_etl を個別に呼べます（テストや細かい制御用）。
- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
    - sources を None にするとデフォルト RSS ソース（Yahoo Finance ビジネス等）を使用します。
    - known_codes を与えると、記事のタイトル/内容から銘柄コード抽出・news_symbols への紐付けを行います。
- J-Quants API を直接利用する例
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を使って ID トークンを発行
  - quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))

実行例（簡易スクリプト）
- DB 初期化と日次 ETL（最小例）
  - from kabusys.config import settings
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema(settings.duckdb_path)
    result = run_daily_etl(conn)
    print(result.to_dict())
- RSS 収集（既知銘柄セットで紐付け）
  - from kabusys.data.news_collector import run_news_collection
    saved = run_news_collection(conn, known_codes={"7203", "6758"})
    print(saved)

設計・運用上の注意
- J-Quants のレート制限（120 req/min）に従う必要があります。本モジュールは内部でスロットリング処理を行いますが、外部からの連続呼び出しでも同様の考慮が必要です。
- トークン自動リフレッシュは 401 発生時に 1 回のみ行います。get_id_token 自体は allow_refresh=False のコンテキストで呼ばれるため再帰しません。
- DuckDB の初期化は init_schema() を利用してください。既存テーブルがある場合はスキップ（冪等実行）されます。
- news_collector は外部 URL からの取得時に SSRF や大容量レスポンス対策を講じていますが、運用ポリシーに応じた追加制限（許可ソースの限定など）を検討してください。
- ETL の backfill_days を適切に設定することで、API 側の後出し修正を吸収できます（デフォルト 3 日）。
- 品質チェック（quality.run_all_checks）は Fail-Fast ではなく全件検査し、呼び出し元が問題の深刻度に応じて対処する想定です。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定読み込み・検証
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得/保存）
    - news_collector.py      — RSS ニュース収集・保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（差分更新・日次 ETL）
    - calendar_management.py — 市場カレンダー管理（営業日判定・更新ジョブ）
    - audit.py               — 監査ログ（トレーサビリティ）スキーマ
    - quality.py             — データ品質チェック
  - strategy/                — 戦略モジュールのプレースホルダ
  - execution/               — 発注実行モジュールのプレースホルダ
  - monitoring/              — 監視用モジュールのプレースホルダ

ライセンス / 貢献
- 本プロジェクトに関するライセンス表記や貢献ガイドラインはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（該当ファイルが無い場合はプロジェクト方針に従って追加してください）。

補足（開発者向け）
- .env の自動ロードはプロジェクトルートの検出に依存するため、パッケージ配布後やテスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化することを推奨します。
- 単体テストでは外部 API 呼び出しやネットワーク I/O をモックすること。news_collector._urlopen や jquants_client._request は容易に差し替えられる設計です。
- 型注釈と明示的な UTC タイムスタンプ（fetched_at）はトレーサビリティや再現性に寄与します。利用側もこの方針を尊重してください。

以上。使い方や API の詳細は各モジュールの docstring（ソース）を参照してください。README に載せてほしい追加項目（例: CLI コマンド、サンプル .env.example、requirements.txt など）があれば教えてください。