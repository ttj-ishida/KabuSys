# KabuSys

日本株向けの自動売買・データプラットフォームライブラリ（KabuSys）。  
DuckDB をデータ層として用い、J-Quants API / RSS ニュース等からデータ取得、特徴量生成、シグナル作成、発注監査までのワークフローをサポートします。

主な目的は「データ収集（ETL）」「ファクター計算／特徴量作成」「シグナル生成」「ニュース収集」「発注／監査のためのスキーマ・ユーティリティ」の提供です。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数の明示的エラー通知

- データ取得・ETL
  - J-Quants API クライアント（認証、ページネーション、レート制御、リトライ）
  - 日足（OHLCV）・財務データ・市場カレンダーのフェッチ
  - 差分更新（バックフィル）を行う ETL パイプライン（run_daily_etl 等）

- データベース（DuckDB）管理
  - スキーマ定義と初期化（init_schema）
  - Raw / Processed / Feature / Execution の多層テーブル定義
  - 各種保存ユーティリティ（raw_prices / raw_financials / raw_news 等）

- ニュース収集
  - RSS フィードの安全な取得（SSRF対策、gzip、サイズ制限、XML防御）
  - 記事の前処理と記事ID生成（URL 正規化 → SHA-256）
  - 銘柄コード抽出と news_symbols 登録

- 研究（research）ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - Zスコア正規化ユーティリティ

- 戦略
  - 特徴量生成（build_features: raw factor → features テーブル）
  - シグナル生成（generate_signals: features + ai_scores → signals テーブル）
  - SELL（エグジット）判定ロジック（ストップロス等）

- 発注／監査（スキーマ）
  - signal_events / order_requests / executions など監査用テーブルを提供

---

## セットアップ手順

前提: Python 3.9+ を想定（コードは型ヒントで union types 等を使用）。DuckDB を使用します。

1. リポジトリをクローン（あるいはパッケージを配置）
   - プロジェクトは src/ 配下にパッケージ kabusys がある想定です。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須（最低限）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   ※ pyproject.toml / requirements.txt がある場合はそれに従ってください。

4. パッケージを editable インストール（開発時）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 必須環境変数（最低限、ETL やシグナル生成を使う場合）:
     - JQUANTS_REFRESH_TOKEN = <J-Quants のリフレッシュトークン>
     - KABU_API_PASSWORD = <kabuステーション API パスワード>
     - SLACK_BOT_TOKEN = <Slack Bot トークン>
     - SLACK_CHANNEL_ID = <Slack 通知先チャンネル ID>
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env ロードを無効化
     - KABUSYS による DB のデフォルトパス:
       - DUCKDB_PATH — default: data/kabusys.duckdb
       - SQLITE_PATH — default: data/monitoring.db
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi

6. データベース初期化
   - Python REPL やスクリプトから DuckDB スキーマを作成します。
   - 例:
     - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

---

## 使い方（簡単な例）

以下は最も典型的なワークフロー例（DB 初期化 → 日次 ETL → 特徴量生成 → シグナル生成 → ニュース収集）。

1. DuckDB 接続を作る（init_schema は既に実行済みとする）
   - from kabusys.data.schema import get_connection
     conn = get_connection("data/kabusys.duckdb")

   - または初期化時:
     - from kabusys.data.schema import init_schema
       conn = init_schema("data/kabusys.duckdb")

2. 日次 ETL を実行（J-Quants からデータ取得）
   - from datetime import date
     from kabusys.data.pipeline import run_daily_etl
     result = run_daily_etl(conn, target_date=date.today())
     print(result.to_dict())

3. 特徴量を構築（戦略用 features テーブルに書き込む）
   - from datetime import date
     from kabusys.strategy import build_features
     count = build_features(conn, target_date=date.today())
     print(f"features upserted: {count}")

