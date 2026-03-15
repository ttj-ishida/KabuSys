# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（骨組み）。  
市場データ取得、DuckDB スキーマ定義、監査ログなど、アルゴリズム取引システムの基盤機能を提供します。

---

## 概要

KabuSys は次の目的で設計された軽量ライブラリです。

- J-Quants API からの市場データ取得（株価日足、財務データ、マーケットカレンダー）
- DuckDB を用いた永続化スキーマ（Raw / Processed / Feature / Execution 層）
- 発注・約定の監査ログ（order_request → execution のトレーサビリティ確保）
- 環境変数による設定管理（.env/.env.local の自動読み込みに対応）

設計上の主なポイント：
- API レート制限（120 req/min）を尊重する RateLimiter 実装
- リトライ・指数バックオフ、401 時の自動トークンリフレッシュ
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を防止
- すべてのタイムスタンプは UTC を想定

---

## 機能一覧

- 環境設定管理（kabusys.config.Settings）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（無効化可能）
  - 必須環境変数の取得と検証
- J-Quants API クライアント（kabusys.data.jquants_client）
  - get_id_token（リフレッシュトークン → idToken）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レート制御、リトライ、ページネーション対応
  - DuckDB に保存する save_* 関数（raw_prices, raw_financials, market_calendar）
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス作成、init_schema / get_connection
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブルとインデックス
  - init_audit_schema / init_audit_db

---

## 動作要件

- Python 3.10 以上（Union 型エイリアスや | アノテーションを使用）
- 依存ライブラリ（最低限）:
  - duckdb
- ネットワーク: J-Quants API（トークンが必要）
- （発注連携を行う場合）kabuステーション等のブローカー API 設定

インストール例（仮）:
```bash
python -m pip install duckdb
# そのほかの依存はプロジェクトに応じて追加
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <this-repo>
   cd <this-repo>
   ```

2. 必要な Python パッケージをインストール
   ```bash
   python -m pip install -r requirements.txt
   ```
   （requirements.txt が無い場合は少なくとも duckdb をインストールしてください）

3. 環境変数の準備
   プロジェクトルートに `.env`（および任意で `.env.local`）を用意すると、自動で読み込まれます。
   読み込み順: OS 環境 > .env.local > .env

   必須（代表）環境変数例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id
   ```

   任意（デフォルトあり）:
   ```
   KABUSYS_ENV=development          # development | paper_trading | live
   LOG_LEVEL=INFO                  # DEBUG|INFO|WARNING|ERROR|CRITICAL
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   ```

   自動 .env 読み込みを無効化したい場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

4. DuckDB の初期化（例）
   Python REPL またはスクリプトで:
   ```python
   from kabusys.config import settings
   from kabusys.data import schema, audit
   # settings.duckdb_path は .env の DUCKDB_PATH またはデフォルトを返す Path
   conn = schema.init_schema(settings.duckdb_path)
   # 監査ログテーブルを追加したい場合
   audit.init_audit_schema(conn)
   ```

---

## 使い方（基本例）

- J-Quants トークン取得:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用して取得
  ```

- 株価日足を取得して DuckDB に保存:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)
  records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  saved = save_daily_quotes(conn, records)
  print(f"{saved} 件保存しました")
  ```

- 財務データ / カレンダーの取得・保存:
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar

- 監査ログ（発注フロー）初期化（別 DB に切り離す場合）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/kabusys_audit.duckdb")
  ```

注意点:
- jquants_client の HTTP リクエストは内部でレートリミッタ・リトライを行いますが、アプリケーション側でも過剰なループ呼び出しを避けてください。
- save_* 系関数は冪等（ON CONFLICT DO UPDATE）なので、同一のデータを複数回保存しても上書きされます。
- ログ出力レベルは環境変数 LOG_LEVEL で制御されます。

---

## ディレクトリ構成

以下は主要ファイルの一覧と役割（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得/保存ロジック、レート制御、リトライ）
    - schema.py
      - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）定義と初期化
    - monitoring.db（デフォルトのパスは設定により変更可）
  - strategy/
    - __init__.py（戦略実装用のプレースホルダ）
  - execution/
    - __init__.py（発注実装用のプレースホルダ）
  - monitoring/
    - __init__.py（監視用のプレースホルダ）

（上記はリポジトリの現状コードベースに基づく概観です。実運用では strategy / execution / monitoring に具体的な実装を追加していきます。）

---

## 運用上の注意

- KABUSYS_ENV は以下のいずれかである必要があります:
  - development, paper_trading, live
  - is_live / is_paper / is_dev プロパティで判定できます
- J-Quants のレート制限は 120 req/min です。jquants_client はこれに従いますが、外部の呼び出しスケジュールも合わせて調整してください。
- 監査ログは削除しない前提で設計されています（ON DELETE RESTRICT）。監査データの保全ポリシーを検討してください。
- DuckDB ファイルの配置場所・バックアップについて運用ルールを定めてください（デフォルト: data/kabusys.duckdb）。

---

必要に応じて README を拡張します。  
- 例: CI/CD での DB 初期化手順、Slack 通知連携のサンプル、具体的な戦略・発注フローの実装例など。必要なトピックを教えてください。