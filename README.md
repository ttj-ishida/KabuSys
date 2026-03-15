# KabuSys

バージョン: 0.1.0

日本株向けの自動売買プラットフォーム基盤ライブラリ。データ取得（J-Quants）、データベース（DuckDB）スキーマ、監査ログ、環境設定を含むモジュール群を提供します。戦略実装や発注実行のための基盤となるユーティリティを備えています。

---

## 概要

KabuSys は以下を目的としたライブラリです。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得
  - レート制限、リトライ、トークン自動リフレッシュ、look-ahead-bias 回避（fetched_at の記録）
- DuckDB を用いた3層データレイヤ（Raw / Processed / Feature）と実行層のスキーマ定義・初期化
- 発注フローの監査ログ（UUID によるトレーサビリティ）を別モジュールで提供
- 環境変数による設定管理（.env の自動読み込み機能を含む）

設計上の注意点:
- Python 型ヒントに新しい構文を使っており、Python 3.10 以上を想定しています。
- 主要な依存は duckdb（その他は標準ライブラリ）です。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の検証 helper（settings）
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD

- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token（リフレッシュトークンから idToken を取得）
  - fetch_daily_quotes（株価日足、ページネーション対応）
  - fetch_financial_statements（四半期財務データ、ページネーション対応）
  - fetch_market_calendar（JPX マーケットカレンダー）
  - レート制限（120 req/min）、指数バックオフリトライ、401 時の自動トークンリフレッシュ
  - DuckDB へ冪等的に保存する save_* 関数（raw_prices, raw_financials, market_calendar）

- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema(db_path) による初期化（冪等）
  - get_connection(db_path)

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの定義
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化

---

## セットアップ手順

前提:
- Python 3.10 以上
- Git 等の一般的な開発環境

1. リポジトリをクローン／取得
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb
   - （プロジェクトを editable install する場合）
     - pip install -e .

   ※ pyproject.toml / requirements.txt がある場合はそちらを参照してください。

4. 環境変数（.env）を準備
   - プロジェクトルート（.git や pyproject.toml を含む階層）に `.env` または `.env.local` を配置できます。
   - KabuSys は起動時に自動で .env を読み込みます（無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須環境変数（例、README に記載されたもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack ボットトークン（通知用）
- SLACK_CHANNEL_ID: Slack チャンネル ID（通知用）

オプション / デフォルト
- KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL （デフォルト: INFO）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

例 .env（最小）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡易例）

以下は主要なユースケースの例です。

- DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb の接続オブジェクト
```

- J-Quants から日足を取得して保存する

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# 全銘柄／日付レンジを指定して取得
records = fetch_daily_quotes(date_from=date(2023, 1, 1), date_to=date(2023, 12, 31))
saved = save_daily_quotes(conn, records)
print(f"保存件数: {saved}")
```

- 財務データの取得と保存

```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = fetch_financial_statements(date_from=date(2022,1,1), date_to=date(2023,12,31))
save_financial_statements(conn, records)
```

- マーケットカレンダーの取得と保存

```python
from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

- id_token を直接取得する（必要に応じて）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

- 環境設定を参照する

```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
print(settings.env, settings.log_level)
```

- 監査ログの初期化（既存接続に追加）

```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

注意点:
- J-Quants API にはレート制限があるため、短時間に大量リクエストを投げないでください。クライアントは内部で制御しますが、運用時のリクエスト設計に配慮してください。
- save_* 関数は冪等（ON CONFLICT DO UPDATE）になっており、重複投入を避けられます。
- fetch_* 系はページネーションをサポートし、内部で id_token キャッシュを共有します。

---

## ディレクトリ構成

（主要ファイル抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数管理・Settings
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（取得・保存ロジック）
      - schema.py              # DuckDB スキーマ定義・初期化
      - audit.py               # 監査ログ（signal/order/execution）
      - audit.py
      - (その他 data モジュール)
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主要モジュールの概要:
- kabusys.config: .env 自動読み込み、Settings オブジェクト
- kabusys.data.jquants_client: API との入出力、リトライ・レート制御、DuckDB への保存ユーティリティ
- kabusys.data.schema: 全テーブルの DDL（Raw/Processed/Feature/Execution）と初期化関数
- kabusys.data.audit: 発注・約定の監査ログ定義と初期化関数

---

## 運用上の注意 / 補足

- 自動で .env を読み込む処理はプロジェクトルート（.git または pyproject.toml の存在する親ディレクトリ）を基準に行います。テストなどで自動ロードを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings.env は development / paper_trading / live のいずれかである必要があります（値検証あり）。
- LOG_LEVEL は標準的なログレベル（DEBUG, INFO, ...）のいずれかにしてください。
- DuckDB の初期化は冪等です。既存テーブルがあれば再作成されません。
- 監査ログは削除しない前提で設計されており、FK は ON DELETE RESTRICT（履歴保持を想定）です。

---

もし README に追加したいセクション（例えば CI/テスト、詳細なスキーマ説明、運用手順、例外処理ポリシー等）があれば教えてください。必要に応じて .env.example のテンプレートや具体的な運用例も作成します。