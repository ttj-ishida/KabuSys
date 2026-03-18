# KabuSys

日本株向け自動売買プラットフォームのライブラリ群（KabuSys）。  
データ取得（J‑Quants）、ETLパイプライン、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ（発注〜約定トレース）などを提供します。

## 概要
KabuSys は以下の目的を持つモジュール群です。

- J‑Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたスキーマ定義と冪等（idempotent）な保存処理
- ETL パイプライン（差分取得／バックフィル／品質チェック）
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策・サイズ制限・トラッキングパラメータ除去）
- マーケットカレンダーの判定・検索ユーティリティ（営業日/前後営業日等）
- 監査ログ（シグナル→発注→約定のトレース用テーブル群）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上のポイント：
- API レート制限やリトライ、Look‑ahead バイアス防止（fetched_at の記録）
- DuckDB の ON CONFLICT を利用した冪等保存
- RSS 収集の安全対策（defusedxml、SSRF/プライベートIP検査、レスポンスサイズ制限）

## 主な機能一覧
- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - get_id_token（リフレッシュトークンからの ID トークン取得）
  - 保存関数：save_daily_quotes / save_financial_statements / save_market_calendar
- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - init_schema, get_connection
  - Raw/Processed/Feature/Execution 層の完全な DDL を含む
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - run_daily_etl（カレンダー → 株価 → 財務 → 品質チェック）
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
- ニュース収集（src/kabusys/data/news_collector.py）
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
  - URL 正規化、ID は URL の SHA-256 先頭32文字
- マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- 監査ログ（src/kabusys/data/audit.py）
  - init_audit_schema, init_audit_db（発注・約定トレース用）
- データ品質チェック（src/kabusys/data/quality.py）
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- 環境設定（src/kabusys/config.py）
  - 環境変数／.env 読み込み、自動ロード（.env/.env.local、OS 環境変数優先）
  - settings オブジェクト経由で設定取得

## セットアップ手順

前提
- Python 3.10 以上（typing の | ユニオン等を使用）
- pip が利用可能

1. リポジトリをクローン / コピー
2. 仮想環境を作成して有効化（推奨）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate
3. 依存パッケージをインストール（最低限）
   - pip install duckdb defusedxml
   - 実運用では logging, urllib 等は標準ライブラリとして同梱されています
   - （プロジェクトに requirements.txt があればそれを使用してください）
4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を配置することで自動読み込みされます（OS 環境変数が優先）。
   - 自動 .env 読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID

任意（デフォルト有り）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- KABUS_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB のパス（デフォルト data/monitoring.db）

例 .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## 使い方（基本例）

以下は Python スクリプトからの利用例です。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) ETL（日次パイプライン）の実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（抽出時に使用）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

4) カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved", saved)
```

5) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

6) J‑Quants の ID トークンを直接取得（テストなど）
```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を使用
```

注意点
- run_daily_etl は内部でカレンダー → 株価 → 財務 → 品質チェックを順に実行します。各ステップは独立してエラーハンドリングされます（1ステップ失敗でも他は継続）。
- jquants_client は 120 req/min のレート制御、指数バックオフによるリトライ（最大 3 回）、401 の場合は自動でリフレッシュして再試行します。
- news_collector は XML パース失敗やレスポンスサイズ超過、SSRF、gzip 解凍失敗などを検出し安全にスキップします。

## 環境設定の自動読み込み挙動
- 自動読み込みはデフォルトで有効です。読み込み順は OS 環境変数 > .env.local > .env（.env の上書きはされないが .env.local は上書きされる）。
- プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定されます。見つからない場合は自動ロードを行いません。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## ロギングと実行モード
- KABUSYS_ENV（development, paper_trading, live）により挙動フラグ（settings.is_dev 等）を利用できます。
- LOG_LEVEL 環境変数でログレベルを指定（デフォルト INFO）。

## ディレクトリ構成

プロジェクト内の主なファイル/モジュール構成は以下の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数 / .env 管理と settings オブジェクト
  - data/
    - __init__.py
    - jquants_client.py        -- J‑Quants API クライアント（取得・保存ロジック）
    - news_collector.py       -- RSS ニュース収集、前処理、DB 保存、銘柄抽出
    - schema.py               -- DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py             -- ETL パイプライン（差分更新、品質チェック）
    - calendar_management.py  -- カレンダー判定・更新ユーティリティ
    - audit.py                -- 監査ログ用テーブル初期化
    - quality.py              -- データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記に含まれるファイルは本リポジトリの主要機能を表しています。）

## 開発・テスト時のヒント
- 単体テストで .env の自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- jquants_client のネットワーク呼び出しは内部で _urlopen や rate limiter を使っているため、テスト時は該当関数をモックすると安全です（例: news_collector._urlopen の差し替え）。
- DuckDB のインメモリ DB を使う場合は db_path に ":memory:" を渡せます（テストで便利）。

## ライセンス / 貢献
- 本 README はコードベースに基づく簡易ドキュメントです。実際のライセンスや貢献ガイドラインはリポジトリのトップレベルファイルを参照してください（LICENSE, CONTRIBUTING など）。

---

何か追加したい機能説明や、README に載せる具体的な実行コマンド（systemd / cron / CI での運用例）などがあれば教えてください。必要に応じて日本語でサンプル .env.example も作成します。