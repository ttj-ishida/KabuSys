# KabuSys

日本株の自動売買・データプラットフォーム用ライブラリ（部分実装）

このリポジトリは日本株のデータ取得、DuckDB スキーマ定義、監査ログ、データ品質チェックなどを提供する内部ライブラリ群です。J-Quants API を利用したデータ収集や、DuckDB を用いた永続化・検査を想定しています。

---

## 主な概要

- パッケージ名: `kabusys`
- 目的: J-Quants 等から株価/財務/市場カレンダーなどを取得して DuckDB に保存し、品質チェックや取引監査ログの管理を行うための基盤的モジュール群。
- 設計上のポイント:
  - J-Quants API のレート制限（120 req/min）を遵守する内部 RateLimiter を備えています。
  - HTTP リクエストは指数バックオフのリトライ（最大 3 回）、401 発生時のトークン自動リフレッシュに対応します。
  - DuckDB へは冪等に保存する（ON CONFLICT DO UPDATE）方式を採用。
  - 監査ログは一貫した UUID 階層でトレーサビリティを確保します（削除なし・UTC タイムスタンプ）。

---

## 機能一覧

- 環境設定管理 (`kabusys.config`)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み（無効化可）
  - 必須環境変数チェックと便利なプロパティ（J-Quants トークン、kabu API, Slack, DB パス など）

- データ取得クライアント (`kabusys.data.jquants_client`)
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得（ページネーション対応）
  - JPX マーケットカレンダー取得
  - レート制御、リトライ、トークン自動リフレッシュ、fetched_at（UTC）記録
  - DuckDB への保存関数（raw_prices, raw_financials, market_calendar） — 冪等（ON CONFLICT DO UPDATE）

- DuckDB スキーマ定義・初期化 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution 層のテーブル定義（DDL）
  - インデックス定義と初期化関数（init_schema / get_connection）

- 監査ログ（Order/Execution トレーサビリティ） (`kabusys.data.audit`)
  - signal_events / order_requests / executions の DDL と初期化関数
  - TIMESTAMP は UTC 保存を前提に設計

- データ品質チェック (`kabusys.data.quality`)
  - 欠損データ検出（OHLC 欠損）
  - 異常値（スパイク）検出（前日比閾値）
  - 重複チェック（主キー重複）
  - 日付不整合チェック（未来日付、非営業日のデータ）
  - 各チェックは QualityIssue オブジェクトのリストを返す（集めて報告する方式）

---

## 必要条件 / 依存

- Python 3.10+
- duckdb
- （ネットワーク接続：J-Quants API）
- その他プロジェクトで必要となるライブラリは実際の実装・運用スクリプトに応じて追加してください。

インストール例（開発用）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb
# パッケージ開発時はプロジェクトルートで:
pip install -e .
```

---

## 環境変数（重要）

以下はコード内で参照される主要な環境変数です（必須のものは README のサンプル .env に示します）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意／デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...。デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合は `1` をセット

サンプル .env:
```
# 必須
JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
KABU_API_PASSWORD=あなたの_kabu_api_password
SLACK_BOT_TOKEN=あなたの_slack_bot_token
SLACK_CHANNEL_ID=あなたの_slack_channel_id

# 任意
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: パッケージはプロジェクトルート（.git または pyproject.toml）から `.env` / `.env.local` を自動読み込みします。自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
2. Python 仮想環境を作成して有効化
3. 依存ライブラリをインストール（最低限 duckdb）
4. プロジェクトルートに `.env` を作成（上記サンプル参照）
5. DuckDB スキーマを初期化

例:
```bash
git clone <repo-url>
cd <repo-root>
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb
# 必要ならプロジェクトを編集可能モードでインストール
pip install -e .
# .env を作成
# DuckDB スキーマ初期化は Python から:
python - <<'PY'
from kabusys.data.schema import init_schema
from kabusys.config import settings
init_schema(settings.duckdb_path)
print("DuckDB initialized at", settings.duckdb_path)
PY
```

---

## 使い方（主要な API 例）

以下は典型的なワークフロー例です。

1) DuckDB スキーマを初期化する:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

2) J-Quants からデータを取得して保存する（株価日足の例）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import get_connection
from kabusys.config import settings

# DuckDB 接続（既に init_schema で初期化済みを想定）
conn = get_connection(settings.duckdb_path)

# 日足を取得（銘柄コードを指定することも可能）
records = fetch_daily_quotes(code="7203")  # 例: トヨタ (7203)
n = save_daily_quotes(conn, records)
print(f"saved {n} daily quote rows")
```

3) 財務データ・カレンダー取得と保存:
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

fin_records = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin_records)

cal_records = fetch_market_calendar()
save_market_calendar(conn, cal_records)
```

4) 監査ログ（audit）テーブルを追加する:
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
init_audit_schema(conn)  # audit テーブルを追加
```

5) データ品質チェックを実行する:
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
    for row in issue.rows:
        print("  sample:", row)
```

6) get_id_token の直接取得（必要に応じて）:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用して取得
```

注意点:
- fetch 系関数は内部でレート制御とリトライを実施します。
- save_* 関数は重複を上書きするため複数回実行しても安全です（冪等性）。
- 監査ログは削除しない想定です。OrderRequest の order_request_id は冪等キーとして利用可能です。

---

## ディレクトリ構成

（本リポジトリに含まれる主要ファイル・モジュール）

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数・設定管理
    - execution/
      - __init__.py                 — 発注関連（未実装のプレースホルダ）
    - strategy/
      - __init__.py                 — 戦略関連（未実装のプレースホルダ）
    - monitoring/
      - __init__.py                 — 監視・メトリクス関連（未実装のプレースホルダ）
    - data/
      - __init__.py
      - jquants_client.py           — J-Quants API クライアント（取得・保存ロジック）
      - schema.py                   — DuckDB スキーマ定義・初期化
      - audit.py                    — 監査ログ（signal / order_request / executions）
      - quality.py                  — データ品質チェック
- pyproject.toml (想定)
- .git/ (想定)

---

## ロギング・実行環境

- 環境変数 `LOG_LEVEL` と `KABUSYS_ENV` により実行モードとログ出力レベルを制御できます。
  - KABUSYS_ENV: `development`, `paper_trading`, `live`
  - LOG_LEVEL: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- すべての永続化タイムスタンプは基本 UTC を想定しています（監査ログは SET TimeZone='UTC' を実行）。

---

## 開発メモ / 注意事項

- この README は現状提供されているソースコードに基づく説明です。戦略ロジックや発注実行の具体実装は含まれていません（execution/strategy/monitoring はプレースホルダ）。
- 実運用では API キー・トークンの厳重な管理、接続先の IP/ネットワーク制御、発注ロジックの前提検証・リスク管理を必ず行ってください。
- DuckDB を他プロセスと共有する場合のロック・排他に注意してください（運用次第で外部 DB を使うことを検討してください）。

---

必要であれば README にサンプル .env.example ファイルや、CI 用の DB 初期化スクリプト、ユニットテストの実行方法などを追記します。どの情報をさらに追加しましょうか？