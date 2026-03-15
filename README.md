# KabuSys

日本株自動売買システム（KabuSys）の軽量ライブラリ部分のリポジトリです。  
このリポジトリにはデータ取得・保存、DuckDB スキーマ定義、監査ログ（Audit）など自動売買システムの基盤となるモジュールが含まれます。

---

## 概要

KabuSys は日本株の自動売買に必要な基盤機能を提供します。主に次を担います。

- J-Quants API からの市場データ取得（OHLCV、財務データ、JPX カレンダー）
- 取得データの DuckDB への永続化（冪等保存、fetched_at の記録）
- DuckDB スキーマ（Raw / Processed / Feature / Execution 層）の初期化
- 監査ログ（signal → order → execution のトレース）用スキーマの初期化
- 環境変数管理（.env 自動読み込み、必須設定の検証）

設計上の重要点：
- API レート制限（J-Quants: 120 req/min）に対応したレートリミッタ
- リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
- すべてのタイムスタンプは UTC で扱う方針（監査ログ等）

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可能）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL の検証
- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - API 呼び出し時のレート制御、リトライ、トークン自動リフレッシュ
  - DuckDB へ保存するための save_* 関数（save_daily_quotes(), save_financial_statements(), save_market_calendar()）
- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path) により DB と全テーブルを初期化（冪等）
  - get_connection(db_path) で既存 DB に接続
- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn), init_audit_db(db_path) により監査用テーブルを初期化
  - signal → order_request → executions を UUID ベースでトレース可能にするスキーマ
- その他（パッケージ構造上のプレースホルダ）
  - 策略層 / 実行層 / モニタリング用のパッケージプレースホルダ（src/kabusys/strategy, execution, monitoring）

---

## 必要条件

- Python 3.10+
  - （コードは型ヒントに `X | None` の表記を使っているため Python 3.10 以上を想定）
- 依存パッケージ
  - duckdb（DuckDB Python バインディング）
  - （標準ライブラリ: urllib, json, datetime 等を使用）

インストール例（仮に pyproject / setup がある場合）:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb
pip install -e .
```
（本リポジトリに requirements.txt / packaging が無い場合は duckdb のみ先に入れてください）

---

## 環境変数（主なもの）

必須（アプリケーション実行に必要）
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（get_id_token 用）
- KABU_API_PASSWORD : kabuステーション API パスワード（発注連携等で使用）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUS_API_BASE_URL : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）

自動 .env 読み込み
- リポジトリのプロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動読み込みします。
- 読み込みを無効化する場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時などで使用）。

備考: README 内のサンプル .env（.env.example）がある場合はそれを参考に作成してください。

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存ライブラリをインストール
   - pip install duckdb
   - 必要に応じてプロジェクトを開発モードでインストール: pip install -e .

3. .env を作成（プロジェクトルート）
   - 必須環境変数を設定（JQUANTS_REFRESH_TOKEN 等）
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. DuckDB スキーマ初期化
   - Python スクリプトや REPL から schema.init_schema() を呼びます（下の「使い方」を参照）。

---

## 使い方（簡単なサンプル）

- DuckDB スキーマ初期化:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # デフォルトパスと同じ
# conn は duckdb.DuckDBPyConnection
```

- J-Quants から日足を取得して DuckDB に保存:
```python
from kabusys.data import jquants_client
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続（初回は init_schema を呼ぶ）
records = jquants_client.fetch_daily_quotes(code="7203")  # 例: トヨタ (7203)
n = jquants_client.save_daily_quotes(conn, records)
print(f"Saved {n} records")
```

- 財務データ取得と保存:
```python
records = jquants_client.fetch_financial_statements(code="7203")
jquants_client.save_financial_statements(conn, records)
```

- JPX マーケットカレンダー取得と保存:
```python
cal = jquants_client.fetch_market_calendar()
jquants_client.save_market_calendar(conn, cal)
```

- ID トークン直接取得（必要なら）:
```python
token = jquants_client.get_id_token()  # refresh token は settings から自動取得
```

- 監査ログスキーマ初期化（既存の DuckDB 接続へ追加）:
```python
from kabusys.data import audit
audit.init_audit_schema(conn)   # conn: duckdb.DuckDBPyConnection
# または専用ファイルに初期化する場合:
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

設計に関する注意点:
- J-Quants の API 呼び出しは内部で 120 req/min を超えないようにスロットリングされます（_RateLimiter）。
- HTTP エラー 401 を受けた場合はトークンを自動リフレッシュして 1 回だけ再試行します。
- 取得データの保存関数は冪等（ON CONFLICT DO UPDATE）で実装されています。
- 監査ログのタイムスタンプや監査方針は UTC を前提としています。

---

## ディレクトリ構成

（リポジトリ内の主要ファイル／ディレクトリ）
- src/
  - kabusys/
    - __init__.py
    - config.py                : 環境設定読み込み・Settings クラス
    - data/
      - __init__.py
      - jquants_client.py      : J-Quants API クライアント（取得・保存ロジック）
      - schema.py              : DuckDB スキーマ定義 / init_schema
      - audit.py               : 監査ログ（signal/order/execution）スキーマ
      - audit.py               : 監査 DB 初期化ユーティリティ
      - (その他)               : raw / processed / feature / execution 層定義
    - strategy/
      - __init__.py            : 戦略層プレースホルダ
    - execution/
      - __init__.py            : 実行層プレースホルダ
    - monitoring/
      - __init__.py            : モニタリングプレースホルダ

---

## 追加情報 / 開発メモ

- schema.init_schema() はテーブル作成を行うだけで、既存のデータがあっても安全に再実行できます（冪等性）。
- audit.init_audit_schema() は conn に対し UTC タイムゾーンを設定します（SET TimeZone='UTC'）。
- .env のパースはシェルライクな幾つかのケースをサポート（export 文やクォート、コメント処理）。
- テストや一時的に .env の自動読み込みを抑制したいときは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。

---

もし README の追加項目（例: CLI 実行例、詳細なスキーマドキュメント、データフロー図、テストの実行方法など）が必要であれば、目的に合わせて追記します。