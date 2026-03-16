# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
J-Quants API から市場データ・財務データ・マーケットカレンダーを取得して DuckDB に保存し、ETL／品質チェック／監査ログの基盤機能を提供します。

---

## 概要

KabuSys は以下の目的を持つ内部ライブラリです。

- J-Quants API から株価（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得
- DuckDB に冪等に保存（ON CONFLICT DO UPDATE）
- 日次 ETL パイプライン（差分取得・バックフィル・カレンダー先読み）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化

設計上のポイント：

- API レート制限（120 req/min）とリトライ（指数バックオフ、401 時の自動トークンリフレッシュ）
- Look-ahead バイアス対策のため取得時刻（UTC）を記録
- ETL は基本的に冪等（重複挿入に対して UPDATE）
- 品質チェックは fail-fast にせず、すべての問題を収集して呼び出し元に返す

---

## 主な機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB への冪等保存）
  - レートリミティング、リトライ、トークンキャッシュ
- data.schema
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) / get_connection(db_path)
- data.pipeline
  - 日次 ETL 実行 run_daily_etl(...)
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
  - 差分取得ロジック・バックフィル・カレンダー調整
- data.quality
  - 欠損、重複、スパイク、日付不整合チェック
  - run_all_checks(...) がすべてのチェックを統合
- data.audit
  - 監査ログ用テーブル（signal_events, order_requests, executions）
  - init_audit_schema(conn), init_audit_db(db_path)
- 設定管理（kabusys.config）
  - .env / .env.local の自動読込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 環境変数経由で各種設定（API トークン・DB パス・Slack 等）を取得

---

## システム要件 / 依存関係

- Python 3.10 以上（型注釈に union types を使用）
- duckdb (Python パッケージ)
- その他：標準ライブラリ（urllib, json, logging, datetime など）

インストール例（仮にパッケージをローカルで開発する場合）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
# pip install -e .  # packaging が整っている場合
```

（実際の追加依存は将来的に execution / monitoring 等で増える可能性があります）

---

## 環境変数（主要）

KabuSys は環境変数で設定を読み込みます。.env / .env.local による自動読み込みをサポート（プロジェクトルート検出による）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に利用される環境変数：

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須)  
  kabuステーション API パスワード
- KABU_API_BASE_URL (任意)  
  デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須)  
  Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID (必須)  
  Slack チャンネル ID
- DUCKDB_PATH (任意)  
  デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)  
  デフォルト: data/monitoring.db
- KABUSYS_ENV (任意)  
  development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意)  
  DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

.env の例:

```
JQUANTS_REFRESH_TOKEN="xxxx..."
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化
2. 必要なパッケージをインストール（少なくとも duckdb）
3. プロジェクトルートに .env を作成して必要な環境変数を設定
4. DuckDB スキーマを初期化

スキーマ初期化の例（Python スクリプト）:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

db_path = settings.duckdb_path  # 環境変数から取得可能
conn = init_schema(db_path)     # テーブル群を作成して接続を返す
conn.close()
```

監査ログ（audit）スキーマを追加したい場合:

```python
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
conn.close()
```

---

## 使い方（基本例）

- 日次 ETL 実行

簡単な ETL 実行スクリプト例:

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# DB 初期化（既に初期化済みであればスキップして接続のみ取得）
conn = init_schema(settings.duckdb_path)

# ETL を実行（ターゲット日を省略すると今日）
result = run_daily_etl(conn)
print(result.to_dict())

conn.close()
```

- API からデータを直接取得する（テスト用など）

```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

token = jq.get_id_token()  # settings.jquants_refresh_token を使用して id_token を取得
records = jq.fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))
print(len(records))
```

- ETL 内部の個別ジョブを使う場合

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl

conn = init_schema("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- 品質チェックを単独で実行する

```python
from kabusys.data.schema import get_connection
from kabusys.data.quality import run_all_checks
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## ディレクトリ構成

（リポジトリ内の主要ファイル構造の概略）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - schema.py              — DuckDB スキーマ定義 / init_schema / get_connection
    - pipeline.py            — ETL パイプライン（差分処理・backfill・品質チェック）
    - quality.py             — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py               — 監査ログ（signal / order_request / execution）
    - pipeline.py
  - strategy/                — 戦略層のプレースホルダ（将来的に拡張）
  - execution/               — 発注実行層のプレースホルダ（将来的に拡張）
  - monitoring/              — 監視/メトリクスのプレースホルダ
- pyproject.toml (存在する場合、プロジェクトルート検出に使用)
- .git/ (存在する場合、プロジェクトルート検出に使用)
- .env, .env.local (任意)

---

## 実装上の注意点 / ベストプラクティス

- Python のバージョンは 3.10 以上を推奨（型アノテーションで新構文を使用）
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。CI やテストで自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のファイルパスは settings.duckdb_path で指定されます。ファイルの親ディレクトリが存在しない場合、init_schema が自動作成します。
- J-Quants API のレート制限（120 req/min）を尊重してください。jquants_client 内で固定間隔スロットリングとリトライを備えていますが、追加リクエストを投げる場合は注意してください。
- ETL は差分更新＆バックフィル方式です。バックフィル日数の調整により API の後出し修正（データ修正）を吸収できます。
- 監査ログは削除しない前提で設計されています（FK は ON DELETE RESTRICT）。トレーサビリティを重要視してください。

---

## 今後の拡張候補（参考）

- execution 層の実実装（kabu ステーションとの連携、発注再試行、約定処理）
- strategy 層の具体的なアルゴリズム / バックテストモジュール
- モニタリング・アラート（Slack / メトリクス送信の実装）
- パッケージ化 / CLI ツールの提供（ETL を cron / Airflow から呼ぶためのコマンド）

---

もし README に含めてほしい追加情報（例えば CI の設定例、具体的な .env.example、サンプルデータの取得手順、CLI コマンドなど）があれば教えてください。必要に応じて追記します。