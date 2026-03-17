# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ）  
データ収集・ETL・品質チェック・監査ログ・カレンダー管理など、戦略実行に必要な基盤機能を提供します。

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの市場データ（株価日足 / 財務 / カレンダー）の取得と DuckDB への保存
- RSS を使ったニュース収集と銘柄紐付け
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- JPX マーケットカレンダー管理（営業日判定、next/prev 等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ定義

設計上の特徴：
- API レート制御・リトライ・トークン自動更新を備えた J-Quants クライアント
- DuckDB を用いた冪等性のある保存（ON CONFLICT での UPDATE / DO NOTHING）
- RSS 取得時の SSRF/ZIP bomb 対策・トラッキングパラメータ除去
- 品質チェックは Fail-Fast とせず検出結果を収集して呼び出し元が対処可能にする

---

## 主な機能一覧

- J-Quants クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーを取得
  - レートリミット（120 req/min）の固定間隔スロットリング
  - 指数バックオフによるリトライ（408/429/5xx）、401 時のリフレッシュ対応
  - fetched_at による取得時刻の記録（Look-ahead 防止）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義、監査ログ用スキーマの初期化
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（複数チェックをまとめて実行）
  - run_daily_etl による日次実行エントリポイント
- ニュース収集
  - RSS 取得、前処理、ID（正規化 URL の SHA-256 前半）、raw_news への冪等保存
  - 銘柄コード抽出と news_symbols 紐付け
  - SSRF / 受信サイズ上限 / gzip 解凍後サイズチェック 等の安全対策
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間更新とバックフィル
- データ品質チェック
  - 欠損、スパイク、重複、将来日付や非営業日の検出
  - QualityIssue 型のリストで詳細を返す
- 監査ログ（audit）
  - signal_events, order_requests, executions 等で完全なトレーサビリティを確保

---

## 前提（Prerequisites）

- Python 3.10 以上（型注釈の `X | Y` を利用）
- pip
- 必要なパッケージ（最低限）:
  - duckdb
  - defusedxml

（プロジェクトの pyproject.toml / requirements.txt がある場合はそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン／ワークディレクトリに移動して仮想環境を作成:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

2. 必要パッケージをインストール（例）:

   ```bash
   pip install duckdb defusedxml
   ```

   ※ 実際の依存はプロジェクトのパッケージ定義に合わせてください。

3. 環境変数の設定:
   - プロジェクトルートに `.env`（および必要に応じ `.env.local`）を置くと、自動で読み込まれます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。
   - 必要な環境変数（例）:

     ```
     JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
     KABU_API_PASSWORD=あなたの_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

   - `KABUSYS_ENV` の有効値: `development`, `paper_trading`, `live`
   - `LOG_LEVEL` の有効値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

4. データベーススキーマの初期化（例: DuckDB ファイルを作成）:

   Python REPL またはスクリプト内で:

   ```python
   from kabusys.data import schema

   conn = schema.init_schema("data/kabusys.duckdb")
   ```

   監査ログ専用 DB を別で作る場合:

   ```python
   from kabusys.data import audit

   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（簡易ガイド）

以下は代表的な操作例です。詳細は各モジュールの API を参照してください。

- J-Quants トークン取得（明示的に利用する場合）:

  ```python
  from kabusys.data.jquants_client import get_id_token

  id_token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
  ```

- 日次 ETL 実行（市場カレンダー更新 → 株価 → 財務 → 品質チェック）:

  ```python
  from kabusys.data import pipeline, schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 市場カレンダーの夜間更新ジョブ:

  ```python
  from kabusys.data import calendar_management, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved:", saved)
  ```

- RSS ニュース収集（既知銘柄セットを渡して銘柄紐付けする例）:

  ```python
  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- データ品質チェックの個別実行:

  ```python
  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注意:
- jquants_client は内部でレートリミット・リトライ・トークンリフレッシュを行います。テストで自動リトライを抑止するには id_token を明示的に渡すなどしてください。
- ニュース収集はネットワーク I/O を含みます。テスト時は _urlopen をモック可能です（fetch_rss の設計に基づく）。

---

## ディレクトリ構成（主要ファイル）

下記はこの README に基づくコードベースの主要なファイル一覧と説明です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込みロジック、Settings クラス（各種設定値取得）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch/save 系）
    - news_collector.py
      - RSS 取得／正規化／raw_news 保存／銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - calendar_management.py
      - マーケットカレンダー更新、営業日判定ユーティリティ
    - audit.py
      - 監査ログ（signal_events / order_requests / executions 等）の DDL と初期化
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - strategy/
    - __init__.py
    - （戦略ロジックを置くモジュール群のためのパッケージ）
  - execution/
    - __init__.py
    - （発注・ブローカー連携ロジックを置くパッケージ）
  - monitoring/
    - __init__.py
    - （監視・メトリクス用のパッケージ）

---

## 設定メモ / 注意点

- 自動環境変数ロード
  - プロジェクトルートはこのファイルから .git または pyproject.toml を探索して特定します。CWD に依存しないためパッケージ配布後も動作します。
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB ファイルパスはデフォルトで `data/kabusys.duckdb`（Settings.duckdb_path）です。必要に応じて .env で `DUCKDB_PATH` を指定してください。
- `KABUSYS_ENV` の値により動作モード（development / paper_trading / live）を区別できます。live モードでは実際の発注を行う前に特別な安全対策を追加することを推奨します。

---

## よくある操作

- スキーマの初期化（新規セットアップ時）
  - schema.init_schema("path/to/db")
  - audit.init_audit_db("path/to/audit_db")（監査ログ専用 DB を使用する場合）

- 日次バッチのスケジューリング
  - run_daily_etl() を cron / Airflow 等から起動して運用する想定です。実行結果は ETLResult として戻るため、監査ログや Slack 通知に流し込むことができます。

---

## 貢献・連絡

- Issue / Pull Request を歓迎します。  
- 重要な変更（DB スキーマ変更・互換性に影響する仕様）はドキュメント・マイグレーション手順を同梱してください。

---

README はここまでです。必要であれば、README に含めるサンプル .env.example、より詳細な API リファレンス、運用手順（バックアップ・復元・移行）やテスト方法を追加します。どの内容を補足しましょうか？