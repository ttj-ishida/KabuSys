# KabuSys

日本株自動売買システム用の共通ライブラリ群。データ取得（J-Quants）、ETLパイプライン、DuckDBスキーマ、ニュース収集、品質チェック、監査ログなど、運用に必要な基盤処理を提供します。

## 概要

KabuSys は、日本株を対象とした自動売買プラットフォームのデータ基盤およびユーティリティを集めた Python パッケージです。本リポジトリに含まれる主要機能は次のとおりです。

- J-Quants API から株価・財務・市場カレンダーを安全かつ冪等に取得
- RSS ベースのニュース収集（トラッキング除去・SSRF抑止・gzip/BOM対策）
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 環境変数ベースの設定管理（.env 自動読み込み、保護機構あり）

設計上のポイントとして、API レート制限・リトライ・トークン自動更新・Look-ahead bias 防止（fetched_at 保存）・DB への冪等保存（ON CONFLICT）等を重視しています。

---

## 機能一覧

- data.jquants_client
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - レートリミット（120 req/min）・リトライ（指数バックオフ）対応
  - get_id_token（リフレッシュトークンから idToken を取得）
  - fetch_* / save_* 系関数（fetch -> DuckDB へ冪等保存）

- data.news_collector
  - RSS フィード取得、記事正規化（URL トラッキングパラメータ除去）
  - SSRF 対策（スキーム検証・プライベートIP拒否・リダイレクト検査）
  - gzip サイズ検査、XML 攻撃対策（defusedxml）
  - raw_news テーブルへの冪等保存、記事⇆銘柄紐付け

- data.schema / data.audit
  - DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）
  - init_schema / init_audit_db による初期化関数

- data.pipeline
  - 日次 ETL（run_daily_etl）：カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別ジョブ

- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks による一括チェックおよび QualityIssue レポート返却

- config
  - 環境変数読み込み（プロジェクトルートの `.env`, `.env.local` を自動ロード）
  - settings オブジェクト経由で設定取得（必須項目は未設定時に ValueError）

---

## セットアップ手順（開発向け）

以下は最小限のセットアップ手順例です。プロジェクト配布時に requirements.txt / pyproject.toml 等があればそちらを参照してください。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb defusedxml

   （プロジェクトに pyproject.toml/requirements.txt があればそれを使用してください）
   - pip install -e .

4. 環境変数を設定（.env をプロジェクトルートに置くと自動読み込みされます）
   - 必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意/デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - LOG_LEVEL — デフォルト: INFO
   - 自動 .env ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   例 .env（プロジェクトルート）:
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG

5. DuckDB スキーマを初期化
   - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

6. （任意）監査DBを初期化
   - python -c "from kabusys.data.audit import init_audit_db; init_audit_db('data/audit.duckdb')"

---

## 使い方（主要 API と例）

以下は最小の利用例です。実運用ではロギング・例外処理・ジョブスケジューラ等を組み合わせてください。

- 設定の参照
  - from kabusys.config import settings
  - settings.jquants_refresh_token / settings.duckdb_path / settings.env など

- DuckDB スキーマ初期化（Python スクリプト内）
  - from kabusys.data.schema import init_schema
    conn = init_schema(settings.duckdb_path)

- 日次 ETL を実行（run_daily_etl を使った例）
  - from kabusys.data.pipeline import run_daily_etl
    from kabusys.data.schema import init_schema
    conn = init_schema(settings.duckdb_path)
    result = run_daily_etl(conn)  # デフォルトは今日
    print(result.to_dict())

  run_daily_etl は以下を順に実行します：
  1. 市場カレンダー差分取得（先読み）
  2. 株価日足の差分取得（backfill により数日前から再取得）
  3. 財務データ差分取得
  4. 品質チェック（オプション）

- 個別ジョブ
  - run_prices_etl / run_financials_etl / run_calendar_etl を直接呼ぶことで任意日・差分を指定可能。

- ニュース収集
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    conn = init_schema(settings.duckdb_path)
    known_codes = {"7203", "6758", ...}  # 事前に有効銘柄セットを準備
    results = run_news_collection(conn, sources=None, known_codes=known_codes)
    print(results)

  fetch_rss / save_raw_news / save_news_symbols が内部で利用されます。RSS のスキーム検証・SSRF対策・gzipサイズ検査・XMLパース保護が行われます。

- J-Quants クライアントを直接使う
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
    token = get_id_token()
    recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- 監査スキーマ初期化（既存接続に追加）
  - from kabusys.data.audit import init_audit_schema
    conn = init_schema(settings.duckdb_path)
    init_audit_schema(conn)  # または init_audit_db('data/audit.duckdb')

- 品質チェックを個別に実行
  - from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=None)
    for i in issues:
        print(i.check_name, i.severity, i.detail)

注意点:
- J-Quants の API は 120 req/min の制約があります。jquants_client は内部で RateLimiter を用いてこの制約を守ります。
- id_token 自動リフレッシュ: 401 発生時にリフレッシュを試み、1 回だけ再試行します。
- データの取得時には fetched_at を UTC で保存し、いつデータを取得したかを明示します（Look-ahead bias 対策）。

---

## ディレクトリ構成

（抜粋）主要なモジュールとファイル:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch/save 関数）
    - news_collector.py       — RSS ニュース収集・前処理・保存
    - schema.py               — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  — マーケットカレンダー管理（営業日判定等）
    - audit.py                — 監査ログスキーマ（signal/order/execution トレース）
    - quality.py              — データ品質チェック
  - strategy/                  — 戦略関連のプレースホルダモジュール
  - execution/                 — 実行（発注）関連のプレースホルダモジュール
  - monitoring/                — 監視関連のプレースホルダモジュール

DuckDB スキーマ（schema.py）は以下の層を定義しています：
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, orders, trades, positions, portfolio_* など
- Audit Layer（audit.py）: signal_events, order_requests, executions（監査用）

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL, デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 にすると .env 自動読み込みを無効化)

config.Settings クラスは上記をラップしており、必須のものは未設定時に ValueError を送出します。

---

## 運用・開発上の注意

- DuckDB ファイルのバックアップ・ローテーションやロック競合に注意してください（複数プロセスでの同時書き込み設計を想定する場合は運用設計が必要です）。
- J-Quants の利用規約や API トークン管理を厳重に行ってください（トークンは環境変数で管理することを推奨）。
- ニュース収集は外部 RSS を扱うため、コンテンツのエラーやしばしば非標準レイアウトに遭遇します。fetch_rss は失敗をログに出して空リストを返す設計です。
- run_daily_etl は Fail-Fast ではなく、各ステップのエラーを収集して処理を継続する設計です。戻り値の ETLResult を確認して運用判断を行ってください。

---

もし README に追加したい内容（実運用のワークフロー例、CRON / Airflow の設定例、より詳細な .env.example、テスト方法など）があれば教えてください。必要に応じてサンプルスクリプトや CLI ラッパーの雛形も作成します。