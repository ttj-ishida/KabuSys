# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム基盤ライブラリです。  
データ収集（J-Quants / RSS）、ETL パイプライン、データ品質チェック、監査ログ（発注 → 約定のトレース）など、アルゴリズム取引に必要な基盤機能を備えています。

バージョン: 0.1.0

---

## 概要

主な責務は以下のとおりです。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存
- RSS フィードからニュースを収集し記事と銘柄コードを紐付けて保存
- ETL（差分取得・バックフィル）を行う日次パイプライン
- データ品質チェック（欠損・スパイク・重複・日付不整合など）
- 監査ログ（signal → order_request → executions）のスキーマと初期化ロジック
- カレンダー管理（営業日判定、前後営業日の検索など）

設計上の特徴：
- API レート制限遵守（J-Quants: 120 req/min）
- リトライ（指数バックオフ）とトークン自動リフレッシュ
- DuckDB への挿入は冪等性を保つ（ON CONFLICT）
- セキュリティ考慮（RSS の SSRF 対策、defusedxml の利用、レスポンスサイズ制限）

---

## 機能一覧

- 環境設定読み込み（.env / .env.local / OS環境変数、オートロード有効）
- J-Quants クライアント（認証、日足・財務・カレンダー取得、DuckDB への保存）
- ニュース収集（RSS -> 前処理 -> ID 生成 -> DuckDB 保存 -> 銘柄抽出）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit）
- ETL パイプライン（差分取得、バックフィル、品質チェックの統合）
- マーケットカレンダー管理（営業日判定、次/前営業日検索、夜間更新ジョブ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査テーブル（signal_events, order_requests, executions）の初期化

主要モジュール：
- kabusys.config: 環境変数 / 設定
- kabusys.data.jquants_client: J-Quants API クライアント
- kabusys.data.news_collector: RSS 収集
- kabusys.data.schema: DuckDB スキーマ初期化
- kabusys.data.pipeline: ETL パイプライン
- kabusys.data.calendar_management: カレンダー処理
- kabusys.data.quality: 品質チェック
- kabusys.data.audit: 監査ログ初期化
- kabusys.strategy / kabusys.execution / kabusys.monitoring: 拡張用プレースホルダ

---

## 前提条件

- Python 3.10+
- 必要な Python パッケージ（最低限）:
  - duckdb
  - defusedxml

（プロジェクトに応じて他の依存が追加される場合があります）

---

## セットアップ手順

1. リポジトリをクローン / コピーして作業ディレクトリに移動。

2. 仮想環境を作成・有効化（推奨）
   - Unix/macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```

   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）

4. 環境変数を準備
   - プロジェクトルートに `.env` または `.env.local` を作成できます（自動ロードあり）。
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（Settings 参照）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (省略可、デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (省略可、デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live、デフォルト: development)
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL、デフォルト: INFO)

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベーススキーマの初期化（DuckDB）
   - Python インタラクティブまたはスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # パスは設定に合わせて変更
     conn.close()
     ```

6. 監査ログ用スキーマ初期化（任意）
   - 監査テーブルを既存の DuckDB 接続に追加する:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.data.audit import init_audit_schema
     conn = init_schema("data/kabusys.duckdb")
     init_audit_schema(conn)
     conn.close()
     ```
   - または専用 DB を作る:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     conn.close()
     ```

---

## 使い方（基本例）

以下はライブラリをプログラムから利用するための例です。

- J-Quants トークン取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使って取得
  ```

- 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")  # なければ作成
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  conn.close()
  ```

- RSS ニュース収集（既存 DuckDB 接続を渡す）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: saved_count}
  conn.close()
  ```

- 市場カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  conn.close()
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data.quality import run_all_checks
  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  conn.close()
  ```

注意:
- jquants_client は API レート制限・リトライ・401 自動リフレッシュを組み込んでいます。テスト時は id_token を引数で注入できます。
- news_collector は defusedxml を使用し、SSRF 対策やレスポンスサイズ制限を行っています。

---

## 実行時の設定ロード（挙動）

kabusys.config は起動時に自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（OS環境変数が優先）。  
自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

読み込み優先順位:
1. OS 環境変数
2. .env.local（存在すれば .env の設定を上書き）
3. .env

---

## ディレクトリ構成

主要ファイル/モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数・設定管理
  - execution/__init__.py           -- 発注/ブローカー連携用プレースホルダ
  - strategy/__init__.py            -- 戦略モジュール用プレースホルダ
  - monitoring/__init__.py          -- 監視用プレースホルダ
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（取得・保存）
    - news_collector.py             -- RSS ニュース収集・保存・銘柄抽出
    - schema.py                     -- DuckDB スキーマ定義・初期化
    - pipeline.py                   -- ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py        -- マーケットカレンダー管理
    - audit.py                      -- 監査ログスキーマ初期化
    - quality.py                    -- データ品質チェック

この README はパッケージルートに配置する想定です。実際のリポジトリでは tests / docs / examples 等の追加ディレクトリがある場合があります。

---

## 開発時のヒント

- テストや CI で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のパスは Settings.duckdb_path によって管理されるため、環境変数 `DUCKDB_PATH` を設定して複数環境で切り替えられます。
- ログレベルは `LOG_LEVEL` で制御できます（DEBUG/INFO/...）。
- news_collector のテスト時は `_urlopen` をモックして外部通信を差し替える設計です。

---

## ライセンス / 貢献

本リポジトリにはライセンスファイルが含まれていません。利用・配布する際はプロジェクトのライセンス方針に従ってください。  
バグ報告や機能提案、プルリクエストは歓迎します。

---

必要であれば README にサンプル .env.example、より詳しい API 使用例、運用手順（cron・Airflow 連携例）、監視/アラート設計などを追加できます。どの項目を拡張するか指示してください。