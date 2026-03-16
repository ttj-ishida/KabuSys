# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ (KabuSys)

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けのデータ収集・ETL、スキーマ定義、監査ログ機能を提供する Python モジュール群です。主に J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存し、品質チェック・監査ログ・戦略／実行層の基盤を整備します。

設計上のポイント:
- J-Quants API のレート制限（120 req/min）を遵守するレートリミッタ
- リトライ（指数バックオフ）、401 受信時の自動トークンリフレッシュ
- データ取得時刻（fetched_at）の記録によるトレーサビリティ（Look-ahead bias 対策）
- DuckDB への挿入は冪等（ON CONFLICT DO UPDATE）
- ETL 内での品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（OHLCV、財務、マーケットカレンダー取得）
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - 保存関数: save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）と初期化関数
  - init_schema(db_path) / get_connection(db_path)
- data/pipeline.py
  - 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
  - run_daily_etl(conn, target_date=..., ...)
- data/quality.py
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - run_all_checks(conn, ...)
- data/audit.py
  - 監査ログ用スキーマと初期化（signal_events / order_requests / executions）
  - init_audit_schema(conn) / init_audit_db(db_path)
- config.py
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）、Settings 経由の型付きアクセス
  - 環境: development / paper_trading / live をサポート

---

## セットアップ手順

前提:
- Python 3.9+ を推奨（コードは型ヒントに Union/| を使用）
- DuckDB を使用（Python パッケージ `duckdb`）

1. リポジトリをクローン / 配布を取得:
   - 例: git clone <repo>

2. 仮想環境作成（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール:
   - pip install duckdb
   - （必要に応じて logging 等は標準ライブラリで賄われます）
   - 将来的には `requirements.txt` を用意して pip install -r することを想定

4. 環境変数の設定:
   - プロジェクトルート（.git か pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（自動ロード無効化目的で `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定可能）。
   - 必須環境変数（Settings が要求するもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN: Slack 通知（Bot）用トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN="xxxxxxxx"
   KABU_API_PASSWORD="your_kabu_password"
   SLACK_BOT_TOKEN="xoxb-xxxx"
   SLACK_CHANNEL_ID="C01234567"
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベーススキーマの初期化:
   - Python REPL やスクリプトから:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")
   - 監査ログを別 DB にする場合:
     - from kabusys.data import audit
     - conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
   - 既に init_schema で作成済みの DB へ接続する場合:
     - conn = schema.get_connection("data/kabusys.duckdb")

---

## 使い方（基本例）

基本的な日次 ETL の実行例（スクリプト形式）:

例: run_etl.py
```python
from datetime import date
from kabusys.data import schema, pipeline

# DB 初期化（存在しなければ作成）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると今日）
result = pipeline.run_daily_etl(conn, target_date=date.today())

print(result.to_dict())
```

J-Quants API を直接利用してデータ取得 / 保存する例:
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")

# トークンは内部で settings.jquants_refresh_token を使用（自動リフレッシュ対応）
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

監査ログの初期化:
```python
from kabusys.data import schema, audit
conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)  # 既存接続に監査テーブルを追加
```

品質チェックの実行:
```python
from kabusys.data import schema, quality
conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

設定の参照（コード内で）:
```python
from kabusys.config import settings
print(settings.kabu_api_base_url)
print(settings.is_live)
```

注意:
- pipeline.run_daily_etl は各ステップ（カレンダー・株価・財務・品質）を順に実行します。各ステップは独立して例外処理され、可能な限り処理を継続します。戻り値は ETLResult オブジェクトです。
- jquants_client は API のページネーション、レート制御、リトライ、401 の自動リフレッシュを内蔵しています。

---

## 環境変数（主要一覧）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン（通知用）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（値が設定されていれば無効）

---

## ディレクトリ構成

リポジトリの主要ファイル（src 以下を記載）:

- src/
  - kabusys/
    - __init__.py
    - config.py                  # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py        # J-Quants API クライアント（取得・保存ロジック）
      - schema.py                # DuckDB スキーマ定義・初期化
      - pipeline.py              # ETL パイプライン（差分更新・品質チェック）
      - audit.py                 # 監査ログ（トレーサビリティ）初期化
      - quality.py               # データ品質チェック
    - strategy/
      - __init__.py              # 戦略関連（拡張ポイント）
    - execution/
      - __init__.py              # 発注 / 約定 / ブローカー連携（拡張ポイント）
    - monitoring/
      - __init__.py              # 監視・メトリクス（拡張ポイント）

---

## 実運用上の注意・ベストプラクティス

- API レート制御: jquants_client は固定間隔スロットリングを用いていますが、複数プロセスで同一 API トークンを共有する場合は別途プロセス間調整が必要です。
- トークン管理: J-Quants のリフレッシュトークンは慎重に管理し、.env は外部から読み取られないように権限を設定してください。
- 本番環境フラグ: KABUSYS_ENV を `live` にすることで実行コンテキストを区別します（is_live 等をコード内で利用）。
- 監査ログ: 発注や約定の監査ログは削除しない前提です。order_request_id は冪等キーとして扱い、二重発注を防止します。
- 品質チェック: run_daily_etl は品質チェックでエラーが検出されても ETL 自体は続行します（呼び出し側で停止判断を行ってください）。
- テスト・CI: 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると良いです。

---

## 拡張ポイント

- strategy と execution パッケージは現状プレースホルダですが、ここに戦略実装（シグナル生成）・ブローカー接続（kabu ステーション API）・リスク管理などを実装できます。
- モニタリング（monitoring）: メトリクス収集／アラートの統合に利用できます。
- Slack 通知: Settings で Slack トークンを取得済みのため、ETL の結果通知やアラート送信を実装可能です。

---

もし README に追加してほしい具体的な使用例（cron や Airflow のジョブ例、Dockerfile、CI 設定など）があればお知らせください。必要に応じて .env.example のテンプレート作成やサンプルスクリプトも作成します。