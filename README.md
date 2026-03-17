# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python ライブラリ群です。J-Quants API からの市場データ取得、DuckDB へのスキーマ管理・ETL、RSS ベースのニュース収集、マーケットカレンダー管理、監査ログ（トレーサビリティ）など、データプラットフォームと自動売買の基盤機能を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境設定管理
  - `.env` / `.env.local` から自動的に環境変数を読み込む（無効化可）
  - 必要な環境変数が未設定の場合は明確なエラーを返す

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）遵守、リトライ、トークン自動リフレッシュ対応
  - 取得時刻を UTC の `fetched_at` で記録（Look-ahead Bias 対策）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化関数
  - 冪等なテーブル作成（IF NOT EXISTS）と索引の定義

- ETL パイプライン
  - 差分更新（最終取得日に基づく差分フェッチ + backfill）
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - 日次 ETL の統合エントリポイント

- ニュース収集（RSS）
  - RSS フィード取得、XML の安全パース（defusedxml）
  - URL 正規化（トラッキングパラメータ除去）と記事 ID 生成（SHA-256）
  - SSRF 対策、受信サイズ上限、冪等保存（DuckDB）と銘柄紐付け

- マーケットカレンダー管理
  - JPX カレンダーの夜間差分更新ジョブ
  - 営業日判定・前後営業日探索・期間内営業日取得

- 監査ログ（Audit）
  - シグナル → 発注 → 約定を UUID 連鎖でトレース可能にする監査テーブル群
  - 監査 DB 初期化ユーティリティ

---

## 前提条件

- Python 3.10 以上（PEP 604 の union types (`|`) を使用）
- 必要な Python パッケージ（代表例）
  - duckdb
  - defusedxml

（プロジェクトに requirements.txt があればそれを使ってください。ない場合は手動インストールを行います。）

例:
```
python -m pip install "duckdb" "defusedxml"
```

開発時にパッケージ化されている場合:
```
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／コピーする
2. Python 環境を用意（仮想環境推奨）
3. 必要パッケージをインストール（上記参照）
4. 環境変数を設定

環境変数は `.env` または OS 環境変数で設定します。自動ロードはプロジェクトルート（`.git` または `pyproject.toml` を基準）から `.env` と `.env.local` を読み込みます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルトあり）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb      # 任意（デフォルト）
SQLITE_PATH=data/monitoring.db       # 任意（デフォルト）
KABUSYS_ENV=development              # development | paper_trading | live
LOG_LEVEL=INFO
```

5. DuckDB スキーマを初期化
- 例: Python REPL / スクリプトから
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
```

監査ログ専用 DB を作る場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主な API と実行例）

以下は典型的な利用例の抜粋です。

- 日次 ETL を実行する
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 引数で target_date, id_token 等を指定可能
print(result.to_dict())
```

- J-Quants から株価を単独で取得して保存する
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"Saved {saved} rows")
```

- RSS ニュース収集ジョブを実行する
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使う有効コード集合（例: 上場銘柄コードセット）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)  # {source_name: saved_count}
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"Saved {saved} calendar rows")
```

- 品質チェックを明示的に実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

- 設定値の取得（環境変数経由）
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

ログレベルや環境モード（development / paper_trading / live）は `KABUSYS_ENV` と `LOG_LEVEL` で制御できます。設定の検証は `kabusys.config.Settings` が行います。

---

## 注意点（設計上の要点・運用上の注意）

- J-Quants API のレート制限（120 req/min）に合わせた内部レートリミッタを持ちます。大量データ取得時は注意してください。
- API からの 401 応答時は自動でリフレッシュトークンを使って ID トークンを再取得し 1 回だけリトライします。
- DB への保存は冪等性を重視しており、raw 層の INSERT は ON CONFLICT で更新する設計です。
- ニュース収集では SSRF 対策、XML の安全パース、最大受信サイズの制限（10MB）などを備えています。
- DuckDB スキーマ初期化後はスキーマに沿ったデータの投入／運用を行ってください。監査ログの初期化は `init_audit_db` または `init_audit_schema` を使用します。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットすると自動で `.env` を読み込まないため、単体テスト等で便利です。

---

## ディレクトリ構成（概要）

プロジェクトの主要ファイル／モジュール構成は以下の通りです（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                         -- 環境変数・設定管理
  - data/
    - __init__.py
    - schema.py                        -- DuckDB スキーマ定義と init_schema()
    - jquants_client.py                -- J-Quants API クライアント（fetch/save）
    - pipeline.py                      -- 日次 ETL パイプライン
    - news_collector.py                -- RSS ニュース収集・保存
    - calendar_management.py           -- マーケットカレンダー管理
    - audit.py                         -- 監査ログ（トレース用）初期化
    - quality.py                       -- データ品質チェック
  - strategy/
    - __init__.py
    (戦略ロジックは strategy パッケージに実装予定)
  - execution/
    - __init__.py
    (発注・ブローカー連携は execution パッケージに実装予定)
  - monitoring/
    - __init__.py
    (監視・アラート系は monitoring パッケージに実装予定)

ドキュメントや DataPlatform.md / DataSchema.md といった設計ドキュメントをプロジェクトルートに置くことを想定しています。

---

## 付録: よく使う関数一覧（短い参照）

- kabusys.config.settings
  - jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id
  - duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - save_daily_quotes(conn, records)
  - fetch_financial_statements(...)
  - save_financial_statements(conn, records)
  - fetch_market_calendar(...)
  - save_market_calendar(conn, records)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.calendar_management
  - calendar_update_job(conn, lookahead_days=90)
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - is_sq_day(conn, d)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

もし README に追加してほしい内容（例: 実運用時の crontab 設定例、Slack 通知の連携例、CI 設定、具体的なテーブル定義の説明など）があれば教えてください。必要に応じて追記・拡張します。