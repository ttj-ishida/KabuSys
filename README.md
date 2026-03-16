# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
J-Quants API からマーケットデータや財務データを取得して DuckDB に蓄積し、ETL パイプライン・品質チェック・監査ログ（トレーサビリティ）を提供します。戦略層・実行層・監視層との接続を想定した基盤コンポーネント群です。

バージョン: 0.1.0

---

## 概要

主な目的は以下です。

- J-Quants API から株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
- API レート制御（120 req/min）・リトライ・トークン自動リフレッシュ機能を備えたクライアント
- DuckDB に対するスキーマ定義（Raw / Processed / Feature / Execution 層）と初期化機能
- ETL パイプライン（差分更新、バックフィル、品質チェック）の実装
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用テーブル群
- 環境変数ベースの設定管理（.env 自動ロード、必須チェック）
- Slack / kabuステーション 等の外部サービス設定を想定

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（ID トークン自動リフレッシュ、ページネーション、レート制限、リトライ）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への冪等保存関数（save_daily_quotes 等）
- data/schema.py
  - DuckDB のスキーマ定義と init_schema / get_connection
  - Raw / Processed / Feature / Execution 層のテーブルとインデックス
- data/pipeline.py
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 差分更新、バックフィル、品質チェックの統合
- data/quality.py
  - check_missing_data, check_duplicates, check_spike, check_date_consistency
  - run_all_checks による一括実行。QualityIssue を返す
- data/audit.py
  - 監査ログ用テーブルの初期化（signal_events, order_requests, executions）
  - 監査インデックス定義、UTC タイムゾーン設定
- config.py
  - .env 自動ロード（プロジェクトルート検出）と設定取得ラッパー（Settings）
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 等のバリデーション
- strategy/, execution/, monitoring/
  - プレースホルダパッケージ（戦略・発注・監視ロジックを拡張する場所）

---

## セットアップ手順

想定環境: Python 3.10+

1. リポジトリをクローン
   - 例: git clone <repository-url>

2. 仮想環境を作成・有効化
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 依存パッケージのインストール
   - 最低限必要なパッケージ:
     - duckdb
   - 例:
     - pip install duckdb
   - プロジェクトに requirements.txt / pyproject.toml がある場合:
     - pip install -r requirements.txt
     - あるいは pip install -e . （パッケージ化されている場合）

4. 環境変数の準備
   - プロジェクトルートに `.env` を配置してください（.env.example を参照）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション（発注API）パスワード
     - SLACK_BOT_TOKEN — Slack Bot トークン（通知用）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意/デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - テストや環境で自動 .env ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース初期化
   - Python REPL やスクリプトから DuckDB スキーマを初期化します（例は次節の「使い方」参照）。

---

## 使い方（簡単な例）

以下は最小限の使用例です。Python スクリプトや REPL で実行できます。

- DuckDB スキーマを初期化して日次 ETL を実行する

```python
from kabusys.data import schema, pipeline, audit

# DB 初期化（ファイル: data/kabusys.duckdb）
conn = schema.init_schema("data/kabusys.duckdb")

# 監査ログテーブルを追加で初期化する（必要なら）
audit.init_audit_schema(conn)

# 日次 ETL 実行（target_date を省略すると今日）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- J-Quants の ID トークンを明示的に取得する（テストや手動実行時）

```python
from kabusys.data import jquants_client as jq

id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
print(id_token)
```

- 品質チェックだけを実行する

```python
from kabusys.data import schema, quality

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn)
for i in issues:
    print(i)
```

注意:
- 自動化（cron / Airflow / systemd timer 等）で日次バッチを実行する場合、仮想環境の有効化と環境変数のロード (.env) を忘れないでください。
- ETL 実行時は J-Quants のレート制限（120 req/min）と API 利用規約に従ってください。jquants_client はレート制御とリトライを備えています。

---

## 設定（環境変数の一覧）

主に使用される環境変数（必須・推奨）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env の自動ロードを無効化

.env ファイルのフォーマットは Bash ライク（export を先頭につける形式にも対応）で、シングル・ダブルクォートやインラインコメントに配慮して読み込まれます。

---

## ディレクトリ構成

プロジェクトの主なファイル・ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py        # J-Quants API クライアント
      - schema.py                # DuckDB スキーマ定義・初期化
      - pipeline.py              # ETL パイプライン
      - quality.py               # データ品質チェック
      - audit.py                 # 監査ログ（トレーサビリティ）
      - audit.py                 # 監査データベース初期化ユーティリティ
    - strategy/
      - __init__.py              # 戦略ロジックの拡張ポイント
    - execution/
      - __init__.py              # 発注・ブローカー連携の拡張ポイント
    - monitoring/
      - __init__.py              # 監視・アラート機能の拡張ポイント

補足:
- data/schema.py に全テーブル DDL が定義されています（Raw / Processed / Feature / Execution 層）。
- audit.py は監査向けの別途テーブル群を提供し、init_audit_schema / init_audit_db を通じて初期化できます。

---

## 運用上の注意

- API キーやシークレットは必ず安全に管理し、リポジトリに直接コミットしないでください。
- KABUSYS_ENV によって挙動（実売買 / シミュレーションなど）を分離してください（コード内での is_live / is_paper フラグを利用）。
- DuckDB ファイルは定期的にバックアップを推奨します。監査ログは削除しない設計を想定しています。
- run_daily_etl は内部で例外を捕捉して処理を継続する設計です。戻り値（ETLResult）の errors / quality_issues を監視して運用対応してください。

---

## 参考と拡張

- strategy/、execution/、monitoring/ パッケージはプレースホルダです。実際の戦略ロジックやブローカー API 連携、監視ダッシュボードはここに実装して統合してください。
- Slack 通知や kabuステーション連携は設定項目を介して実装することを想定しています（現状は設定読み取りの仕組みのみ提供）。

---

質問や追加でドキュメント化してほしい箇所があれば教えてください。設定例（.env.example）や ETL の実行例、CI/CD やデプロイ手順なども必要に応じて追記できます。