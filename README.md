# KabuSys

日本株自動売買プラットフォーム用のライブラリ群（KabuSys）。  
データ収集・スキーマ管理・監査ログなど、トレーディングシステムの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした内部ライブラリ群です。

- J-Quants API からの市場データ（株価日足・財務情報・マーケットカレンダー）取得
- DuckDB によるスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 監査用テーブル（シグナル→発注→約定のトレース）定義と初期化
- 環境変数／設定管理（.env の自動読み込み、Settings クラス）
- rate limit・リトライ・トークン自動リフレッシュ等を考慮した API クライアント設計

設計上の特徴：
- API レート制限（J-Quants: 120 req/min）をモジュール内で制御
- HTTP リトライ（指数バックオフ、最大 3 回、特定ステータスで再試行）
- 401 時はリフレッシュトークンで自動更新して再試行（1回）
- データ取得時に fetched_at を UTC で記録し、look-ahead bias を低減
- DuckDB への挿入は冪等になるよう ON CONFLICT DO UPDATE を使用

---

## 主な機能一覧

- 環境変数管理（kabusys.config.Settings）
  - 自動的にプロジェクトルートの `.env` / `.env.local` を読み込み（必要に応じて無効化可能）
  - 必須キーチェック（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - get_id_token（リフレッシュトークンを用いた idToken 取得）
  - DuckDB に保存する save_* 関数（save_daily_quotes 等、冪等）
- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path) : 全テーブル・インデックスを作成
  - get_connection(db_path) : 既存 DB への接続取得
- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn) / init_audit_db(db_path) : 監査用テーブルを初期化
  - signal_events / order_requests / executions 等の DDL
- モジュール構造：strategy, execution, monitoring 用のパッケージプレースホルダあり

---

## 必要条件

- Python 3.9+
- 依存ライブラリ（最低限）
  - duckdb
- ネットワーク接続（J-Quants API へのアクセス）
- 環境変数（後述）

（パッケージとして配布する際は、pyproject.toml / requirements.txt で依存を明示してください）

---

## セットアップ手順

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2. 依存パッケージをインストール
   - pip install duckdb

3. リポジトリをプロジェクトルートに配置（.git か pyproject.toml が存在する場所が自動的に探されます）

4. 環境変数ファイルを作成（プロジェクトルートに .env を置く）
   - 自動読み込みが有効（デフォルト）だと、kabusys.config が起動時に `.env` / `.env.local` を読み込みます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例: .env（最低限の項目）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
# (オプション) KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development  # development|paper_trading|live
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

以下は J-Quants から日足を取得して DuckDB に保存する基本的なワークフロー例です。

1. スキーマを初期化して接続を取得
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は .env の DUCKDB_PATH を参照
conn = init_schema(settings.duckdb_path)
```

2. データ取得と保存
```python
from kabusys.data import jquants_client
from datetime import date

# 銘柄コードや日付範囲を指定して取得
records = jquants_client.fetch_daily_quotes(
    code="7203",                     # 銘柄コード（省略で全銘柄）
    date_from=date(2023, 1, 1),
    date_to=date(2023, 12, 31),
)

# 保存（冪等）
n = jquants_client.save_daily_quotes(conn, records)
print(f"{n} 件保存しました")
```

3. 監査ログの初期化（必要に応じて）
```python
from kabusys.data.audit import init_audit_schema

# 既存の conn に監査用テーブルを追加
init_audit_schema(conn)
```

補足：
- get_id_token(refresh_token=None) を直接呼ぶと、Settings.jquants_refresh_token を使ってトークンを取得します。
- fetch_* 関数は内部でトークンをキャッシュし、ページネーションに対応しています。
- save_* 関数は ON CONFLICT DO UPDATE を使って冪等に保存します。

---

## 設定（Settings）

kabusys.config.Settings から設定を取得できます。主なプロパティ：

- jquants_refresh_token: J-Quants のリフレッシュトークン（必須）
- kabu_api_password: kabuステーション API のパスワード（必須）
- kabu_api_base_url: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- slack_bot_token: Slack Bot トークン（必須）
- slack_channel_id: Slack チャンネル ID（必須）
- duckdb_path: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- sqlite_path: SQLite ファイルパス（監視用、デフォルト: data/monitoring.db）
- env: KABUSYS_ENV（development|paper_trading|live）
- log_level: LOG_LEVEL（DEBUG/INFO/...）

例：
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

自動 .env ロード：
- デフォルトでは、パッケージがロードされる際にプロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を読み込みます。
- OS 環境変数は保護され、`.env.local` は `.env` の値を上書きします（ただし OS 環境変数は上書きされません）。
- 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 運用上の注意 / 実装ノート

- J-Quants API のレート制限（120 req/min）に合わせて内部で固定間隔スロットリングを行っています（_RateLimiter）。
- ネットワークエラーや 429/408/5xx に対しては指数バックオフで最大 3 回リトライします。429 の場合は Retry-After ヘッダーを優先します。
- 401 が返った場合は一度だけリフレッシュトークンで id_token を再取得しリトライします（無限再帰防止あり）。
- データ保存関数は fetched_at を UTC 時刻で記録しており、いつデータを取得したか追跡できます（Look-ahead Bias 対策）。
- DuckDB の初期化は冪等（init_schema は既存テーブルを上書きしない）です。
- 監査ログ（audit）は削除しない前提で設計されています（ON DELETE RESTRICT 等）。

---

## ディレクトリ構成

リポジトリの主要ファイル（抜粋）：

- src/
  - kabusys/
    - __init__.py
    - config.py                -- 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py      -- J-Quants API クライアント（取得・保存ロジック）
      - schema.py              -- DuckDB スキーマ定義・初期化
      - audit.py               -- 監査ログ（signal/order/execution）
      - audit.py
      - (その他データ関連モジュール)
    - strategy/
      - __init__.py            -- 戦略関連プレースホルダ
    - execution/
      - __init__.py            -- 発注・ブローカー連携プレースホルダ
    - monitoring/
      - __init__.py            -- 監視系プレースホルダ

主要なファイルの役割：
- config.py: .env 読込ロジック、Settings クラス（必須環境変数チェック等）
- data/jquants_client.py: API 呼び出し、ページネーション、リトライ、保存用ユーティリティ
- data/schema.py: Raw/Processed/Feature/Execution レイヤーの DDL と init_schema()
- data/audit.py: 監査ログ用 DDL と init_audit_schema()

---

## 追加情報 / 開発者向けメモ

- strategy, execution, monitoring パッケージは現状プレースホルダです。戦略実装や実際のブローカー連携はこれらに実装してください。
- DuckDB は大きなデータを扱う際に高速で便利です。ファイルパスは settings.duckdb_path で管理してください。
- ロギングは標準 logging を利用します。LOG_LEVEL 環境変数で設定してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを防げます。

---

必要であれば、README にサンプル .env.example ファイル、より詳しい API 使用例、CI/テスト実行方法などを追記できます。どの追加情報が必要か教えてください。