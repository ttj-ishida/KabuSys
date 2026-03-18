# KabuSys

日本株自動売買システムのライブラリ群（KabuSys）。データ取得（J-Quants）、ETL パイプライン、ニュース収集、データ品質チェック、DuckDB スキーマ定義、監査ログ（発注〜約定のトレーサビリティ）を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株の自動売買基盤向けに設計されたコンポーネント群です。主な目的は次のとおりです。

- J-Quants API を用いた株価・財務・マーケットカレンダーの取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を利用した階層的なデータスキーマ（Raw / Processed / Feature / Execution / Audit）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS によるニュース収集と銘柄紐付け（SSRF 対策、トラッキング除去、重複排除）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）

設計上の特徴として、冪等性（ON CONFLICT）、Look-ahead バイアス防止のための fetched_at 記録、API レート制御、XML の安全パースなど多数の安全策を備えています。

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント
  - レートリミッティング（120 req/min）
  - リトライ（408/429/5xx）、401 での自動トークンリフレッシュ
  - fetch/save 関数（daily quotes, financial statements, market calendar）
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）

- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema(db_path) でテーブル・インデックスを作成

- data/pipeline.py
  - 日次 ETL（run_daily_etl）
  - 差分更新ロジック、バックフィル、品質チェック統合

- data/news_collector.py
  - RSS 取得（gzip 対応、受信サイズ上限）
  - URL 正規化・トラッキング除去・記事ID（SHA-256 先頭32文字）
  - SSRF対策（スキーム検証・プライベートIP拒否・リダイレクト検査）
  - DuckDB への冪等保存と銘柄紐付け

- data/calendar_management.py
  - market_calendar 管理、営業日判定、next/prev_trading_day、カレンダー更新ジョブ

- data/quality.py
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）
  - run_all_checks で一括実行

- data/audit.py
  - 監査ログテーブル（signal_events, order_requests, executions）と初期化ユーティリティ
  - init_audit_db(db_path) で監査用 DB を初期化

- config.py
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得ラッパ（settings オブジェクト）
  - KABUSYS_ENV / LOG_LEVEL などの検証ロジック

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の | や標準ライブラリの型ノーテーションを使用）
- Git リポジトリルートまたは pyproject.toml がプロジェクトルートにあることを想定

1. 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # mac/linux
   .venv\Scripts\activate     # Windows (PowerShell)
   ```

2. 必要なパッケージをインストール
   本リポジトリは最小限の外部依存として duckdb と defusedxml を使用します。必要に応じて他のパッケージ（例: requests など）を追加してください。
   ```bash
   pip install duckdb defusedxml
   ```

3. 環境変数の設定
   プロジェクトルートに `.env` または `.env.local` を作成して必要な環境変数を設定します。自動読み込み順は OS 環境変数 > .env.local > .env です。OS 環境を優先したい場合は `.env` を用意すれば OK。

   必須環境変数（ライブラリ内で _require によりチェックされます）
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API パスワード
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

   任意 / デフォルトあり:
   - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — SQLite 用パス（デフォルト: data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると自動 .env ロードを無効化（テスト用）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C1234567890
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベース初期化
   DuckDB スキーマを初期化します（ファイルパスは DUCKDB_PATH に合わせるか直接指定）。
   Python REPL、スクリプト、もしくは管理コマンドから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

   監査ログ専用 DB を別途作る場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   audit_conn.close()
   ```

---

## 使い方（サンプル）

ここでは代表的なユースケースの最小例を示します。

- 日次 ETL を実行してデータを取得・保存・品質チェックする
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # 初回: init_schema() を使ってファイル作成＆DDL 実行
  conn = init_schema("data/kabusys.duckdb")

  # 日次 ETL 実行（id_token を省略すると内部で settings 参照して自動取得）
  result = run_daily_etl(conn)
  print(result.to_dict())

  conn.close()
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "6501"}  # 事前に整備した有効銘柄コードセット
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)  # source_name -> 新規保存数
  conn.close()
  ```

- J-Quants から日足を個別取得して保存
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,1))
  saved = save_daily_quotes(conn, records)
  print("saved", saved)
  conn.close()
  ```

- 品質チェックを単体実行
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  conn.close()
  ```

- カレンダー関連ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  d = date(2025, 1, 1)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  conn.close()
  ```

---

## 重要な挙動・運用ノート

- .env 自動ロード
  - config.py はプロジェクトルート（.git または pyproject.toml）を基準に `.env` と `.env.local` を自動的に読み込みます。
  - 読み込み順: OS 環境変数（最優先） > .env.local (override=True) > .env (override=False)
  - テスト等で自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- トークン管理
  - J-Quants の id_token は内部でキャッシュされます。401 を受けた場合は自動でリフレッシュを試みます（1 回のみ）。
  - get_id_token へ直接 refresh_token を渡して呼び出すことも可能です。

- API レート制御とリトライ
  - jquants_client は 120 req/min のレート上限を守るために固定間隔のスロットリングを行います。
  - 408 / 429 / 5xx 系は指数バックオフで最大 3 回リトライします。429 の場合は Retry-After ヘッダを優先します。

- ニュース収集の安全性
  - defusedxml を用いた XML パース（XML Bomb 等の緩和）
  - リダイレクト先のスキーム・ホストを検査しプライベート IP へのアクセスを拒否（SSRF 対策）
  - レスポンスサイズを上限（10 MB）で制約、gzip 解凍後もチェック

- DuckDB スキーマ
  - init_schema は冪等でテーブル・インデックスを作成します。
  - audit 用スキーマは init_audit_db / init_audit_schema で追加可能。UTC タイムゾーンを固定します。

- 環境モード
  - settings.env により挙動を切り替えられます（development / paper_trading / live）。
  - settings.is_live / is_paper / is_dev を用いてアプリ側で振る舞いを分岐可能。

---

## ディレクトリ構成

リポジトリ内の主要ファイルと概要（src/kabusys を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py              — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py    — J-Quants API クライアント（fetch/save）
      - news_collector.py    — RSS ニュース収集と保存
      - schema.py            — DuckDB スキーマ定義・初期化
      - pipeline.py          — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py — カレンダー管理（営業日判定・更新ジョブ）
      - audit.py             — 監査ログ（signal/order/execution）初期化
      - quality.py           — データ品質チェック
    - strategy/
      - __init__.py          — 戦略関連（未実装のプレースホルダ）
    - execution/
      - __init__.py          — 発注実行関連（未実装のプレースホルダ）
    - monitoring/
      - __init__.py          — 監視関連（未実装のプレースホルダ）

---

## 開発者向けメモ

- 型ヒントと Python 3.10 の構文（|）を使用しているため、最低 Python 3.10 を想定しています。
- DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を直接渡す設計で、ユニットテストではインメモリ DB（":memory:"）を使えます。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、環境変数を明示的に注入してください。
- 外部 API 呼び出し部分（_urlopen や jquants_client._request 等）はモックを注入しやすい設計になっています。

---

必要に応じて README に追加したい項目（例: CI/テスト手順、デプロイ/運用手順、.env.example の雛形など）があれば教えてください。README をプロジェクト固有の運用フローに合わせてさらに充実させます。