# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants API などから市場データ（株価・財務・カレンダー）やニュースを収集し、DuckDB に冪等的に保存、品質チェックや監査ログ（発注→約定のトレーサビリティ）を提供します。

主な用途:
- データ収集（株価日足・財務データ・JPX カレンダー）
- ニュース収集と銘柄紐付け
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- DuckDB ベースのスキーマ初期化・監査ログ管理

バージョン: 0.1.0

---

## 主な機能一覧

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX カレンダーの取得
  - API レート制御（120 req/min）とリトライ（指数バックオフ）
  - 401 発生時の自動トークンリフレッシュ（1回）とページネーション対応
  - fetched_at（UTC）を付与して Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）

- ニュース収集（RSS）
  - RSS 取得・XML パースに defusedxml を使用して安全性確保
  - URL 正規化（トラッキング除去）・記事 ID（SHA-256 の先頭 32 文字）生成
  - SSRF 対策（スキーム検査、プライベートIPブロック、リダイレクト検査）
  - 受信サイズ制限、gzip 解凍対応、DuckDB へのバルク挿入（INSERT ... RETURNING）
  - 銘柄コード抽出（4桁数字、known_codes によるフィルタ）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル DDL を提供
  - init_schema() でスキーマ初期化（冪等）
  - 監査用スキーマ（signal_events / order_requests / executions）初期化機能

- ETL パイプライン
  - 差分更新（最終取得日を参照）＋ backfill
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損・スパイク・重複・日付不整合）を収集して報告
  - run_daily_etl() によりフルパイプライン実行可能

- マーケットカレンダー管理
  - 営業日判定・前後営業日取得・期間内営業日リスト取得
  - calendar_update_job() による夜間差分更新

---

## 動作要件（推奨）

- Python 3.10+
- 依存パッケージ（最小）
  - duckdb
  - defusedxml

（プロジェクトの packaging/requirements ファイルがある場合はそちらを使用してください）

---

## セットアップ手順（開発環境向け）

1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. パッケージインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （もしパッケージ配布ファイルがあるなら）
     - pip install -e .

   ※requirements.txt が存在する場合: pip install -r requirements.txt

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 読み込み優先順位: OS 環境 > .env.local > .env

4. 必要な環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabuステーション API ベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: environment (development | paper_trading | live)（デフォルト development）
   - LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト INFO）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=yourpassword
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 初期化・基本的な使い方

以下は Python インタープリタ／スクリプトでの利用例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)  # ファイルがなければ parent ディレクトリも自動作成
  ```

- 監査ログ用 DB 初期化（監査専用 DB に分ける場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- 日次 ETL 実行（株価・財務・カレンダーの差分更新＋品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ（既知銘柄セットを渡して紐付けを行う）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count}
  ```

- J-Quants から生株価を取得して保存（低レベル）
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  recs = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
  saved = jq.save_daily_quotes(conn, recs)
  print("saved:", saved)
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("calendar saved:", saved)
  ```

---

## API と運用上の注意点

- J-Quants のレート制限を遵守（120 req/min）するため RateLimiter が組み込まれています。大規模な並列処理では別途考慮してください。
- ネットワークエラーや 5xx、408、429 については最大 3 回のリトライ（指数バックオフ）を行います。429 の場合はレスポンスの Retry-After ヘッダを優先します。
- get_id_token() はリフレッシュトークンから ID トークンを取得します。_request() は 401 時にトークンを自動更新・再試行しますが、無限再帰を防ぐため一部呼び出しではトークン更新を無効にしています。
- DuckDB への保存は多くのケースで ON CONFLICT を用い冪等性を確保しています。
- ニュース収集は外部の RSS を扱うため SSRF 対策や受信サイズ制限、gzip 解凍後のサイズ検査を実装しています。外部サイトの取得失敗は個別にハンドリングして他ソースに影響を与えません。
- 環境変数は .env(.local) を自動的に読み込みますが、テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成

リポジトリ内の主なファイル・ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                - 環境変数・設定管理（自動 .env ロード）
  - data/
    - __init__.py
    - schema.py              - DuckDB スキーマ定義と init_schema()
    - jquants_client.py      - J-Quants API クライアント（取得・保存）
    - pipeline.py            - ETL パイプライン（差分更新・品質チェック）
    - news_collector.py      - RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py - マーケットカレンダー管理（営業日判定等）
    - quality.py             - データ品質チェック（欠損・スパイク等）
    - audit.py               - 監査ログ（発注→約定のトレーサビリティ）
    - pipeline.py            - ETL 統合処理
  - strategy/                 - 戦略関連（未実装プレースホルダ）
  - execution/                - 発注・実行関連（未実装プレースホルダ）
  - monitoring/               - 監視関連（未実装プレースホルダ）

（README に記載のないサブモジュールやファイルがあれば適宜参照してください）

---

## 開発・テストのヒント

- 設定の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。パッケージ配布後に異なる CWD で動かす場合は環境変数を直接設定してください。
- ネットワーク呼び出し部分（fetch_rss / _urlopen / jquants_client._request）をモックしてユニットテストを書くことを推奨します。news_collector._urlopen はテストで差し替え可能になるように設計されています。
- DuckDB のテストでは ":memory:" を渡すとインメモリ DB が利用できます（init_schema(":memory:")）。

---

## ライセンス / 貢献

（ここにはプロジェクトのライセンスや貢献方法を記載してください。リポジトリに LICENSE ファイルがある場合はその内容に従います。）

---

この README はコードの現状（src ディレクトリの内容）に基づいて作成しています。実際の運用では環境変数、依存関係、運用スクリプト（systemd / cron / Airflow 等）をプロジェクトの運用方針に合わせて整備してください。必要であれば README の補足（CI/CD、デプロイ手順、Slack 通知設定例など）も作成します。