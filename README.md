# KabuSys

KabuSys は日本株の自動売買・データプラットフォーム向けの小規模フレームワークです。  
J-Quants などの外部 API から株価・財務・マーケットカレンダー・ニュースを収集して DuckDB に保存し、ETL、品質チェック、監査ログの仕組みを備えています。

- 現バージョン: 0.1.0
- Python 3.10+ を想定（型記法に `X | None` を使用しているため）

---

## 主要機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーをページネーション対応で取得
  - レート制限（120 req/min）とリトライ（指数バックオフ、401 時はトークン自動リフレッシュ）対応
  - データ取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）

- ニュース収集
  - RSS フィードからニュースを取得して前処理後に raw_news に保存
  - URL 正規化、トラッキングパラメータ除去、記事 ID は正規化 URL の SHA-256 の先頭 32 文字
  - SSRF 対策、gzip 解凍上限、XML パーサーに defusedxml を使用
  - 銘柄コード（4 桁）抽出機能と news_symbols への紐付け

- DuckDB スキーマ定義 / 初期化
  - Raw / Processed / Feature / Execution 層のテーブルとインデックスを定義
  - 監査ログ（signal_events / order_requests / executions）用スキーマを別途初期化可能

- ETL パイプライン
  - daily ETL（calendar → prices → financials → 品質チェック）
  - 差分更新・バックフィル（デフォルト: 3 日）対応
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- マーケットカレンダー管理
  - JPX カレンダーの夜間バッチ更新ジョブ
  - 営業日判定、前後営業日検索、期間内営業日列挙、SQ 日判定

- 監査ログ（トレーサビリティ）
  - シグナルから発注・約定まで UUID ベースで追跡可能な監査テーブル群
  - order_request_id を冪等キーとして二重発注防止

---

## 必要な環境変数

KabuSys は環境変数（またはプロジェクトルートの `.env` / `.env.local`）を参照します。主に必須となるもの:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

自動で `.env` / `.env.local` をロードします（優先順: OS 環境変数 > .env.local > .env）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env）:
```
JQUANTS_REFRESH_TOKEN= your_refresh_token_here
KABU_API_PASSWORD= your_kabu_password
SLACK_BOT_TOKEN= xoxb-...
SLACK_CHANNEL_ID= C12345678
DUCKDB_PATH= data/kabusys.duckdb
KABUSYS_ENV= development
LOG_LEVEL= INFO
```

---

## セットアップ手順

1. Python と依存パッケージのインストール

   - Python 3.10+
   - 必要パッケージ（最低限）:
     - duckdb
     - defusedxml

   例:
   ```
   python -m pip install "duckdb" "defusedxml"
   ```

   （このコードベースは標準ライブラリの urllib を使用しているため、HTTP ライブラリは追加必須ではありません。プロジェクト全体のパッケージ管理がある場合は pyproject.toml を参照してください。）

2. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を作成し、上記の必須変数を設定します。
   - あるいは OS 環境変数として設定してください。

3. DuckDB スキーマの初期化

   Python から実行:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # デフォルトパスと同等
   ```

4. 監査ログスキーマ（任意）
   ```python
   from kabusys.data.audit import init_audit_schema
   # conn は上で作成した DuckDB 接続
   init_audit_schema(conn)
   ```

---

## 使い方（主要な操作例）

以下は簡単な Python スニペット例です。プロダクション用途ではログ設定やエラーハンドリングを適切に行ってください。

- ETL（日次実行）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 市場カレンダー夜間更新ジョブ
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

- ニュース収集（RSS）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
# known_codes: 抽出に使う有効な銘柄コードのセット（例: {'7203', '6758', ...}）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(res)
```

- J-Quants のトークン取得（明示的）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
print(token)
```

- DuckDB 接続を取得する（スキーマ初期化済みの DB に接続）
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

---

## 主要モジュール / API サマリ

- kabusys.config
  - settings: Settings インスタンス（環境変数アクセス用）
- kabusys.data.jquants_client
  - get_id_token(...)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(...), save_financial_statements(...), save_market_calendar(...)
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources, known_codes, timeout)
- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - run_daily_etl(...)
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job(...)
- kabusys.data.quality
  - run_all_checks(conn, target_date, reference_date, spike_threshold)
  - 個別チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## ディレクトリ構成

プロジェクトの主要ファイル / ディレクトリ例（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                 -- 環境変数管理 / Settings
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント（取得・保存）
    - news_collector.py       -- RSS ニュース収集 / 前処理 / 保存
    - schema.py               -- DuckDB スキーマ定義と初期化
    - pipeline.py             -- ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py  -- マーケットカレンダーの管理・判定ロジック
    - audit.py                -- 監査ログ（signal/order/execution）定義・初期化
    - quality.py              -- データ品質チェック
  - strategy/
    - __init__.py             -- （戦略モジュール置き場）
  - execution/
    - __init__.py             -- （発注 / ブローカー連携置き場）
  - monitoring/
    - __init__.py             -- （監視関連置き場）

---

## 設計上の注意点 / 備考

- 自動環境読み込みは `.env` / `.env.local` をプロジェクトルート（.git や pyproject.toml があるディレクトリ）から探して行います。CI／テストで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のレート制限（120 req/min）に合わせた内部レートリミッタを実装しています。外部呼び出しを並列化する場合はその影響に注意してください。
- DuckDB に対する INSERT は可能な限り冪等（ON CONFLICT）を採用していますが、外部から手動でテーブルを変更する場合は品質チェックで検出できます。
- ロギングはモジュール内で行っています。実行環境で適切にロガーを設定して運用してください。
- NewsCollector は SSRF 対策を行っていますが、外部 URL を扱う場合はさらに運用上の注意（プロキシ、タイムアウト設定等）を検討してください。

---

## よくある操作のサンプル（短縮）

DuckDB 初期化 → 日次 ETL の簡易ワンライナー:
```bash
python - <<'PY'
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
conn = init_schema("data/kabusys.duckdb")
res = run_daily_etl(conn)
print(res.to_dict())
PY
```

---

ご不明点や README に追加したい内容（例: 実行スクリプト、cron 設定例、CI 設定、より詳しい .env.example）などがあれば教えてください。必要に応じて追記・整形します。