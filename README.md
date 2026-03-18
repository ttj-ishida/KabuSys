# KabuSys

日本株自動売買プラットフォーム（モジュール群）のリポジトリ用 README。  
本ドキュメントはソースコード（src/kabusys 以下）を元に作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なデータ取得・ETL・データ品質チェック・監査ログ・ニュース収集などをモジュール化したライブラリ群です。主要な役割は以下の通りです。

- J-Quants API からの市場データ（株価日足、財務データ、JPX カレンダー）取得
- RSS からのニュース収集および銘柄抽出
- DuckDB を用いたデータスキーマ定義と永続化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- 市場カレンダー管理（営業日判定、next/prev/trading days 等）
- 監査ログ（シグナル→発注→約定のトレース用スキーマ）
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）

設計上の特徴として、API レート制限・リトライ・トークン自動リフレッシュ、冪等性を意識した DB 操作、SSRF 対策や XML パースの安全化（defusedxml など）が組み込まれています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（rate limiter、リトライ、トークンリフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への冪等的保存（save_* 関数）
- data.news_collector
  - RSS フィード取得、記事正規化、ID生成（SHA-256）、SSRF対策、Gzip/サイズチェック
  - raw_news への冪等保存、news_symbols（銘柄紐付け）
- data.schema
  - DuckDB スキーマ（Raw/Processed/Feature/Execution）定義と init_schema()
- data.pipeline
  - 差分ETL（run_daily_etl）: カレンダー→株価→財務→品質チェック
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- data.calendar_management
  - 営業日判定関数（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）
  - calendar_update_job（夜間更新バッチ）
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- data.audit
  - 監査ログ用スキーマ（signal_events, order_requests, executions）と初期化関数 init_audit_schema / init_audit_db
- config
  - 環境変数管理（.env 自動読み込み、必須チェック、設定値取得用 settings）

---

## セットアップ手順（開発者向け）

前提
- Python 3.10 以上（ソースで `X | Y` 型ヒントを使用）
- DuckDB が必要（Python パッケージ duckdb）
- defusedxml（安全な XML パースのため）
- ネットワークアクセス（J-Quants API / RSS）

例: 必要パッケージのインストール（仮想環境内で）
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 実プロジェクトでは requirements.txt / pyproject.toml からインストールしてください
```

環境変数
- 自動的にプロジェクトルート（.git または pyproject.toml がある場所）から `.env` / `.env.local` を読み込みます。
  - 読み込み順: OS 環境 > .env.local (override=True) > .env (override=False)
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 主要な環境変数（必須は明記）
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
  - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
  - KABU_API_BASE_URL — デフォルト `http://localhost:18080/kabusapi`
  - SLACK_BOT_TOKEN (必須) — Slack 通知用
  - SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネルID
  - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
  - SQLITE_PATH — デフォルト `data/monitoring.db`
  - KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト `development`）
  - LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト `INFO`）

DuckDB 初期化
- スキーマを作成するには data.schema.init_schema(db_path) を呼び出します。親ディレクトリが無ければ自動作成されます。

監査用 DB
- 監査ログ専用 DB を作る場合は data.audit.init_audit_db(db_path) を使用します（UTC タイムゾーン固定）。

---

## 使い方（簡単なコード例）

Python スクリプト例を示します。実務ではログ設定や例外処理を適切に行ってください。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path
```

2) 日次 ETL 実行（J-Quants からデータ取得して保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)  # 既存 DB へ接続
result = run_daily_etl(conn)  # デフォルトで今日の ETL 実行
print(result.to_dict())
```

3) RSS ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う有効な銘柄コード集合（例: {"7203", "6758"}）
results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(results)  # {source_name: 新規保存件数}
```

4) 監査テーブル初期化
```python
from kabusys.data.schema import get_connection
from kabusys.data.audit import init_audit_schema

conn = get_connection("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

5) J-Quants API を直接呼ぶ（ID トークン取得）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

token = get_id_token()  # settings.JQUANTS_REFRESH_TOKEN を使用して idToken を取得
quotes = fetch_daily_quotes(id_token=token, code="7203", date_from="20230101", date_to="20231231")
```

注意点
- jquants_client はレート制限（120 req/min）に従うため内部で待機します。
- 401 が返った場合はリフレッシュトークンで自動リフレッシュして 1 回再試行します。
- ネットワークエラーや 408/429/5xx は指数バックオフ付きでリトライします（最大3回）。

---

## ディレクトリ構成（概要）

以下はリポジトリ内の主要なファイル・モジュール（src/kabusys 以下）の抜粋です。

- src/
  - kabusys/
    - __init__.py
    - config.py              # 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py    # J-Quants API クライアント（取得・保存）
      - news_collector.py    # RSS ニュース収集・正規化・DB保存
      - schema.py            # DuckDB スキーマ定義・初期化
      - pipeline.py          # ETL パイプライン（差分更新・品質チェック）
      - calendar_management.py  # カレンダー管理（営業日判定等）
      - audit.py             # 監査ログ（シグナル→発注→約定のトレース）
      - quality.py           # データ品質チェック
      - pipeline.py
    - strategy/
      - __init__.py          # 戦略関連モジュール（拡張ポイント）
    - execution/
      - __init__.py          # 発注 / 実行関連（拡張ポイント）
    - monitoring/
      - __init__.py

（実際の追加モジュールやドキュメントはプロジェクトのルートにあるはずです）

---

## 運用上の注意 / 実装上のポイント

- 環境変数の自動読み込み
  - プロジェクトルートにある `.env` / `.env.local` が自動で読み込まれます。テストで無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 冪等性
  - DB 保存処理は可能な限り ON CONFLICT DO UPDATE / DO NOTHING を使って冪等性を担保しています。
- セキュリティ
  - RSS の XML パースは defusedxml を使い、SSRF 対策（スキーム検証、ホストのプライベートアドレスチェック、リダイレクト検査）を実装しています。
- 日付/時間
  - 監査系・fetched_at 等のタイムスタンプは UTC を想定して保存する設計が組み込まれています（audit.init_audit_schema は TimeZone を UTC に固定します）。
- 品質チェックは Fail-Fast ではなく全件収集を行い、呼び出し元が判断して運用停止等の対処を行う設計です。

---

## さらに進めるために

- strategy / execution / monitoring パッケージは拡張ポイントです。戦略ロジックや発注実装、監視処理をここに実装します。
- CI / デプロイや実運用では、ログの集中化、ジョブスケジューラ（cron/airflow 等）、障害時のリトライポリシー、証券会社 API の発注安全性（冪等キー、二重発注防止）を整備してください。
- 本 README はソースコードから自動生成された概要を含みます。実際の利用にあたってはプロジェクト固有の README/.env.example/運用手順を確認してください。

---

必要なら README の英語版や .env.example のテンプレート、さらに具体的な運用手順（cron ジョブ例や Docker 起動手順など）を追加できます。追加希望の項目を教えてください。