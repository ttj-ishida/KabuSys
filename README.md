# KabuSys

日本株向け自動売買プラットフォームの基盤ライブラリ。J-Quants からの市場データ取得、RSS ニュース収集、DuckDB ベースのデータスキーマ／ETL、データ品質チェック、監査ログ機能などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要となるデータ基盤とユーティリティ群を提供する Python パッケージです。主に次の責務を持ちます。

- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に保存
- RSS フィードからニュースを収集し正規化して保存、銘柄抽出
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- データスキーマ（Raw / Processed / Feature / Execution / Audit）を定義・初期化
- 監査ログ（シグナル→注文→約定のトレーサビリティ）管理
- ETL パイプラインの実行補助（差分更新、バックフィル、品質チェック）

設計上のポイント:
- J-Quants API のレート制限・リトライ・トークン自動リフレッシュに対応
- DB 保存は冪等（ON CONFLICT）を採用
- RSS 収集は SSRF / XML Bomb / 大容量レスポンスを考慮した安全実装

---

## 機能一覧

- 環境設定管理（.env 自動ロード、必須環境変数の検証）
- J-Quants クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ取得（四半期 BS/PL）
  - マーケットカレンダー取得
  - トークン取得・キャッシュ・自動リフレッシュ
  - レートリミット & リトライ（指数バックオフ）
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution / audit）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（run_daily_etl など）
- ニュース収集
  - RSS 取得・前処理・記事ID生成（SHA-256）・保存（冪等）
  - 銘柄コード抽出・news_symbols への紐付け
  - SSRF / private IP / gzip サイズ等の対策
- カレンダー管理（営業日判定、前後営業日の算出、夜間更新ジョブ）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ（signal_events / order_requests / executions 等）

---

## 要件（Prerequisites）

- Python 3.10 以上
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- OS 環境により追加のライブラリが必要な場合があります

（プロジェクトの配布方法に応じて pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. レポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 参考（最低限の依存）:
     ```
     pip install duckdb defusedxml
     ```
   - もしプロジェクトに requirements.txt / pyproject.toml があればそれに従ってください:
     ```
     pip install -e .
     ```

4. 環境変数の設定
   - 必須環境変数（実行に必要）:
     - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token
     - KABU_API_PASSWORD : kabuステーション API パスワード
     - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID : Slack チャネル ID
   - オプション:
     - DUCKDB_PATH (既定: data/kabusys.duckdb)
     - SQLITE_PATH (既定: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) デフォルト development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

   - .env ファイルをプロジェクトルートに置くと自動で読み込まれます（.env.local は .env を上書き）。
     自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   - 例 `.env`:
     ```
     JQUANTS_REFRESH_TOKEN="xxxx..."
     KABU_API_PASSWORD="hoge"
     SLACK_BOT_TOKEN="xoxb-..."
     SLACK_CHANNEL_ID="C12345678"
     DUCKDB_PATH="data/kabusys.duckdb"
     ```

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで実行:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB を作る場合:
     ```python
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（サンプル）

以下は代表的な利用例です。実運用コードではログ・例外処理・トークン管理を適切に組み込んでください。

- 設定取得
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  ```

- スキーマ初期化
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務の取得と品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema 済みを想定
  result = run_daily_etl(conn)  # 引数で target_date など指定可
  print(result.to_dict())
  ```

- RSS ニュース収集（単一ソース）
  ```python
  import duckdb
  from kabusys.data import news_collector

  conn = duckdb.connect("data/kabusys.duckdb")
  articles = news_collector.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  new_ids = news_collector.save_raw_news(conn, articles)
  print("saved:", len(new_ids))
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("calendar saved:", saved)
  ```

- 品質チェックを個別実行
  ```python
  from kabusys.data import quality
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- J-Quants トークン取得（必要に応じて直接呼ぶ）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使って取得
  ```

---

## 環境変数と自動ロード挙動

- パッケージ起動時、プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動読み込みします。
  - 読み込み優先度: OS環境 > .env.local > .env
  - OS 環境変数は保護され .env で上書きされません（ただし .env.local は上書き可能）。
- 自動ロードを無効化するには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- 必須の環境変数が不足している場合、settings のプロパティ参照で ValueError を送出します。

---

## ディレクトリ構成

以下はパッケージの主要構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（取得・保存）
    - news_collector.py            -- RSS 収集・前処理・保存・銘柄抽出
    - schema.py                    -- DuckDB スキーマ定義・初期化
    - pipeline.py                  -- ETL パイプライン（差分更新・run_daily_etl 等）
    - calendar_management.py       -- マーケットカレンダー管理（営業日判定・更新ジョブ）
    - audit.py                     -- 監査ログテーブルの初期化
    - quality.py                   -- データ品質チェック
  - strategy/
    - __init__.py                  -- 戦略レイヤ（拡張ポイント）
  - execution/
    - __init__.py                  -- 発注/約定/ポジション管理（拡張ポイント）
  - monitoring/
    - __init__.py                  -- 監視用モジュール（将来拡張）

---

## 開発・拡張想定ポイント

- strategy / execution / monitoring モジュールはシステム固有の戦略・ブローカ接続を実装するための拡張ポイントです。
- DuckDB スキーマは DataPlatform.md に基づく想定であり、用途により追加カラムや索引を追加できます。
- ニュースの銘柄抽出は単純な 4 桁数字抽出を行っています（将来的に NLP での改善が可能）。

---

## 注意事項

- 実運用での取引は法的・技術的リスクを伴います。実際に注文を出す前に、十分なテスト（ペーパートレーディング）を行ってください。
- 機密情報（API トークン等）は安全に管理してください（.env ファイルの取り扱いに注意）。
- J-Quants / kabu API の利用規約・レート制限を遵守してください。

---

必要に応じて README に実行例や CI / デプロイ手順、より詳細な設定テンプレート（.env.example）を追加できます。追加希望があれば指定してください。