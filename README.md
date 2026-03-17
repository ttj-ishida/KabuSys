# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
J-Quants や各種 RSS フィードからのデータ収集、DuckDB を用いたデータスキーマ、ETL パイプライン、品質チェック、監査ログ（トレーサビリティ）など、実運用を意識したコンポーネント群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を持つ Python モジュール群です（主に src/kabusys 以下）:

- J-Quants API クライアント（株価日足、財務データ、JPX カレンダー）
  - レート制限制御（120 req/min）
  - リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - データ取得時に fetched_at を UTC で記録（Look-ahead Bias 対策）
  - DuckDB への冪等保存（ON CONFLICT）
- ニュース収集（RSS → raw_news）
  - URL 正規化・トラッキングパラメータ除去、記事ID は URL の SHA-256（先頭32文字）
  - SSRF 対策、受信サイズ上限、defusedxml による安全な XML パース
  - 銘柄コード抽出と news_symbols への紐付け
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
  - run_daily_etl などの高レベル API
- マーケットカレンダー管理（営業日判定・前後営業日取得・夜間更新ジョブ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution を UUID で追跡）
- 環境変数ベースの設定管理（.env 自動読み込み、設定の検証）

---

## 機能一覧

主な提供機能（モジュール別）

- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）
  - 必須環境変数取得（例: JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能
  - KABUSYS_ENV（development / paper_trading / live）・LOG_LEVEL 等

- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB に冪等保存）
  - 内部で RateLimiter、リトライ、トークンキャッシュを実装

- kabusys.data.news_collector
  - fetch_rss（RSS 取得・パース・前処理）
  - save_raw_news, save_news_symbols, run_news_collection
  - セキュリティ（SSRF、gzip/サイズ制限、defusedxml）

- kabusys.data.schema
  - init_schema(db_path) : DuckDB スキーマ（テーブル・インデックス）を初期化
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - run_daily_etl（カレンダー取得 → 株価 → 財務 → 品質チェック）
  - ETLResult（実行結果オブジェクト）

- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job（夜間バッチでカレンダー差分更新）

- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks

- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(db_path)（監査ログ用テーブル）

---

## セットアップ手順

1. リポジトリをクローン

   git clone <このリポジトリのURL>
   cd <repo>

2. Python 環境（推奨: venv）を作成・有効化

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows (PowerShell では .venv\Scripts\Activate.ps1)

3. 必要なパッケージをインストール

   このコードベースでは標準ライブラリに加えて以下が必要です:
   - duckdb
   - defusedxml

   例:

   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml

   （パッケージ化されている場合は `pip install -e .` でもインストールできます）

4. 環境変数の設定 (.env)

   プロジェクトルートに `.env`（および個人用の `.env.local`）を作成してください。主な必須変数:

   - JQUANTS_REFRESH_TOKEN=あなたのJ-Quantsリフレッシュトークン
   - KABU_API_PASSWORD=kabuステーション API パスワード
   - SLACK_BOT_TOKEN=Slack Bot トークン
   - SLACK_CHANNEL_ID=通知先チャンネル ID

   任意 / デフォルト:
   - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
   - DUCKDB_PATH=data/kabusys.duckdb  （デフォルト）
   - SQLITE_PATH=data/monitoring.db

   自動で .env を読み込む挙動はデフォルトで有効です。無効にする場合は環境変数:
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DB スキーマ初期化

   Python REPL またはスクリプト内で初期化を行います。

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

   監査ログだけ別 DB にしたい場合:

   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（例）

以下は典型的なワークフローの例です。適宜エラーハンドリングやログ出力を追加してください。

- DuckDB スキーマ作成（初回）

  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL 実行

  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")  # あるいは init_schema で既に作成済みの conn
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュース収集ジョブ実行

  from kabusys.data.news_collector import run_news_collection
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット（任意）
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- カレンダー夜間更新ジョブ

  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved: {saved}")

- J-Quants の直接呼び出し（取得と保存）

  from kabusys.data import jquants_client as jq
  from kabusys.data import schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
  saved = jq.save_daily_quotes(conn, records)

- 品質チェックのみ実行

  from kabusys.data.quality import run_all_checks
  from kabusys.data import schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)

- 監査スキーマ初期化

  from kabusys.data import audit
  conn = schema.get_connection("data/kabusys.duckdb")
  audit.init_audit_schema(conn)

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token により ID トークンを取得。
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード。
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン。
- SLACK_CHANNEL_ID (必須)
  - Slack の投稿先チャンネル ID。
- DUCKDB_PATH (任意)
  - デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）。
- SQLITE_PATH (任意)
  - 監視用 SQLite パス（任意）。
- KABUSYS_ENV (任意; default: development)
  - 有効値: development, paper_trading, live
- LOG_LEVEL (任意; default: INFO)
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意)
  - 1 をセットすると .env 自動読み込みを無効化

設定はプロジェクトルートの `.env` と `.env.local`（存在する場合）から自動的に読み込まれます。読み込み順は OS 環境変数 > .env.local > .env です。.env の自動読み込みはプロジェクトルートを .git または pyproject.toml で検出します。

---

## ディレクトリ構成

リポジトリ内の主なファイル／ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                          # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py                # J-Quants API クライアント（取得・保存）
      - news_collector.py                # RSS ニュース収集・保存・銘柄抽出
      - schema.py                        # DuckDB スキーマ定義・初期化
      - pipeline.py                      # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py           # マーケットカレンダー管理
      - audit.py                         # 監査ログ（トレーサビリティ）スキーマ
      - quality.py                       # データ品質チェック
    - strategy/
      - __init__.py                       # 戦略フレームワーク（拡張用）
    - execution/
      - __init__.py                       # 発注／執行管理（拡張用）
    - monitoring/
      - __init__.py                       # 監視・メトリクス関連（未実装のエントリポイント等）
- pyproject.toml / setup.cfg / README.md（本ファイル） 等

---

## 設計上のポイント / 注意事項

- DuckDB をメインのデータストアとして利用します。初回は schema.init_schema() を実行してテーブルを作成してください。
- J-Quants API はレート制限が厳しいため、クライアントは固定間隔スロットリングと指数バックオフを実装済みです。
- ニュース収集はセキュリティを重視（SSRF, XML Bomb, gzip 大量展開等）しています。外部 RSS の追加は信頼できるソースを推奨します。
- run_daily_etl は Fail-Fast ではなく、各ステップを独立して実行・ログ出力します。品質チェックで error レベルの問題を検出した場合は呼び出し元で適切に対処してください。
- 環境変数の自動読み込みは便利ですが、本番環境では OS 環境変数やシークレット管理サービスの利用を推奨します。
- 時刻管理は UTC を原則としています（fetched_at や監査ログのタイムスタンプ等）。

---

## よくある操作のワンライナー（参考）

- スキーマ初期化（対話）

  python -c "from kabusys.data import schema; schema.init_schema('data/kabusys.duckdb')"

- 日次 ETL を Python スクリプトで定期実行（例: cron）

  /usr/bin/env python - <<'PY'
  from kabusys.data import schema
  from kabusys.data.pipeline import run_daily_etl
  conn = schema.get_connection('data/kabusys.duckdb')
  r = run_daily_etl(conn)
  print(r.to_dict())
  PY

---

必要に応じて README を拡張します（テスト方法、CI、より詳細な API ドキュメント、運用手順書など）。どの部分を詳しくしたいか指示してください。