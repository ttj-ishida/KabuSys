# KabuSys — 日本株自動売買プラットフォーム（README）

概要
- KabuSys は日本株のデータ取得・ETL・品質チェック・ニュース収集・監査ログ化などを行う自動売買プラットフォーム基盤ライブラリです。
- 主に以下を提供します：
  - J-Quants API 経由の株価・財務・市場カレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
  - DuckDB を用いたスキーマ定義・初期化・保存（冪等性を考慮）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - RSS ベースのニュース収集（SSRF・XML攻撃対策・トラッキング除去・銘柄抽出）
  - 市場カレンダー管理（営業日判定、次/前営業日検索、夜間更新ジョブ）
  - 監査ログ（シグナル→発注→約定のトレース用スキーマ）
- 設計方針：冪等性、トレーサビリティ、セキュリティ（SSRF/XML対策）、API レート制御、品質検査の分離。

主な機能一覧
- data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
  - レートリミッタ、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）と初期化関数 init_schema
- data.pipeline
  - 日次 ETL 実行 run_daily_etl（差分取得・バックフィル・品質チェック統合）
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 実行結果を表す ETLResult（品質問題やエラーの集約）
- data.news_collector
  - RSS フィード取得 fetch_rss（gzip, XML パース, SSRF・Gzip bomb 対策）
  - raw_news への保存 save_raw_news、news_symbols への銘柄紐付け保存
  - 記事IDは正規化URLのSHA-256先頭32文字を使用して冪等性確保
  - extract_stock_codes による本文からの4桁銘柄コード抽出
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間差分取得・保存
- data.audit
  - 監査用スキーマ（signal_events / order_requests / executions 等）と初期化 helper
  - init_audit_db / init_audit_schema（UTC 時刻保存を強制）
- data.quality
  - 欠損チェック / 重複 / スパイク検出 / 日付不整合チェック
  - run_all_checks でまとめて実行

セットアップ手順（開発環境）
1. Python 環境を用意
   - 推奨: Python 3.9+
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存パッケージのインストール
   - 最低限:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があればそちらを利用）
4. 環境変数の準備
   - ルートに .env または .env.local を置くと自動ロードされます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（最低限設定が必要）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルトがある変数:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - .env の例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

初期化（DB スキーマ）
- DuckDB スキーマを初期化する（ファイル DB または :memory:）
  - 例（Python REPL / スクリプト）:
    from kabusys.data import schema
    conn = schema.init_schema("data/kabusys.duckdb")
- 監査ログ専用 DB を作る:
    from kabusys.data import audit
    audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
  - または既存の conn に監査スキーマを追加:
    from kabusys.data import audit, schema
    conn = schema.init_schema("data/kabusys.duckdb")
    audit.init_audit_schema(conn)

基本的な使い方（サンプル）
- 日次 ETL（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）
  from datetime import date
  from kabusys.data import pipeline, schema
  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュース収集（RSS から取得して保存、銘柄紐付け）
  from kabusys.data import news_collector, schema
  conn = schema.init_schema("data/kabusys.duckdb")
  # sources は {source_name: rss_url} の辞書、省略時は DEFAULT_RSS_SOURCES を使用
  known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
  stats = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(stats)

- カレンダー夜間更新ジョブ
  from kabusys.data import calendar_management, schema
  conn = schema.init_schema("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved", saved)

- J-Quants への直接リクエストやデータ保存
  from kabusys.data import jquants_client as jq, schema
  conn = schema.init_schema("data/kabusys.duckdb")
  # 日足を取得して保存
  records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
  saved = jq.save_daily_quotes(conn, records)

その他の注意点
- 自動環境ロード
  - パッケージはプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を起点に .env / .env.local を自動で読み込みます。
  - テスト時などで自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 時刻とタイムゾーン
  - 監査スキーマでは SET TimeZone='UTC' を実行して UTC を統一しています。raw データの fetched_at なども UTC 表記に整えています。
- セキュリティ考慮
  - news_collector は SSRF 対策（リダイレクト時のホスト検査）、defusedxml による XML 攻撃防止、レスポンスサイズ上限（Gzip を含む）などを実装しています。
  - jquants_client は API レート制御・リトライ・401 切れトークンの自動リフレッシュを行います。
- 冪等性
  - DuckDB への INSERT は多くの場合 ON CONFLICT DO UPDATE / DO NOTHING を使い重複を避けます。ETL は差分取得ロジックとバックフィルを組み合わせています。

ディレクトリ構成
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存・レート制御）
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（差分更新・品質チェック統合）
    - calendar_management.py — 市場カレンダー管理・営業日判定・更新ジョブ
    - audit.py               — 監査ログスキーマ（シグナル→発注→約定のトレース）
    - quality.py             — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - strategy/
    - __init__.py            — 戦略モジュール領域（拡張ポイント）
  - execution/
    - __init__.py            — 発注・実行管理モジュール領域（拡張ポイント）
  - monitoring/
    - __init__.py            — モニタリング関連（拡張ポイント）

開発上の拡張ポイント
- strategy パッケージ：特徴量／AI スコアを用いたシグナル生成ロジックを実装
- execution パッケージ：kabuステーション等に対する注文送信・ステータス管理
- monitoring：Prometheus / Slack 通知等の監視連携
- scheduler：日次 ETL / カレンダー更新 / 発注キュー処理を定期実行する外部ジョブ（cron, Airflow 等）

トラブルシューティング
- DuckDB 初期化時にディレクトリがない場合、自動で親ディレクトリを作成します。
- J-Quants への接続エラーはログ（logger）に詳細が出力されます。ログレベルは環境変数 LOG_LEVEL で変更可能です。
- RSS の取得で XML パースエラーやサイズ超過が起きた場合は該当ソースのみスキップします（他のソースは継続）。

ライセンス・貢献
- （README 作成時点ではライセンス情報はソースに含まれていません。必要に応じて LICENSE ファイルを追加してください。）
- 機能追加・バグ修正は Pull Request を歓迎します。実装・テスト方針に従い、ユニットテストやモックを含めてください。

---

ご要望があれば、README に実行スクリプト（例: CLI ラッパー）、requirements.txt の候補、CI 用の簡易テスト例、またはより詳細な運用手順（運用時のバックアップ/ローテーションや監視設定）を追記します。どれを優先して追加しますか？