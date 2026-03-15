# KabuSys

日本株自動売買システムのコアライブラリ。データ取得（J-Quants）、データベーススキーマ（DuckDB）、監査ログ、環境設定など、自動売買システムの基盤機能を提供します。

概要、機能、セットアップ、使い方、ディレクトリ構成を以下に記載します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームの基盤モジュール群です。  
主に次の責務を持ちます。

- J-Quants API からの市場データ（株価日足、財務データ、マーケットカレンダー）取得
- DuckDB によるデータスキーマ定義・初期化（Raw / Processed / Feature / Execution レイヤー）
- 監査ログ（シグナル → 発注 → 約定）用スキーマの提供
- 環境変数ベースの設定読み込み（.env 自動ロード、設定オブジェクト提供）
- API 呼び出しのレート制御、リトライ、トークン自動リフレッシュ等の堅牢な HTTP ロジック

設計上、以下を重視しています。
- レート制限とリトライ（J-Quants のレート制限を遵守）
- Look-ahead bias 回避（データ取得時刻を UTC で記録）
- 冪等性（DuckDB への INSERT は ON CONFLICT で更新）

---

## 主な機能一覧

- 環境設定
  - .env/.env.local の自動読み込み（プロジェクトルートを自動検出）
  - settings オブジェクト経由で必要設定を取得（必須キーは未設定時に例外）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

- データ取得（J-Quants）
  - 株価日足（fetch_daily_quotes）
  - 財務データ（fetch_financial_statements）
  - JPX マーケットカレンダー（fetch_market_calendar）
  - トークン取得（get_id_token）
  - レート制限（120 req/min 固定）・指数バックオフ・401 時のトークン自動更新

- DuckDB スキーマ
  - init_schema(db_path) による全テーブル・インデックスの作成（冪等）
  - get_connection(db_path) で既存 DB に接続

- 監査ログ（Audit）
  - init_audit_schema(conn) により監査テーブルを初期化
  - init_audit_db(db_path) により監査専用 DB を初期化

---

## 要求事項 / 依存

- Python 3.10 以上（型ヒントで | 演算子を使用）
- pip パッケージ（最低限）:
  - duckdb
- 標準ライブラリ: urllib, json, logging, datetime, pathlib, os など

推奨: 仮想環境（venv/virtualenv/poetry など）を利用してください。

---

## セットアップ手順

1. リポジトリをクローン/配置
2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb
   ```
   開発パッケージを含める場合はプロジェクトに requirements.txt / pyproject.toml に従ってください。
4. パッケージをインストール（編集可能モード）
   ```
   pip install -e .
   ```
   （setup が用意されていない場合は、直接 PYTHONPATH に src を追加して利用できます）

5. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（優先度: OS > .env.local > .env）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 環境変数（主なキー）

必須のキー（未設定時は settings 呼び出しで ValueError）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

オプション / デフォルト有り:
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")。デフォルト "development"
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)。デフォルト "INFO"
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 など真値）
- KABUS_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）

参考: .env.example（プロジェクトにあれば参照してください）

---

## 使い方（簡単な例）

以下は代表的な利用例です。実行前に適切な環境変数を設定してください。

- settings の利用
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 未設定なら例外
print(settings.duckdb_path)
```

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリは自動作成されます）
conn = init_schema("data/kabusys.duckdb")
```

- J-Quants から日足を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# 単一銘柄を期間指定で取得
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# raw_prices テーブルに保存（ON CONFLICT DO UPDATE により冪等）
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

- 財務データ・マーケットカレンダー取得
```python
from kabusys.data.jquants_client import fetch_financial_statements, fetch_market_calendar, save_financial_statements, save_market_calendar
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

fins = fetch_financial_statements(code="7203")
save_financial_statements(conn, fins)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

- トークン手動取得
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使って POST
```

- 監査ログ（Audit）スキーマ初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
# もしくは既存 conn に init_audit_schema(conn)
```

注意点:
- J-Quants API はレート制限（120 req/min）を内部で制御しますが、複数プロセスからの同時アクセス等は別途注意してください。
- fetch_* 系関数はページネーション対応で全件取得します。大量データ取得時の時間・レートに注意してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py                -- パッケージ初期化（version 等）
    - config.py                  -- 環境変数読み込み・Settings 定義（.env 自動ロード含む）
    - data/
      - __init__.py
      - jquants_client.py        -- J-Quants API クライアント（取得/保存ロジック、レート制御、リトライ）
      - schema.py                -- DuckDB スキーマ定義・初期化（全レイヤー）
      - audit.py                 -- 監査ログ（signal / order_request / executions）スキーマ
      - audit.py                 -- 監査ログ初期化ユーティリティ
      - ...                      -- 将来的に data 層の拡張
    - strategy/
      - __init__.py               -- 戦略関連モジュール（未実装ファイルがプレースホルダ）
    - execution/
      - __init__.py               -- 発注・ブローカー連携（プレースホルダ）
    - monitoring/
      - __init__.py               -- モニタリング関連（プレースホルダ）

上記以外にプロジェクトルートに `.env`, `.env.local`, `pyproject.toml`, `.git` 等が想定されます。

---

## 開発 / テストのヒント

- 自動 .env 読み込みを無効にする場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  ユニットテストなどで OS 環境変数のみを制御したい場合に便利です。

- DuckDB をインメモリで試す:
  ```python
  conn = init_schema(":memory:")
  ```

- ログレベルや環境切替は環境変数で制御できます（KABUSYS_ENV / LOG_LEVEL）。

---

この README は現状のコードベースの主要機能と使い方を簡潔にまとめたものです。さらに詳しい設計方針（DataSchema.md, DataPlatform.md 等）が別途あれば併せて参照してください。必要であればセットアップ手順や使用例を具体的なユースケース（戦略 → 発注のフロー）に合わせて追記します。