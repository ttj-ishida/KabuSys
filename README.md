# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants / RSS 等からデータを取得し、DuckDB に保存・ETL・品質チェックを行うためのモジュール群を提供します。監査ログ / 発注関連スキーマも含み、戦略・実行・モニタリング層の基盤を担います。

---

目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 使い方（簡単なコード例）
- 環境変数（.env）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株のデータ取得・保存・品質管理・監査ログ管理を目的とした内部ライブラリです。主に以下を行います：

- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを取得
- RSS フィードからニュースを収集し正規化して保存
- DuckDB に対するスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- カレンダー管理・営業日判定ユーティリティ
- 監査ログ（signal → order_request → execution のトレース）

設計上のポイント：
- API レートリミット対応（J-Quants: 120 req/min）
- リトライ（指数バックオフ）、トークン自動リフレッシュ（401 の場合）
- DuckDB への保存は冪等（ON CONFLICT）で実装
- RSS 用に SSFR/XXS 対策（defusedxml、リダイレクト検査、受信サイズ制限 等）

---

## 主な機能（機能一覧）

- data/jquants_client.py
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_* 系関数で DuckDB に冪等保存
- data/news_collector.py
  - fetch_rss(), save_raw_news(), save_news_symbols(), run_news_collection()
  - URL 正規化、トラッキング除去、SSRF 対策、gzip 漏れ対策
- data/schema.py
  - init_schema(db_path) : DuckDB の全スキーマ（Raw/Processed/Feature/Execution）を作成
  - get_connection(db_path)
- data/pipeline.py
  - run_daily_etl(conn, ...) : 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - run_prices_etl(), run_financials_etl(), run_calendar_etl()
- data/calendar_management.py
  - is_trading_day(), next_trading_day(), prev_trading_day(), get_trading_days(), calendar_update_job()
- data/quality.py
  - 欠損/スパイク/重複/日付不整合 等のチェック、run_all_checks()
- data/audit.py
  - 監査ログ用スキーマ初期化（signal_events, order_requests, executions）
  - init_audit_db(db_path)
- config.py
  - .env 自動ロード（.env, .env.local）、必須環境変数チェック（Settings クラス）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化

---

## 前提条件

- Python 3.10 以上（型ヒントで `X | Y` を使用）
- 必要なパッケージ（例）:
  - duckdb
  - defusedxml

インストール例（最低限）:
pip install duckdb defusedxml

プロジェクトが配布パッケージ化されていれば:
pip install -e .

---

## セットアップ手順

1. リポジトリをクローン / ソースを入手

2. Python 仮想環境を作成・有効化（推奨）
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
pip install duckdb defusedxml

4. .env を準備（下記「環境変数」参照）
プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env/.env.local を用意すると自動ロードされます。
自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. DuckDB スキーマ初期化（例）
python -c "from kabusys.data.schema import init_schema; from kabusys.config import settings; init_schema(settings.duckdb_path)"

6. 監査ログ DB（監査専用）を初期化する場合:
python -c "from kabusys.data.audit import init_audit_db; from kabusys.config import settings; init_audit_db('data/audit.duckdb')"

---

## 使い方（簡単な例）

以下は Python からの基本的な操作例です。

- スキーマ初期化
from kabusys.data.schema import init_schema
from kabusys.config import settings
conn = init_schema(settings.duckdb_path)

- 日次 ETL を実行
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())

- ニュース収集（RSS）を実行
from kabusys.data.news_collector import run_news_collection
# known_codes を与えると記事中の銘柄コード抽出・紐付けまで行う
known_codes = {"7203", "6758"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)

- 監査DBを初期化（別 DB に分ける場合）
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")

- J-Quants 直接利用（トークン取得・API 呼び出し）
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()
rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

注意:
- run_daily_etl 等は内部で品質チェックを行います。品質チェックの結果は ETLResult.quality_issues に格納されます。
- DuckDB の接続オブジェクト型は duckdb.DuckDBPyConnection を使用します。

---

## 環境変数（.env）

config.Settings で参照される主な環境変数（必須・任意）:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知先チャネル ID

任意（デフォルトあり）:
- KABUSYS_ENV           : development | paper_trading | live （デフォルト: development）
- LOG_LEVEL             : DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- KABU_API_BASE_URL     : kabu API のベース URL（既定: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 DB パス（既定: data/monitoring.db ※実装では Path を返すが DB エンジンは DuckDB）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml）を探索して .env をロードします。
- 読み込み順: OS 環境変数 > .env.local > .env
- テスト・特殊用途で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して下さい。

注意:
- settings は必須環境変数を参照するときに未設定で ValueError を投げます（早期検出）。

---

## 実運用でのポイント / 推奨

- 機密情報（トークン等）は .env.local に保存し、リポジトリにはコミットしない（.gitignore へ追加）。
- DuckDB ファイルは定期的にバックアップを推奨（特に監査ログ）。
- ETL のスケジューリングは cron / Airflow / GitHub Actions 等を使用。run_daily_etl をラップして実行・監視ログを残してください。
- ログレベルは本番環境で INFO、デバッグ時に DEBUG を使用。
- ニュース収集の既知銘柄リスト（known_codes）は外部ソースから定期更新することを推奨（銘柄の網羅性向上のため）。

---

## ディレクトリ構成

プロジェクト内の主要ファイルとディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理（.env 自動ロード、Settings）
  - data/
    - __init__.py
    - schema.py                — DuckDB スキーマ定義・init_schema / get_connection
    - jquants_client.py        — J-Quants API クライアント（取得／保存）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - news_collector.py        — RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py   — 市場カレンダー管理（営業日判定など）
    - quality.py               — データ品質チェック
    - audit.py                 — 監査ログ（signal/order_request/executions）スキーマ初期化
    - pipeline.py
  - strategy/
    - __init__.py              — 戦略層用エントリ（拡張部分）
  - execution/
    - __init__.py              — 発注 / 実行周り（拡張部分）
  - monitoring/
    - __init__.py              — モニタリング（拡張部分）

その他:
- .env.example （プロジェクトルートに用意すると良い。必要な環境変数のサンプルを記述）

---

必要に応じて README に以下の情報を追加できます（希望があればお知らせください）:
- 具体的な .env.example のサンプル
- CI / CD 用の実行例（cron / systemd unit / GitHub Actions サンプル）
- より詳細な API 使用例（ページネーションの扱い、トークンリフレッシュの挙動）
- 単体テスト・モックの方針（外部APIのモック方法など）

必要な追記があれば教えてください。README の内容を .env.example 付きで生成することも可能です。