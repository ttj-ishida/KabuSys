# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ／内部用）

このリポジトリは、データ取り込み・スキーマ管理・品質チェック・監査ログといった
自動売買プラットフォームの基盤機能を提供します。J-Quants API などから市場データを取得して
DuckDB に永続化し、戦略・実行・監視層へ橋渡しする用途を想定しています。

バージョン: 0.1.0

---

## 概要

主な設計方針・特徴

- J-Quants API クライアントを提供（日足・財務データ・マーケットカレンダー）
  - レート制限（120 req/min）順守
  - リトライ（指数バックオフ、401 の場合は自動トークンリフレッシュ）
  - ページネーション対応
  - Look-ahead bias を防ぐための fetched_at 記録
- DuckDB ベースのスキーマ定義（Raw / Processed / Feature / Execution）
  - 冪等な INSERT（ON CONFLICT DO UPDATE）を使用
  - インデックス定義を含む初期化機能
- 監査ログ（signal_events / order_requests / executions）を別途初期化する機能
  - 発注フローのトレーサビリティを保証（UUID 連鎖、冪等キー）
- データ品質チェックモジュール
  - 欠損データ、スパイク（急騰・急落）、重複、日付不整合を検出
  - QualityIssue のリストを返す設計（Fail-Fast ではない）

---

## 機能一覧

- 環境設定管理（自動で .env/.env.local をプロジェクトルートから読み込み）
  - 環境変数の必須チェック（不足時は ValueError）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化
- data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- data.schema
  - init_schema(db_path)
  - get_connection(db_path)
  - DuckDB 用の完全なスキーマ（raw, processed, feature, execution）
- data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)
  - 監査ログ用テーブルとインデックス
- data.quality
  - check_missing_data(conn, target_date=None)
  - check_spike(conn, target_date=None, threshold=...)
  - check_duplicates(conn, target_date=None)
  - check_date_consistency(conn, reference_date=None)
  - run_all_checks(conn, ...)
- パッケージ構成は strategy, execution, monitoring といった層を想定（プレースホルダ）

---

## 動作要件

- Python 3.10 以上（型注釈に `X | None` を使用）
- 必要なパッケージ（最低限）
  - duckdb
- （外部 API 連携のため）ネットワークアクセス

例（必要パッケージのインストール）:
```bash
python -m pip install duckdb
```

パッケージ配布形式がある場合は:
```bash
pip install -e .
# または
pip install -r requirements.txt
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン／展開

2. 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb
   ```

3. プロジェクトルートに .env（必要な環境変数）を用意
   - パッケージは実行時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動探索して
     `.env` → `.env.local` の順で読み込みます。OS 環境変数が優先され、`.env.local` は上書きされます。
   - 自動読み込みを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB スキーマを初期化
   - 例: デフォルトの DB パスを使用する場合（settings.duckdb_path）
   - もしくは明示的にファイルを指定して初期化

---

## 環境変数（.env の例）

必須項目（実運用で必須）:
- JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
- KABU_API_PASSWORD=<your_kabu_password>
- SLACK_BOT_TOKEN=<your_slack_bot_token>
- SLACK_CHANNEL_ID=<your_slack_channel_id>

任意／デフォルトあり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=password123
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- Settings クラスは必須変数がないと ValueError を投げます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動で .env を読み込まなくなります（テスト向け）。

---

## 使い方（抜粋例）

以下は主要なユースケースの簡単な使用例です。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルがなければディレクトリを作成
```

- 監査ログ（audit）用スキーマ追加
```python
from kabusys.data.audit import init_audit_schema
# 既に init_schema() で得た conn を渡して監査テーブルを追加
init_audit_schema(conn)
```

- J-Quants から日足を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# 取得（例: 特定銘柄と期間）
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
# 保存（raw_prices テーブルに ON CONFLICT DO UPDATE で保存）
n_saved = save_daily_quotes(conn, records)
print(f"saved: {n_saved}")
```

- 財務データ・マーケットカレンダーも同様に fetch_* / save_* を使用

- データ品質チェック実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
    for row in issue.rows:
        print(row)
```

- ID トークンを直接取得（内部でリフレッシュを行う）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

注意点:
- J-Quants API 呼び出しはレート制限・リトライ等を内部で処理します。
- fetch_* はページネーションを内部で処理してすべてのレコードを返します（大規模データの場合は注意）。

---

## ディレクトリ構成

主要ファイルと用途:
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理、.env 自動読み込みロジック、Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック）
    - schema.py
      - DuckDB スキーマ DDL 定義、init_schema / get_connection
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）初期化
    - quality.py
      - データ品質チェック群（欠損・スパイク・重複・日付不整合）
    - (その他: news/audit/..)
  - strategy/
    - __init__.py (戦略層プレースホルダ)
  - execution/
    - __init__.py (発注層プレースホルダ)
  - monitoring/
    - __init__.py (監視層プレースホルダ)

---

## 開発上の注意点 / 補足

- 型や構文は Python 3.10 の構文（X | None 等）を使用しています。3.10 以上を推奨します。
- config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env ファイルを読み込みます。テストで .env の自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の ON CONFLICT 等の動作に依存した設計です。スキーマを変更する場合は既存データとの後方互換性に注意してください。
- 監査テーブルは基本的に削除しない前提（ON DELETE RESTRICT）で設計されています。

---

## 参考・連絡

この README はコードベースからの主要機能を抜粋した概要です。実装の詳細や運用ルール（DataPlatform.md / DataSchema.md 等）が別ドキュメントとしてある場合、それらを参照してください。

問題や改善点があればリポジトリの issue や担当者へ連絡してください。