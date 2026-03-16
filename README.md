# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリ（骨組み）。  
データ収集（J-Quants）、DuckDB スキーマ管理、差分 ETL、データ品質チェック、監査ログなどを提供します。

---

## 概要

KabuSys は日本株のマーケットデータを自動的に取得・永続化し、戦略や発注ロジックが利用できるように整備するためのライブラリ群です。本リポジトリには主に以下を実装しています。

- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB 用のスキーマ定義／初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ用スキーマ（シグナル→発注→約定のトレース）

バージョン: `0.1.0`

---

## 主な機能一覧

- data/jquants_client.py
  - 日次株価（OHLCV）、財務（四半期 BS/PL）、JPX カレンダーの取得
  - API レート制御（120 req/min）、指数バックオフ再試行、401 自動リフレッシュ
  - DuckDB への冪等的保存（ON CONFLICT DO UPDATE）
- data/schema.py
  - DuckDB のフルスキーマ（raw, processed, feature, execution）を定義・初期化
  - インデックス作成、":memory:" モード対応
- data/pipeline.py
  - 差分 ETL（カレンダー先読み、株価と財務の差分取得＋バックフィル）
  - ETL 結果を ETLResult で返却（取得数／保存数／品質問題／エラー）
- data/quality.py
  - 欠損データ、スパイク、重複、日付不整合のチェック
  - 各チェックは QualityIssue を返す（error/warning）
- data/audit.py
  - 監査ログ用テーブル（signal_events, order_requests, executions）を初期化
  - トレーサビリティのための制約とインデックス

---

## 動作環境

- Python 3.10 以上（型注釈に `|` を使用）
- 必須パッケージ（例）
  - duckdb
- ネットワーク経由で J-Quants API を使用するためインターネット接続が必要

（プロジェクトに pyproject.toml / requirements があればそちらを参照してください）

---

## セットアップ手順（ローカル）

1. リポジトリを取得
   - git clone などで本リポジトリを取得します。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージをインストール
   - pip install -e .
   - pip install duckdb

   （プロジェクトに依存リストがあれば `pip install -r requirements.txt` を使用）

4. 環境変数を設定
   - 必要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意／デフォルト値
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development|paper_trading|live、デフォルト: development)
     - LOG_LEVEL (DEBUG|INFO|...、デフォルト: INFO)

   自動ロード:
   - パッケージはプロジェクトルート（.git か pyproject.toml）を探索し、`.env` と `.env.local` を自動で読み込みます。
   - 読み込み優先度: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単なクイックスタート）

以下は基本的な使い方例です。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH から取得される
conn = init_schema(settings.duckdb_path)
```

2) 監査ログテーブルを追加したい場合
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

3) 日次 ETL を実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日を対象に実行
print(result.to_dict())       # ETL の詳細結果を確認
```

4) jquants_client の直接呼び出し（テストや個別取得）
```python
from kabusys.data import jquants_client as jq

# id_token を指定しなければ内部キャッシュを使用（必要に応じ自動リフレッシュ）
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = jq.save_daily_quotes(conn, records)
```

---

## ETL の設計上のポイント

- 差分更新:
  - DB の最終取得日を基に未取得分だけを取得します。未取得がない場合はスキップ。
  - backfill_days（デフォルト 3 日）を使って、API の後出し修正を吸収するために数日前から再取得します。
- 品質チェック:
  - run_daily_etl の最後に品質チェックを実行（オプション）。問題は QualityIssue のリストとして返却されます。
  - 欠損はエラー扱い、スパイクは警告扱いといった分離がされています。
- J-Quants クライアント:
  - 120 req/min のレート制御を実装（固定間隔スロットリング）。
  - ネットワークエラーや 408/429/5xx に対し指数バックオフで最大 3 回リトライ。
  - 401 受信時は自動でリフレッシュして 1 回だけ再試行。

---

## API（主なモジュールと関数）

- kabusys.config
  - settings: アプリケーション設定（環境変数経由）
- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)
- kabusys.data.schema
  - init_schema(db_path) -> DuckDB connection
  - get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date: date|None, ...) -> ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.quality
  - run_all_checks(conn, target_date, ...) -> list[QualityIssue]
  - 各チェック: check_missing_data / check_spike / check_duplicates / check_date_consistency
- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(db_path)

---

## ディレクトリ構成（主要ファイル）

src/
  kabusys/
    __init__.py                # パッケージ定義（__version__）
    config.py                  # 環境変数 / 設定管理
    data/
      __init__.py
      jquants_client.py        # J-Quants API クライアント（取得・保存）
      schema.py                # DuckDB スキーマ定義・初期化
      pipeline.py              # ETL パイプライン（差分＋品質チェック）
      quality.py               # データ品質チェック
      audit.py                 # 監査ログ（signal/order/execution）
      pipeline.py
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py

（上記は本コードベースに含まれる主要モジュールです）

---

## 運用・開発時の注意点

- 環境変数の自動読み込みはプロジェクトルート（.git or pyproject.toml）から行われます。テストなどで自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のファイルパスのディレクトリは自動作成されますが、適切な権限が必要です。
- すべてのタイムスタンプは UTC を前提に扱っています（監査ログ初期化時に `SET TimeZone='UTC'` を実行）。
- J-Quants のレート制限/認証に配慮した実装が入っていますが、外部の API 利用規約に従ってください。
- ETL／品質チェックは "Fail-Fast" ではなく、可能な限り問題を収集して呼び出し元に通知する設計です。呼び出し元での扱い（停止・通知など）を検討してください。

---

## 連絡先 / 貢献

詳細な仕様書（DataPlatform.md や DataSchema.md）や CI、テストコードがあればそれらに従ってください。バグ報告や機能追加の提案は Issue を通じてお願いします。

---

README は以上です。必要であれば、インストール用の pyproject.toml / requirements.txt の例や、より詳しい ETL 実行・監視フロー（cron / Airflow / Prefect などでの運用例）を追加できます。どのトピックを拡張しますか？