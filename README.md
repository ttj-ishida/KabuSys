# KabuSys

日本株自動売買プラットフォームのコアライブラリ。データ取得（J-Quants）、ETL、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ（発注〜約定のトレース）など、アルゴリズム取引基盤に必要な主要機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なデータ基盤とユーティリティ群を提供する Python パッケージです。主な目的は以下：

- J-Quants API からの時系列・財務・カレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いた 3 層（Raw / Processed / Feature）スキーマの管理と初期化
- RSS ベースのニュース収集と記事→銘柄紐付け
- ETL（差分取得・バックフィル・品質チェック）の実装
- マーケットカレンダーによる営業日判定ユーティリティ
- 発注〜約定までをトレースする監査ログスキーマ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上、冪等性・トレーサビリティ・セキュリティ（SSRF対策、XMLパーサ防御、受信サイズ制限）に配慮しています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（rate limit 管理、リトライ、401時のトークン自動リフレッシュ）
  - 株価日足、財務データ、マーケットカレンダーのページネーション対応取得
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）
- data.schema
  - DuckDB 用の包括的スキーマ（raw / processed / feature / execution / audit）
  - スキーマ初期化関数（init_schema, init_audit_db）
- data.pipeline
  - 日次 ETL（差分取得、バックフィル、品質チェックの実行）
  - run_daily_etl 等のエントリポイント
- data.news_collector
  - RSS 取得、テキスト前処理、記事ID生成（正規化URL→SHA-256）、DuckDB への冪等挿入、銘柄抽出と紐付け
  - SSRF、gzip/サイズ制限、defusedxml による安全性対策
- data.calendar_management
  - market_calendar を元にした営業日判定、next/prev_trading_day、期間内営業日取得、夜間カレンダー更新ジョブ
- data.quality
  - 欠損、重複、スパイク、日付不整合のチェック関数と総合実行
- data.audit
  - signal / order_request / executions を含む監査ログスキーマ。UTC タイムゾーン固定・冪等キー設計

---

## セットアップ手順

以下は開発環境 / 実行環境の最小セットアップ例です。

1. Python 仮想環境作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール  
   （このリポジトリに setup.py/pyproject.toml がある想定での例）
   ```bash
   pip install -e .
   # または必要なパッケージを個別に pip install duckdb defusedxml
   ```

3. 環境変数を設定  
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   必須環境変数（少なくとも下記は設定が必要）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID

   任意 / デフォルト値:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/... （デフォルト: INFO）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用途の SQLite パス（デフォルト: data/monitoring.db）

4. データベース初期化（例）
   Python REPL かスクリプトから：
   ```python
   from kabusys.data.schema import init_schema, init_audit_db
   # メイン DB を初期化（ファイルパス指定、":memory:" も可）
   conn = init_schema("data/kabusys.duckdb")
   # 監査ログ専用 DB を初期化する場合
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要 API と実行例）

ここではライブラリ関数を利用する典型例を示します。

- J-Quants から株価日足を取得して保存
  ```python
  import duckdb
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # id_token は省略可（内部で refresh_token を使って取得・キャッシュします）
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print("saved:", saved)
  ```

- 日次 ETL（市場カレンダー取得→株価→財務→品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- RSS ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes に有効な銘柄コードセットを渡すと銘柄抽出を実行
  known_codes = {"7203", "6758", "8306"}  # 例
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)
  ```

- マーケットカレンダー更新（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("calendar saved:", saved)
  ```

- 品質チェックを単体で実行
  ```python
  from kabusys.data.quality import run_all_checks
  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注意点：
- J-Quants API のレート制限（120 req/min）はクライアント側で制御されています。
- get_id_token() はリフレッシュトークンを用いて idToken を取得します（自動リフレッシュの仕組みあり）。
- 環境変数の不足は Settings クラスで ValueError を投げます（必須変数を確認してください）。

---

## ディレクトリ構成（主要ファイル・モジュールの説明）

プロジェクト内の主要モジュールは以下の通りです（抜粋）:

- src/kabusys/
  - __init__.py: パッケージ定義、エクスポート
  - config.py: 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py: RSS 収集、記事前処理、DB保存、銘柄抽出
    - schema.py: DuckDB スキーマ定義と初期化（init_schema, get_connection）
    - pipeline.py: ETL パイプライン（差分更新・バックフィル・品質チェック）
    - calendar_management.py: マーケットカレンダー管理・営業日ユーティリティ・夜間更新ジョブ
    - audit.py: 監査ログ（signal / order_requests / executions）スキーマと初期化
    - quality.py: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - strategy/
    - __init__.py （戦略層のエントリポイントを想定）
  - execution/
    - __init__.py （発注実行層のエントリポイントを想定）
  - monitoring/
    - __init__.py （監視関連の将来的な実装場所）

---

## 設定詳細・注意事項

- .env の自動読み込み
  - パッケージ実行時、プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に有用）。
- 環境変数バリデーション
  - KABUSYS_ENV は `development`, `paper_trading`, `live` のいずれか
  - LOG_LEVEL は `DEBUG, INFO, WARNING, ERROR, CRITICAL` のいずれか
- セキュリティ設計
  - NewsCollector は SSRF 対策（スキーム検証、プライベート IP 検査、リダイレクト検査）や defusedxml を使用
  - RSS 読み込み時に受信サイズ上限（デフォルト 10MB）を設けることでメモリ DoS を防止
- DuckDB
  - init_schema() により必要な全テーブルとインデックスを冪等に作成します。初回は init_schema を利用してください。get_connection は既存 DB へ接続するだけです。
- トレーサビリティ
  - audit モジュールにより signal → order_request → execution のチェーンを保存可能。監査ログは基本削除しない設計です。

---

## 開発・テスト時のヒント

- 単体テスト時に .env の自動ロードを無効化するには:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- jquants_client のネットワーク呼出し等はモック可能です（モジュール内の _urlopen などを差し替え）。
- DuckDB はインメモリ DB（":memory:"）を使えばテストが簡単です。

---

## ライセンス / 貢献

（ここにはライセンスや貢献ガイドラインを記載してください。リポジトリに LICENSE ファイルがある場合はそちらを参照します。）

---

README は以上です。必要であれば、README に含めるサンプル .env.example や具体的な CI / デプロイ手順、Slack 通知の利用例、kabu ステーションとの統合例（発注フロー）などの追記を行えます。どの情報を追加しますか？