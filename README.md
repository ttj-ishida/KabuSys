# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
J-Quants API からの市場データ取得、DuckDB ベースのスキーマ管理、ETL パイプライン、ニュース収集、データ品質チェック、監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやデータ基盤向けに設計されたモジュール群です。主に以下の機能を備えます。

- J-Quants API を用いた株価（日次 OHLCV）・財務データ・市場カレンダーの取得（ページネーション・リトライ・トークン自動更新対応、レート制御）
- DuckDB を用いたスキーマ（Raw / Processed / Feature / Execution / Audit）定義と初期化
- ETL パイプライン（差分取得／バックフィル／品質チェック）
- RSS からのニュース収集と記事 → 銘柄紐付け（SSRF 対策・XML 攻撃対策・サイズ制限）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル → 発注 → 約定 のトレースを保つテーブル群）
- 環境変数による設定管理（.env の自動ロード機能あり）

設計のポイントとして、冪等性（ON CONFLICT を用いる）、トレーサビリティ（fetched_at / created_at / UTC 保存）、外部 API の堅牢性（再試行・バックオフ・レート制御）、およびセキュリティ（SSRF/XML Bomb 対策）に重きを置いています。

---

## 機能一覧

- data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
  - レート制御・リトライ・トークン自動リフレッシュ・fetched_at 記録
- data.schema
  - DuckDB のスキーマ定義（raw, processed, feature, execution 層）と init_schema / get_connection
- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl（差分取得・バックフィル・品質チェック）
- data.news_collector
  - fetch_rss / save_raw_news / save_news_symbols / run_news_collection
  - URL 正規化、トラッキングパラメータ除去、SSRF/リダイレクト検査、gzip サイズ制限、XML パース保護
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - QualityIssue を返して呼び出し元が対応を決定
- data.audit
  - 監査用テーブルと初期化（init_audit_schema / init_audit_db）
- config
  - 環境変数の読み込み（.env/.env.local 自動ロード）、必須変数チェック、設定オブジェクト settings
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

前提:
- Python 3.10 以上（型記法や | ユニオンを使用）
- Git リポジトリのルートに `.env` / `pyproject.toml` 等があることを想定

1. リポジトリをクローンして仮想環境を作る（任意）
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要なパッケージをインストール
   - 最低限必要な外部依存:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - （パッケージ化されている場合は）開発環境としてインストール:
     ```
     pip install -e .
     ```

3. 環境変数設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと自動で読み込まれます。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合（必須となっているプロパティあり）
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル
     - KABU_API_PASSWORD: kabuステーション等を使う場合
   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 sqlite（デフォルト: data/monitoring.db）

   例 `.env`（最低限 JQUANTS_REFRESH_TOKEN を設定）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. DB スキーマ初期化
   - Python REPL やスクリプトで DuckDB を初期化します（ファイル DB または ":memory:"）。
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # または init_schema(":memory:")
   ```

---

## 使い方（主要な利用例）

- DuckDB スキーマ初期化（上と同様）
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- 個別 ETL ジョブ
  ```python
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  # 各関数は (fetched_count, saved_count) を返します
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- ニュース収集
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 有効銘柄コード集合（抽出用）
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存数}
  ```

- J-Quants API を直接利用（トークン取得）
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を利用
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))
  ```

- 品質チェックの実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意:
- J-Quants の API レート制限（120 req/min）を内部で尊重しています。
- トークン期限切れ（401）時は自動でリフレッシュし、1 回だけリトライします。
- news_collector は SSRF 対策や XML 攻撃対策、gzip サイズ制限を組み込んでいます。

---

## ディレクトリ構成

（主要ファイルのみを抜粋）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / 設定管理（.env の自動ロード含む）
  - data/
    - __init__.py
    - schema.py            — DuckDB スキーマ定義と init_schema / get_connection
    - jquants_client.py    — J-Quants API クライアント（取得＋保存）
    - pipeline.py          — ETL パイプライン（差分取得 / backfill / 品質チェック）
    - news_collector.py    — RSS ニュース収集 / 保存 / 銘柄抽出
    - quality.py           — データ品質チェック
    - audit.py             — 監査ログ（signal / order_request / executions テーブル）
    - audit.py             — 監査ログ初期化用（注: 上記と併記）
    - pipeline.py
  - strategy/
    - __init__.py          — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py          — 発注・ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py          — 監視・メトリクス（拡張ポイント）

- pyproject.toml（想定）
- .env, .env.local（ユーザ作成想定）

各モジュールは拡張・差し替えが容易に設計されています。たとえば、news_collector._urlopen をテスト用にモックして外部通信を抑制できます。

---

## 注意点・運用上のヒント

- settings は必須の環境変数が未設定の場合にエラーを投げます。開発時は .env を用意してください。
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（ユニットテストなどで便利）。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作成されます。複数プロセスで同一ファイルにアクセスする設計上の注意が必要です（運用ポリシーに応じて DB 管理を行ってください）。
- J-Quants のレートとリトライポリシーは jquants_client 内で制御されていますが、大量取得時は API 利用規約に従ってください。

---

もし README に環境変数のテンプレート（.env.example）や起動スクリプト（例: run_etl.py）の追加を希望される場合は、その雛形を作成します。