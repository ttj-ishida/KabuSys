# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
このリポジトリはデータ取得・保存・品質チェック・監査トレーサビリティを中心とした基盤機能を提供します。

- バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータプラットフォーム／自動売買基盤の一部を構成する Python モジュール群です。主に以下を提供します。

- J-Quants API からのデータ取得（株価日足、四半期財務、JPX カレンダー）
- DuckDB を用いたスキーマ定義と永続化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェックを含む日次 ETL）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル→発注→約定までのトレーサビリティ）

設計の要点:
- API レート制限（120 req/min）の遵守、指数バックオフを含むリトライ、401 時の自動トークンリフレッシュ
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- すべてのタイムスタンプは UTC を基本（監査ログ等）

---

## 主な機能一覧

- data.jquants_client
  - J-Quants からのページネーション対応データ取得（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - レートリミッタ、リトライ、IdToken キャッシュ／自動リフレッシュ
  - DuckDB への安全な保存関数（save_daily_quotes 等）
- data.schema
  - DuckDB のスキーマ（Raw / Processed / Feature / Execution）を定義する DDL と初期化関数（init_schema）
- data.pipeline
  - 日次 ETL（run_daily_etl）：カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分判定、backfill、品質チェック（quality モジュール）を備えた ETLResult を返す
- data.quality
  - 欠損データ、重複、スパイク、日付不整合の検出（QualityIssue を返す）
- data.audit
  - シグナル／発注／約定の監査テーブル群と初期化（init_audit_schema / init_audit_db）
- config
  - .env ファイルまたは環境変数からの設定読み込み（自動ロード機能、必要な環境変数チェック）
- execution / strategy / monitoring
  - パッケージプレースホルダ（将来の実装ポイント）

---

## 要件

- Python 3.10+
- duckdb（Python パッケージ）

インストール例:
```bash
python -m pip install duckdb
```

その他は標準ライブラリのみで動作します（ネットワーク呼び出しは urllib を使用）。

---

## セットアップ手順

1. リポジトリをクローン／取得する

2. 必要な Python パッケージをインストール
   ```bash
   python -m pip install -r requirements.txt
   ```
   （requirements.txt がない場合は最低限 duckdb をインストールしてください）
   ```bash
   python -m pip install duckdb
   ```

3. 環境変数を設定する
   - プロジェクトルートの `.env` / `.env.local` を自動的に読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必須の環境変数（Settings クラス参照）:

     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション等の API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   - 任意／デフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: モニタリング用 SQLite（デフォルト: data/monitoring.db）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

   - サンプル `.env`（プロジェクトルートに置く）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ初期化
   - 実稼働用 DB を作成する:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ（audit）テーブルを追加:
     ```python
     from kabusys.data import audit
     audit.init_audit_schema(conn)
     ```

---

## 使い方（簡易クイックスタート）

Python スクリプトや REPL で以下のように利用します。

- インポートと設定参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- DuckDB スキーマ初期化（ファイルまたはメモリ）
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  # またはメモリDB
  # conn = schema.init_schema(":memory:")
  ```

- 日次 ETL の実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema
  from datetime import date

  conn = schema.init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

  ETL 実行は以下の処理を行います:
  1. 市場カレンダー取得（先読み）
  2. 株価差分取得（backfill による後出し修正吸収）
  3. 財務データ差分取得
  4. 品質チェック（check_missing_data, check_duplicates, check_spike, check_date_consistency）

- 監査ログを別 DB に初期化（監査専用 DB）
  ```python
  from kabusys.data import audit
  conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
  ```

- J-Quants の個別 API 呼び出し（テストや高度な用途）
  ```python
  from kabusys.data import jquants_client as jq
  # トークン省略時は settings から取得（キャッシュ・自動更新あり）
  records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
  ```

---

## 環境変数 / 設定一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で .env 自動読み込み無効化)

Settings クラスは未設定の必須値があると ValueError を送出します。

---

## 実装上の注意点 / 動作仕様

- API レート制限: J-Quants は 120 req/min を想定。内部で固定間隔スロットリングを行います。
- リトライ: 408/429/5xx は指数バックオフで最大 3 回リトライします。429 の場合は Retry-After ヘッダを優先します。
- 401 Unauthorized: トークン期限切れと判断した場合は自動でリフレッシュして 1 回だけ再試行します。
- データ保存は冪等（ON CONFLICT DO UPDATE）で、再取得や重複挿入を安全に処理します。
- すべての監査テーブルは UTC タイムスタンプを使用するよう初期化時に SET TimeZone='UTC' を実行します。
- データ品質チェックは Fail-Fast ではなくすべての問題を収集して返します。呼び出し側が致命的判定（severity="error"）を見て対処してください。

---

## ディレクトリ構成

リポジトリの主要ファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存ロジック）
    - schema.py             — DuckDB スキーマ定義と初期化
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - quality.py            — データ品質チェック
    - audit.py              — 監査ログ（signal / order_request / executions）
  - strategy/
    - __init__.py           — 戦略モジュール（将来的に実装）
  - execution/
    - __init__.py           — 発注 / 実行モジュール（将来的に実装）
  - monitoring/
    - __init__.py           — 監視 / メトリクス（将来的に実装）

（上記はソースツリーの要旨です。実際のリポジトリには README / pyproject.toml 等が含まれる想定です。）

---

## 開発・テスト時のヒント

- 自動環境変数読み込みを無効化したい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- テストではメモリ DuckDB（":memory:"）を使うと簡単に初期化できます。
- run_daily_etl や個別 ETL 関数は id_token を引数で注入可能なので、モックや固定トークンを渡して単体テストが可能です。

---

## ライセンス / 貢献

この README に含まれる情報はコードベースから自動生成されたドキュメントです。実際のライセンスや貢献ガイドラインはレポジトリのルートにある LICENSE / CONTRIBUTING ファイル等を参照してください。

---

質問や補足の要望があれば、どのセクションを詳しく書き直すか（例: 実行例、CI / デプロイ手順、スキーマ詳細のドキュメント化）を教えてください。