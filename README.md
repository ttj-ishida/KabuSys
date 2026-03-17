# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ（発注〜約定のトレース）等の基盤機能を提供します。

---

## 概要

KabuSys は次の目的に設計された Python パッケージです。

- J-Quants API から株価・財務・カレンダー等のデータを安全に取得
- DuckDB を用いた三層データレイヤ（Raw / Processed / Feature）および Execution / Audit テーブルの管理
- ETL パイプライン（差分更新・バックフィル・品質チェック）を実行
- RSS からニュースを収集し、記事→銘柄紐付けを行うニュースコレクタ
- マーケットカレンダー（JPX）管理、営業日判定ユーティリティ
- 発注・約定フローを監査ログで完全にトレース可能にするスキーマ

設計上のポイント:
- API のレート制御、リトライ、トークン自動リフレッシュを備えた堅牢なクライアント実装
- DuckDB への冪等保存（ON CONFLICT）とトランザクション管理
- SSRF / XML BOM / Gzip Bomb 等への防御策を組み込んだニュース収集
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 主な機能一覧

- データ取得
  - J-Quants: 株価日足（OHLCV）、四半期財務、マーケットカレンダー
  - RateLimiter（120 req/min）・リトライ・トークン自動更新対応

- ETL / パイプライン
  - 差分取得（最終取得日からの新規分）・バックフィル対応
  - 日次 ETL エントリポイント（run_daily_etl）

- データベース（DuckDB）
  - Raw / Processed / Feature / Execution / Audit のテーブル定義と初期化
  - インデックス定義・冪等テーブル作成

- ニュース収集
  - RSS フィード取得・前処理・SHA-256 ベースの冪等記事ID生成
  - raw_news への保存と記事⇄銘柄紐付け
  - SSRF / XML 攻撃対策、最大受信サイズ制限

- カレンダー管理
  - JPX カレンダーの差分更新ジョブ
  - 営業日判定、前後営業日、期間内営業日取得、SQ判定

- データ品質チェック
  - 欠損、重複、スパイク、日付不整合チェック（QualityIssue を返す）

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルによるフローの完全トレース

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈の | 演算子を使用）
- pip インストール可能な環境

1. リポジトリをクローンまたはソースを用意します。

2. 依存ライブラリをインストールします（例）:
   ```
   pip install duckdb defusedxml
   ```
   必要に応じて開発用依存や packaging 用に追加ライブラリをインストールしてください。

3. 環境変数の準備
   - プロジェクトルートの `.env` または `.env.local` に設定を置くと、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意:
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/...) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例 `.env`（雛形）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベーススキーマを初期化します（DuckDB）:
   - プログラムから初期化:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```
   - 監査ログ（Audit）を追加する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```

---

## 使い方（主な API 例）

- J-Quants トークン取得（内部で自動リフレッシュを行う関数も利用可能）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS）を実行して DB に保存
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は 4桁銘柄コードの集合（紐付け用）
  known_codes = {"7203", "6758", "6954"}  # 例
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: 新規保存件数}
  ```

- カレンダー更新ジョブ（夜間バッチ）:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved: {saved}")
  ```

- 品質チェック（任意のタイミングで実行）
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意点:
- jquants_client は内部でレート制御とリトライを行います。大量リクエスト時は 120 req/min のレート制限に従ってください。
- ニュース取得は外部ネットワークアクセスを行うため SSRF 対策・URL 検証を行っています。テスト時は _urlopen をモックできます。

---

## ディレクトリ構成

主要なファイルと役割（リポジトリの src/kabusys ツリーを基準）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（.env 自動ロード、settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch/save / 認証トークン管理 / レートリミッタ / リトライ）
    - news_collector.py
      - RSS 収集・前処理・raw_news 保存・銘柄抽出・紐付け
    - schema.py
      - DuckDB スキーマ定義（Raw / Processed / Feature / Execution）と初期化関数
    - pipeline.py
      - ETL パイプライン（差分更新 / backfill / run_daily_etl）
    - calendar_management.py
      - マーケットカレンダーの更新ジョブ、営業日ユーティリティ
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）初期化
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py
    - （戦略ロジックを配置するためのモジュール群を想定）
  - execution/
    - __init__.py
    - （発注・ブローカー連携・注文管理の実装を想定）
  - monitoring/
    - __init__.py
    - （監視/メトリクス/Slack 通知等を想定）

---

## 運用上の注意 / 実装メモ

- 環境変数の自動ロード:
  - プロジェクトルートにある `.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）。
  - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

- トークン管理:
  - J-Quants の ID トークンはモジュールレベルでキャッシュされ、401 を受けた場合は自動でリフレッシュして 1 回だけリトライします。

- DuckDB:
  - init_schema() は冪等にテーブル・インデックスを作成します。初回のみ実行してください。
  - 監査ログは init_audit_schema を呼んで追加（既存接続に対して追記）できます。

- セキュリティ/堅牢性:
  - news_collector は SSRF、XML 脆弱性、受信サイズ上限、gzip 展開後のサイズ検査などを考慮しています。
  - DB 書き込みはトランザクションでまとめ、ON CONFLICT 構文で冪等性を担保しています。

---

## 貢献・拡張

- 戦略（strategy）や発注バックエンド（execution）はこのコアを基盤として実装/接続できます。
- テストを書く際は、外部リクエスト（HTTP、J-Quants）や _urlopen、get_id_token 等をモックして依存を切り離してください。
- 新たなデータソース追加や品質チェック追加は data 以下にモジュールを追加して、schema の拡張・ETL への組み込みを行ってください。

---

必要であれば、README に実行例の手順（cron / systemd / Airflow による定期実行、Slack 通知の連携方法等）や、より詳細な .env.example、DB マイグレーション方針、CI 設定例を追記できます。どの部分を詳しく書きたいか教えてください。