# KabuSys

KabuSys は日本株向けの自動売買基盤（ミニマム実装）です。  
データ収集、スキーマ管理、監査ログを備え、戦略・発注・監視モジュールの土台を提供します。

主な設計方針：
- データ取得は J-Quants API を利用（レート制限・リトライ・トークン自動リフレッシュを組み込み）
- データ永続化に DuckDB を採用。DDL は冪等（ON CONFLICT / CREATE IF NOT EXISTS）で安全に初期化
- 発注フローは監査ログ（UUID 階層）で完全にトレース可能
- .env / 環境変数で設定を管理

バージョン: 0.1.0

---

## 機能一覧

- 環境変数・設定管理
  - .env/.env.local を自動読み込み（無効化可能）
  - settings オブジェクトから各種設定にアクセス
- J-Quants API クライアント（data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）の厳守（固定間隔スロットリング）
  - リトライ（指数バックオフ、対象: 408/429/5xx、最大 3 回）
  - 401 時はトークン自動リフレッシュして 1 回リトライ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を軽減
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマを定義
  - init_schema(db_path) で初期化（テーブル・インデックス作成）
  - get_connection(db_path) で既存 DB に接続
- 監査ログ（data.audit）
  - signal_events / order_requests / executions を定義
  - 発注フローを UUID 階層で完全トレース
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化

---

## セットアップ手順

前提:
- Python 3.9+（type hint に union の短縮記法等を使用）
- Git が利用できる環境（プロジェクトルート自動検出に .git または pyproject.toml を使用）

1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone <repo> && cd <repo>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要なパッケージをインストール
   - duckdb は必須。pip でインストールしてください:
     - pip install duckdb
   - （他に必要なパッケージがある場合は pyproject.toml / requirements.txt を参照してください）

4. 環境変数の設定 (.env)
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（例）:
     - JQUANTS_REFRESH_TOKEN  - J-Quants の refresh token
     - KABU_API_PASSWORD       - kabuステーション API のパスワード
     - SLACK_BOT_TOKEN        - Slack 通知用 Bot Token
     - SLACK_CHANNEL_ID       - Slack 通知先チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live)  デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|...) デフォルト: INFO
     - KABU_API_BASE_URL （デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH デフォルト: data/kabusys.duckdb
     - SQLITE_PATH デフォルト: data/monitoring.db

例 .env
```
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C12345678"
KABUSYS_ENV=development
```

---

## 使い方（主要な例）

- 設定値にアクセスする

```python
from kabusys.config import settings

# 必須項目に未設定があれば ValueError が送出される
token = settings.jquants_refresh_token
db_path = settings.duckdb_path
print(settings.env, settings.is_dev)
```

- DuckDB スキーマを初期化する

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルがなければ自動でディレクトリ作成
# conn は duckdb.DuckDBPyConnection
```

- J-Quants からデータを取得して保存する（例：株価日足）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)

# 例: 2023-01-01 から 2023-01-31 までのデータ
records = fetch_daily_quotes(date_from=date(2023, 1, 1), date_to=date(2023, 1, 31), code=None)
n = save_daily_quotes(conn, records)
print(f"{n} 件を保存しました")
```

- 財務データ・マーケットカレンダーの取得と保存

```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

fin = fetch_financial_statements(date_from=date(2022,1,1))
save_financial_statements(conn, fin)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

- 監査ログの初期化（既存接続に追加する）

```python
from kabusys.data.audit import init_audit_schema
# conn は init_schema() で得た接続を渡すのが一般的
init_audit_schema(conn)
```

- 監査ログ専用 DB を使う場合

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意点：
- J-Quants API 呼び出しは内部でレート制限とリトライを行います。大量のリクエストを送る際も設計上 120 req/min を想定しています。
- トークン期限切れで 401 が返ると自動で refresh（1 回）して再試行します。

---

## 環境変数・設定の詳細

主な設定項目（settings 経由でアクセス）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (オプション、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

.env のパースは Bash ライクな書式（export KEY=val, quoted values, inline comment 処理など）に対応しています。

---

## ディレクトリ構成

リポジトリ（src 配下の重要ファイル）:

- src/kabusys/
  - __init__.py                : パッケージ初期化（バージョン等）
  - config.py                  : 環境変数 / Settings 管理（自動 .env 読み込み等）
  - data/
    - __init__.py
    - jquants_client.py        : J-Quants API クライアント（fetch / save ロジック）
    - schema.py                : DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
    - audit.py                 : 監査ログ（signal_events / order_requests / executions）
    - (その他: audit/schema 関連モジュール)
  - strategy/
    - __init__.py              : 戦略モジュール（未実装の枠）
  - execution/
    - __init__.py              : 発注モジュール（未実装の枠）
  - monitoring/
    - __init__.py              : 監視関連（未実装の枠）

主要ファイル:
- src/kabusys/data/jquants_client.py : API 呼び出し・保存ロジック
- src/kabusys/data/schema.py        : CREATE TABLE DDL を集約
- src/kabusys/data/audit.py         : 監査ログ DDL と初期化関数
- src/kabusys/config.py             : Settings と .env パーサ

---

## 開発・運用メモ

- DuckDB はファイルベースなのでバックアップ/バージョン管理方針を検討してください（特に監査ログは削除しない前提）。
- すべての TIMESTAMP は UTC で扱う設計になっています（audit.init_audit_schema は SET TimeZone='UTC' を実行）。
- 発注系（execution）および戦略（strategy）層は本リポジトリに骨組みを用意しています。実際の発注接続やリスク管理ロジックは各プロジェクトで実装してください。
- テスト実行時などで .env 自動読み込みを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

README はここまでです。追加で以下を用意できます:
- .env.example のテンプレート
- サンプルスクリプト（データ収集バッチ）
- CI / デプロイ手順

どれを追加しますか？