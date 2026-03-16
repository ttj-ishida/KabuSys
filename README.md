# KabuSys

日本株向けの自動売買・データプラットフォームライブラリ（KabuSys）。  
J-Quants API から市場データを取得して DuckDB に蓄積し、品質チェック・ETL・監査ログ・発注フローの基盤を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを取得するクライアント
- DuckDB に対するスキーマ定義と初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上のポイント:
- API レート制限遵守（120 req/min 固定間隔スロットリング）
- リトライ、指数バックオフ、401 時の自動トークンリフレッシュ
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- すべてのタイムスタンプは UTC を想定

---

## 主な機能一覧

- 環境変数管理（`.env` の自動読み込み、必須変数チェック）
- J-Quants API クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンから ID トークン取得）
  - レートリミッタ・リトライ・トークンキャッシュ
- DuckDB スキーマ管理
  - init_schema(db_path)：全テーブル・インデックスを作成
  - get_connection(db_path)
- ETL パイプライン
  - run_daily_etl(conn, ...)：カレンダー → 株価 → 財務 → 品質チェック の一括処理
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別ジョブ
- データ品質チェック
  - 欠損データ、重複、スパイク（前日比）、日付不整合チェック
  - run_all_checks(conn, ...)
- 監査ログ（audit）
  - init_audit_schema(conn) / init_audit_db(path)
  - シグナル・発注要求・約定の監査テーブルを提供

---

## セットアップ手順

1. Python 仮想環境を作成して有効化（任意だが推奨）

   bash
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存ライブラリをインストール

   必須: duckdb（その他の HTTP メソッドは標準ライブラリを使用）

   bash
   ```
   pip install duckdb
   ```

   （プロジェクトをパッケージとして扱う場合は、レポジトリのルートで）
   ```
   pip install -e .
   ```

3. 環境変数を準備

   プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと、自動的にロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。

   必須環境変数（例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   ```

   オプション（デフォルト値あり）
   ```
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development  # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

4. データベース初期化

   Python REPL やスクリプトで DuckDB スキーマを作成します（":memory:" も可）。

   python
   ```
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # パスは設定に合わせて変更
   ```

5. （必要に応じて）監査ログテーブルの初期化

   python
   ```
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（主要な例）

- 設定値を参照する

  python
  ```
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

  注意:
  - settings は環境変数から値を取得します。必須変数が未設定の場合は ValueError が発生します。
  - 自動 .env ロードを無効にしたい場合は、インポート前に環境変数を設定します:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

- J-Quants から株価を取得して保存する（個別）

  python
  ```
  from kabusys.data import jquants_client as jq
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
  # トークンは settings から自動で取得（キャッシュ・リフレッシュあり）
  records = jq.fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f"saved: {saved}")
  ```

- 日次 ETL の実行（推奨: run_daily_etl を使用）

  python
  ```
  from kabusys.data import pipeline
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

  run_daily_etl は下記を自動で行います:
  1. マーケットカレンダーの先読み取得（デフォルト +90 日）
  2. 株価の差分取得（最終取得日から backfill_days を考慮して取得）
  3. 財務データの差分取得
  4. 品質チェック（デフォルト有効）

  戻り値は ETLResult オブジェクト（to_dict() で辞書化可能）。

- 品質チェックのみ実行

  python
  ```
  from kabusys.data import quality
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i)
  ```

- 監査ログ DB を別ファイルで初期化する

  python
  ```
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使用（ボットトークン）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development | paper_trading | live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env の自動ロードを無効化

---

## ディレクトリ構成

リポジトリの主要なファイル・ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - audit.py               — 監査ログスキーマ
    - quality.py             — データ品質チェック
  - strategy/                 — 戦略関連（未実装テンプレート）
    - __init__.py
  - execution/                — 発注/約定関連（未実装テンプレート）
    - __init__.py
  - monitoring/               — 監視関連（未実装テンプレート）

主要ファイル（一覧）:
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/schema.py
- src/kabusys/data/pipeline.py
- src/kabusys/data/quality.py
- src/kabusys/data/audit.py

---

## 実運用上の注意 / ヒント

- レート制限:
  - J-Quants の制限（120 req/min）を守るため、モジュールは固定間隔スロットリングを実装しています。大量の並列リクエストは避けてください。
- トークン更新:
  - get_id_token はリフレッシュトークンを使って ID トークンを取得します。HTTP 401 を検知した場合は自動でリフレッシュして一度だけリトライします。
- 冪等性:
  - データ保存関数（save_*）は ON CONFLICT DO UPDATE を使い、重複や再実行に耐える設計です。
- バックフィル:
  - デフォルトで直近 N 日分を再取得することで、API の後出し修正（後追い修正）を吸収します（backfill_days=3 がデフォルト）。
- テスト:
  - env 自動ロードを無効にして（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）テスト用に明示的な設定を注入してください。
- DuckDB の ":memory:" を使えばメモリ DB での単体テストが容易です。

---

## 例: シンプルな ETL スクリプト

python
```
from kabusys.data import schema, pipeline
from kabusys.config import settings

# DB 初回作成 (既に存在する場合はスキップ)
conn = schema.init_schema(settings.duckdb_path)

# 日次 ETL 実行（デフォルト設定）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

---

## ライセンス / 貢献

（この README にライセンス情報は含まれていません。レポジトリルートに LICENSE ファイルを置いてください。）  
機能追加・バグ修正の提案は Pull Request を通じて歓迎します。

---

README はこのコードベースの現状（初期実装）を前提に記載しています。戦略や発注ロジック、監視機能は今後の拡張ポイントです。必要であればサンプル戦略や運用手順のテンプレートも作成します。必要な内容を教えてください。