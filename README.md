# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）。  
データ取得、DuckDBスキーマ管理、監査ログなど、自動売買プラットフォームの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からのマーケットデータ（株価日足、財務データ、マーケットカレンダー）取得
- DuckDB を利用したスキーマ定義・初期化（Raw / Processed / Feature / Execution レイヤ）
- 監査（audit）用テーブルの提供（シグナル→発注→約定のトレーサビリティ）
- 環境変数ベースの設定管理（.env 自動読み込み、必須変数チェック）
- レートリミット・リトライ・トークン自動リフレッシュ等を備えた API クライアント

設計上のポイント：
- J-Quants API のレート制限（120 req/min）を守る固定間隔スロットリングを実装
- リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ対応
- データ保存は冪等（ON CONFLICT DO UPDATE）で重複を回避
- すべてのタイムスタンプは UTC を想定（監査ログ等）

---

## 機能一覧

- 環境変数・設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート基準）
  - 必須設定の取得（未設定時は例外）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - get_id_token（リフレッシュトークンから ID トークン取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - 保存処理：save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path) で全テーブル（Raw/Processed/Feature/Execution）を作成
  - get_connection(db_path) で接続を取得
- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn) / init_audit_db(path) による監査テーブル初期化
  - シグナル→オーダーリクエスト→実行（executions）を追跡するテーブル群
- 基本モジュール構造：strategy / execution / monitoring（拡張ポイント）

---

## 要件

- Python 3.10 以上（Union 型表記 X | Y を使用しているため）
- 必要パッケージ（例）
  - duckdb
- 標準ライブラリ: urllib, json, datetime 等

（実際のプロジェクトでは pyproject.toml / requirements.txt に依存関係を明記してください）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（例: venv）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

2. 必要パッケージをインストール
   - 例（最低限）:
     - pip install duckdb

   - プロジェクトに requirements.txt / pyproject.toml がある場合:
     - pip install -r requirements.txt
     - または pip install -e .（編集インストール）

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動で読み込まれます（無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

4. .env の例（プロジェクトルートに `.env` を作成）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単なサンプル）

以下は基本的な利用例です。実行前に環境変数を設定してください。

1) DuckDB スキーマを初期化して接続を取得
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Path を返します（.env の DUCKDB_PATH を参照）
conn = init_schema(settings.duckdb_path)
```

2) J-Quants から日次株価を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# トークンは内部で settings.jquants_refresh_token を使い自動取得/リフレッシュされます
records = fetch_daily_quotes(code="7203")  # 銘柄コードを指定（省略で全銘柄）
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

3) 財務データやマーケットカレンダーも同様
```python
from kabusys.data.jquants_client import fetch_financial_statements, fetch_market_calendar, save_financial_statements, save_market_calendar

fin = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

4) 監査ログテーブルを既存接続に追加
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

5) 設定の利用
```python
from kabusys.config import settings

print(settings.env)          # development / paper_trading / live
print(settings.duckdb_path)  # Path
```

注意点：
- jquants_client は内部で固定間隔のレート制御を行い、リトライ・ID トークンの自動リフレッシュを試みます。
- save_* 系はレコード重複に対して ON CONFLICT DO UPDATE を行うため冪等です。

---

## ディレクトリ構成

リポジトリは src 配下にパッケージを置く構成です。主要ファイルは以下の通りです。

- src/
  - kabusys/
    - __init__.py
    - config.py              -- 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
    - data/
      - __init__.py
      - jquants_client.py    -- J-Quants API クライアント（取得・保存ロジック）
      - schema.py            -- DuckDB スキーマ定義と init_schema / get_connection
      - audit.py             -- 監査ログ（signal_events, order_requests, executions）
    - strategy/
      - __init__.py          -- 戦略関連の拡張ポイント（未実装ファイル）
    - execution/
      - __init__.py          -- 発注・ブローカー連携の拡張ポイント（未実装ファイル）
    - monitoring/
      - __init__.py          -- モニタリング関連（未実装ファイル）

（実際のリポジトリでは README.md、pyproject.toml、.gitignore、.env.example 等をプロジェクトルートに置くことを推奨します）

---

## 動作上の注意・設計メモ

- API レート制御は固定間隔スロットリング（_RateLimiter）を用いており、最大 120 req/min を意識した実装です。
- リトライは最大 3 回（指数バックオフ）、HTTP 408 / 429 / 5xx を対象に再試行します。429 の場合は Retry-After ヘッダを優先します。
- 401 を受信した場合は一度だけトークンをリフレッシュして再試行します（無限再帰回避のためのフラグあり）。
- 取得したデータに対して fetched_at を UTC で保存し、Look-Ahead Bias の防止を支援します。
- 監査ログは削除しない前提で設計されており、FK は ON DELETE RESTRICT を使用します。すべての TIMESTAMP は UTC で保存します（init_audit_schema は SET TimeZone='UTC' を実行）。

---

## 開発・拡張

- strategy / execution / monitoring パッケージは拡張ポイントです。戦略ロジック、ポートフォリオ最適化、ブローカー接続（kabuステーション等）を実装してください。
- Unit test や CI を導入して、特に DB スキーマのマイグレーション／互換性・API クライアントの挙動を検証することを推奨します。

---

必要であれば README に追加する内容（例：API 使用制限のより詳細な説明、テスト実行手順、CI 設定例、貢献ガイドライン等）を教えてください。