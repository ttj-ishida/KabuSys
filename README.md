# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python ライブラリ群です。J‑Quants や kabuステーション 等からデータを取得して DuckDB に格納し、ETL、品質チェック、ニュース収集、監査ログ（発注〜約定トレーサビリティ）をサポートします。

主な設計方針：
- データ取得は冪等性（ON CONFLICT）を重視
- API レート制限・リトライ・トークン自動更新に対応
- SSRF / XML Bomb 等に配慮した堅牢なニュース収集
- DuckDB を中心とした軽量かつ高速なローカルデータ基盤

---

## 機能一覧
- 環境設定の統合管理（.env / OS 環境変数読み込み、自動ロード）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レートリミット制御、指数バックオフによるリトライ、401 時のトークン自動リフレッシュ
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集（RSS → 前処理 → DuckDB へ冪等保存）
  - URL 正規化、トラッキングパラメータ除去、SSRF 対策、受信サイズ制限
- マーケットカレンダー管理（営業日判定・前後営業日検索・夜間更新ジョブ）
- 監査ログ（signal → order_request → executions のトレーサビリティ）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で `X | None` を使用しているため）
- Git, virtualenv 等は任意

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   - 必須: duckdb, defusedxml
   - 例:
     pip install duckdb defusedxml

   （プロジェクトが pyproject.toml / setup.py を持つ場合）
     pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（`.env.local` があればそれが優先され上書きされます）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。

必要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャネル ID（必須）
- KABUSYS_ENV           : 環境 ("development" | "paper_trading" | "live")（省略時: development）
- LOG_LEVEL             : ログレベル ("DEBUG" | "INFO" | ...)
- DUCKDB_PATH           : DuckDB データベースファイル（省略時: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite パス（監視等で使用、省略時: data/monitoring.db）

例 (.env)
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（基本例）

以下は主要な利用フローのサンプルコード例です。実際の運用ではログや例外処理、シークレット管理に注意してください。

1) DuckDB スキーマの初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# 監査ログ用スキーマを追加
from kabusys.data import audit
audit.init_audit_schema(conn, transactional=True)
```

2) 日次 ETL を実行（J-Quants から株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット（例）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

4) J-Quants API を直接使う（トークンは settings から取得）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

# id_token を自動的にキャッシュ・リフレッシュする場合は省略可能
id_token = jq.get_id_token(settings.jquants_refresh_token)

# 株価取得（例）
records = jq.fetch_daily_quotes(id_token=id_token, date_from="20230101", date_to="20230131")
```

5) 品質チェックの個別実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 主要 API（概要）
- kabusys.config.settings
  - 環境変数アクセス（例: settings.jquants_refresh_token）
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を読み込む

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token：リフレッシュトークンから id_token を取得（POST）

- kabusys.data.schema
  - init_schema(db_path): DuckDB スキーマ作成（冪等）

- kabusys.data.pipeline
  - run_daily_etl(conn, ...): 日次の差分 ETL + 品質チェック

- kabusys.data.news_collector
  - fetch_rss(url, source): RSS 取得・パース
  - save_raw_news(conn, articles): raw_news へ保存（INSERT ... RETURNING）
  - run_news_collection(conn, ...): 複数ソースをまとめて処理

- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job(conn): 夜間更新ジョブ

- kabusys.data.audit
  - init_audit_schema(conn): 監査ログテーブル初期化
  - init_audit_db(db_path): 監査ログ専用 DB 初期化

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - pipeline.py
  - calendar_management.py
  - audit.py
  - quality.py
- strategy/
  - __init__.py
  (戦略ロジックを実装するモジュール群)
- execution/
  - __init__.py
  (発注 / ブローカー連携ロジック)
- monitoring/
  - __init__.py

※ 実行ファイルや CLI スクリプトは含まれていません。必要に応じてエントリポイントを作成してください。

---

## 運用上の注意点
- J-Quants のレート制限（120 req/min）に対応した内部 RateLimiter を備えていますが、過度な同時実行は避けてください。
- トークン自動リフレッシュは 401 発生時に1回のみ実行する設計です。連続失敗時は例外になります。
- DuckDB のスキーマは冪等に作成されますが、DDL を大きく変更する際はマイグレーション戦略を用意してください。
- ニュース収集では受信サイズ制限・gzip 解凍サイズチェック・SSRF 対策等の安全機構がありますが、外部フィードに依存するため想定外の形式に対しては失敗することがあります。
- 監査ログは削除しない前提で設計されています（ON DELETE RESTRICT）。運用での長期保存・アーカイブを検討してください。

---

## 依存関係（主なもの）
- Python >= 3.10
- duckdb
- defusedxml

必要に応じて logging 設定や Slack 通知の実装を追加してください。

---

README に載せきれない実装詳細や設計意図は各モジュールの docstring に記載されています。具体的な拡張（戦略実装やブローカー連携）については strategy/ と execution/ に実装を追加して下さい。必要ならサンプル・ユーティリティや CLI を用意することを推奨します。