# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（モジュール群）。  
データ取得、スキーマ管理、監査ログ、戦略・実行・モニタリングの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたライブラリです。

- J-Quants API からの市場データ（株価日足・財務データ・JPXカレンダー等）の取得と DuckDB への永続化
- データレイヤ（Raw / Processed / Feature / Execution）を意識したスキーマ定義と初期化
- 発注・約定までをトレース可能にする監査ログ（監査テーブル群）
- 環境変数ベースの設定管理（自動 .env ロード機構）
- レート制限・リトライ・トークン自動リフレッシュ等を備えた堅牢な API クライアント設計

設計上のポイント:
- J-Quants API のレート制限（120 req/min）を固定間隔スロットリングで守る
- ネットワーク/HTTP エラーに対する指数バックオフ付きリトライ（最大 3 回）
- 401 発生時はリフレッシュトークンから自動で ID トークンを更新してリトライ
- DuckDB への挿入は ON CONFLICT ... DO UPDATE による冪等処理
- 監査ログは削除しない前提で設計（FK は ON DELETE RESTRICT）

対応 Python バージョン:
- Python 3.10 以上（型注釈の union 演算子 `|` を使用）

---

## 機能一覧

- 環境設定管理（settings）
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN 等）
  - 自動的な .env / .env.local の読み込み（project root を基準）
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`
- J-Quants API クライアント
  - get_id_token（リフレッシュトークンから ID トークンを取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レートリミット、リトライ、ページネーション対応
  - save_* 系で DuckDB への保存（raw_prices / raw_financials / market_calendar）
- DuckDB スキーマ管理（data.schema）
  - init_schema(db_path) で全テーブル・インデックスを作成
  - get_connection(db_path) で既存 DB に接続
  - Raw / Processed / Feature / Execution の多層スキーマ
- 監査ログ（data.audit）
  - init_audit_schema(conn) で監査ログ用テーブルを追加
  - init_audit_db(db_path) で監査ログ専用 DB を初期化
  - signal_events, order_requests, executions を含むトレーサビリティ階層
- その他のプレースホルダモジュール（strategy, execution, monitoring の初期化）

---

## セットアップ手順

前提:
- Python 3.10+
- pip が利用可能

1. 仮想環境（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージのインストール（最低限 DuckDB）
   ```
   pip install duckdb
   ```
   ※ 他に Slack API などを利用する場合は各ライブラリ（例: slack-sdk）を追加してください。

3. リポジトリを開発モードでインストール（パッケージ化されている場合）
   ```
   pip install -e .
   ```
   もしくはプロジェクトルートから直接 `src/` を PYTHONPATH に設定して利用できます。

4. 環境変数の設定
   - プロジェクトルート（`.git` または `pyproject.toml` のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 読み込み順序（優先度高 → 低）: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

必須環境変数（ライブラリ内で `_require` を呼んでいるもの）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live、デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)

例: .env（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方

以下は主要な利用例です。実行前に必ず必須環境変数を設定してください。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb の接続オブジェクト（duckdb.DuckDBPyConnection）
```

2) J-Quants から日足を取得して保存する（例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# 事前に settings.JQUANTS_REFRESH_TOKEN を環境変数で用意しておく
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
# conn は init_schema で取得した接続
n = save_daily_quotes(conn, records)
print(f"{n} レコードを保存しました")
```

3) 財務データ・市場カレンダーの取得と保存
```python
from kabusys.data.jquants_client import fetch_financial_statements, fetch_market_calendar, save_financial_statements, save_market_calendar

fin = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

4) 監査ログ用スキーマの初期化（既存接続へ追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # conn は init_schema で得た接続
```

5) settings の利用
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)
print(settings.is_live)
```

注意点:
- J-Quants クライアントは内部でレート制御とリトライを行います。大量にループで呼ぶ際もレート制限に注意してください。
- fetch_* 関数はページネーションに対応しています（pagination_key を追いかける）。
- save_* 関数は冪等（ON CONFLICT DO UPDATE）なので、再投入しても重複しません。

---

## ディレクトリ構成

以下はコードベースの主要ファイル・ディレクトリ構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（取得・保存機能）
      - schema.py              # DuckDB スキーマ定義・初期化
      - audit.py               # 監査ログ（signal/order/execution）定義・初期化
    - strategy/
      - __init__.py            # 戦略関連（将来的な実装）
    - execution/
      - __init__.py            # 発注関連（将来的な実装）
    - monitoring/
      - __init__.py            # モニタリング（将来的な実装）

主な機能は data パッケージ（jquants_client, schema, audit）に集約されています。strategy / execution / monitoring は骨組みとして用意されています。

---

## 実運用に向けた補足

- 本ライブラリはデータ取得・保存・監査ログの基盤を提供します。実際の戦略ロジック・リスク管理・ブローカー API 連携（kabuステーション等）は execution / strategy モジュールで拡張してください。
- 監査ログは削除しない前提（データ保持）で設計されています。運用の要件に応じてバックアップ・アーカイブ方針を検討してください。
- DuckDB ファイルの保存先（DUCKDB_PATH）は十分なディスク容量を確保してください。
- Slack 通知等を行う際は別途 Slack クライアントライブラリ（slack-sdk 等）を導入し、settings からトークン等を取得して利用してください。

---

この README はコードベースの現在の実装に基づいています。追加の実装（戦略・発注実行・モニタリング機能）が入るにつれて README も更新してください。