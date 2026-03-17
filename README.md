# KabuSys

日本株自動売買システム用ライブラリ（KabuSys）。J-Quants / RSS / kabuステーション 等からデータを取得・保存し、ETL・品質チェック・監査ログ・ニュース収集などの基盤機能を提供します。

---

## 概要

KabuSys は、以下を目的とした内部ライブラリ／モジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存
- RSS フィードからニュースを収集して DuckDB に保存し、銘柄コードと紐付け
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日の算出）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（シグナル→発注→約定のトレーサビリティ）  
- 環境変数による設定管理（.env 自動ロードをサポート）

設計上、API レート制限やリトライ、SSRF/XML 攻撃対策、冪等保存（ON CONFLICT）などの実運用上の考慮が組み込まれています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークン自動更新・DuckDB への保存）
  - news_collector: RSS 収集・前処理・記事ID生成（SHA-256ベース）・SSRF防止・DuckDB へ冪等保存
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 日次 ETL（差分取得、バックフィル、品質チェック）
  - calendar_management: 市場カレンダー管理・営業日判定・バッチ更新ジョブ
  - audit: 監査ログ（signal / order_request / executions）スキーマの初期化
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
- config:
  - 環境変数管理（.env 自動ロード、必須キー検査、KABUSYS_ENV 判定など）
- strategy/ execution/ monitoring/
  - 戦略・実行・監視用の空パッケージ（拡張ポイント）

---

## 要求環境（推奨）

- Python 3.9+
- 必要パッケージ（一例）
  - duckdb
  - defusedxml
  - その他標準ライブラリ（urllib, logging, gzip, hashlib, ipaddress 等）

推奨インストール例（仮の requirements）:

pip install duckdb defusedxml

（プロジェクト配布に requirements.txt/pyproject.toml があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン / 作業ディレクトリへ

2. 仮想環境の作成（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があれば pip install -e . / pip install -r requirements.txt）

4. 環境変数の設定
   ルートプロジェクトに `.env` / `.env.local` を配置すると、kabusys.config が自動でロードします（CWD ではなくパッケージ位置を基準にプロジェクトルートを判定します）。

   例（.env）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack (通知用)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # データベース
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 動作モード / ログ
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

   - 必須環境変数（Settings._require により ValueError を発生させる）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化できます（テスト用）

5. DuckDB スキーマ初期化（例）
   Python REPL やスクリプトで初期化します。

   ```
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（クイックスタート）

- DuckDB 初期化（1回だけ）
  ```
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ファイルと親ディレクトリを自動作成
  ```

- 日次 ETL（市場カレンダー→株価→財務→品質チェック）
  ```
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 引数省略で本日が対象日、id_tokenは自動取得
  print(result.to_dict())
  ```

- 部分実行（株価ETLのみ）
  ```
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- RSS ニュース収集（既定ソース）
  ```
  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, known_codes={"7203","6758"})  # known_codes を渡すと銘柄紐付けを実行
  print(results)
  ```

- J-Quants の id_token を直接取得（必要な場合）
  ```
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用
  ```

- 監査スキーマの初期化（audit テーブルを追加）
  ```
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  ```

- 自動 .env ロードを無効化して独自の環境設定を行う（テスト用）
  ```
  import os
  os.environ["KABUSYS_DISABLE_AUTO_ENV_LOAD"] = "1"
  ```

---

## 設定（環境変数一覧）

主な環境変数（Settings で参照）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — 動作モード
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

注意: 必須変数が未設定だと Settings のプロパティ参照時に ValueError が発生します。

---

## ディレクトリ構成

以下は主要なファイル / モジュールとその役割（プロジェクトの src/kabusys 配下）です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（自動 .env ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント。fetch_* / save_* 関数（株価・財務・カレンダー）
      - RateLimiter、トークンキャッシュ、リトライ・指数バックオフ、メモリ整形
    - news_collector.py
      - RSS 取得、前処理、ID 算出、SSRF/サイズ制限対策、DuckDB への保存 + 銘柄紐付け
    - schema.py
      - DuckDB の DDL 定義（Raw / Processed / Feature / Execution）と init_schema
    - pipeline.py
      - ETL（差分取得・バックフィル・品質チェック）の実装。run_daily_etl がエントリポイント
    - calendar_management.py
      - market_calendar 関連のユーティリティ（is_trading_day, next_trading_day, prev_trading_day 等）と calendar_update_job
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）DDL と初期化関数
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）と QualityIssue 型
  - strategy/
    - __init__.py  # 戦略実装置き場
  - execution/
    - __init__.py  # 発注実装置き場
  - monitoring/
    - __init__.py  # 監視・メトリクス置き場

---

## 開発・拡張メモ

- ETL・収集処理は冪等性（ON CONFLICT）を重視しているため、繰り返し実行しても重複しない設計です。
- jquants_client は 120 req/min のレート制限を遵守するようにスロットリングしています。
- news_collector は RSS の XML パースに defusedxml を使用して XML ボム等の攻撃に備えています。
- DB のタイムゾーンやタイムスタンプについては audit.init_audit_schema で UTC を設定しています（SET TimeZone='UTC'）。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にして .env の自動ロードを無効化できます。

---

README に記載のない詳細は各モジュールのドキュメント文字列（docstring）を参照してください。追加のセットアップファイル（requirements.txt、pyproject.toml、.env.example など）がある場合はそれに従ってください。必要であれば README を英語版や使用例を拡充して作成します。