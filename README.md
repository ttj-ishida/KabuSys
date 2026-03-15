# KabuSys

日本株自動売買システムのライブラリ（KabuSys）。  
データ取得・DBスキーマ管理・監査ログ・（将来的な）戦略／発注モジュールの基盤を提供します。

主な設計方針：
- J-Quants API 等からの市場データ取得を行い、DuckDB に保存（冪等性を担保）
- 監査ログ（signal → order_request → execution）の完全なトレーサビリティを保持
- API レート制限・リトライ・トークン自動リフレッシュ等の堅牢な HTTP ロジック
- すべてのタイムスタンプは UTC 扱いで記録

---

## 機能一覧

- 環境変数／.env 自動読み込み管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルートから自動読み込み（CWD に依存しない探索）
  - 必須変数チェック helper（settings オブジェクト）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダー取得
  - API レート制限（120 req/min）遵守（内部 RateLimiter）
  - リトライ（指数バックオフ、最大 3 回）、401 時のトークン自動リフレッシュ
  - fetched_at（UTC）を付与して Look-ahead Bias 対策
  - DuckDB への保存関数（冪等化: ON CONFLICT DO UPDATE）

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス、外部キー、制約を含む DDL を提供
  - init_schema() / get_connection() API

- 監査ログ（src/kabusys/data/audit.py）
  - signal_events / order_requests / executions テーブルを提供
  - 冪等キー（order_request_id / broker_execution_id）やステータス遷移管理
  - init_audit_schema() / init_audit_db() API

（将来的に strategy、execution、monitoring モジュールの拡張を想定）

---

## セットアップ手順

前提：Python 3.9+（typing の使用に合わせることを推奨）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb
   - （開発用）pip install -e . などパッケージ化している場合はその手順に従ってください

   ※ このコードベースは最低限 duckdb を利用します。HTTP リクエストは標準ライブラリ urllib を使用しているため追加は不要です。
   必要に応じて他の依存（slack クライアント等）を追加してください。

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を用意してください。
   - 自動読み込みはプロジェクトルート（.git または pyproject.toml を起点）を探索します。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env に設定すべき主な環境変数（例）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  (任意、デフォルトあり)
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb    (任意、デフォルト)
- SQLITE_PATH=data/monitoring.db     (任意、デフォルト)
- KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
- LOG_LEVEL=INFO|DEBUG|...           (デフォルト: INFO)

---

## 使い方（簡単な例）

以下は主要なユースケースのサンプルです。実運用では例外処理やログ、リトライ戦略等を追加してください。

- DuckDB スキーマ初期化（データ保存用）
```python
from kabusys.data.schema import init_schema
# ファイルパスを指定（parent ディレクトリがなければ自動作成）
conn = init_schema("data/kabusys.duckdb")
# 以降 conn を使って保存関数を呼ぶ
```

- J-Quants から日足を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
# conn は init_schema で取得した DuckDB connection
records = fetch_daily_quotes(code="7203")  # トヨタなどの銘柄コード
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

- 財務データやマーケットカレンダーの取得＆保存
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

fin_records = fetch_financial_statements(date_from=date(2022,1,1), date_to=date(2023,1,1))
save_financial_statements(conn, fin_records)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

- id_token を明示的に取得する（必要な場合）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って POST で取得
```

- 監査ログテーブル初期化（既存 conn に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
# または独立した監査専用 DB を作成:
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

- 環境設定の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)  # KABUSYS_ENV が 'live' のとき True
```

注意点（設計上の重要点）：
- J-Quants クライアントは API レート（120 req/min）を守るようスロットリングしています。
- リトライは 408 / 429 / 5xx に対して行われ、429 の場合は Retry-After ヘッダを優先します。
- 401 受信時はリフレッシュトークンで ID トークンを再取得して 1 回だけリトライします。
- 保存系関数は冪等（ON CONFLICT DO UPDATE）で重複を抑止します。
- 取得時刻（fetched_at）は UTC で記録されます（Look-ahead Bias のトレーサビリティ）。

---

## ディレクトリ構成

リポジトリの主要ファイル・ディレクトリ構成（抜粋）
```
src/
  kabusys/
    __init__.py           # パッケージ定義（__version__ 等）
    config.py             # 環境変数・設定管理（settings オブジェクト）
    data/
      __init__.py
      jquants_client.py   # J-Quants API クライアント（取得・保存ロジック）
      schema.py           # DuckDB スキーマ定義と init_schema/get_connection
      audit.py            # 監査ログテーブル定義と初期化
    strategy/
      __init__.py         # 戦略関連（拡張ポイント）
    execution/
      __init__.py         # 発注実行関連（拡張ポイント）
    monitoring/
      __init__.py         # 監視・メトリクス（拡張ポイント）
```

主要モジュール：
- kabusys.config: settings（JQUANTS_REFRESH_TOKEN 等の取得）
- kabusys.data.jquants_client: fetch_*/save_* 関数、get_id_token
- kabusys.data.schema: init_schema, get_connection
- kabusys.data.audit: init_audit_schema, init_audit_db

---

## その他メモ

- データベース初期化関数は親ディレクトリが存在しない場合に自動作成します。
- DuckDB の接続オブジェクトはそのまま executemany などで利用できます。
- 監査ログは削除しない前提（FK は ON DELETE RESTRICT）で設計されています。
- ログレベルは環境変数 LOG_LEVEL で制御可能（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

---

README に記載されていない使い方や追加のユースケース（例：kabuステーションとの連携、Slack 通知、具体的なバックテストフロー等）について要望があれば、その用途に合わせたサンプルや機能説明を作成します。