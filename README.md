# KabuSys

日本株自動売買システム用のライブラリ群（部分実装）。  
このリポジトリはデータ取得・格納・品質管理・監査ログなど、トレーディングプラットフォームのデータプラットフォーム周りの共通機能を提供します。

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買プラットフォーム向けの共通モジュール群です。主に以下を提供します。

- J-Quants API クライアント（株価、財務、マーケットカレンダー取得）
- DuckDB を使ったデータスキーマ定義と初期化
- データ保存（Raw → DuckDB）用の冪等な保存ロジック
- 監査ログ（シグナル→発注→約定 のトレーサビリティ）テーブルおよび初期化
- データ品質チェック（欠損・異常値・重複・日付不整合）
- 環境変数/設定管理（.env 自動読み込み機能）

設計上のポイントとして、API レート制限の遵守、リトライロジック、Look-ahead bias 回避のための fetched_at 記録、冪等性などが取り入れられています。

---

## 機能一覧

- 環境変数管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（ただし環境変数優先）
  - 必須変数未設定時にエラーを出す Settings クラス（kabusys.config.settings）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - get_id_token(): トークンリフレッシュ
  - fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - API レート制御（120 req/min）とリトライ、401 自動リフレッシュ対応
  - DuckDB へ保存する save_* 関数（冪等化された INSERT ... ON CONFLICT）
- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path)
  - get_connection(db_path)
  - Raw / Processed / Feature / Execution 層のテーブル定義
- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn)
  - init_audit_db(db_path)
  - シグナル／発注要求／約定を保存するテーブル群（トレーサビリティ確保）
- データ品質チェック（kabusys.data.quality）
  - check_missing_data(), check_spike(), check_duplicates(), check_date_consistency()
  - run_all_checks() で一括実行、QualityIssue のリストを返す

---

## 動作環境 / 必要要件

- Python 3.10 以上（型注釈に `X | None` を使用）
- pip パッケージ:
  - duckdb
- 標準ライブラリのみで動作する部分も多いですが、DuckDB を使う機能を使う場合は duckdb が必要です。

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
```

---

## 環境変数（主な項目）

kabusys.config.Settings で参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL     : kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャネル ID（必須）
- DUCKDB_PATH           : DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（省略時: data/monitoring.db）
- KABUSYS_ENV           : 環境（development | paper_trading | live）省略時: development
- LOG_LEVEL             : ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）省略時: INFO

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を検出）から `.env` → `.env.local` の順で読み込み（`.env.local` が上書き）。
- OS 環境変数が最優先。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で使用）。

例: .env（.env.example の雛形）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <this-repo-url>
   cd <repo>
   ```

2. Python 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（最低限: duckdb）
   ```bash
   pip install duckdb
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定してください。
   - 必須: JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID

5. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")  # ファイルを作成してスキーマを作る
   # 以降は get_connection() で接続を取得して利用
   ```

6. 監査ログ（audit）テーブル初期化（既存 conn に追加する場合）
   ```python
   from kabusys.data.audit import init_audit_schema
   # conn は init_schema() の戻り値など
   init_audit_schema(conn)
   ```
   または別 DB として初期化する:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要なコード例）

- J-Quants から日足を取得して DuckDB に保存する流れ:
```python
from kabusys.data import jquants_client
from kabusys.data.schema import init_schema

# DB 初期化 / 接続
conn = init_schema("data/kabusys.duckdb")

# データ取得（トークンは settings から自動的に取得・リフレッシュされます）
records = jquants_client.fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# 保存（冪等）
n = jquants_client.save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

- 財務データ・マーケットカレンダーの取得・保存:
```python
fin = jquants_client.fetch_financial_statements(code="7203")
jquants_client.save_financial_statements(conn, fin)

cal = jquants_client.fetch_market_calendar()
jquants_client.save_market_calendar(conn, cal)
```

- データ品質チェック:
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.table, issue.severity, issue.detail)
    for row in issue.rows:
        print("  ", row)
```

- 監査ログ初期化（別 DB）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
# audit_conn 上で監査テーブルにレコードを入れていく設計
```

---

## ディレクトリ構成

リポジトリの主なファイル/モジュール構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py                - パッケージ定義（__version__ = "0.1.0"）
  - config.py                  - 環境変数・設定管理（.env 自動読み込み、Settings）
  - data/
    - __init__.py
    - jquants_client.py        - J-Quants API クライアント（取得＋DuckDB 保存）
    - schema.py                - DuckDB スキーマ定義と init_schema / get_connection
    - audit.py                 - 監査ログ（signal / order_request / executions）初期化
    - quality.py               - データ品質チェック機能（各種検査）
  - strategy/
    - __init__.py              - 戦略層（空のパッケージ初期化ファイル）
  - execution/
    - __init__.py              - 発注実行層（空のパッケージ初期化ファイル）
  - monitoring/
    - __init__.py              - 監視関連（空のパッケージ初期化ファイル）

注: strategy / execution / monitoring パッケージの中身はこのコードベースではまだ提供されていません（プレースホルダー）。

---

## 注意事項 / 実運用での考慮点

- J-Quants API のレート制限（120 req/min）や retry ロジックは実装済みですが、実際の運用量に応じて追加のスロットリングやバックプレッシャー機構を考慮してください。
- DuckDB はローカル分析向けの組み込み DB です。大規模同時アクセスや複雑なマルチプロセス運用を行う場合は設計を再検討してください。
- すべての TIMESTAMP（特に監査ログ）は UTC 保存を前提としています。ログの解釈や表示の際はタイムゾーンに注意してください。
- 環境変数やシークレット（API トークンなど）は安全に管理してください。リポジトリにトークンをコミットしないでください。

---

## 開発者向けメモ

- 自動 .env 読み込みの停止:
  - テストや CI で自動読み込みを止めたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 型注釈は Python 3.10+ の構文を使用しています（`X | None` 等）。
- DuckDB のテーブル定義には CHECK 制約や PRIMARY KEY が多用されており、保存関数は ON CONFLICT DO UPDATE により冪等性を保ちます。

---

必要であれば、README にサンプル .env.example や、より具体的なスクリプト（ETL ワークフロー・スケジューリング例）、unit test の書き方、CI 設定例なども追加します。どの項目を優先して追加しますか？