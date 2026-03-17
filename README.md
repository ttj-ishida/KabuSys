# KabuSys

日本株向けの自動売買データ基盤 / ETL / 監査ライブラリです。  
J-Quants API から市場データ（株価、財務、カレンダー）や RSS ニュースを取得し、DuckDB に冪等に保存、品質チェックや監査（発注～約定トレース）までをサポートします。

---

## 主な特徴

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）を尊重する内部 RateLimiter
  - リトライ（指数バックオフ）、401 受信時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB へ冪等保存（ON CONFLICT で UPDATE）

- ニュース収集（RSS）
  - RSS フィードの取得・前処理（URL除去・空白正規化）
  - 記事ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性確保
  - SSRF 対策（スキーム検査・プライベートIPブロック・リダイレクト検査）
  - defusedxml を使用して XML 攻撃を防止
  - DuckDB へのトランザクション単位のバルク挿入（INSERT ... RETURNING）

- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層を想定したスキーマ
  - 必要なテーブル・インデックスを自動作成する初期化関数を提供

- ETL パイプライン
  - 差分更新（最終取得日からの差分のみ取得）、バックフィルオプション
  - カレンダーの先読み（lookahead）対応
  - 品質チェック（欠損・重複・スパイク・日付不整合）を実行

- 監査ログ
  - シグナル→発注→約定のトレーサビリティを UUID 連鎖で保存
  - 監査用スキーマを別途初期化可能（UTC タイムゾーン固定）

---

## 要求環境 / 依存パッケージ

- Python 3.10 以上（型アノテーションで `|` を使用）
- 主要依存（最低限）:
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# もしパッケージ配布がある場合は `pip install -e .` を推奨
```

（プロジェクトによっては追加依存が必要になる可能性があります。requirements を用意している場合はそちらをご利用ください）

---

## 環境変数

config モジュールはプロジェクトルートの `.env` / `.env.local` を自動読み込みします（OS 環境変数 > .env.local > .env の優先順）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（実行時に必要となる項目）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意／デフォルト値:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: モニタリング用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env の自動ロード無効化

簡単な .env 例:
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

## セットアップ手順（ローカルでの最小セットアップ例）

1. リポジトリをクローンして仮想環境を作成・有効化
2. 依存パッケージをインストール（前節参照）
3. 必要な環境変数を `.env` に設定（上記参照）
4. DuckDB スキーマを初期化

例:
```bash
# 仮想環境作成
python -m venv .venv
source .venv/bin/activate

# 依存をインストール
pip install duckdb defusedxml

# .env を作成して必須値を設定（J-Quants トークンなど）

# Python REPL やスクリプトでスキーマ初期化
python - <<'PY'
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
print("initialized:", conn)
conn.close()
PY
```

監査ログ用 DB 初期化（別DBに分けたい場合）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要 API / サンプル）

以下は主要なユースケースの呼び出し例です。実際はスクリプトやジョブランナー、コンテナ化して定期実行することを想定しています。

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
conn.close()
```

- 単独で株価 ETL を実行（差分更新）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl

conn = init_schema("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
print("fetched", fetched, "saved", saved)
```

- RSS ニュース収集と銘柄紐付け（news_collector）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes は既知の有効銘柄コードの集合（例: {'7203','6758',...}）
results = run_news_collection(conn, known_codes=set(["7203", "6758"]))
print(results)  # {source_name: 新規保存件数}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("market_calendar saved:", saved)
```

- 監査スキーマの初期化（既存接続に追加）
```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 主要モジュールの概要

- kabusys.config
  - .env / 環境変数の読み込み・Settings オブジェクトの提供
  - 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を探索
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

- kabusys.data.jquants_client
  - J-Quants API への HTTP ラッパー（トークン管理・リトライ・ページネーション）
  - fetch_* / save_* 系関数（fetch_daily_quotes, save_daily_quotes 等）

- kabusys.data.news_collector
  - RSS 取得、前処理、DuckDB への冪等保存、銘柄コード抽出・紐付け
  - SSRF 対策やサイズ上限・gzip 解凍チェックを実装

- kabusys.data.schema
  - DuckDB スキーマ（DDL）を定義し初期化する init_schema 関数

- kabusys.data.pipeline
  - 日次 ETL / 個別 ETL ジョブ（prices/financials/calendar）と品質チェック統合

- kabusys.data.quality
  - 欠損、スパイク、重複、日付不整合を検出するチェック群（QualityIssue を返す）

- kabusys.data.calendar_management
  - 営業日判定、next/prev 営業日、期間内営業日取得、夜間カレンダー更新ジョブ

- kabusys.data.audit
  - 監査ログ（signal_events / order_requests / executions）スキーマと初期化関数

---

## ディレクトリ構成

（リポジトリの主要ファイル・ディレクトリを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - schema.py
    - jquants_client.py
    - pipeline.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - audit.py
    - pipeline.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

DuckDB スキーマで作成される主なテーブル（抜粋）:
- Raw: raw_prices, raw_financials, raw_news, raw_executions
- Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature: features, ai_scores
- Execution: signals, signal_queue, orders, trades, positions, portfolio_performance
- Audit: signal_events, order_requests, executions

---

## 運用上の注意 / 補足

- J-Quants API のレート制限（120 req/min）を守るよう内部で間隔制御を行っていますが、大量の並列処理を行う場合は上位で制御してください。
- DuckDB に対する大量挿入はチャンク分割・トランザクション制御を行っているため基本的に安全ですが、運用時はバックアップ・ローテーションを検討してください。
- news_collector は外部 URL を扱うため SSRF や巨大レスポンス対策を実装していますが、運用ネットワークポリシー（プロキシ／アクセス制限）に応じて調整してください。
- env の自動ロードは便利ですが、CI / テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して明示的に環境を制御することを推奨します。

---

README に記載のサンプルコードは簡易的な利用例です。実運用ではエラーハンドリング、ロギング設定、ジョブスケジューラ（cron / Airflow / Prefect 等）との統合、監視（alerts）を追加してください。質問や追加のドキュメントが必要であればお知らせください。