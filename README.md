# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、DuckDB スキーマ／監査ログなど、システム全体の基盤機能を提供します。

> 現バージョン: 0.1.0

## プロジェクト概要
KabuSys は日本株の自動売買システムで必要となる基盤機能群を提供する Python パッケージです。主な目的は以下です：
- J-Quants API からの株価・財務・市場カレンダーの取得
- DuckDB を用いたスキーマ定義・永続化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策やサイズ制限等の安全対策を実装）
- 監査ログ（signal → order → execution のトレーサビリティ）

設計上のポイント：
- API レート制御（120 req/min）とリトライ（指数バックオフ、401 時はトークン自動リフレッシュ）
- DuckDB へ冪等に保存（ON CONFLICT DO UPDATE / DO NOTHING）
- ニュース収集でのセキュリティ対策（defusedxml、SSRF 検査、受信サイズ制限）
- 品質チェックでデータの欠損・スパイク・重複・日付不整合を検出

---

## 機能一覧
- data/jquants_client.py
  - J-Quants からの株価（日足）、財務（四半期）、市場カレンダー取得
  - レートリミット、リトライ、トークン自動リフレッシュ
  - DuckDB への保存関数（save_*）を提供
- data/schema.py
  - DuckDB 向けの DDL（Raw / Processed / Feature / Execution 層）定義と初期化
  - インデックス作成・接続ユーティリティ
- data/pipeline.py
  - 日次 ETL（差分取得、バックフィル、品質チェック）の実装（run_daily_etl）
  - 個別 ETL ジョブ（prices, financials, calendar）
- data/news_collector.py
  - RSS フィード取得、前処理、記事ID生成（正規化 URL → SHA256 truncated）
  - SSRF 対策、gzip 保護、XML セーフパース
  - DuckDB への冪等保存（raw_news）と銘柄紐付け（news_symbols）
- data/calendar_management.py
  - market_calendar の更新ジョブ、営業日判定（next/prev/get/is_trading_day/is_sq_day）
- data/quality.py
  - 欠損、スパイク（前日比閾値）、重複、日付不整合のチェック群
- data/audit.py
  - 監査ログ用テーブル（signal_events / order_requests / executions）と初期化

その他:
- config.py: .env 自動ロード、環境変数ラッパー、必須変数チェック
- execution/, strategy/, monitoring/ モジュールのプレースホルダ

---

## セットアップ手順

前提: Python 3.9+ を推奨（コードは型注釈に union 型や typing 機能を利用）

1. リポジトリをクローンし作業ディレクトリへ移動
   - (省略)

2. 仮想環境を作成・有効化
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 必要パッケージをインストール
   - 最低依存:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - プロジェクト配布方法により:
     - pip install -e . など（pyproject.toml がある場合）

4. 環境変数 (.env) を準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（config.py の自動ロード）。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

例: .env.example（プロジェクトルートにコピーして値を設定）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
- SLACK_BOT_TOKEN=your_slack_bot_token
- SLACK_CHANNEL_ID=your_slack_channel_id
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development  # development | paper_trading | live
- LOG_LEVEL=INFO

注意: Settings クラスで必須とされている環境変数は未設定だと ValueError が発生します（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_*）。

---

## 使い方（基本例）

以下は代表的なユースケースのサンプルコードです。実行は Python REPL / スクリプト内で行います。

1) DuckDB スキーマ初期化
- 全テーブルを作成し接続を取得します。
- 例:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL（株価・財務・カレンダーの差分取得 + 品質チェック）
- run_daily_etl は ETLResult を返します。
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

3) ニュース収集ジョブ
- RSS ソースから記事を取得し raw_news に保存、銘柄紐付けを行う。
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  known_codes = {"7203", "6758", ...}  # 事前に管理している銘柄コードセット
  result_map = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(result_map)

4) カレンダー更新バッチ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"market_calendar saved: {saved}")

5) 監査ログスキーマ初期化
- data/schema.init_schema で作成した接続に audit スキーマを追加:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

6) 設定アクセス
- 環境変数をラップする Settings オブジェクト:
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  is_live = settings.is_live

---

## よく使う API 一覧（抜粋）
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.schema.get_connection(db_path)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)
- kabusys.data.news_collector.fetch_rss(url, source)
- kabusys.data.news_collector.save_raw_news(conn, articles)
- kabusys.data.calendar_management.is_trading_day(conn, date)
- kabusys.data.quality.run_all_checks(conn, target_date=None, ...)

---

## ディレクトリ構成

(コードベースの主要ファイル一覧)

- src/kabusys/
  - __init__.py
  - config.py                      # .env 自動ロードと Settings
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント（取得/保存/リトライ/レート制御）
    - news_collector.py            # RSS ニュース収集・前処理・保存・銘柄紐付け
    - pipeline.py                  # ETL パイプライン（差分更新・品質チェック）
    - schema.py                    # DuckDB スキーマ定義・初期化
    - calendar_management.py       # 市場カレンダー管理・営業日判定
    - audit.py                     # 監査ログスキーマ（signal/order/execution）
    - quality.py                   # データ品質チェック
  - strategy/
    - __init__.py                  # 戦略関連モジュール（プレースホルダ）
  - execution/
    - __init__.py                  # 発注実行関連（プレースホルダ）
  - monitoring/
    - __init__.py                  # 監視機能（プレースホルダ）

---

## 運用上の注意・トラブルシューティング
- .env 自動ロード
  - パッケージはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に .env/.env.local を自動読み込みします。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。

- API レート・リトライ
  - J-Quants へのリクエストは 120 req/min を守るため内部でレートリミッタを使用します。
  - ネットワーク障害や 429/408/5xx に対しては指数バックオフでリトライします。

- DuckDB 保存は冪等
  - fetch → save のパターンは ON CONFLICT を使用し重複を排除／上書きします。外部から不正にデータが入った場合は quality.check_duplicates で検出可能です。

- ニュース収集の安全対策
  - defusedxml を使った XML パース、SSRF ブロック（リダイレクト先の検査）、最大受信サイズ制限などを実装済みです。
  - 大きな RSS フィードや gzip 圧縮・解凍に注意してください（サイズ制限あり）。

- ログ
  - settings.log_level でログレベルを制御できます。運用時は INFO/WARNING、デバッグ時は DEBUG を推奨します。

---

## 貢献・拡張
- strategy/、execution/、monitoring/ は各チームの実装を組み込むための拡張ポイントです。
- 新しい品質チェックは data/quality.py に追加し run_all_checks に登録してください。
- 新しいニュースソースは data/news_collector.DEFAULT_RSS_SOURCES に追加し、run_news_collection の sources 引数で指定可能です。

---

何か README の追加項目（例: CI / テスト実行方法、より詳細な使用例、コマンドラインツールの追加）を希望される場合は教えてください。README を目的に合わせて拡張します。