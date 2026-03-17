# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（ライブラリ部分）。  
データ取得・ETL・品質チェック・ニュース収集・監査ログ等、データパイプラインと監査基盤を中心に実装されています。

---

## 概要

KabuSys は日本株の自動売買に必要なデータ基盤と補助機能群を提供する Python モジュール群です。主に以下を目的としています。

- J-Quants API からの市場データ（株価日足、財務情報、マーケットカレンダー）取得
- DuckDB を用いたスキーマ定義・永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、保存、品質チェック）
- RSS ベースのニュース収集と銘柄紐付け
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 環境変数による設定管理（.env 自動読み込み対応）

設計においては、API レート制限の遵守、リトライ・トークンリフレッシュ、冪等性（ON CONFLICT）や SSRF 対策など実運用を見据えた堅牢性を重視しています。

---

## 主な機能

- J-Quants API クライアント
  - get_id_token（リフレッシュトークンからIDトークン取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レート制限（120 req/min）とリトライ（指数バックオフ、401 リフレッシュ対応）
- DuckDB スキーマ管理
  - init_schema: Raw / Processed / Feature / Execution 層のテーブル作成
  - init_audit_schema / init_audit_db: 監査用テーブルの初期化
- ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl：日次一括 ETL + 品質チェック
  - 差分取得・バックフィル対応（最終取得日を元に自動判定）
- データ品質チェック
  - 欠損検出、主キー重複、スパイク検出（日次変化率が閾値超）
  - 未来日付や非営業日のデータ整合性チェック
- ニュース収集（RSS）
  - fetch_rss: RSS 取得・パース・前処理（URL除去、正規化）
  - save_raw_news / save_news_symbols: DuckDB への冪等保存と銘柄紐付け
  - SSRF 対策、応答サイズ制限、gzip 解凍上限など安全機能を実装
- 環境変数設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - Settings オブジェクト経由で設定取得（必須値は未設定時にエラー）

---

## 依存関係（主なもの）

- Python 3.9+（typing の機能を多用）
- duckdb
- defusedxml

（標準ライブラリで実装されている部分も多いです。実際のプロジェクトでは requirements.txt 等を用意してください。）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <your-repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   （例: duckdb, defusedxml）
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（デフォルト自動ロードは有効）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時など）。

   最低限必要な環境変数（設定オブジェクトで必須とされるもの）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   追加設定（任意/デフォルトあり）:
   - KABUSYS_ENV (development | paper_trading | live) - デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) - デフォルト: INFO
   - DUCKDB_PATH - デフォルト: data/kabusys.duckdb
   - SQLITE_PATH - デフォルト: data/monitoring.db

   .env の簡易例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要な操作例）

以下はインタラクティブに Python から操作する例です。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   # :memory: を渡すとインメモリ DB を使用
   ```

2. 日次 ETL を実行（J-Quants の ID トークンは内部キャッシュ/自動取得）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

   - run_daily_etl はカレンダー取得→株価→財務→品質チェックの順で実行します。
   - id_token を明示的に渡してテストすることも可能です（引数 id_token）。

3. ニュース収集ジョブ
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   # known_codes は銘柄抽出時に有効とする銘柄コード集合
   known_codes = {"7203", "6758", "9984"}
   stats = run_news_collection(conn, known_codes=known_codes)
   print(stats)  # {source_name: 新規保存数}
   ```

4. J-Quants API 直接呼び出し例
   ```python
   from kabusys.data import jquants_client as jq
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   # 例: 2024-01-01 から今日までの株価を取得して保存
   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date.today())
   saved = jq.save_daily_quotes(conn, records)
   ```

5. 監査ログ初期化（監査テーブル追加）
   ```python
   from kabusys.data.audit import init_audit_schema
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   init_audit_schema(conn)
   ```

---

## 設定と運用上の注意

- 環境変数は .env / .env.local をプロジェクトルートから自動読み込みします（ただしプロジェクトルートは .git または pyproject.toml を基準に探索）。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API はレート制限（120 req/min）に従う必要があります。本ライブラリは固定間隔の RateLimiter を実装していますが、上流からの多重並列呼び出しには注意してください。
- DuckDB への保存は ON CONFLICT を利用して冪等に行われます。外部システムから DB を直接操作する場合はスキーマ整合性に注意してください。
- ニュース収集では外部 URL を扱うため、SSRF 対策（ホストがプライベートかの検査やリダイレクト時の検査等）や最大受信バイト数制限を実装しています。

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主なモジュール構成は以下の通りです（src/kabusys）:

- __init__.py
- config.py
  - Settings（環境変数管理、自動 .env 読み込み）
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py
    - RSS 収集・前処理・DB 保存・銘柄抽出
  - pipeline.py
    - ETL パイプライン（差分取得、保存、品質チェック）
  - schema.py
    - DuckDB スキーマ DDL と init_schema / get_connection
  - audit.py
    - 監査ログ（signal_events, order_requests, executions）
  - quality.py
    - データ品質チェック（欠損・重複・スパイク・日付不整合）
- strategy/
  - __init__.py（戦略層のエントリ／将来実装）
- execution/
  - __init__.py（発注・ブローカー連携のエントリ／将来実装）
- monitoring/
  - __init__.py（監視・アラート関連／将来実装）

---

## 開発メモ / テスト時の利便性

- テスト時は DB をインメモリ ":memory:" で初期化して高速に回せます:
  ```python
  conn = init_schema(":memory:")
  ```
- 設定の自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
- news_collector._urlopen や jquants_client のネットワーク呼び出しは個別にモック可能な設計になっています（ユニットテスト容易性を考慮）。

---

この README はライブラリの利用開始と主要なワークフロー（DB 初期化 → 日次 ETL → ニュース収集 → 監査初期化）に必要な情報を中心にまとめています。  
より詳細な設計仕様（DataPlatform.md, DataSchema.md 等）や実運用向けのランブックは別途参照してください。