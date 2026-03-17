# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants や RSS からデータを収集し、DuckDB に保存して ETL / 品質チェック / カレンダー管理 / ニュース収集 / 監査ログなどを提供します。

この README はコードベース（src/kabusys 以下）に基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買とデータ基盤を支援するライブラリです。主に以下を目的とします。

- J-Quants API から株価（日足）、財務データ、JPX マーケットカレンダーを取得して保存
- RSS フィードからニュースを収集し、記事と銘柄コードの紐付けを行う
- DuckDB を用いた三層（Raw / Processed / Feature）スキーマと実行・監査テーブルの初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）の実行
- マーケットカレンダー管理（営業日判定、next/prev 取得）
- 監査ログ（シグナル→発注→約定のトレース）を記録するためのスキーマ

設計上、API レート制御、リトライ、冪等性（ON CONFLICT 句）、SSRF 対策、XML セキュリティ対策（defusedxml）などを考慮しています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（rate limiting / retry / token refresh / pagination 対応）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存用 save_* 関数（冪等）
- data.news_collector
  - RSS フィード取得（SSRF対策・gzip サイズ制限）
  - 記事正規化・ID生成（URL 正規化→SHA-256）
  - raw_news / news_symbols への冪等保存
  - extract_stock_codes（本文から銘柄コード抽出）
- data.pipeline
  - ETL ユーティリティ（差分取得、backfill、品質チェック統合）
  - run_daily_etl により日次 ETL をまとめて実行
- data.schema / data.audit
  - DuckDB スキーマ初期化（Raw / Processed / Feature / Execution / Audit）
  - 監査ログ用スキーマ（signal_events, order_requests, executions）
- data.calendar_management
  - market_calendar を元に営業日ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - calendar_update_job（夜間バッチでの差分更新）
- data.quality
  - 欠損 / スパイク / 重複 / 日付不整合 のチェック（QualityIssue のリストで返却）
- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）と Settings API
  - 必須環境変数の検証

---

## セットアップ手順

1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2. 依存パッケージのインストール
   - 必須: duckdb, defusedxml
   - 例:
     - pip install duckdb defusedxml
   - パッケージ化されている場合:
     - pip install -e .

   ※ 実プロジェクトでは requirements.txt / pyproject.toml に依存を記載してください。

3. 環境変数の用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置可能です。
   - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テスト時など）。

4. 必須環境変数（少なくとも下記を設定してください）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - （任意）KABU_API_BASE_URL: kabu API のベース URL（デフォルト "http://localhost:18080/kabusapi"）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
   - SQLITE_PATH: SQLite（監視用）パス（デフォルト `data/monitoring.db`）
   - KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

   注意: Settings オブジェクトは未設定の必須変数で ValueError を投げます。`.env.example` を元に `.env` を作成する運用を推奨します（本リポジトリに .env.example がある想定）。

---

## 使い方（例）

以下はライブラリ API を直接使う最小の利用例です。実行前に環境変数を適切に設定してください。

- DuckDB スキーマ初期化（最初に一度実行）
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  # conn は duckdb.DuckDBPyConnection
  ```

- 監査ログ DB 初期化（監査専用 DB を別にする場合）
  ```python
  from kabusys.data import audit
  conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
  ```

- 日次 ETL 実行（J-Quants から差分取得→保存→品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import pipeline, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS 収集して raw_news に保存、銘柄紐付け）
  ```python
  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  print(results)
  ```

- カレンダー夜間バッチ更新
  ```python
  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn, lookahead_days=90)
  print("saved:", saved)
  ```

- J-Quants の ID トークンを直接取得（テストなど）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を参照
  print(token)
  ```

ログ出力やエラーは Settings.log_level に従います。KABUSYS_ENV によって本番（live）判定などができます。

---

## よくある運用ポイント

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI 等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants クライアントはレート制御（120 req/min）と再試行ロジック、401 時の自動トークンリフレッシュを内蔵しています。
- news_collector は RSS のサイズ制限（デフォルト 10 MB）や gzip 解凍後のサイズ検査、SSRF 防止（リダイレクト先のプライベート IP 拒否）などセキュリティ対策を備えています。
- DuckDB に対する保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を考慮しているため、再実行しても重複登録を抑制します。
- 品質チェック（data.quality）は Fail-Fast ではなく問題を集めて返す設計です。ETL の継続/停止判断は呼び出し側で行ってください。

---

## ディレクトリ構成

（コードベースに含まれている主要ファイル・モジュールの構成）

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ execution/
   │  └─ __init__.py
   ├─ strategy/
   │  └─ __init__.py
   ├─ monitoring/
   │  └─ __init__.py
   └─ data/
      ├─ __init__.py
      ├─ jquants_client.py
      ├─ news_collector.py
      ├─ pipeline.py
      ├─ calendar_management.py
      ├─ schema.py
      ├─ audit.py
      └─ quality.py
```

各モジュールの役割は上の「主な機能一覧」を参照してください。

---

## 開発・テスト時の注意

- テスト実行時に .env 自動読み込みが邪魔な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のインメモリ DB を使う場合はパスに `":memory:"` を渡せます（init_schema/get_connection）。
- ネットワーク呼び出し（J-Quants / RSS）は外部依存があるため、ユニットテストでは get_id_token / _urlopen 等をモックしてテストしてください（コード内にもモックしやすい設計の箇所があります）。

---

## ライセンス・貢献

本 README はコードベースの説明に基づくもので、実プロジェクトでは別途 LICENSE / CONTRIBUTING ドキュメントを用意してください。

---

必要に応じて README に追加したいサンプル（cron での実行例、Dockerfile、systemd ユニット、Slack 通知のサンプルなど）があれば教えてください。具体的な実行コマンドや運用スクリプトも作成できます。