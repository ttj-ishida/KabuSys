# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ群。データ取得（J-Quants）、データベース（DuckDB）スキーマ管理、監査ログ、戦略・実行・モニタリングのための基盤を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された内部ライブラリです。

- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを取得するクライアント
- 取得データを保存・整形するための DuckDB スキーマ定義と初期化
- 発注・約定フローを完全にトレースする監査ログ（order_request_id / broker_order_id など）
- 環境変数による設定管理（.env の自動読み込み、強制保護など）
- レート制限・リトライ・トークン自動リフレッシュを備えた堅牢な API 呼び出し

設計方針として、Look-ahead bias の回避（fetched_at の記録）、冪等性（ON CONFLICT DO UPDATE）、監査トレーサビリティを重視しています。

---

## 主な機能

- 環境設定管理（自動 .env ロード、必須キーの取得ラッパー）
- J-Quants API クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レート制限（120 req/min）・指数バックオフリトライ・401 時の自動トークンリフレッシュ
  - ページネーション対応
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution の多層スキーマ定義
  - init_schema(db_path) による一括初期化（冪等）
  - get_connection(db_path)（既存 DB への接続）
- データ保存ユーティリティ
  - save_daily_quotes / save_financial_statements / save_market_calendar（冪等）
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル、インデックス
  - init_audit_schema(conn) / init_audit_db(db_path)

---

## 要件

- Python 3.10+
- duckdb（DuckDB Python パッケージ）
- （標準ライブラリのみで実装されている部分もあるため、他はプロジェクトの依存に合わせて追加してください）

※ requirements.txt / pyproject.toml はこの抜粋には含まれていません。プロジェクト配布時に依存管理を追加してください。

---

## インストール（開発環境例）

ローカルで利用する場合の例:

1. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール（例）
   ```
   pip install duckdb
   ```

3. パッケージを開発モードでインストール（パッケージ配布構成がある場合）
   ```
   pip install -e .
   ```

---

## 環境変数と .env の扱い

KabuSys はプロジェクトルート（.git または pyproject.toml を基準）を検出し、次の順で自動的に .env ファイルを読み込みます（ただし OS 環境変数は保護され、上書きされません）:

1. OS 環境変数（最優先）
2. .env（既に OS にあるキーは上書きしない）
3. .env.local（.env の上書き、ただし OS に存在するキーは保護）

自動読み込みを無効化する場合は環境変数を設定:
```
KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

必須環境変数（Settings が参照するもの）:

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN : Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID（必須）

任意（またはデフォルトあり）:

- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL : デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH : デフォルト "data/kabusys.duckdb"
- SQLITE_PATH : デフォルト "data/monitoring.db"

例: .env
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## クイックスタート（基本的な使い方）

1) DuckDB スキーマを初期化する

Python REPL またはスクリプトで:
```python
from kabusys.data import schema
# ファイル DB を初期化して接続を得る
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

2) J-Quants からデータを取得して DuckDB に保存する

```python
from kabusys.data import jquants_client
from kabusys.data import schema

# 接続は既に init_schema で作成済みと仮定
conn = schema.get_connection("data/kabusys.duckdb")

# 日足の取得（例: 2023-01-01 から 2023-03-31）
from datetime import date
records = jquants_client.fetch_daily_quotes(
    date_from=date(2023,1,1),
    date_to=date(2023,3,31),
)
saved = jquants_client.save_daily_quotes(conn, records)
print(f"Saved {saved} rows into raw_prices")
```

3) 監査ログを初期化する（監査テーブルを別 DB にすることも可能）
```python
from kabusys.data import audit, schema
conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
# または専用 DB を作る
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## J-Quants クライアントの特徴と注意点

- レート制限: 120 req/min（モジュール内 RateLimiter により自動スロットリング）
- リトライ: ネットワークエラーや 408/429/5xx に対して指数バックオフで最大 3 回
- 401 Unauthorized 受信時にはリフレッシュトークンを使用して ID トークンを自動再取得して 1 回リトライ
- ページネーション対応: fetch_* 系は pagination_key を自動で追跡
- 取得時刻（fetched_at）を UTC タイムスタンプで記録（Look-ahead bias 防止）
- 保存関数は冪等（ON CONFLICT DO UPDATE）: 既存レコードを上書きして同一 PK を重複させない

関数一覧（主なもの）:

- get_id_token(refresh_token: str | None = None) -> str
- fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None) -> list[dict]
- fetch_financial_statements(...)
- fetch_market_calendar(...)
- save_daily_quotes(conn, records) -> int
- save_financial_statements(conn, records) -> int
- save_market_calendar(conn, records) -> int

---

## 監査（Audit）について

監査用モジュールは発注までのフローを完全にトレースできる設計です。主なテーブル:

- signal_events: 戦略が生成したシグナル（棄却やエラーも含む）
- order_requests: 発注要求（order_request_id が冪等キー）
- executions: 証券会社からの約定情報（broker_execution_id を冪等キーとして保存）

API:

- init_audit_schema(conn) : 既存の DuckDB 接続に監査用テーブルを追加
- init_audit_db(db_path) : 監査専用 DB を初期化して接続を返す

設計上、監査ログは削除しない前提で、TIMESTAMP は UTC を使用します。

---

## ディレクトリ構成

このコードベースの主要ファイル／ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - __version__ = "0.1.0"
    - config.py                — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント（取得＋保存処理）
      - schema.py              — DuckDB スキーマ定義と init_schema / get_connection
      - audit.py               — 監査ログ（signal_events / order_requests / executions）
      - audit_db (functions)   — init_audit_db, init_audit_schema
      - その他（raw/processed テーブル定義）
    - strategy/
      - __init__.py            — 戦略関連モジュール（拡張ポイント）
    - execution/
      - __init__.py            — 発注／ブローカー連携コード（拡張ポイント）
    - monitoring/
      - __init__.py            — モニタリング関連（拡張ポイント）

---

## 開発上の注意点 / ベストプラクティス

- .env の取り扱い:
  - OS の環境変数は最優先で保護され、.env で誤って上書きされることはありません（ただし .env.local は .env を上書き可能）。
  - テスト時に自動読み込みを阻止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。
- DB 初期化:
  - 実運用前に schema.init_schema() を実行しておくと安全です。既に存在するテーブルはスキップされるため冪等です。
- API 呼び出し:
  - J-Quants のレート制限に注意してください。クライアントは間隔制御を実装していますが、大量の並列リクエストを行う設計は避けてください。
- トークン管理:
  - JQUANTS_REFRESH_TOKEN は機密情報です。アクセス管理・保護に注意してください。
- 監査ログ:
  - order_request_id を冪等キーとして利用することで二重発注を防止できます。発注処理では必ずこのキーを管理してください。

---

## 例: 簡単なフルフロー（取得→保存→監査初期化）

```python
from datetime import date
from kabusys.data import schema, jquants_client, audit

# DB 初期化
conn = schema.init_schema("data/kabusys.duckdb")

# 監査テーブル追加
audit.init_audit_schema(conn)

# データ取得と保存
records = jquants_client.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
n = jquants_client.save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

---

## 貢献 / 拡張ポイント

- strategy、execution、monitoring モジュールは今後の実装箇所です。シグナル生成、ポートフォリオ最適化、ブローカー連携（kabu ステーション API）等をここに追加してください。
- DuckDB スキーマ／インデックスは利用パターンに応じて調整できます。
- J-Quants クライアントの API パス追加、または別データソース（ニュース、代替データ）の追加を想定した拡張が可能です。

---

必要に応じて README のサンプルコードや .env.example を追加で生成します。どの部分を詳しく載せたいか教えてください。