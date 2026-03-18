# KabuSys

日本株向けの自動売買基盤ライブラリ（データ取得・ETL・品質チェック・監査ログなど）です。  
J-Quants や RSS、kabuステーション（発注系）を組み合わせて、データプラットフォームから戦略・発注レイヤまでをサポートします。

---

## 概要

このプロジェクトは次の目的を持ちます。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する ETL パイプライン
- RSS フィードからニュース記事を収集して前処理・保存するニュースコレクタ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー管理（営業日判定、前後営業日の取得など）
- 監査ログ（signal → order_request → execution の追跡を可能にする監査スキーマ）
- 発注／戦略／モニタリング用の骨組み（モジュール構造を提供）

設計上の特徴として、API レート制限厳守、リトライ/トークン自動リフレッシュ、冪等性（ON CONFLICT）や SSRF 対策など安全性・再現性に配慮されています。

---

## 主な機能（機能一覧）

- J-Quants クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期）取得
  - JPX マーケットカレンダー取得
  - トークン取得/自動リフレッシュ・リトライ/レートリミット制御
- DuckDB スキーマ初期化 / 接続
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義
- ETL パイプライン
  - 差分更新（最終取得日に基づく自動算出）
  - backfill（後出し修正の吸収）
  - 日次バッチ（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合（run_all_checks）
- ニュース収集（RSS）
  - URL 正規化・トラッキングパラメータ除去
  - SSRF 対策、受信サイズ制限、XML パースの堅牢化
  - raw_news・news_symbols への冪等保存
- マーケットカレンダー管理
  - 営業日判定、next/prev_trading_day、期間内営業日リスト
  - カレンダー夜間バッチ更新
- 監査ログスキーマ
  - signal_events / order_requests / executions の定義と初期化

---

## 要件

- Python 3.10 以上（型ヒントに `|` 演算子を使用しているため）
- 必要な Python パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS）

推奨の最低セットアップ（例）
- Python 3.10+
- pip

---

## セットアップ手順

1. リポジトリをクローン

   ```
   git clone <repository-url>
   cd <repository-dir>
   ```

2. 仮想環境を作成して有効化（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール

   requirements.txt がある場合はそちらを利用してください（プロジェクトに合わせて適宜作成してください）。最低限の依存は以下です：

   ```
   pip install duckdb defusedxml
   ```

   開発インストール（パッケージ化されている場合）:

   ```
   pip install -e .
   ```

4. 環境変数（.env）を準備

   プロジェクトルート（`.git` または `pyproject.toml` のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。

   主な環境変数:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（モニタリング等）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境 (development | paper_trading | live)
   - LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

   サンプル（.env）:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   自動ロードを無効にする場合（テスト等）:

   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

5. DuckDB スキーマ初期化

   以下のような簡単なスクリプトで DB を初期化します：

   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")  # ファイルパス or ":memory:"
   conn.close()
   ```

6. 監査ログ DB（監査専用）を初期化する場合:

   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/kabusys_audit.duckdb")
   conn.close()
   ```

---

## 使い方（基本の例）

以下はライブラリ関数を呼んで日次 ETL やニュース収集を行う最小例です。実運用ではジョブスケジューラ（cron / Airflow 等）やロギング・通知を組み合わせてください。

- 日次 ETL の実行（株価・財務・カレンダーを差分更新して品質チェック）

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- ニュース収集ジョブ（RSS を取得して raw_news に保存、銘柄紐付け）

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes: 銘柄抽出で参照する有効なコードセット
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- 市場カレンダー夜間更新ジョブ

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  conn.close()
  ```

注意点:
- jquants_client は内部でレート制御とトークンリフレッシュを行います。
- テスト容易性のため id_token を外部から注入することが可能です（関数の引数として渡せます）。
- news_collector の HTTP 呼び出しは _urlopen をモックして差し替えられます。

---

## 主要 API / エントリポイント（抜粋）

- kabusys.config.settings — 環境設定アクセス（settings.jquants_refresh_token 等）
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ作成・接続
- kabusys.data.jquants_client.*
  - get_id_token(...)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(...), save_financial_statements(...), save_market_calendar(...)
- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...) — 日次 ETL
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection — ニュース収集
- kabusys.data.calendar_management.calendar_update_job — カレンダー更新
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログ初期化
- kabusys.data.quality.run_all_checks — 品質チェック一括実行

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（監視用）
- KABUSYS_ENV — 実行環境: development | paper_trading | live
- LOG_LEVEL — ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動読み込みします。OS の環境変数は保護され、.env.local は .env を上書きします。

---

## ディレクトリ構成

リポジトリ（src/kabusys 以下）のおおまかな構成：

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動読み込み、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py — RSS ニュース収集・前処理・保存
    - pipeline.py — ETL パイプライン（差分更新・日次 ETL）
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - audit.py — 監査ログ（signal/order_request/execution の DDL と初期化）
    - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - strategy/
    - __init__.py — 戦略レイヤ（拡張用）
  - execution/
    - __init__.py — 発注実行レイヤ（拡張用）
  - monitoring/
    - __init__.py — モニタリング関連（拡張用）

各ファイルに詳細な設計方針・制約がコメントで記載されています。必要に応じて拡張してご利用ください。

---

## テスト・デバッグのヒント

- .env の自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- news_collector の外部 HTTP 呼び出しはモジュール内の `_urlopen` をモックして置き換えられる設計です（ユニットテストでの差し替えが容易）。
- jquants_client の API 呼び出しは id_token を引数に注入できるため、単体テストでトークンを固定して検証できます。
- DuckDB はインメモリ DB（":memory:"）を使えるので、単体テスト実行時にファイルを残す必要がありません。

---

## 依存関係

主な外部依存パッケージ例：

- duckdb
- defusedxml

その他、プロジェクト固有の依存（HTTP クライアント等）を requirements.txt にまとめてください。

---

## 貢献

バグ報告、機能提案、プルリクエスト歓迎です。大きな変更を行う場合は事前に Issue を立てて設計方針を共有してください。

---

README は以上です。必要であれば「運用例（cron / systemd / Airflow 向けサンプル）」「.env.example の雛形」「CI 用テスト手順」などを追加します。どれを追加しますか？