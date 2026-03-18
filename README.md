# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants や RSS 等から市場データ・ニュースを収集し、DuckDB に保存、ETL・品質チェック・監査ログの初期化／実行をサポートします。

## プロジェクト概要
KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API から株価（OHLCV）、四半期財務データ、マーケットカレンダーを取得
- RSS フィードからニュースを収集し、記事と銘柄コードを紐付けて保存
- DuckDB を用いたスキーマ定義・初期化・ETL パイプライン
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 発注・監査ログ用スキーマ（監査トレース用テーブル群）
- レート制御・リトライ・トークン自動リフレッシュ・SSRF 対策等の堅牢な実装

設計方針として、冪等性（ON CONFLICT）、レート制限遵守、Look-ahead バイアス対策（fetched_at の記録）、およびセキュリティ（XML/SSRF/圧縮爆弾対策）を重視しています。

---

## 主な機能一覧
- データ取得
  - jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レート制限（120 req/min）、指数バックオフによるリトライ、401 時のトークン自動リフレッシュ
- DuckDB スキーマ管理
  - data.schema.init_schema(db_path)
  - audit 用スキーマの初期化（init_audit_schema / init_audit_db）
- ETL パイプライン
  - 差分取得（最終取得日からの差分のみ）とバックフィル、run_daily_etl() による一括実行
- ニュース収集
  - RSS フィード取得（gzip 対応）、記事正規化、ID 生成（URL 正規化 + SHA-256）
  - SSRF 回避、受信サイズ制限、defusedxml による安全な XML パース
  - raw_news / news_symbols へ冪等保存
- データ品質チェック
  - 欠損データ、重複、スパイク（前日比閾値）、日付不整合を検出
  - run_all_checks() でまとめて実行
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job

---

## セットアップ手順（開発環境）
1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール  
   （プロジェクトの requirements.txt や pyproject.toml がある場合はそちらを利用してください。ここでは主要依存のみ記載）
   - pip install duckdb defusedxml

3. 環境変数の設定  
   プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（起動時に自動ロードされます）。
   - 自動ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID      : 通知先 Slack チャンネル ID（必須）

   任意 / デフォルト値あり:
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite ファイル（デフォルト: data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（コード例）

- DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # :memory: でインメモリ DB
```

- 日次 ETL 実行（株価・財務・カレンダー・品質チェック）
```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集（RSS）を実行して保存
```python
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
sources = {"yahoo": "https://news.yahoo.co.jp/rss/categories/business.xml"}
known_codes = {"7203", "6758"}  # 銘柄コードセット（extract_stock_codes に使用）
results = news_collector.run_news_collection(conn, sources=sources, known_codes=known_codes)
print(results)
```

- audit（監査）スキーマ初期化
```python
from kabusys.data import audit
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=True)
# or init_audit_db("data/kabusys_audit.duckdb")
```

- J-Quants の手動トークン取得 / API 呼び出し
```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使って取得
quotes = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 主要モジュール説明
- kabusys.config
  - 環境変数の自動読み込み（.env, .env.local）と設定取得（Settings）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
- kabusys.data.jquants_client
  - J-Quants API クライアント。レート制御・リトライ・トークンリフレッシュを備える。
  - fetch_* / save_* 系で取得と DuckDB への冪等保存を行う。
- kabusys.data.news_collector
  - RSS フィードから記事を安全に収集し、raw_news / news_symbols に保存。
  - URL 正規化・ID 生成、SSRF/サイズ制限対策、defusedxml を使用。
- kabusys.data.schema
  - DuckDB の全テーブル DDL（Raw/Processed/Feature/Execution/監査用）を定義・初期化。
  - init_schema, get_connection を提供。
- kabusys.data.pipeline
  - 日次 ETL の orchestration（差分取得・保存・品質チェック）。
- kabusys.data.quality
  - 欠損、重複、スパイク、日付不整合のチェックを実装。
  - run_all_checks でまとめて実行して QualityIssue を返す。
- kabusys.data.calendar_management
  - market_calendar の更新ジョブ、営業日判定や next/prev_trading_day 等のユーティリティ。
- kabusys.data.audit
  - 発注・約定の監査ログテーブル群と初期化ユーティリティ。
- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - パッケージを分割するためのプレースホルダ（将来的に戦略・発注・監視ロジックを格納）。

---

## ディレクトリ構成
（主要ファイルのみ抜粋）
```
src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      pipeline.py
      calendar_management.py
      schema.py
      audit.py
      quality.py
      pipeline.py
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py
```

---

## 運用上の注意点 / ベストプラクティス
- 環境変数は `.env` / `.env.local` に保存する際、機密情報（トークン等）を適切に管理してください。
- J-Quants のレート制限（120 req/min）を遵守するため client は内部でスロットリングしています。過度な並列アクセスは避けてください。
- run_daily_etl は個々のステップで例外を捕捉して継続します。重大な品質問題は ETLResult の quality_issues に含まれるため、監視やアラート連携を行ってください。
- news_collector は受信サイズや XML の安全性、SSRF に対する複数の対策を実装していますが、外部フィードの取り扱いは常に注意してください。
- DuckDB ファイル（DUCKDB_PATH）は定期的にバックアップしてください。監査ログなど削除しない前提のデータが含まれます。

---

## 参考 / ヘルプ
- 設定値取得例:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.env, settings.log_level)
```

- 自動 .env ロードの仕様:
  - プロジェクトルートはこのパッケージのファイル位置から上位ディレクトリをさかのぼり、.git または pyproject.toml を検出して決定します。
  - 読み込み順: OS 環境 > .env.local > .env（.env.local は override=True）
  - テスト時など自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

この README はコードベース（src/kabusys 以下）の注釈を元に作成しています。実行・運用前に環境変数・依存ライブラリのインストール・DB 初期化を行い、ローカルで小規模に動作確認してください。必要があれば各モジュールの docstring を参照して詳細な挙動を確認してください。