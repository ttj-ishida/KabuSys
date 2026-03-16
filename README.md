# KabuSys

日本株向け自動売買基盤（KabuSys）のライブラリ/モジュール群です。  
データ取得（J-Quants）、ETL・品質チェック、DuckDBスキーマ、監査ログなど、運用に必要な基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下の機能を備えたバックエンドライブラリです：

- J-Quants API を使った株価（OHLCV）、四半期財務、JPX マーケットカレンダーの取得
- DuckDB を用いた三層データレイヤ（Raw / Processed / Feature）と実行層のスキーマ定義・初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損／スパイク／重複／日付不整合）
- 監査ログ（シグナル → 発注要求 → 約定のトレースを担保する監査テーブル群）

設計上のポイント：
- J-Quants のレート制限（120 req/min）に対応するレートリミッタとリトライロジック
- トークン自動リフレッシュ（401 を検出して 1 回リフレッシュ）
- ETL/保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で安全に上書き可能
- 品質チェックは Fail-Fast ではなく全問題を収集して呼び出し元に委ねる

---

## 機能一覧

- data/jquants_client.py
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - レート制御・リトライ・トークンキャッシュを内蔵

- data/schema.py
  - init_schema(db_path)
  - get_connection(db_path)
  - DuckDB のテーブル群（raw_prices, raw_financials, market_calendar, features, signals, orders, trades, positions, など）を定義

- data/pipeline.py
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(...) — 日次 ETL のメインエントリ（カレンダー取得 → 株価 → 財務 → 品質チェック）

- data/quality.py
  - check_missing_data(...)
  - check_spike(...)
  - check_duplicates(...)
  - check_date_consistency(...)
  - run_all_checks(...)

- data/audit.py
  - init_audit_schema(conn)
  - init_audit_db(db_path)
  - 監査ログテーブル（signal_events, order_requests, executions）を初期化

- config.py
  - 環境変数読み込みロジック（.env, .env.local の自動読み込み）
  - Settings クラス（必要な環境変数をプロパティで提供）
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## 必要条件 / 依存関係

- Python 3.9+
- duckdb (DuckDB Python バインディング)
- そのほかは標準ライブラリ（urllib 等）を利用しています。実運用では Slack 通知や kabu API クライアント等を追加で導入する可能性があります。

※ パッケージ管理はプロジェクト側で提供される `pyproject.toml` や要求ファイルに従ってください。

---

## セットアップ手順

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb
   - （プロジェクトをパッケージとして提供している場合）pip install -e .

3. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（config.py の挙動）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトで以下を実行して DB ファイルとテーブルを作成します（デフォルトは `data/kabusys.duckdb` を想定）:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")

5. 監査ログテーブルの初期化（必要に応じて）
   - from kabusys.data import audit
   - conn = schema.get_connection("data/kabusys.duckdb")
   - audit.init_audit_schema(conn)
   - または audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 環境変数（.env の例）

最低限必要な環境変数（Settings で参照されます）:

- JQUANTS_REFRESH_TOKEN ・・・ J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      ・・・ kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN        ・・・ Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       ・・・ Slack チャンネル ID（必須）

オプション/デフォルト:
- KABUSYS_ENV            ・・・ development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              ・・・ DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD ・・・ 自動 .env ロードを無効化（1 をセット）
- KABUSYS_API_BASE_URL   ・・・ kabu API のベース URL（config では KABU_API_BASE_URL）
- DUCKDB_PATH            ・・・ DuckDB のパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            ・・・ 監視用 SQLite（デフォルト: data/monitoring.db）

例（.env）:
"""
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
"""

自動 .env パーサはコメントやクォートをある程度サポートします。

---

## 使い方（サンプル）

- DuckDB スキーマの初期化:

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 監査ログスキーマの追加:

```python
from kabusys.data import audit
# 既存の conn に監査テーブルを追加する
audit.init_audit_schema(conn)
```

- J-Quants トークンを取得（明示的に）:

```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用して取得
```

- 株価データの取得と保存（直接呼び出す例）:

```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"fetched={len(records)}, saved={saved}")
```

- 日次 ETL の実行（推奨）:

```python
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())
```

run_daily_etl は以下の流れを実行します：
1. マーケットカレンダー取得（先読み）
2. 株価日足 ETL（差分 + backfill）
3. 財務データ ETL（差分 + backfill）
4. 品質チェック（run_quality_checks=True の場合）

- 品質チェックのみ実行:

```python
from kabusys.data import quality, schema

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

注:
- jquants_client はリトライ／レート制御／401 の自動リフレッシュを行います。テスト時は id_token を外部から注入して deterministic にできます。

---

## ディレクトリ構成

プロジェクト内の主なファイル/モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント（fetch/save）
    - schema.py                # DuckDB スキーマと初期化
    - pipeline.py              # ETL パイプライン（差分取得・バックフィル・品質チェック）
    - quality.py               # データ品質チェック
    - audit.py                 # 監査ログ（signal/order_request/executions）
    - pipeline.py
    - audit.py
  - strategy/
    - __init__.py              # 戦略モジュール（未実装のプレースホルダ）
  - execution/
    - __init__.py              # 実行（ブローカー連携）モジュール（プレースホルダ）
  - monitoring/
    - __init__.py              # 監視・アラートモジュール（プレースホルダ）

Data / schema の DDL は以下のレイヤに分かれています：
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, orders, trades, positions, portfolio_performance
- Audit: signal_events, order_requests, executions（監査専用）

---

## 運用上の注意

- 環境変数は必須項目に未設定があると Settings プロパティで ValueError を投げます。`.env.example` を参考に `.env` を作成してください。
- J-Quants API のレート制限（120 req/min）を超えないように設計されていますが、長時間の大量取得や複数プロセスによる同時実行には注意してください。
- DuckDB のファイルはバイナリ形式であり、複数プロセスからの並行書き込みは適切なロック設計が必要です。並列 ETL を行う場合は接続管理に注意してください。
- 監査ログテーブルは基本的に削除しない前提で設計されています（FK は ON DELETE RESTRICT）。

---

必要があれば README を拡張して、CI / テスト、開発フロー、運用手順（Cron や Airflow での ETL スケジューリング例）、Slack 通知の実装例等を追加します。どの情報を優先して追記しますか？