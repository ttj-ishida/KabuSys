# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants API からマーケットデータや財務情報、JPX カレンダーを取得して DuckDB に蓄積し、ニュース収集やデータ品質チェック、監査ログ（発注→約定のトレース）までをサポートします。戦略や発注部分は拡張可能なモジュール構成になっています。

---

## 概要

主に次の目的を持つモジュール群で構成されています。

- J-Quants API クライアント（レート制御、リトライ、トークン自動更新を含む）
- データ ETL パイプライン（差分更新・バックフィル・品質チェック）
- ニュース収集（RSS からの記事取得・正規化・銘柄紐付け）
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 監査ログテーブル（シグナル〜発注〜約定のトレーサビリティ）
- カレンダー管理（営業日判定・夜間更新ジョブ）
- （拡張箇所）strategy, execution, monitoring パッケージ

設計上のポイント:
- API レート制限（J-Quants: 120 req/min）を守る RateLimiter を実装
- リトライ（指数バックオフ、408/429/5xx、401 時は自動リフレッシュ）
- ETL は冪等（ON CONFLICT）で安全に再実行可能
- ニュース収集は SSRF 対策・XML 脆弱性対策・受信サイズ制限など安全対策を実施
- データ品質チェックで欠損/重複/日付不整合/スパイクを検出

---

## 機能一覧

- データ取得
  - 株価日足（OHLCV）取得 / 保存（fetch_daily_quotes / save_daily_quotes）
  - 財務データ（四半期 BS/PL）取得 / 保存（fetch_financial_statements / save_financial_statements）
  - JPX マーケットカレンダー取得 / 保存（fetch_market_calendar / save_market_calendar）
- ETL パイプライン
  - 差分更新、バックフィル（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 日次 ETL エントリ（run_daily_etl）
- ニュース収集
  - RSS 取得と前処理、DuckDB への冪等保存（fetch_rss / save_raw_news）
  - 記事 → 銘柄コードの抽出・紐付け（extract_stock_codes / save_news_symbols）
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合の検出（quality.run_all_checks 等）
- スキーマ管理
  - DuckDB スキーマ初期化（data.schema.init_schema）
  - 監査ログ（audit.init_audit_schema / init_audit_db）
- カレンダー管理
  - 営業日判定 / 翌営業日・前営業日取得（is_trading_day / next_trading_day / prev_trading_day）
  - 夜間カレンダー更新ジョブ（calendar_update_job）

---

## 前提条件

- Python 3.9+
- DuckDB（Python パッケージとして duckdb を利用）
- ネットワークアクセス（J-Quants API、RSS フィード）
- 必要な環境変数（下記参照）

推奨パッケージ（インストール済みであることを想定）:
- duckdb
- defusedxml

---

## 環境変数（主要）

プロジェクトルートの `.env` / `.env.local`、または OS 環境変数で設定します。自動読み込みはデフォルトで有効（プロジェクトルートに .git または pyproject.toml がある場合）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — {development, paper_trading, live}（デフォルト: development）
- LOG_LEVEL — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合に `1`
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）ファイル（デフォルト: data/monitoring.db）
- KABUSYS では .env.example を参考に .env を作成してください（コード内で .env.example の自動生成は行いません）。

例（.env の最小例）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 開発環境にインストール（パッケージルートが pyproject.toml を持つ想定）
   - 仮想環境推奨（venv, pyenv-virtualenv 等）
   - インストール:
     - pip install -e .  （ローカル開発用）
     - または pip install .（配布パッケージとして）

3. 必要パッケージをインストール（requirements があればそちらを使用）。最低限:
   - pip install duckdb defusedxml

4. 環境変数設定（.env を作成するか、OS 環境変数として設定）
   - プロジェクトルートに `.env` / `.env.local` を作成するか、環境にエクスポート

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # デフォルトパスと一致
```
  - 監査ログのみ別 DB に分けたい場合:
```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（代表的な例）

以下は基本的な Python スニペット例です。

- 日次 ETL（株価・財務・カレンダーの差分取得＆品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data import schema, pipeline

# DB 初期化（必要に応じて一度だけ）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL（引数で target_date / id_token / バックフィル等を指定可能）
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ（RSS）
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存接続
# 収集ソースをカスタマイズ可能（省略時は DEFAULT_RSS_SOURCES が使用される）
results = news_collector.run_news_collection(conn, known_codes={"7203", "6758"})
print(results)  # {source_name: new_saved_count}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

- J-Quants から直接データを取得する（テストやユーティリティ）
```python
from kabusys.data import jquants_client as jq
# トークンは settings から自動取得される（環境変数必須）
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 品質チェック（手動で実行）
```python
from kabusys.data import quality, schema
conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

---

## API の注意点

- J-Quants API のレート制限: 120 req/min を守るため内部で固定間隔のスロットリングを実施します。
- リトライ: ネットワーク 408/429/5xx の場合は指数バックオフで最大 3 回リトライします。
- トークン管理: 401 受信時は自動でリフレッシュを試み、1 回だけリトライします。
- DuckDB への保存は冪等に設計されています（ON CONFLICT DO UPDATE / DO NOTHING を多用）。
- ニュース収集では SSRF 対策・XML 防御（defusedxml）・受信サイズ制限を行っています。

---

## ディレクトリ構成（主要ファイルと役割）

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / 設定管理（自動 .env ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save 関数を提供）
    - news_collector.py — RSS ニュース取得・前処理・DB 保存・銘柄抽出
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理・営業日ロジック
    - schema.py — DuckDB スキーマ定義・初期化（init_schema / get_connection）
    - audit.py — 監査ログ（signal / order_request / executions）テーブル定義・初期化
    - quality.py — データ品質チェック
  - strategy/ — 戦略関連（拡張ポイント）
  - execution/ — 発注/ブローカー接続（拡張ポイント）
  - monitoring/ — 監視・アラート（拡張ポイント）

---

## 開発者向けポイント

- settings = kabusys.config.settings を通じて各種設定値を取得できます。
- 単体テスト環境などで自動 .env ロードを避けたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ニュースの article ID は URL の正規化後の SHA-256（先頭 32 文字）で冪等性を確保しています。
- DuckDB スキーマは初期化時に必要なディレクトリを自動作成します（ファイル DB を使用する場合）。

---

もし README に「インストール方法（パッケージ配布）」「CI やデプロイ手順」「具体的な .env.example ファイル」など追記したい点があれば、必要な情報を教えてください。必要に応じてサンプル .env.example や運用手順も作成します。