# KabuSys

日本株向けの自動売買／データプラットフォーム基盤ライブラリです。  
J-Quants API から市場データ・財務データ・マーケットカレンダーを取得し、DuckDB に保存／加工、品質チェック、監査ログを備えた ETL パイプラインと監査スキーマを提供します。

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール群を含みます。

- J-Quants API クライアント（認証・ページネーション・レート制御・リトライ）
- DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 環境変数管理（.env の自動ロード機能）

設計上のポイント：
- API レート制限（J-Quants: 120 req/min）を厳守する RateLimiter 実装
- 401 受信時の自動トークンリフレッシュと、408/429/5xx に対する指数バックオフリトライ
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- 品質チェックは Fail-Fast とせず問題を収集して呼び出し元に返す

---

## 機能一覧

- データ取得
  - 株価日足（OHLCV）取得（fetch_daily_quotes）
  - 財務データ（四半期 BS/PL）取得（fetch_financial_statements）
  - JPX マーケットカレンダー取得（fetch_market_calendar）
- データ保存（DuckDB）
  - raw_prices / raw_financials / market_calendar などへの冪等保存（save_*）
- スキーマ初期化
  - init_schema(db_path) による全テーブル作成
  - 監査用スキーマの追加 init_audit_schema(conn) / init_audit_db(path)
- ETL
  - run_daily_etl(...)：カレンダー・株価・財務の差分ETL + 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
- 品質チェック
  - 欠損チェック（OHLC 欠損）
  - スパイク検出（前日比閾値）
  - 重複チェック（主キー重複）
  - 日付整合性チェック（未来日付・非営業日のデータ）
- 監査ログ（signal_events, order_requests, executions）
- 環境変数管理
  - プロジェクトルートの .env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）

---

## セットアップ手順

前提: Python 3.10+ を想定（型アノテーションに | を使用）。必要なパッケージは主に duckdb です。

1. 仮想環境の作成と有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

2. 必要パッケージのインストール
   - pip install duckdb

   （実行環境によっては追加で requests 等が使われる可能性があるため、要件に応じて追加してください。）

3. 環境変数の設定
   - プロジェクトルートに .env を配置すると自動ロードされます（.git や pyproject.toml を基準にプロジェクトルートを特定）。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

サンプル .env（必須キーを含む）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabu API（kabuステーション連携がある場合）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack（通知用）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DBパス（省略時 defaults: data/kabusys.duckdb）
DUCKDB_PATH=data/kabusys.duckdb

# 環境とログ
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

---

## 使い方（簡易ガイド）

以下は基本的な利用例です。Python スクリプトや REPL で実行できます。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（カレンダー先読み・バックフィル付き）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日
print(result.to_dict())
```

3) 品質チェックを個別実行
```python
from kabusys.data.quality import run_all_checks
from datetime import date

issues = run_all_checks(conn, target_date=date(2026,1,20))
for i in issues:
    print(i)
```

4) 監査スキーマの初期化（既存 conn に追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

5) 低レベル API を直接呼ぶ例（トークン取得・データ取得）
```python
from kabusys.data import jquants_client as jq

id_token = jq.get_id_token()  # settings の refresh token を使う
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,1,31))
jq.save_daily_quotes(conn, records)
```

注意点：
- run_daily_etl は内部でカレンダーを先に取得し、営業日に調整して株価／財務データを取得します。
- J-Quants のレート制限（120 req/min）を守るため内部で待ちが入ります。
- 401 を受け取った場合は自動的にリフレッシュを行い 1 回リトライします。

---

## 環境変数一覧（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知に使用する bot token
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注連携を行う場合）

オプション／デフォルトあり:
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 任意（設定すると .env の自動ロードを無効化）

設定が不足している必須キーを参照すると ValueError が発生します（Settings._require）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル/モジュールは以下の通りです（src/kabusys をルートとしたツリー）：

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（取得・リトライ・保存）
    - schema.py                 # DuckDB スキーマ定義・初期化
    - pipeline.py               # ETL パイプライン（差分更新・バックフィル・品質チェック）
    - audit.py                  # 監査ログ（signal/order_request/executions）
    - quality.py                # データ品質チェック
  - execution/
    - __init__.py               # (発注・実行ロジックの拡張ポイント)
  - strategy/
    - __init__.py               # (戦略モジュールの拡張ポイント)
  - monitoring/
    - __init__.py               # (監視・アラート用拡張ポイント)

主要なエントリポイント:
- data.schema.init_schema / get_connection
- data.jquants_client.fetch_* / save_*
- data.pipeline.run_daily_etl（高レベル ETL）
- data.quality.run_all_checks
- data.audit.init_audit_schema / init_audit_db

---

## 開発・テスト時のヒント

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を基準に行われます。テストで環境を汚したくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化してください。
- ETL の差分ロジックは DB の最終取得日を参照します。初回ロード時は最小日付（2017-01-01）から取得します。
- DuckDB のパスを ":memory:" にすることでインメモリ DB を使い、テストを高速にできます。
- jquants_client はページネーション中の id_token をモジュールレベルでキャッシュし、必要に応じてリフレッシュします。get_id_token の呼び出しでは allow_refresh=False を指定して無限再帰を防いでいます。

---

もし README に追加したい実行例（デプロイ手順、CI 設定、発注シミュレーション例など）があれば教えてください。必要に応じてサンプルスクリプトや .env.example の完全版を作成します。