# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（ミニマム実装）です。  
主にデータ取得・永続化（DuckDB）と監査ログ（監査用スキーマ）の初期化、J‑Quants API クライアントを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J‑Quants API から市場データ（株価日足、財務データ、JPX カレンダー）を取得
- 取得データを DuckDB に冪等的に保存（Raw / Processed / Feature / Execution 層のスキーマ定義）
- 発注〜約定フローの監査ログ（監査テーブル）を提供し、UUID ベースでトレーサビリティを担保
- 環境変数を .env/.env.local から自動読み込みするユーティリティ
- API 呼び出し時のレート制御・リトライ・トークン自動リフレッシュを内蔵

設計上の注意点：
- J‑Quants API のレート制限（120 req/min）を内部で守ります。
- リトライ（指数バックオフ）や 401 のトークン自動更新に対応しています。
- DuckDB への保存は ON CONFLICT DO UPDATE で冪等性を確保します。
- すべてのタイムスタンプは UTC を想定して扱います（監査スキーマでは明示的に SET TimeZone='UTC' を実行）。

---

## 機能一覧

- 環境変数読み込み / 設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可）
  - 必須値チェック（例: JQUANTS_REFRESH_TOKEN など）
  - KABUSYS_ENV / LOG_LEVEL の検証

- J‑Quants API クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes: 株価日足（ページネーション対応）
  - fetch_financial_statements: 四半期財務データ（ページネーション対応）
  - fetch_market_calendar: JPX カレンダー
  - get_id_token: リフレッシュトークンから id_token を取得
  - 内部でレートリミッタ、リトライ、401 自動リフレッシュを実装
  - 取得データを DuckDB に保存する save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）

- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path): Raw / Processed / Feature / Execution 層のテーブルとインデックスを作成
  - get_connection(db_path): 既存 DB への接続取得（初回は init_schema を推奨）

- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn): 監査テーブル（signal_events, order_requests, executions）を既存接続へ追加
  - init_audit_db(db_path): 監査専用 DB の初期化と接続返却

- ユーティリティ
  - 型変換ユーティリティ（_to_float / _to_int）
  - 固定間隔スロットリングによるレート制御

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型注釈の Union などを使用）
- DuckDB を利用するために duckdb パッケージが必要

1. リポジトリをクローン／配置する
   - パッケージは `src/` 配下に配置されています。

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - 最低限: duckdb
     - pip install --upgrade pip
     - pip install duckdb
   - （Slack 通知などを使う場合は slack_sdk 等を追加でインストールしてください）

4. 環境変数の準備
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成してください。
   - 必須環境変数（少なくとも次を設定すること）:
     - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack Bot Token（監視通知等を使う場合）
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意/デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化
     - KABUSYS データベースパス:
       - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
       - SQLITE_PATH（デフォルト: data/monitoring.db）

   - .env の読み込みは以下の優先順位:
     - OS 環境変数 > .env.local > .env

5. スキーマ初期化（サンプル）
   - Python スクリプトまたは REPL で実行:
     - from kabusys.data.schema import init_schema
       conn = init_schema("data/kabusys.duckdb")
     - 監査スキーマを既存接続へ追加する場合:
       - from kabusys.data.audit import init_audit_schema
         init_audit_schema(conn)
     - 監査専用 DB を作る場合:
       - from kabusys.data.audit import init_audit_db
         conn_audit = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（簡単な例）

1. スキーマの初期化とデータ取得→保存

```python
from kabusys.data.schema import init_schema
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# DB 初期化（ファイルは settings.duckdb_path 等を使っても良い）
conn = init_schema("data/kabusys.duckdb")

# J‑Quants から日足を取得（モジュールは内部でトークンを自動利用／更新）
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# 取得した日足を DuckDB に保存（冪等）
n = save_daily_quotes(conn, records)
print(f"{n} レコードを保存しました")
```

2. 財務データやカレンダーの取得・保存も同様の呼び出しパターンです：
- fetch_financial_statements / save_financial_statements
- fetch_market_calendar / save_market_calendar

3. id_token を明示的に取得する：
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って取得
```

注意点:
- fetch_* 系はページネーション対応で、モジュール内キャッシュされた id_token を共有します。
- ネットワークエラーや 408/429/5xx はリトライ（最大 3 回）されます。401 を受けた場合はトークンを 1 回自動更新してリトライします。

---

## 環境変数（主なキー）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須: Slack を使う場合)
- SLACK_CHANNEL_ID (必須: Slack を使う場合)
- DUCKDB_PATH (省略可、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (省略可、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 にすると自動 .env ロードを無効化)

設定が不足している必須キーを参照すると、Settings のプロパティで ValueError が投げられます。

---

## ディレクトリ構成

リポジトリ内の主要ファイル／モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数／設定管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py           — J‑Quants API クライアント（取得・保存ロジック）
    - schema.py                   — DuckDB スキーマ定義・初期化
    - audit.py                    — 監査ログ（signal/order/execution）スキーマ
    - audit (関連関数)...
    - その他データ関連モジュール
  - strategy/
    - __init__.py                 — 戦略関連（将来的に実装）
  - execution/
    - __init__.py                 — 発注・実行関連（将来的に実装）
  - monitoring/
    - __init__.py                 — 監視・メトリクス（将来的に実装）

README に記載の関数は上記のモジュールで提供されています。詳細は各ソースの docstring を参照してください。

---

## 開発上の注記 / Tips

- .env の読み込みはプロジェクトのルート（.git または pyproject.toml の存在するディレクトリ）を起点に行われます。テスト等で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化は冪等であり、既存テーブルがあれば上書きせずにそのまま利用します。
- 監査ログは削除しない前提（ON DELETE RESTRICT）で設計されています。運用で監査ログの扱いには注意してください。
- J‑Quants の API レート制御やリトライロジックは jquants_client に実装済みですが、上位でさらにキューイングやバックオフ戦略を適用することも可能です。

---

必要に応じて README の拡張（例: CI/テスト手順、より詳しい使い方、サンプルスクリプト）を作成できます。どの追加情報が必要か教えてください。