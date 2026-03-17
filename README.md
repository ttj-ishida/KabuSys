# KabuSys

日本株向け自動売買／データプラットフォームのライブラリ群です。  
J-Quants / kabuステーション 等の外部 API から市場データを収集・永続化し、品質チェックや監査ログ、ニュース収集、ETL パイプラインを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（サンプル）
- 環境変数一覧
- ディレクトリ構成
- 実装上の注意事項

---

## プロジェクト概要

KabuSys は以下の目的で設計されたモジュール群です。

- J-Quants API から株価（日足：OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得して DuckDB に保存する。
- RSS フィードからニュース記事を収集し前処理して保存、銘柄コードと紐付ける。
- データ品質チェック（欠損、重複、スパイク、日付不整合）を実行する。
- 市場カレンダーの営業日判定や翌営業日／前営業日取得を提供する。
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマを提供する。
- ETL パイプライン（差分取得／バックフィル／品質チェック）を提供する。

設計上のポイント：
- API 呼び出しはレートリミット（120 req/min）や再試行（指数バックオフ、401 の場合はトークン自動更新）を扱う。
- データの取得時間（fetched_at）を UTC で記録して Look-ahead bias を防ぐ。
- DuckDB 上の保存は冪等（ON CONFLICT）を採用。
- ニュース取得は SSRF や XML Bomb 対策を実装。

---

## 主な機能一覧

- data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - レート制御・リトライ・トークン自動リフレッシュを含む HTTP クライアント

- data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - extract_stock_codes(text, known_codes)
  - RSS の前処理（URL 除去、空白正規化）・URL 正規化（utm 等除去）・SSRF 対策

- data.schema
  - init_schema(db_path)  // DuckDB の初期スキーマ作成（Raw / Processed / Feature / Execution レイヤ）
  - get_connection(db_path)

- data.pipeline
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(...)  // 日次 ETL の高レベル関数

- data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - is_sq_day(conn, d)
  - calendar_update_job(conn, lookahead_days=90)

- data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - 個別チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency

- data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

- config
  - settings: 環境変数から設定を読み込み（自動ロード機能・.env サポート）

---

## セットアップ手順

※ プロジェクト全体のインストール方法はお使いの環境に合わせてください。以下は一般的な手順例です。

1. Python 環境を作成（推奨: venv / pyenv）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール  
   （実際の requirements.txt / pyproject.toml に合わせてください。ここでは概念的に示します）
   ```
   pip install duckdb defusedxml
   ```

3. 環境変数の設定  
   リポジトリルートに `.env`（あるいは `.env.local`）を置けば、`kabusys.config` が自動で読み込みます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

   必要な環境変数の例（値は置き換えてください）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルト有）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb     # 省略可（デフォルト）
   SQLITE_PATH=data/monitoring.db      # 省略可（デフォルト）
   KABUSYS_ENV=development             # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   Python REPL やスクリプトで：
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
   ```

5. 監査ログ（audit）を追加したい場合：
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)  # conn は init_schema の返り値
   ```

---

## 使い方（代表的なサンプル）

- 日次 ETL を実行する（シンプル）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 日次 ETL を特定日で・トークン注入して実行
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(":memory:")
  # id_token をテスト用に注入可能
  res = run_daily_etl(conn, target_date=date(2024, 1, 10), id_token="dummy_token")
  ```

- ニュース収集ジョブを走らせる
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)
  ```

- カレンダー更新ジョブ
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved={saved}")
  ```

- 監査 DB（別 DB）を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- 品質チェックを実行する
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

---

## 環境変数一覧

主に以下の環境変数が参照されます（説明とデフォルト）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token に使用。

- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード。

- KABU_API_BASE_URL (任意)
  - kabuステーション API のベース URL。デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN (必須)
  - Slack 通知に使用するボットトークン。

- SLACK_CHANNEL_ID (必須)
  - Slack 通知先チャネル ID。

- DUCKDB_PATH (任意)
  - DuckDB データベースファイルパス。デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)
  - モニタリング用 SQLite パス。デフォルト: data/monitoring.db

- KABUSYS_ENV (任意)
  - 動作モード。development / paper_trading / live（デフォルト: development）

- LOG_LEVEL (任意)
  - ログレベル。DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、config の .env 自動ロードを無効化します（テスト向け）。

config モジュールは、プロジェクトルート（.git または pyproject.toml を起点）から `.env` → `.env.local` の順に読み込みます。OS 環境変数は上書きされません（ただし .env.local は override=True のため既存非保護環境変数を上書きできます）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py               -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py             -- DuckDB スキーマ定義・init
    - jquants_client.py     -- J-Quants API クライアント（取得・保存）
    - pipeline.py           -- ETL パイプライン（差分更新・日次 ETL）
    - calendar_management.py-- 市場カレンダーの判定・更新ジョブ
    - news_collector.py     -- RSS 収集・保存・銘柄抽出
    - quality.py            -- データ品質チェック
    - audit.py              -- 監査ログスキーマ（signal/order_request/execution）
  - strategy/
    - __init__.py           -- 戦略関連のエントリ（拡張ポイント）
  - execution/
    - __init__.py           -- 発注・執行関連（拡張ポイント）
  - monitoring/
    - __init__.py           -- モニタリング関連（拡張ポイント）

---

## 実装上の注意事項 / ベストプラクティス

- API レート制御
  - J-Quants へのリクエストはモジュール内で 120 req/min に制御されますが、外部の並列処理を行う場合は更に注意してください。

- 認証トークン
  - get_id_token はリフレッシュトークンから id_token を取得し、401 時の自動リフレッシュを備えています。テストでは id_token を外部から注入することで再現性を確保できます。

- DuckDB スキーマ
  - init_schema は冪等的にテーブルを作成します。運用では初回のみ init_schema を実行し、以降は get_connection で接続してください。

- ニュース収集のセキュリティ
  - RSS 取得ではスキーム検証（http/https のみ）、リダイレクト時のプライベートアドレスブロック、受信バイト上限、defusedxml による XML パース保護を行っています。

- 品質チェック
  - run_all_checks は fail-fast ではなく全チェックを行い、検出結果を呼び出し側に返します。呼び出し側で重大度に応じた対応を決定してください。

- テスト
  - ネットワーク呼び出しを含む関数（_jquants_client._request、news_collector._urlopen など）はモックしやすい設計になっています。CI ではこれらをモックして単体テストを行ってください。

---

必要に応じて README を拡張（CLI 実行例、Docker 化手順、CI 設定、より詳細な API リファレンス）できます。追加で記載して欲しい内容があれば教えてください。