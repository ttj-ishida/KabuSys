# KabuSys

日本株向け自動売買 / データプラットフォーム用のライブラリ群。  
J-Quants・kabuステーション等の外部APIからデータを取得し、DuckDBに格納してETL・品質チェック・監査ログを行うためのモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株自動売買システムのインフラ部分（データ取得、ETL、品質チェック、監査ログ、発注管理のスキーマ等）を提供するライブラリです。主な目的は次の通りです。

- J-Quants API から株価・財務・マーケットカレンダー等を取得して DuckDB に蓄積する。
- ETL（差分更新・バックフィル）を行い、Idempotent（重複安全）にデータを保存する。
- データ品質チェック（欠損、スパイク、重複、日付不整合）を実行する。
- 発注／約定の監査ログ（トレーサビリティ）用スキーマを提供する。
- 将来的に戦略・実行・モニタリング層と連携できる構成。

設計上のポイント:
- API レート制限（J-Quants: 120 req/min）を守るための内部レートリミッタを実装。
- HTTP リトライ（指数バックオフ、特定ステータスでの再試行、401 時のトークン自動リフレッシュ）。
- DuckDB へは ON CONFLICT DO UPDATE を使って冪等性を確保。
- 監査ログは削除せずトレーサビリティを担保（UTC タイムスタンプ）。

---

## 機能一覧

- config
  - 環境変数の読み込み（`.env`, `.env.local` 自動ロード。プロジェクトルートは .git または pyproject.toml を基準に探索）
  - 必須設定の検証（未設定時は例外）
- data.jquants_client
  - J-Quants API クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - 保存関数: save_daily_quotes / save_financial_statements / save_market_calendar
  - レート制御・リトライ・トークン自動リフレッシュ・fetched_at の記録
- data.schema
  - DuckDB スキーマ（Raw / Processed / Feature / Execution）定義と初期化
  - init_schema / get_connection
- data.pipeline
  - 日次 ETL 実行: run_daily_etl（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 部分的ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分取得、バックフィル、品質チェックの組み合わせ
- data.quality
  - 欠損データ検出、スパイク検出、重複チェック、日付不整合チェック
  - run_all_checks でまとめて実行。QualityIssue オブジェクトで結果を返す
- data.audit
  - 監査テーブル（signal_events / order_requests / executions）の定義と初期化
  - init_audit_schema / init_audit_db
- (空のパッケージ): strategy, execution, monitoring — 将来的な拡張ポイント

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（型ヒントで union 型を使用）
- DuckDB を利用（Python パッケージ duckdb が必要）

1. リポジトリをクローン / ダウンロード
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - duckdb は必須です。プロジェクトで requirements.txt/pyproject.toml があればそちらを使用してください。
   - 簡易:
     - pip install duckdb

   - 開発中にパッケージとして使う場合:
     - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（→自動ロードされます）を作成してください。自動ロードはプロジェクトルート（.git または pyproject.toml がある場所）から行われます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須環境変数（Settings から）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabu API のパスワード
     - SLACK_BOT_TOKEN (必須) — Slack 通知用（必要に応じて）
     - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
   - 任意（デフォルト値あり）:
     - KABUS_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (省略時: data/kabusys.duckdb)
     - SQLITE_PATH (省略時: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live。省略時: development)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL。省略時: INFO)

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. データベース初期化
   - DuckDB スキーマを作成します（初回のみ）。Python REPL かスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # :memory: も可
   conn.close()
   ```
   - 監査ログ用スキーマを追加する場合:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.audit import init_audit_schema
   conn = init_schema("data/kabusys.duckdb")
   init_audit_schema(conn)
   ```

---

## 使い方

以下は代表的な利用例です（簡易）。

- 日次 ETL を実行する
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 接続（既に init_schema で作成済みなら get_connection で OK）
  conn = init_schema("data/kabusys.duckdb")

  # ETL 実行（target_date を省略すると今日）
  result = run_daily_etl(conn)
  print(result.to_dict())  # ETL の概要（取得件数・保存件数・品質問題など）
  conn.close()
  ```

- 部分ジョブ（株価のみ取得）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_prices_etl

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched}, saved={saved}")
  conn.close()
  ```

- 監査 DB を別個に初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は UTC タイムゾーン設定済みで監査テーブルが作成される
  conn.close()
  ```

- 品質チェックのみ実行する
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.quality import run_all_checks
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  conn.close()
  ```

内部的な振る舞いのポイント:
- J-Quants クライアントは 120 req/min の制限に合わせて固定間隔でスロットリングします。
- HTTP エラー（408, 429, 5xx）に対して指数バックオフで最大3回リトライします。429 の場合は Retry-After ヘッダを尊重します。
- 401 を受けた場合はリフレッシュトークンから id_token を再取得して 1 回だけ再試行します。
- fetch 関数はページネーションを扱い、pagination_key を使って全ページ取得します。
- 保存関数は ON CONFLICT DO UPDATE により冪等です。

ETL の結果は ETLResult オブジェクトで返り、品質チェック結果やエラーを含みます。

---

## ディレクトリ構成

リポジトリの主要ファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアントと保存関数
    - schema.py              — DuckDB スキーマ定義と初期化
    - pipeline.py            — ETL パイプライン（差分更新・品質チェック）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ（トレーサビリティ）定義
  - strategy/
    - __init__.py            — 戦略層（将来的な拡張ポイント）
  - execution/
    - __init__.py            — 発注/実行層（将来的な拡張ポイント）
  - monitoring/
    - __init__.py            — モニタリング層（将来的な拡張ポイント）

データベース・スキーマ:
- DuckDB: data/kabusys.duckdb（デフォルト）
  - raw_prices, raw_financials, market_calendar, 等の Raw/Processed/Feature/Execution テーブル
- 監査ログ: audit 用テーブル（signal_events, order_requests, executions）
- SQLite（monitoring 用）: data/monitoring.db（設定次第）

---

## 注意点 / 運用メモ

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）から行います。CIやテストで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 環境変数の保護: OS 環境変数は .env によって上書きされないよう設計されています（ただし .env.local は override=True のため優先されますが、OS の既存キーは protected として扱われます）。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかを設定してください。無効な値を設定すると例外になります。
- LOG_LEVEL は "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL" のいずれか。
- DuckDB のファイルパスの親ディレクトリが存在しない場合、init_schema 等が自動作成します。
- ETL は部分的な失敗を許容する設計（1つのステップが失敗しても他のステップは継続し、エラーは ETLResult.errors に蓄積されます）。
- 品質チェックの結果は警告とエラーに分かれます。呼び出し元でエラーがあればアラートや停止判定を行ってください。

---

## 開発 / 貢献

- strategy / execution / monitoring パッケージは将来的に機能を追加するための場所です。コントリビュートの際はテストとドキュメントを追加してください。
- 既存関数はできるだけ引数で依存（例: id_token, DB 接続）を注入できるようにしており、ユニットテストが書きやすいように設計しています。

---

ご不明点や追加で README に載せたい情報（例: CI の設定、具体的な .env.example、pytest 設定など）があれば教えてください。必要に応じてサンプル .env.example やチュートリアルを追加します。