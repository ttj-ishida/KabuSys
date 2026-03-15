# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買プラットフォーム向けの基盤ライブラリです。データの取得・保存、データベース（DuckDB）スキーマ初期化、監査ログ（トレーサビリティ）管理、設定読み込みなどの共通機能を提供します。

主な設計方針:
- Look-ahead bias を防ぐためにデータ取得時刻（fetched_at）を UTC で記録
- 冪等性を重視（DuckDB への INSERT は ON CONFLICT DO UPDATE を使用）
- 外部 API に対してレート制限・リトライ・トークン自動リフレッシュを実装
- 監査ログ（signal → order_request → execution の連鎖）で完全なトレースを保証

---

## 機能一覧

- 環境設定管理
  - .env / .env.local / OS 環境変数から設定を読み込み
  - 必須キーの取得とバリデーション
  - 自動読み込みの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）

- J-Quants API クライアント（data.jquants_client）
  - 日足（OHLCV）データ取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得（ページネーション対応）
  - JPX マーケットカレンダー取得
  - レートリミッタ（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - DuckDB へデータ保存するユーティリティ（冪等な保存関数）

- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution 層を含む多数のテーブル DDL を提供
  - 初期化関数 init_schema(db_path) によるテーブル作成（冪等）
  - 接続取得ユーティリティ get_connection(db_path)

- 監査ログ（data.audit）
  - signal_events / order_requests / executions の監査用テーブルと索引
  - トレーサビリティ階層を保証する設計（UUID 連鎖）
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化

---

## 必要条件 / 依存

- Python 3.10+
  - 型ヒントで PEP 604 (a | b) を使用しているため 3.10 以上を想定
- 主要依存パッケージ
  - duckdb
- 標準ライブラリ（urllib 等）で外部 HTTP 呼び出しを実施

（プロジェクトの実環境では J-Quants のアクセストークン、kabuAPI の設定、Slack トークン等が必要です）

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID

オプション（デフォルトあり）:
- KABUSYS_ENV — 環境 (development / paper_trading / live)。デフォルト: development
- LOG_LEVEL — ログレベル (DEBUG/INFO/...)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env ロードを無効化
- KABUS_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

.env 自動読み込み:
- プロジェクトルートは __file__ の親ディレクトリから .git または pyproject.toml を探索して特定します。
- 読み込み順序: OS 環境変数 > .env.local（上書き） > .env（未設定のみセット）
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

簡易 .env 例:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

---

## セットアップ手順

1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - pip install duckdb
   - （パッケージをローカル開発としてインストールする場合）
     - pip install -e .

   ※ requirements.txt / pyproject.toml がある場合はそちらに従ってください。

3. 環境変数設定
   - プロジェクトルートに .env を作成するか、OS 環境変数に必要なキーを設定します。
   - テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動読み込みを無効化できます。

4. DuckDB スキーマ初期化
   - Python から init_schema を呼んでデータベースとテーブルを作成します（後述の使い方参照）。

---

## 使い方（例）

以下はライブラリの主要機能の簡単な利用例です。

1) 設定の参照
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必須: 未設定なら例外
print(settings.duckdb_path)            # Path オブジェクト
print(settings.env, settings.is_dev)
```

2) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path を使って初期化（必要に応じて親ディレクトリを自動作成）
conn = init_schema(settings.duckdb_path)
# 以降 conn を使用してクエリ実行や保存処理を行う
```

3) J-Quants から日足取得して DuckDB に保存
```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

# 例: 銘柄コード 7203（トヨタ）を 2023-01-01 から 2023-12-31 まで取得
records = fetch_daily_quotes(code="7203", date_from=date(2023, 1, 1), date_to=date(2023, 12, 31))
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

4) 財務データ / 市場カレンダー / 監査ログ初期化
```python
from kabusys.data.jquants_client import fetch_financial_statements, fetch_market_calendar, save_financial_statements, save_market_calendar
from kabusys.data.audit import init_audit_schema

# 既存の DuckDB 接続に監査テーブルを追加
init_audit_schema(conn)
```

5) トークン取得（内部で自動リフレッシュ処理がある）
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使用して取得
```

注意点:
- J-Quants API 呼び出しは内部でレート制限とリトライを行います（120 req/min、最大 3 回等）。
- fetch_* 関数はページネーションに対応しています（pagination_key を利用）。
- save_* 関数は ON CONFLICT DO UPDATE を用いて冪等的に保存します。

---

## ディレクトリ構成

プロジェクトの主要ファイルとディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py                (パッケージ定義、バージョン: 0.1.0)
  - config.py                  (環境変数・設定管理)
  - data/
    - __init__.py
    - jquants_client.py        (J-Quants API クライアント・保存ユーティリティ)
    - schema.py                (DuckDB スキーマ定義・初期化)
    - audit.py                 (監査ログ（signal/order_requests/executions）)
    - audit.py
    - audit.py
    - audit.py
    - audit.py
  - strategy/
    - __init__.py              (戦略関連のエントリポイント)
  - execution/
    - __init__.py              (発注・実行管理のエントリポイント)
  - monitoring/
    - __init__.py              (モニタリング関連のエントリポイント)

README 作成時点の主要モジュール:
- kabusys.config.Settings: 環境変数や各種パス / フラグの取得
- kabusys.data.jquants_client: API 呼び出し、rate limit、retry、保存関数
- kabusys.data.schema: DuckDB の DDL 定義と init_schema/get_connection
- kabusys.data.audit: 監査用スキーマの定義と初期化

（実際のリポジトリではさらにテスト・CI・ドキュメント・戦略実装等のファイルが存在する想定です）

---

## 補足 / 運用上の注意

- 時刻・タイムゾーン
  - 取得時刻（fetched_at）や監査 TIMESTAMP は UTC を使用する設計です。監査 DB 初期化では SET TimeZone='UTC' を行います。

- 冪等性
  - raw テーブルの保存関数は PRIMARY KEY に基づき ON CONFLICT DO UPDATE を行うため、再実行しても上書き（更新）によりデータの重複は発生しません。

- 自動 .env ロード
  - テストや CI で明示的に環境を管理したい場合、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化してください。

- API レート制御とリトライ
  - J-Quants のレート制限（120 req/min）に合わせた固定間隔のスロットリングを実装しています。429 / 408 / 5xx 系は指数バックオフで再試行し、401 はトークンを一度自動リフレッシュしてリトライします。

---

この README はコードベースの現状（主要ファイルの実装）に基づいて作成しています。戦略ロジック（strategy/）、発注実行（execution/）、監視・通知（monitoring/）などは別途実装を追加してください。必要であればインストール手順や CI 設定、より詳細な API サンプルを追記します。