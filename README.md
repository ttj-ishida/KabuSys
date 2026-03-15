# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。データ取得・永続化、監査ログ、スキーマ定義、戦略・発注・モニタリングの足掛かりを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の機能を持つ内部ライブラリ群です。

- J-Quants API からの市場データ（株価日足、財務データ、JPX カレンダー）取得クライアント
- DuckDB を用いた層別スキーマ（Raw / Processed / Feature / Execution）定義と初期化
- 監査ログ（signal → order_request → executions）用テーブルの定義と初期化
- 環境変数ベースの設定管理（.env 自動読み込み、必須キーの検証）
- レート制限・リトライ・トークン自動更新を備えた API 呼び出しロジック

設計上のポイント:
- API レート制限（J-Quants: 120 req/min）を固定間隔スロットリングで遵守
- リトライ（指数バックオフ、最大 3 回。408/429/5xx 対象）、401 時はトークン自動リフレッシュ
- データ取得時に fetched_at を UTC で記録し、Look-ahead Bias を防止
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で多重挿入を防止
- 監査ログは削除しない前提で設計（トレーサビリティ重視）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得メソッド（未設定時は例外）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロードの無効化

- データ:
  - J-Quants クライアント:
    - get_id_token(refresh_token=None)
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
  - DuckDB スキーマ初期化:
    - init_schema(db_path)
    - get_connection(db_path)
  - データ保存ユーティリティ:
    - save_daily_quotes(conn, records)
    - save_financial_statements(conn, records)
    - save_market_calendar(conn, records)

- 監査ログ:
  - init_audit_schema(conn)
  - init_audit_db(db_path)
  - 監査用テーブル: signal_events, order_requests, executions

- パッケージ構成キー:
  - kabusys.config: 環境変数管理
  - kabusys.data: データ取得・スキーマ・監査
  - kabusys.strategy / kabusys.execution / kabusys.monitoring: プレースホルダ（拡張領域）

---

## 動作環境 / 前提

- Python 3.10 以上（PEP 604 の | 型記法を使用）
- 依存パッケージ（最小）:
  - duckdb
- ネットワークアクセス可能であること（J-Quants API、kabu API 等）
- 推奨: 仮想環境（venv / pyenv）を使用

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# その他の開発ツールやテスト用パッケージはプロジェクトに合わせて追加
```

---

## 環境変数（必須 / 任意）

主に以下の環境変数が使用されます。必須項目はアプリ起動時に検証されます。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（デフォルト値あり）:
- KABUSYS_ENV — 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env の自動読み込みを無効化
- KABUSYS_API_BASE_URL 等はコード内にデフォルトを持っています

DB パス:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

サンプル .env（README 用例）:
```
# .env
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動読み込み:
- プロジェクトルート（.git または pyproject.toml の親ディレクトリ）を基に .env / .env.local を自動で読み込みます。
- OS 環境変数が優先され、.env.local は .env を上書きします（.env.local は override=True）。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb
   ```

2. 必要な環境変数を設定（.env ファイル作成推奨）
   - 上記のサンプル .env を参考に .env を作成します。

3. DuckDB スキーマの初期化
   - 永続 DB ファイルを作る場合:
     ```python
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     ```
   - インメモリでテストする場合:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema(":memory:")
     ```

4. 監査ログテーブルの初期化（任意／別 DB を使う時）
   - 既存の conn に追加する:
     ```python
     from kabusys.data.audit import init_audit_schema
     from kabusys.data.schema import get_connection
     conn = get_connection("data/kabusys.duckdb")
     init_audit_schema(conn)
     ```
   - 監査専用 DB を作る:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（主な API 例）

- 環境設定を取得する:
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必須。未設定だと ValueError
print(settings.duckdb_path)            # Path オブジェクト
print(settings.env)                    # development / paper_trading / live
```

- J-Quants から日足を取得して DuckDB に保存する:
```python
from kabusys.data.jquants_client import (
    fetch_daily_quotes, get_id_token, save_daily_quotes
)
from kabusys.data.schema import init_schema

# DB 初期化（既に初期化済みであれば get_connection を使って接続を得る）
conn = init_schema("data/kabusys.duckdb")

# 取得（必要なら get_id_token で明示的にトークン取得も可能）
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# 保存（冪等）
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

- 財務データ / カレンダーの使用法は fetch_financial_statements / fetch_market_calendar と対応する save_* 関数を呼び出します。

- トークン取得を直接行う（テスト等）:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って ID トークンを取得
```

- 自動環境読み込みを無効にする（テストなどで必要な場合）:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 注意点 / 実装上の特徴

- J-Quants クライアントはモジュールレベルで ID トークンキャッシュを持ち、ページネーション間で再利用します。401 受信時は一度だけ自動リフレッシュして再試行します。
- リトライは最大 3 回、408/429/5xx を対象に指数バックオフ（429 は Retry-After ヘッダ優先）を行います。
- DuckDB への保存は ON CONFLICT ... DO UPDATE を用いて冪等に実装されています。
- すべての監査ログタイムスタンプは UTC 保存を前提としています（init_audit_schema は TimeZone='UTC' を設定します）。
- 型変換ユーティリティは厳格に empty / malformed 値を None にする実装です（例: 小数表現の整数化は安全を期す）。

---

## ディレクトリ構成

以下は主要ファイルの一覧（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py       — J-Quants API クライアント（取得・保存）
      - schema.py               — DuckDB スキーマ定義・初期化
      - audit.py                — 監査ログスキーマ（signal/order_request/executions）
      - audit.py
      - (その他: audit 関連)
    - strategy/
      - __init__.py             — 戦略モジュール（拡張ポイント）
    - execution/
      - __init__.py             — 発注 / ブローカー連携（拡張ポイント）
    - monitoring/
      - __init__.py             — 監視・メトリクス（拡張ポイント）

---

## 拡張・次のステップ（開発者向け）

- strategy / execution / monitoring パッケージに戦略実装、発注実装、モニタリングロジックを実装してください。
- Slack 通知や実行環境ごとの設定（paper/live）に応じた安全制御（サンドボックス / 実際の注文抑止）を実装してください。
- テストカバレッジを拡充し、network 呼び出しをモック化して CI を構築してください。
- 必要に応じて requirements.txt / pyproject.toml を整備し、パッケージ配布を行ってください。

---

## ライセンス / 責務

この README はコードベースの説明用です。運用環境で自動売買を行う場合は、金融商品取引法や各種規約、取引所・ブローカーのガイドラインに従ってください。実運用に先立ち、十分なバックテストとリスク管理を行ってください。

---

ご要望があれば、README に含める具体的な .env.example、セットアップ用スクリプト、またはパッケージ化手順（pyproject.toml の例）を作成します。どの内容を優先しますか？