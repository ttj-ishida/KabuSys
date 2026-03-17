# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
J-Quants API や RSS ニュースフィード、DuckDB を用いたデータ収集・ETL・品質チェック・監査ログ機能を提供します。

主要な設計方針：
- データ取得は冪等（idempotent）に保存（DuckDB の ON CONFLICT を活用）
- API レート制限遵守・リトライ・トークン自動リフレッシュを実装
- ニュース収集は SSRF や XML 攻撃対策を施した安全設計
- 品質チェック・監査ログによるトレーサビリティ確保

---

## 機能一覧

- 環境変数・設定管理（自動 .env ロード、Settings クラス）
- J-Quants API クライアント（株価日足・財務・市場カレンダー）
  - レートリミット（120 req/min）のスロットリング
  - リトライ（指数バックオフ、特定ステータスの再試行）・401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアスを軽減
- DuckDB 用スキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
  - 日次 ETL エントリポイント（run_daily_etl）
- ニュース収集モジュール（RSS -> raw_news / news_symbols）
  - URL 正規化、トラッキングパラメータ除去、記事ID を SHA-256 で生成
  - DefusedXML を用いた XML 攻撃対策、受信サイズ制限、SSRF 対策
- マーケットカレンダー管理（営業日判定、前後営業日取得、夜間更新ジョブ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- DuckDB への便利な保存関数（save_daily_quotes 等）

---

## 前提・依存関係

- Python 3.10 以上（明示的な型記法（|）を使用）
- 必要パッケージ（代表例）
  - duckdb
  - defusedxml

インストール例（venv を利用）:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージをプロジェクトとしてインストールする場合（プロジェクト配布時）
pip install -e .
```

（プロジェクトを pip パッケージ化している場合は setup/pyproject からインストールしてください）

---

## 環境変数

このライブラリは環境変数（またはプロジェクトルートの .env / .env.local）から設定を読み込みます。自動ロードはデフォルトで有効です（.git または pyproject.toml をプロジェクトルート判定に利用）。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD : kabu API 用パスワード（必須）
- SLACK_BOT_TOKEN : Slack ボットトークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）

任意 / デフォルト:
- KABUSYS_ENV : development / paper_trading / live （デフォルト: development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL （デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）

自動 .env ロードを無効にする:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（簡易）

1. Python 環境を作成・有効化
2. 依存パッケージをインストール（duckdb, defusedxml 等）
3. プロジェクトルートに .env を作成して環境変数を設定
4. DuckDB スキーマを初期化

DuckDB スキーマ初期化例:
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリがなければ自動生成）
conn = schema.init_schema("data/kabusys.duckdb")
```

監査ログスキーマを追加する場合:
```python
from kabusys.data import audit

# 既存の conn に監査スキーマを追加
audit.init_audit_schema(conn)
```

---

## 使い方（主要ユースケース）

- 日次 ETL を実行する（市場カレンダー -> 株価 -> 財務 -> 品質チェック）:
```python
from kabusys.data import schema, pipeline
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- 市場カレンダー夜間更新ジョブ:
```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
```

- RSS ニュース収集実行:
```python
from kabusys.data import schema, news_collector

conn = schema.get_connection("data/kabusys.duckdb")
# デフォルトソースを使用。known_codes に有効な銘柄コードセットを渡すと銘柄紐付けを行う。
known_codes = {"7203", "6758", ...}
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)
```

- J-Quants から日足取得と保存を個別に実行:
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

- 品質チェックを個別実行:
```python
from kabusys.data import quality, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

---

## ディレクトリ構成（主要ファイル）

（この README は src 配下の構成に基づく想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・Settings 管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（差分取得・バックフィル）
    - calendar_management.py — 市場カレンダーの管理・営業日判定・更新ジョブ
    - audit.py               — 監査ログスキーマ（signal/order_request/executions）
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

---

## 開発メモ / 注意事項

- J-Quants の API レート制限（120 req/min）に合わせた固定間隔スロットリングを実装しています。大量取得時は呼び出し間隔に注意してください。
- ニュース収集は外部 URL を扱うため SSRF・XML 攻撃対策（_SSRFBlockRedirectHandler / defusedxml / MAX_RESPONSE_BYTES）を行っています。fetch_rss で受け入れる URL は http/https のみです。
- DuckDB のテーブルは ON CONFLICT を用いて冪等性を確保していますが、外部から直接 DB を編集した場合は品質チェックで検出される可能性があります。
- KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を設定するとパッケージ起動時の .env 自動読み込みを無効化できます（テスト等で利用してください）。
- すべての TIMESTAMP は UTC を想定している箇所があります（監査ログ等で明示）。

---

## まとまった流れ（推奨）

1. .env を準備して必須トークン等を設定
2. DuckDB を init_schema() で初期化（ファイル作成）
3. run_daily_etl() をスケジューラ（cron / Airflow 等）で日次実行
4. 監査ログを用いる場合は init_audit_schema() を実行して監査テーブルを作成
5. ニュース収集は別スケジュールや ETL 内で実行して raw_news を蓄積

---

必要であれば README をプロジェクトの実際の pyproject.toml / setup.cfg / CI スクリプトに合わせて調整します。追加で「運用ガイド（実行 cron 例、ログ設定、Slack 通知の利用例）」や「Xユースケースのコード例」を作成することも可能です。どの追加情報が欲しいか教えてください。