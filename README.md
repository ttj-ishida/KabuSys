# KabuSys

日本株向けの自動売買データ基盤 / ETL ライブラリです。  
J-Quants API や RSS ニュースを取得して DuckDB に格納し、品質チェック・カレンダー管理・監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を主目的とした Python パッケージです。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制御・自動トークンリフレッシュ・リトライ付き）
- RSS ニュース収集と銘柄コード抽出（SSRF 対策・XML セキュリティ・サイズ制限）
- DuckDB による階層化されたデータスキーマ（Raw / Processed / Feature / Execution）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）

設計上、冪等性・トレーサビリティ・外部 API の安定性（レート制御やリトライ）・セキュリティ（SSRF/ZIP/XML）に重点を置いています。

---

## 主な機能一覧

- J-Quants クライアント
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - レート制限（120 req/min）固定間隔スロットリング
  - 指数バックオフによるリトライ（408/429/5xx）
  - 401受信時の自動トークンリフレッシュ（1回）

- データ永続化（DuckDB）
  - schema.init_schema() によるスキーマ初期化（Raw / Processed / Feature / Execution）
  - ON CONFLICT DO UPDATE / DO NOTHING を用いた冪等的保存関数（save_*）

- ETL パイプライン
  - 差分更新（DB 上の最終取得日を基に新規範囲を算出）
  - バックフィル（既存データの数日前から再取得して API の後出し修正を吸収）
  - 品質チェック（欠損・重複・スパイク・日付不整合）を実行して結果を返却

- ニュース収集
  - RSS フィード取得（gzip 解凍・サイズ制限・defusedxml の利用）
  - URL 正規化（トラッキングパラメータ除去）→ SHA-256 ハッシュによる記事 ID 生成
  - SSRF 対策（スキーム検証、ホストがプライベートかどうかの判定、リダイレクト検査）
  - raw_news / news_symbols への冪等保存

- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day

- 監査ログ（audit）
  - signal_events, order_requests, executions などを用いたトレース可能な監査テーブル
  - 全ての TIMESTAMP を UTC で保存する実装を提供

---

## セットアップ手順

前提
- Python >= 3.10（型ヒントで PEP 604 の Union 型表現（A | B）などを使用）
- pip が利用可能

1. リポジトリをクローン（またはソースを取得）してパッケージをインストール

   pip install -e . などで開発インストールできます（setup/pyproject の設定に依存）。

2. 必要なライブラリ（例）

   pip install duckdb defusedxml

   - duckdb: データベース
   - defusedxml: 安全な XML パーサ

   実際のプロジェクトでは requirements.txt / pyproject.toml に依存関係を明記してください。

3. 環境変数（.env）を作成

   下記必須環境変数を設定してください（.env ファイルをプロジェクトルートに置くと自動読み込みされます）。
   自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   必須:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabu ステーション API のパスワード（使用する場合）
   - SLACK_BOT_TOKEN       : Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャネルID

   任意（デフォルトあり）:
   - KABUSYS_ENV           : development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL
   - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite（監視用）パス（デフォルト data/monitoring.db）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース初期化

   DuckDB にスキーマを作成します（親ディレクトリが無ければ自動作成されます）。

   Python から:
   ```
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

   監査ログ専用 DB を初期化する場合:
   ```
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主な利用例）

以下は最も基本的なワークフロー例です。

- 日次 ETL を実行して J-Quants からデータ取得・保存・品質チェックを行う

  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行し、銘柄紐付けを行う

  ```
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は適切な銘柄コードセット（例: ファイルや DB から読み出した set）
  known_codes = {"7203", "6758", "9432"}
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: 新規挿入件数}
  ```

- J-Quants から直接データを取得して保存する

  ```
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  id_token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  recs = fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
  saved = save_daily_quotes(conn, recs)
  ```

- 品質チェック単体実行

  ```
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

---

## 知っておくべき設計上の注意点 / セキュリティ

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。テストなどで自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API 呼び出しはモジュールレベルで ID トークンをキャッシュし、401 の場合に自動リフレッシュを試みます（1 回のみ）。リトライは 3 回まで、429 は Retry-After を尊重します。
- ニュース収集では SSRF 対策、受信サイズ上限、gzip 解凍後のサイズチェック、defusedxml による XML の安全なパース等を実装しています。
- DuckDB の INSERT は冪等性を考慮して ON CONFLICT を使用する実装が多用されています。

---

## ディレクトリ構成

パッケージ内部（src/kabusys）の主要ファイル構成は以下の通り（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 -- 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント（取得・保存）
    - news_collector.py       -- RSS ニュース収集・保存
    - schema.py               -- DuckDB スキーマ定義と初期化
    - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  -- マーケットカレンダー管理
    - audit.py                -- 監査ログ（signal/order/execution）
    - quality.py              -- データ品質チェック
    - pipeline.py
  - strategy/
    - __init__.py             -- 戦略モジュール（将来的な拡張領域）
  - execution/
    - __init__.py             -- 発注/実行関連（将来的な拡張領域）
  - monitoring/
    - __init__.py             -- モニタリング関連（将来的な拡張領域）

---

## 開発 / 貢献

- コードは型ヒントを含み、テスト容易性を重視して設計されています（ID トークン注入、_urlopen の差替えなど）。
- 追加の機能（戦略、実行モジュール、Slack 通知、監視用 DB の連携など）は strategy/, execution/, monitoring/ に実装してください。

---

必要に応じて README に追記します。README に入れてほしい具体的なサンプルや、要求される実行フロー（例: cron での日次 ETL / 夜間の calendar_update_job など）があれば教えてください。