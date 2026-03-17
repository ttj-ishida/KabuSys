KabuSys — 日本株自動売買プラットフォーム（README）
================================================

概要
----
KabuSys は日本株の自動売買（データ収集／ETL／品質チェック／監査ログ整備）を目的とした Python パッケージです。  
主に J-Quants API からの市場データ取得、RSS ベースのニュース収集、DuckDB を用いたデータ格納と品質チェック、監査ログ（発注→約定トレース）などの基盤機能を提供します。

主な設計方針（抜粋）
- API レート制御・リトライ・トークン自動リフレッシュ（J-Quants クライアント）
- DuckDB による冪等的なデータ保存（ON CONFLICT / DO UPDATE）
- ニュース収集での SSRF / XML Bomb 対策、トラッキングパラメータ除去、ID のハッシュ化
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（signal → order_request → executions）によるトレーサビリティ

機能一覧
--------
- 環境設定管理
  - .env / .env.local の自動読み込み（OS 環境変数優先、.env.local は上書き）
  - 必須環境変数の取得と検証
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期）および市場カレンダー取得
  - 固定間隔レートリミット（120 req/min）
  - 指数バックオフによるリトライ、401 時の自動トークンリフレッシュ
  - DuckDB へ冪等保存用の save_* 関数
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、テキスト前処理、記事ID生成（正規化 URL の SHA-256）
  - SSRF 対策・gzip・XML の安全パース・受信サイズ制限
  - raw_news / news_symbols への冪等保存
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック（最終取得日からの差分取得、バックフィル）
  - 日次 ETL 実行（カレンダー→株価→財務→品質チェック）
  - 個別 ETL 関数（run_prices_etl / run_financials_etl / run_calendar_etl）
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチで JPX カレンダーを更新）
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク（前日比）・日付不整合の検出
  - QualityIssue 型で検出結果を返却
- スキーマ＆監査（kabusys.data.schema, kabusys.data.audit）
  - DuckDB のスキーマ初期化（Raw / Processed / Feature / Execution 層）
  - 監査ログ用スキーマ（signal_events / order_requests / executions）と初期化ユーティリティ

システム要件
-------------
- Python 3.10 以上（型ヒントで | 演算子使用のため）
- DuckDB（Python パッケージ: duckdb）
- defusedxml（RSS XML の安全パース用）
- ネットワークアクセス（J-Quants API、RSS フィード）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - (例) git clone ... && cd your-repo

2. 仮想環境を作成して有効化
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. pip を更新して依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - プロジェクトがパッケージとしてインストール可能な場合:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（既定）。  
     自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   - 必須環境変数（Settings から抜粋）
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD      — kabu API のパスワード（必須）
     - SLACK_BOT_TOKEN        — Slack 通知用 BOT トークン（必須）
     - SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID（必須）

   - 任意 / デフォルト付き
     - KABUSYS_ENV            — development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL              — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL      — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH            — SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）

   - .env のサンプル（例）
     - JQUANTS_REFRESH_TOKEN= your_refresh_token_here
     - KABU_API_PASSWORD= your_kabu_password
     - SLACK_BOT_TOKEN= xoxb-...
     - SLACK_CHANNEL_ID= C01234567
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO

使い方（簡単な例）
-----------------

1) DuckDB スキーマ初期化
- Python REPL / スクリプトで:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

  - ":memory:" を渡すとインメモリ DB を使用します。

2) 日次 ETL を実行する（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 引数で target_date, id_token 等を指定可
  print(result.to_dict())

3) ニュース収集ジョブを実行
  from kabusys.data.news_collector import run_news_collection
  # known_codes は記事中の4桁銘柄コード抽出に使用する有効コード集合（None なら紐付けをスキップ）
  results = run_news_collection(conn, known_codes={"7203","6758"})
  print(results)  # {source_name: 新規保存件数}

4) 監査ログ用 DB 初期化（監査専用 DB を分離する場合）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

5) J-Quants API を直接使ってページネーション取得
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用
  records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)

主要 API の抜粋
----------------
- data.schema.init_schema(db_path)
  - DuckDB スキーマの作成（冪等）。接続を返す。

- data.audit.init_audit_db(db_path)
  - 監査ログ専用 DB を初期化して接続を返す。

- data.pipeline.run_daily_etl(conn, target_date=None, ...)
  - 日次 ETL を実行し ETLResult を返す（品質チェック結果含む）。

- data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
  - 複数 RSS ソースから記事を収集し raw_news / news_symbols を更新。

- data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - J-Quants からデータを取得（ページネーション対応）。

- data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
  - DuckDB へ冪等（ON CONFLICT）で保存。

ディレクトリ構成
----------------
（プロジェクトの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定管理（.env 自動読み込み含む）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - news_collector.py      # RSS ニュース収集
    - pipeline.py            # ETL パイプライン（差分取得・品質チェック）
    - schema.py              # DuckDB スキーマ定義・初期化
    - calendar_management.py # マーケットカレンダー管理ユーティリティ
    - audit.py               # 監査ログ（signal / order / executions）初期化
    - quality.py             # データ品質チェック
  - strategy/
    - __init__.py            # 戦略レイヤ（拡張用）
  - execution/
    - __init__.py            # 発注/約定/ポジション管理（拡張用）
  - monitoring/
    - __init__.py            # 監視機能（拡張用）

運用上の注意・ヒント
-------------------
- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を起点に行われます。テストで自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants の API レート制限（120 req/min）に合わせたスロットリング実装がありますが、大量データの取得や並列化には注意してください。
- DuckDB のファイルはアプリケーションのアクセスパターンに合わせて配置してください（デフォルト: data/kabusys.duckdb）。
- ニュース収集は外部フィードへの接続を行うため、社内ネットワークやプロキシ環境で SSRF 制限や DNS 解決に依存する挙動に注意してください。
- 監査ログ（order_requests / executions）は削除しない設計です。監査性を保つため、不要な削除操作は避けてください。

拡張と開発
-----------
- strategy/ や execution/、monitoring/ は拡張用のエントリポイントです。ここに戦略ロジック、ブローカー接続ラッパー、監視用アダプタ等を実装してください。
- テストを作成する際は config モジュールの自動 .env 読み込みを無効化するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると干渉を避けられます。
- データ品質チェック（quality.py）は ETL 後のガードとして機能します。必要に応じてチェック項目や閾値を調整してください。

ライセンス / コントリビューション
--------------------------------
この README はコードベースから自動で生成しています。実際のライセンス・貢献ルールはリポジトリの LICENSE / CONTRIBUTING ファイルに従ってください。

補足・問い合わせ
-----------------
使い方や内部実装に関して不明点があれば、どの機能について詳しく知りたいかを教えてください。簡単な実行例やユースケースに合わせた設定例も用意できます。