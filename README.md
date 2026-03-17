# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。データ取得（J-Quants）、ETL、品質チェック、ニュース収集、マーケットカレンダー管理、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を中心とした内部用ライブラリです：

- J-Quants API からの株価（日足）、財務データ、マーケットカレンダー取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB を利用したスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集（SSRF対策・XML安全パース・トラッキング除去・銘柄抽出）
- マーケットカレンダー管理（営業日判定・次営業日/前営業日取得・夜間更新ジョブ）
- 監査ログ（signal → order_request → executions のトレース用スキーマ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上のポイント：API レート制御、冪等性（ON CONFLICT）、Look-ahead バイアス対策（fetched_at の記録）、堅牢なエラーハンドリング。

---

## 主な機能一覧

- データ取得 / 保存
  - kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
- DB スキーマ
  - kabusys.data.schema.init_schema / get_connection（DuckDB スキーマ定義と初期化）
  - kabusys.data.audit.init_audit_schema / init_audit_db（監査ログ）
- ETL パイプライン
  - kabusys.data.pipeline.run_daily_etl（市場カレンダー→株価→財務→品質チェックの一連処理）
  - run_prices_etl / run_financials_etl / run_calendar_etl 個別ジョブ
- ニュース収集
  - kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
  - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成
  - SSRF 対策・XML 安全パース・サイズ上限（10MB）等の保護
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 品質チェック
  - kabusys.data.quality.run_all_checks（欠損・スパイク・重複・日付不整合）
- 設定 / 環境変数管理
  - kabusys.config.settings（.env / .env.local の自動読み込み、必須パラメータの取得）

---

## セットアップ手順

前提: Python 3.9+（型注釈の union 記法や型ヒントを利用）

1. リポジトリをクローンしてパッケージをインストール（ローカル開発向け）
   - pip editable install（任意の方法でパッケージとして利用してください）
   - 例:
     - python -m pip install -e .

2. 必要パッケージのインストール
   - duckdb, defusedxml などが必要です。pyproject.toml / requirements に従ってください。
   - 例:
     - python -m pip install duckdb defusedxml

3. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants のリフレッシュトークン）
     - KABU_API_PASSWORD（kabu API のパスワード）
     - SLACK_BOT_TOKEN（Slack 通知用）
     - SLACK_CHANNEL_ID
   - 任意（デフォルト有り）:
     - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) デフォルト: INFO
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

   - .env（例）
     - JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

4. DuckDB スキーマ初期化
   - Python スクリプトや REPL で次を実行してスキーマを作成します（ファイルの親ディレクトリは自動作成されます）:

     - 例:
       from kabusys.data import schema
       conn = schema.init_schema("data/kabusys.duckdb")

   - 監査ログ用スキーマのみを追加したい場合:
       from kabusys.data import audit
       audit.init_audit_schema(conn)
     または audit.init_audit_db("data/audit.duckdb")

---

## 使い方（主要な利用例）

以下は代表的なスクリプト利用例です。実運用ではエラーハンドリング・ログ設定を適宜追加してください。

- 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 例:
    from datetime import date
    from kabusys.data import schema, pipeline

    conn = schema.init_schema("data/kabusys.duckdb")
    result = pipeline.run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- 個別ジョブ
  - 市場カレンダー更新:
    from kabusys.data import pipeline
    fetched, saved = pipeline.run_calendar_etl(conn, target_date=date.today())

  - 株価差分 ETL:
    fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())

- ニュース収集と銘柄紐付け
  - 例:
    from kabusys.data.news_collector import run_news_collection
    # known_codes は抽出で利用する有効銘柄コード集合
    results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
    print(results)

- J-Quants から直接データ取得
  - 例:
    from kabusys.data import jquants_client as jq
    token = jq.get_id_token()  # settings からリフレッシュトークンを使用して取得
    records = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- 監査ログ初期化
  - 例:
    from kabusys.data import audit
    conn = schema.init_schema("data/kabusys.duckdb")
    audit.init_audit_schema(conn)

ログ出力や Slack 通知の統合はアプリケーション側で行ってください。settings.slack_* の値は設定から参照できます。

---

## ディレクトリ構成（重要ファイル抜粋）

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（レート制御・リトライ）
    - news_collector.py         — RSS ニュース収集・DB保存・銘柄抽出
    - schema.py                 — DuckDB スキーマ定義 / init_schema
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — カレンダー判定・更新ジョブ
    - audit.py                  — 監査ログ（signal / order_request / executions）
    - quality.py                — データ品質チェック
  - strategy/
    - __init__.py               — 戦略関連モジュール（骨子）
  - execution/
    - __init__.py               — 発注 / 約定管理（骨子）
  - monitoring/
    - __init__.py               — 監視 / モニタリング（骨子）

（README 用の抜粋。詳細は各モジュールの docstring を参照してください。）

---

## 注意点 / 補足

- 自動環境変数読み込み:
  - プロジェクトルートにある `.env` と `.env.local` を自動読み込みします（優先度: OS 環境 > .env.local > .env）。
  - テストや特別な実行時に自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 認証トークン:
  - J-Quants の ID トークンは内部でキャッシュされ、401 を受けた場合はリフレッシュを試みます（1 回のみ）。get_id_token は明示的に呼び出すことも可能です。
- レート制御 / リトライ:
  - jquants_client では 120 req/min のレート制御、指数バックオフ、408/429/5xx へのリトライ、401 時のトークン自動更新などのロジックがあります。
- セキュリティ:
  - news_collector は defusedxml を利用した XML パース、URL スキーム検証、プライベート IP の検出（SSRF 対策）、最大レスポンスサイズ制限（10MB）を行っています。
- DuckDB による冪等性:
  - save_* 関数は ON CONFLICT を利用して冪等にデータを書き込みます。

---

## 開発 / 貢献

- コードの追加・修正はモジュールの docstring に従って行ってください。テストは新機能に合わせて追加してください。
- 自動環境読み込みはテスト時に想定外の影響を与えるため、ユニットテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用し、必要な設定はテスト内で注入することを推奨します。

---

不明点や README の補足項目（例: サンプル .env.example、CI 実行手順、デプロイ手順など）を追加したい場合は教えてください。必要に応じて具体的なスクリプト例や CLI 実装案も作成します。