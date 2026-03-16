# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
J-Quants API や kabuステーション と連携してデータ取得（OHLCV、財務、マーケットカレンダー）・ETL・データ品質チェック・監査ログ（トレーサビリティ）を行うための基盤を提供します。

バージョン: 0.1.0

---

## 主要機能

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務諸表、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）順守
  - 再試行（指数バックオフ, 最大3回）、401 時の自動トークンリフレッシュ
  - ページネーション対応、取得時刻（fetched_at）を UTC で記録

- DuckDB ベースのスキーマ管理
  - Raw / Processed / Feature / Execution 層を含むスキーマ DDL を提供
  - インデックス定義・冪等なテーブル初期化（CREATE IF NOT EXISTS / ON CONFLICT）

- ETL パイプライン
  - 差分更新（最終取得日からの差分取得、バックフィル対応）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - ETL 実行結果を集約する ETLResult（品質問題やエラーの収集）

- 監査ログ（audit）
  - シグナル→発注→約定まで UUID を連鎖させてトレース可能にする監査テーブル群
  - 発注の冪等性（order_request_id）をサポート
  - UTC タイムスタンプ保存

- 設定管理
  - .env / .env.local / OS 環境変数からの設定自動読み込み（プロジェクトルートを検出して自動ロード）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能

---

## 必須依存ライブラリ

- Python 3.10+
  - (型注釈に `X | None` 形式を使用しているため 3.10 以降を推奨)
- duckdb
- 標準ライブラリ（urllib, logging, json, datetime 等）

pip でのインストール例（プロジェクトルートで）:
```bash
python -m pip install -r requirements.txt
# requirements.txt がない場合:
python -m pip install duckdb
```

（必要に応じてパッケージ化・セットアップを追加してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python と依存パッケージをインストール（上記参照）
3. プロジェクトルートに `.env`（および `.env.local`）を配置

推奨される環境変数（`.env` の一例）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token

# kabuステーション
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack（通知等）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# データベースパス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動読み込みの仕様:
- 自動ロード順序: OS 環境変数 > .env.local > .env
- プロジェクトルートは `.git` または `pyproject.toml` を親階層で探索して決定
- テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## 使い方（簡単な例）

以下は代表的な利用例の抜粋です。詳細は各モジュールを参照してください。

- DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```
- 監査ログテーブルの初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```
- J-Quants の ID トークン取得
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して取得
```
- ETL の日次実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```
- 個別データ取得（例: 銘柄の日足をフェッチして保存）
```python
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,1))
saved = jq.save_daily_quotes(conn, records)
```

- 品質チェックを単体で実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

ヒント:
- テストや一時実行には DuckDB のインメモリ接続 `":memory:"` を使用できます:
  conn = init_schema(":memory:")

---

## 主要モジュール / API 概要

- kabusys.config
  - settings: 環境変数からアプリケーション設定を取得（必須キーは _require で検証）
  - 主要プロパティ: jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(...)

- kabusys.data.quality
  - check_missing_data(...)
  - check_spike(...)
  - check_duplicates(...)
  - check_date_consistency(...)
  - run_all_checks(...)

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## ディレクトリ構成

リポジトリの主要ファイル/ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - schema.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主要な役割:
- data: データ取得（J-Quants）／DBスキーマ／ETL／データ品質／監査ログ
- strategy: 売買戦略を置く場所（このリポジトリでは初期化のみ）
- execution: 発注・ブローカー連携関連（初期化のみ）
- monitoring: 監視・メトリクス（初期化のみ）

---

## 運用上の注意

- レート制限・再試行: jquants_client は 120 req/min に基づくスロットリングとリトライ（指数バックオフ）を実装済みですが、大量取得や並列化を行う場合はこの実装が十分か検討してください。
- トークン管理: get_id_token は refresh token を使って id token を取得し、モジュール内でキャッシュします。テストや複数プロセス構成ではキャッシュの整合性に注意してください。
- 時刻は UTC を基準に扱う方針です（fetched_at / created_at 等）。
- 品質チェックは Fail-Fast ではなく全件収集を行います。ETL の停止制御は呼び出し側で行ってください。
- DuckDB の DDL は CREATE IF NOT EXISTS / ON CONFLICT を使って冪等性を担保しています。スキーマ変更は互換性を考慮して行ってください。

---

## 追加情報 / 開発

- テストを行う際は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して .env の自動読み込みを無効化できます。
- audit（監査）用の DDL は data.audit モジュールにあり、別途 init_audit_schema を呼び出して組み込めます。
- 将来的には strategy / execution / monitoring 層に具体的な実装（アルゴリズム・ブローカー adapter・アラート出力）を追加してください。

---

ご不明点や README の補足に必要な項目（例: CI、実運用時の注意点、追加の依存パッケージなど）があれば教えてください。README を拡張して追記します。