4. シグナル生成
   - from datetime import date
     from kabusys.strategy import generate_signals
     total = generate_signals(conn, target_date=date.today())
     print(f"signals written: {total}")

   - 重みや閾値を指定する場合:
     - generate_signals(conn, target_date=date.today(), threshold=0.65, weights={"momentum":0.5,"value":0.2,"volatility":0.15,"liquidity":0.1,"news":0.05})

5. ニュース収集（RSS）
   - from kabusys.data.news_collector import run_news_collection
     known_codes = {"7203","6758", ...}  # 有効な銘柄コードセット（extract_stock_codes に利用）
     results = run_news_collection(conn, sources=None, known_codes=known_codes)
     print(results)

6. 監査／発注ロジックはスキーマとユーティリティを組み合わせて利用します。発注 API 連携や broker 固有の送信ロジックは execution 層で実装してください（パッケージ内 execution モジュールの拡張を想定）。

---

## よく使うモジュールと API

- kabusys.config
  - settings: 環境変数にアクセスするための Settings インスタンス。
  - 主要プロパティ:
    - settings.jquants_refresh_token
    - settings.kabu_api_password
    - settings.kabu_api_base_url
    - settings.slack_bot_token
    - settings.slack_channel_id
    - settings.duckdb_path
    - settings.env / settings.log_level / settings.is_live / settings.is_paper / settings.is_dev

- kabusys.data.schema
  - init_schema(db_path) → DuckDB 接続（スキーマ作成済み）
  - get_connection(db_path) → 既存 DB への接続

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...) → ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別実行）

- kabusys.research
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary
  - zscore_normalize

- kabusys.strategy
  - build_features(conn, target_date) → features テーブル更新
  - generate_signals(conn, target_date, threshold, weights) → signals テーブル更新

- kabusys.data.news_collector
  - fetch_rss(url, source) → 記事リスト
  - save_raw_news(conn, articles) → 新規挿入 ID リスト
  - run_news_collection(conn, sources, known_codes) → {source: inserted_count}

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API のリフレッシュトークン。

- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード（execution 層で使用）。

- KABU_API_BASE_URL (任意)
  - kabuステーション API のベース URL。デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN (必須)
  - Slack 通知に使用するボットトークン。

- SLACK_CHANNEL_ID (必須)
  - 通知先チャネル ID。

- DUCKDB_PATH (任意)
  - DuckDB ファイルパスのデフォルト（settings.duckdb_path）。デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)
  - 監視用途の SQLite パス（settings.sqlite_path）。デフォルト: data/monitoring.db

- KABUSYS_ENV (任意)
  - environment: development | paper_trading | live（大文字・小文字は考慮）。デフォルト: development

- LOG_LEVEL (任意)
  - ログレベル。デフォルト: INFO

- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意)
  - 値が設定されていれば .env 自動ロードを無効化（テスト用途等）。

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - stats.py
      - features.py
      - calendar_management.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/  (モジュール群は README で言及されているがコードベースに応じて追加)
- pyproject.toml / setup.cfg / requirements.txt （プロジェクトに合わせて配置）

上記は主なファイルを抜粋した構成です。実際のリポジトリには追加のモジュールやドキュメントが含まれる可能性があります。

---

## 注意事項 / 運用上のヒント

- データの取得・発注には外部 API 認証情報が必要です。開発・検証は paper_trading モードで行ってください（settings.is_paper が True）。
- 自動化ジョブ（ETL / calendar_update_job 等）は cron / CI ワーカーで定期実行することを想定しています。実稼働（live）ではリスク管理・二重発注防止ロジックを十分に実装してください。
- NewsCollector は外部ネットワークアクセスを行います。内部ネットワークへのリダイレクトや大容量レスポンス等の対策を実装済みですが、運用環境での検証を行ってください。
- DuckDB ファイルは定期的にバックアップしてください。監査ログは基本的に削除しない前提になっています。

---

もし README に追加したい操作例（cron 例、Dockerfile、CI 構成、より詳細な .env.example 等）があれば教えてください。必要に応じて追記します。