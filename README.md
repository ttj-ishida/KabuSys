# KabuSys

日本株自動売買プラットフォーム向けのコアライブラリ群です。  
データ取得（J-Quants）、ETLパイプライン、ニュース収集、品質チェック、DuckDB スキーマ定義、監査（オーディット）などの機能を提供します。

## プロジェクト概要
KabuSys は日本株の自動売買システムに必要なデータ基盤と運用用ユーティリティを提供する Python パッケージです。主に以下の目的を想定しています。

- J-Quants API からの株価・財務・カレンダー取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いた永続化（Raw / Processed / Feature / Execution 層）
- RSS ベースのニュース収集と銘柄抽出（SSRF／XML攻撃対策、トラッキングパラメータ除去）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定・次/前営業日の取得）
- 監査ログ用スキーマ（シグナル→発注→約定までトレース可能）

## 主な機能一覧
- J-Quants API クライアント（jquants_client）
  - 株価日足、財務データ、JPX マーケットカレンダー取得
  - レートリミット遵守（120 req/min）、指数バックオフ、401 時トークン自動リフレッシュ
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）
- ETL パイプライン（data.pipeline）
  - 差分更新、バックフィル、品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次 ETL のエントリポイント run_daily_etl
- ニュース収集（data.news_collector）
  - RSS 取得、テキスト前処理、記事ID生成（正規化URL の SHA-256）、DB 保存（冪等）
  - SSRF 対策、XML デフューズ、受信サイズ制限
- スキーマ定義・初期化（data.schema）
  - Raw / Processed / Feature / Execution 層の DuckDB テーブル定義
  - init_schema(), get_connection()
- マーケットカレンダー管理（data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 品質チェック（data.quality）
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- 監査ログ（data.audit）
  - signal_events / order_requests / executions テーブルの初期化と index 作成

## 必要条件
- Python 3.10 以上（型注釈で | 記法を使用）
- 依存ライブラリ（最低限）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS ソース など）

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

## セットアップ手順

1. リポジトリをクローンして開発環境を準備します（例）:

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   # 開発インストール（pyproject.toml / setup.py があれば）
   # pip install -e .
   ```

2. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると、自動的に読み込まれます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みは無効化されます）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注等で使用）
     - SLACK_BOT_TOKEN — Slack 通知用トークン
     - SLACK_CHANNEL_ID — Slack チャネル ID
   - 任意（デフォルトあり）:
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
     - LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）

   .env の例（参考）:
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

3. DuckDB スキーマ初期化
   - 初回はスキーマを作成します。以下は Python からの例:

   ```python
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   ```

   - 監査ログ専用スキーマを追加する場合:

   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

## 使い方（代表的な例）

- 日次 ETL を実行（市場カレンダー、株価、財務、品質チェック）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

  run_daily_etl は ETLResult を返します。ETLResult.has_errors や has_quality_errors で状態判定ができます。

- 個別 ETL ジョブ（株価のみ差分取得）:

  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_prices_etl

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched}, saved={saved}")
  ```

- RSS ニュース収集と保存:

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema("data/kabusys.duckdb")
  # known_codes が与えられると記事→銘柄紐付けを行う
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- マーケットカレンダーの夜間更新ジョブ:

  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn, lookahead_days=90)
  print(f"calendar saved={saved}")
  ```

## ディレクトリ構成
（src 配下を示します）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス（設定アクセス）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、取得関数（fetch_daily_quotes 等）、保存関数（save_*）
    - news_collector.py
      - RSS 取得・前処理・保存、銘柄抽出
    - schema.py
      - DuckDB スキーマ DDL と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（差分取得、バックフィル、品質チェック、run_daily_etl）
    - calendar_management.py
      - 営業日判定や calendar_update_job
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）の DDL と初期化
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py  （戦略モジュールを配置）
  - execution/
    - __init__.py  （発注・ブローカー連携を配置）
  - monitoring/
    - __init__.py  （監視/アラート関連を配置）

## 設計上の注意点・運用メモ
- J-Quants のレート制限（120 req/min）を守るよう RateLimiter が組み込まれています。大量取得時は注意してください。
- jquants_client は 401 を受けたときに自動的にリフレッシュを試みます（1 回）。get_id_token() により明示的にトークンを取得できます。
- news_collector は SSRF、XML Bomb、GZIP 解凍後サイズ上限など各種防御処理を行っています。外部からの URL を扱う際の安全対策を参照してください。
- DuckDB のファイルパスの位置（デフォルト data/kabusys.duckdb）やバックアップポリシーは運用者側で管理してください。
- 開発・テスト時に自動 .env 読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## テスト・開発
- 主要な関数は id_token を引数で注入可能になっているため、モックトークンやモック HTTP レスポンスで単体テストが容易です。
- news_collector._urlopen や jquants_client の HTTP 呼び出しをモックすることで外部アクセスを伴わないテストが可能です。

---

ご不明な点や追加してほしい利用例（例: 発注フロー、Slack 通知連携サンプル、CI 用の DB 初期化スクリプト等）があれば教えてください。README を拡張して、さらに具体的な使用方法や運用手順を追加します。