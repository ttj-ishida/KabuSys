# KabuSys

日本株向け自動売買基盤（KabuSys）のリポジトリです。  
この README は、コードベースに含まれる主要モジュールの概要、機能、セットアップ方法、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は、日本株のデータ収集・整形・品質チェック・監査ログ・発注フローの基盤を提供するライブラリ／モジュール群です。  
主に以下を目的とします：

- J-Quants API を用いた株価日足・財務データ・市場カレンダーの取得（レート制限・自動リトライ対応）
- RSS フィードからのニュース収集と記事→銘柄の紐付け（SSRF 回避、サイズ上限、XML セキュリティ）
- DuckDB を用いた 3 層データレイヤ（Raw / Processed / Feature）と実行（Execution）層のスキーマ定義と初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（信号→発注→約定までのトレース可能なテーブル群）

設計上の特徴として、冪等性、トレーサビリティ、外部APIへの配慮（レート制限・トークン自動更新・リトライ）、およびセキュリティ対策（defusedxml、SSRF/プライベートIP回避、レスポンスサイズ制限）を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（株価日足・財務データ・市場カレンダー）
  - レート制御（120 req/min）、指数バックオフ再試行、401時のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- data/news_collector.py
  - RSS 取得・パース（defusedxml 使用）・前処理（URL除去、空白正規化）
  - 記事IDは正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策・受信サイズ上限・gzip 対応
  - raw_news / news_symbols への冪等保存（チャンク挿入、INSERT RETURNING）
- data/schema.py
  - DuckDB 用スキーマ（Raw / Processed / Feature / Execution）の DDL 定義
  - init_schema() による初期化とインデックス作成
- data/pipeline.py
  - 差分 ETL（市場カレンダー・株価・財務）と backfill、品質チェックの統合実行（run_daily_etl）
  - ETL 実行結果を表す ETLResult（品質問題やエラーの収集）
- data/quality.py
  - 欠損データ、スパイク（前日比閾値）、重複、日付整合性チェック
  - run_all_checks で一括実行し QualityIssue のリストを返却
- data/audit.py
  - 信号（signal_events）→発注要求（order_requests）→約定（executions）を追跡する監査テーブル
  - init_audit_schema() による追加初期化（UTCタイムゾーン enforced）
- config.py
  - 環境変数読み込み（.env / .env.local 自動ロード、プロジェクトルート検出）
  - 設定取得 API（Settings クラス）
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部で | 型を使用）
- DuckDB を利用するためネイティブ拡張の入手が必要（pip でインストール可能）

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）:

   ```bash
   git clone <repository-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install -e ".[dev]"   # setup に extras があれば使用。ない場合は下記依存を個別インストール
   ```

2. 必要な Python パッケージ（主なもの）:

   ```bash
   pip install duckdb defusedxml
   ```

   - 他に標準ライブラリ以外の依存があれば requirements.txt / pyproject.toml を参照してください。

3. 環境変数の準備:
   - プロジェクトルートに `.env` または `.env.local` を置くと自動でロードされます（ただし CI/テスト時は無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルトあり）:
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) (default: development)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) (default: INFO)
   - 自動 .env ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   例 `.env`（テンプレート）:

   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベースの初期化（DuckDB スキーマ作成）:

   Python REPL やスクリプトから:

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   # またはメモリ DB を使う場合
   # conn = init_schema(":memory:")
   ```

---

## 使い方（主要なユースケース）

- J-Quants の id_token を明示的に取得する:

  ```python
  from kabusys.data.jquants_client import get_id_token

  token = get_id_token()  # settings.jquants_refresh_token を使って取得
  ```

  - jquants_client はトークンをモジュールレベルでキャッシュし、401 で自動リフレッシュします。

- 日次 ETL を実行する（市場カレンダー、株価、財務、品質チェック）:

  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)  # 初回は必須
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

  - ETLResult オブジェクトには取得数・保存数・品質問題・エラーの要約が入ります。
  - pipeline は差分更新（DBにある最終日からの更新）と backfill（デフォルト 3 日）を行います。

- RSS ニュース収集を実行する:

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 保存件数}
  ```

  - fetch_rss は defusedxml を使用し、SSRF 対策やレスポンスサイズ上限チェックを行います。
  - save_raw_news は INSERT ... RETURNING を使って挿入された記事IDのみを返します。

- データ品質チェックを個別で実行する:

  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- 監査スキーマを初期化（既存の接続へ追加）:

  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  ```

---

## 参考 API / 実装ノート（運用者向け）

- jquants_client の振る舞い:
  - レート：120 req/min。モジュール内で固定間隔スロットリングを実装。
  - リトライ：408/429/5xx に対して指数バックオフで最大 3 回リトライ。429 時は Retry-After を優先。
  - 401：1 回だけトークンをリフレッシュしてリトライ（無限再帰防止）。
  - データ取得時に fetched_at（UTC）を記録して Look-ahead Bias を防止。
  - DuckDB 保存は冪等（ON CONFLICT）で上書き。

- news_collector のセキュリティ設計:
  - defusedxml を使用して XML Bomb 等から守る。
  - URL 正規化で utm_* 等のトラッキングパラメータを除去し、SHA-256 ハッシュで記事IDを生成。
  - リダイレクト先のスキームやホスト（プライベートIP）を検査して SSRF を防ぐ。
  - レスポンスは最大 10MB に制限。gzip 経由での Gzip bomb を考慮して解凍後のサイズも検査。

- スキーマ（DuckDB）:
  - Raw / Processed / Feature / Execution 層を定義。
  - Audit（監査）用のテーブル群は別途 init_audit_schema で追加。
  - 全テーブルは冪等的に作成（CREATE TABLE IF NOT EXISTS）。

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - quality.py
      - audit.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主な機能は data 以下に集約されています。strategy / execution / monitoring は将来的な戦略実装や発注連携のためのプレースホルダ（package 初期化ファイル）として存在します。

---

## テスト・開発時の便利なフラグ

- 自動 .env ロードの無効化（テストで環境を汚さないため）:

  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

- DB をメモリで使うと高速に単体テスト可能:

  ```python
  conn = init_schema(":memory:")
  ```

---

## 貢献 / 連絡

バグ報告や機能提案は Issue を立ててください。  
PR を送る際は、関連する単体テストと README の更新をお願いします。

---

以上が本リポジトリの基本的な README です。必要であれば、実運用向けのデプロイ手順（systemd / Docker / コンテナ化）、CI/CD ワークフロー、監視アラート設定、Slack通知の利用方法などの項目を追加できます。どの情報を優先して追記したいか教えてください。