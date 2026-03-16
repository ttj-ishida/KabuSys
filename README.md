# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ。  
データ取得・保存（J-Quants → DuckDB）、データ品質チェック、監査ログスキーマなど、取引全体のデータ基盤（Data Platform）を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムを構築するための基盤モジュール群です。主に以下を提供します。

- J-Quants API クライアント（株価・財務・マーケットカレンダー取得）
- DuckDB 用スキーマ定義と初期化
- 監査ログ（signal → order → execution のトレーサビリティ）
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- 環境変数 / 設定管理（.env 自動読込機能）
- （戦略 / 実行 / モニタリング用のパッケージ構成用意）

設計方針として、データ取得はレート制限・リトライ・トークン自動更新を備え、保存は冪等（ON CONFLICT DO UPDATE）で行います。監査ログは削除しない前提で UTC タイムスタンプを用いています。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（OS 環境変数優先）
  - 必須環境変数取得（未設定時は ValueError）
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL 検証

- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - RateLimiter（120 req/min）、リトライ（指数バックオフ、最大 3 回）、401 時のトークン自動リフレッシュ
  - DuckDB への保存用関数: save_daily_quotes / save_financial_statements / save_market_calendar（冪等）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution のテーブル群を定義
  - init_schema(db_path) でテーブル・インデックスを作成
  - get_connection(db_path) で接続取得（初回は init_schema を推奨）

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions を定義
  - init_audit_schema(conn) / init_audit_db(db_path) を提供
  - 全て UTC 保存、冪等キーや制約を設定

- データ品質チェック（kabusys.data.quality）
  - check_missing_data, check_duplicates, check_spike, check_date_consistency
  - run_all_checks で一括実行。QualityIssue オブジェクトで結果を返す（error/warning）

---

## 前提要件

- Python 3.10 以上（型アノテーションで | 演算子を使用）
- 必要パッケージ（例）
  - duckdb

インストール例（プロジェクト単体で依存は少ないため、最低限 duckdb を入れる）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
# 開発中はパッケージを editable-install する場合:
# pip install -e .
```

---

## 環境変数 / .env

kabusys.config.Settings が参照する主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, デフォルト: development) — 有効値: development, paper_trading, live
- LOG_LEVEL (任意, デフォルト: INFO) — 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意) — 自動 .env 読込を無効化する場合は "1" を設定

自動読み込みの優先順位:
OS 環境変数 > .env.local > .env

自動読込はプロジェクトルート（.git または pyproject.toml を基準）から行われます。読み込みを無効にしたいテストなどでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 .env（実際には .env.example を参照して作成してください）:

```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=passwd
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境作成・有効化
3. 依存インストール（最低: duckdb）
4. .env をプロジェクトルートに用意（または環境変数を OS レベルで設定）
5. DuckDB スキーマ初期化

コマンド例:

```bash
git clone <repo-url>
cd <repo-dir>
python -m venv .venv
source .venv/bin/activate
pip install duckdb

# .env を用意する (.env.local があればそれが優先で上書きされます)
# DB 初期化は Python から実行します（以下参照）
```

---

## 使い方（主要 API の例）

以下は代表的な使用例です。実環境ではエラーハンドリングやログ設定を適切に行ってください。

- 設定取得:

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env, settings.is_live)
```

- DuckDB スキーマ初期化:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成される
```

- J-Quants から日足を取得して保存:

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
n = save_daily_quotes(conn, records)
print(f"{n} 件保存されました")
```

- 財務データ / マーケットカレンダーの取得と保存:

```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements, fetch_market_calendar, save_market_calendar

fin = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

- 監査ログテーブルを既存接続に追加:

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # conn は init_schema の返り値など
```

- 監査ログ専用 DB を作る:

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

- データ品質チェックの実行:

```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.table, issue.severity, issue.detail)
    for row in issue.rows:
        print(" ", row)
```

---

## 注意点 / 実装上の補足

- J-Quants クライアント
  - レート制御（120 req/min）を行うため、短時間に大量のリクエストを投げる用途では注意してください。
  - HTTP エラー時は最大 3 回リトライ（408/429/5xx 等）。429 の場合は Retry-After ヘッダを優先。
  - 401 の場合はリフレッシュトークンから ID トークンを自動取得して 1 回だけリトライします。

- DuckDB スキーマ
  - init_schema は冪等（既存テーブルは変更しない）。初回のみ実行してください。
  - get_connection は既存 DB への単純な接続を返します（スキーマ初期化は行わない）。

- データ品質チェック
  - 各チェックは全ての問題点を収集して返す設計です（Fail-Fast ではありません）。
  - 呼び出し元で severity を見て ETL の中断や運用アラートを検討してください。

- 環境変数読み込み
  - 自動読み込みはプロジェクトルート検出（.git または pyproject.toml）に依存します。パッケージとして配布した場合は読み込みが期待通り動作しないケースがあるため、その場合は OS 環境変数を直接設定してください。

- 空のパッケージ
  - strategy、execution、monitoring パッケージは初期化ファイルのみ用意されています。戦略実装や発注ロジック、監視ロジックはこれらに追加していきます。

---

## ディレクトリ構成

リポジトリの主要なファイル／ディレクトリ（src 配下）:

- src/kabusys/
  - __init__.py  -- パッケージ初期化（__version__ など）
  - config.py    -- 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py  -- J-Quants API クライアント（取得・保存関数）
    - schema.py          -- DuckDB スキーマ定義・初期化
    - audit.py           -- 監査ログ（signal / order_requests / executions）
    - quality.py         -- データ品質チェック（QualityIssue, run_all_checks）
    - (その他)           -- raw / processed / feature / execution に関する DDL
  - strategy/
    - __init__.py  -- 戦略用モジュール（拡張ポイント）
  - execution/
    - __init__.py  -- 発注／ブローカー連携用モジュール（拡張ポイント）
  - monitoring/
    - __init__.py  -- 監視・アラート用モジュール（拡張ポイント）

その他、プロジェクトルートに .env / .env.local / pyproject.toml 等を置く想定です。

---

## 貢献 / 拡張ポイント

- strategy／execution／monitoring パッケージに戦略ロジック、発注アダプタ、監視ジョブを実装してください。
- データ取得対象の拡張（ニュース、ティッカー等）や品質チェックの追加が可能です。
- 運用用スクリプト（定期取得ジョブ、ETL パイプライン）を整備すると実運用が楽になります。

---

もし README に追加したい運用手順（CI/CD、データバックアップ、サンプル .env.example など）があれば教えてください。必要に応じて追記します。