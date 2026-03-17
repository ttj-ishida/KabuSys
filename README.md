# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（KabuSys）。  
データ取得（J-Quants）、ETL パイプライン、ニュース収集、DuckDB スキーマ、監査ログ、マーケットカレンダー管理など、取引戦略・実行基盤の基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を備えた内部ライブラリです。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB ベースのスキーマ定義 / 初期化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と記事の DB 保存（SSRF対策・トラッキング除去・冪等保存）
- マーケットカレンダー管理（営業日判定、次/前営業日の取得）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- データ品質チェック（欠損、スパイク、重複、日付不整合検出）

設計上の特徴：
- ETL/保存は冪等（ON CONFLICT）を意識しているため再実行が安全
- Look-ahead bias 対策のため fetched_at / 時刻は UTC で記録
- ネットワーク・XML パース・SSRF 等のセキュリティ対策を導入

---

## 機能一覧

主な公開 API / 機能（抜粋）

- 環境設定
  - kabusys.config.settings: 環境変数から設定を取得
- データ取得（J-Quants）
  - jquants_client.get_id_token(...)
  - jquants_client.fetch_daily_quotes(...)
  - jquants_client.fetch_financial_statements(...)
  - jquants_client.fetch_market_calendar(...)
  - jquants_client.save_daily_quotes(...)
  - jquants_client.save_financial_statements(...)
  - jquants_client.save_market_calendar(...)
- データベース / スキーマ
  - data.schema.init_schema(db_path)
  - data.schema.get_connection(db_path)
- ETL パイプライン
  - data.pipeline.run_daily_etl(...)
  - data.pipeline.run_prices_etl(...)
  - data.pipeline.run_financials_etl(...)
  - data.pipeline.run_calendar_etl(...)
- ニュース収集
  - data.news_collector.fetch_rss(url, source)
  - data.news_collector.save_raw_news(conn, articles)
  - data.news_collector.run_news_collection(conn, sources, known_codes)
- マーケットカレンダー管理
  - data.calendar_management.is_trading_day(conn, date)
  - data.calendar_management.next_trading_day(conn, date)
  - data.calendar_management.prev_trading_day(conn, date)
  - data.calendar_management.get_trading_days(conn, start, end)
  - data.calendar_management.calendar_update_job(conn, lookahead_days)
- 監査ログ
  - data.audit.init_audit_db(db_path)
  - data.audit.init_audit_schema(conn)
- 品質チェック
  - data.quality.run_all_checks(conn, target_date, reference_date, spike_threshold)

---

## 必要な環境変数

このプロジェクトはいくつかの必須環境変数を参照します。例:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID

オプション（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite (monitoring) ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG" | "INFO" | ... )（デフォルト: INFO）

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

注意:
- settings.* のプロパティは未設定時に ValueError を投げます（必須項目）。

サンプル `.env`（実際の値は各自で差し替えてください）:
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

## セットアップ手順

1. Python のインストール
   - 対応する Python バージョン（3.9+ 推奨）を用意してください。

2. 必要パッケージのインストール
   - 必要な外部依存（少なくとも以下）をインストールしてください:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - プロジェクトに requirements ファイルがあればそれを使用してください。

3. パッケージのインストール（開発）
   - プロジェクトルートで:
     - pip install -e .

4. 環境変数の設定
   - 上記の必須環境変数を `.env` または OS 環境に設定してください。
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定）。

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで以下を実行して DB とテーブルを初期化します:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
   - 監査用 DB は別途初期化できます:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（代表的な例）

以下は簡単な利用例。適宜ログ設定や例外ハンドリングを追加してください。

1) 日次 ETL の実行（単一スクリプト内で）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)
print(result.to_dict())
```

2) 市場カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

3) ニュース収集の実行（RSS）
```python
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection(settings.duckdb_path)
# sources を省略するとデフォルトの RSS ソースを使用
results = run_news_collection(conn, known_codes={"7203", "6758"})  # known_codes は任意
print(results)
```

4) J-Quants から直接データ取得（テスト/ユーティリティ）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

token = jq.get_id_token()  # settings.jquants_refresh_token を使用して取得
records = jq.fetch_daily_quotes(id_token=token, date_from="20230101", date_to="20230131")
```

5) 品質チェックを個別実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

---

## ディレクトリ構成

リポジトリ内の主要ファイル・ディレクトリ（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定読み込みロジック
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存）
    - news_collector.py               — RSS ニュース収集・保存
    - schema.py                       — DuckDB スキーマ定義 / 初期化
    - pipeline.py                     — ETL パイプライン（差分更新・日次 ETL）
    - calendar_management.py          — 市場カレンダー管理 / 営業日ロジック
    - audit.py                        — 監査ログ（signal/order_request/execution）
    - quality.py                      — データ品質チェック
  - strategy/                         — 戦略関連（未実装／拡張ポイント）
  - execution/                        — 発注 / execution 関連（拡張ポイント）
  - monitoring/                       — 監視関連（将来のモジュール）

---

## 開発ノート / 注意点

- 自動 .env 読み込みは .git または pyproject.toml がある親ディレクトリをプロジェクトルートとして探索します。配布パッケージ等では挙動が変わる点に注意してください。
- J-Quants API はレート制限（120 req/min）があります。jquants_client は内部でスロットリングとリトライを行いますが、大量一括処理では配慮してください。
- DuckDB の INSERT 文には ON CONFLICT を使用して冪等性を確保しています。外部からスキーマを破壊しないように注意してください。
- news_collector では SSRF 対策、XML の hardening（defusedxml）、レスポンスサイズ制限、トラッキングパラメータの除去などを行っています。RSS ソース登録時は信頼できる URL を利用してください。
- audit.init_audit_schema はデフォルトで TimeZone を UTC に固定します。全ての TIMESTAMP は UTC で扱う設計です。

---

不明点や README に追加したい具体的な利用シナリオ（例: デプロイ手順、CI設定、監視設定など）があれば教えてください。必要に応じてサンプルスクリプトや補足ドキュメントを作成します。