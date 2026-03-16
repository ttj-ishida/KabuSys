# KabuSys

日本株向けの自動売買基盤のコアライブラリ（KabuSys）。  
データ取得・ETL、DuckDBスキーマ定義、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）などの基盤機能を含みます。

注意: このリポジトリはライブラリ/内部ツールであり、ブローカー接続や戦略（strategy）、発注（execution）、監視（monitoring）は別モジュールで実装・拡張する想定です。

---

## 概要

主な目的は以下です。

- J-Quants API から株価・財務・マーケットカレンダー等を安全に取得する。
  - レート制限（120 req/min）を守る固定間隔スロットリング
  - リトライ（指数バックオフ）・401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止
- DuckDB に対するスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、保存、品質チェック）の実装
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → executions を UUID 連鎖でトレース）

---

## 機能一覧

- 環境変数/設定管理（自動 .env 読み込み、保護・上書き制御）
  - 自動読み込みはプロジェクトルート（.git か pyproject.toml）を探索して `.env`, `.env.local` をロード
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - fetch_daily_quotes（OHLCV）
  - fetch_financial_statements（四半期 BS/PL）
  - fetch_market_calendar（JPXカレンダー）
  - 冪等で DuckDB に保存する save_* 関数
- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema(db_path) による初期化（冪等）
  - get_connection(db_path)
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新、バックフィル、カレンダー先読み
  - run_daily_etl() による日次一括処理
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
- データ品質チェック（src/kabusys/data/quality.py）
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合
  - run_all_checks() で一括実行
- 監査ログ（src/kabusys/data/audit.py）
  - signal_events, order_requests, executions 等のテーブルとインデックス
  - init_audit_schema / init_audit_db による初期化（UTC タイムスタンプの設定）

---

## 必要条件

- Python 3.10 以上（型注釈に `|` を使用）
- 依存パッケージ（最低限）
  - duckdb

インストールにあたっては仮想環境を推奨します。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
```

（プロジェクトとして配布する場合は requirements.txt / pyproject.toml を用意してください）

---

## 環境変数（主なもの）

下記の環境変数は設定が必須／推奨されます（Settings クラスにより取得）。

必須（例）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意／デフォルトあり
- KABUSYS_ENV — 動作環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite （監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env の自動読み込みを無効化

.sample の例（README 用）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb
   ```
2. 環境変数を設定（.env をプロジェクトルートに置く）
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。
   - `.env` と `.env.local` は自動で読み込まれます（ただしプロジェクトルートが見つからない場合はスキップ）。
3. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで実行:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
     ```
   - 監査ログを追加で初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```
4. 日次 ETL 実行（手動/スケジューラ）
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.data.pipeline import run_daily_etl
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
     result = run_daily_etl(conn)
     print(result.to_dict())
     ```

---

## 使い方（代表的な例）

- J-Quants から株価を取得して DB に保存（単発）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f"saved: {saved}")
  ```

- 日次 ETL（カレンダー先読み、バックフィル、品質チェック）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 品質チェックのみ実行
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.quality import run_all_checks
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

- 監査ログ（発注→約定）テーブル初期化（別 DB に分けることも可能）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                    -- 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py          -- J-Quants API クライアント（取得 + 保存）
      - schema.py                  -- DuckDB スキーマ定義・初期化
      - pipeline.py                -- ETL パイプライン（差分更新、backfill、品質チェック）
      - quality.py                 -- データ品質チェック
      - audit.py                   -- 監査ログ（signal / order_requests / executions）
      - pipeline.py
    - strategy/
      - __init__.py                -- 戦略層モジュール（拡張ポイント）
    - execution/
      - __init__.py                -- 発注・約定ロジック（拡張ポイント）
    - monitoring/
      - __init__.py                -- 監視・アラート（拡張ポイント）

---

## 設計上のポイント・注意点

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI やテストで自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API へのリクエストはレート制限（120 req/min）を厳守するため内部でスロットリングしています。また、リトライとトークン自動リフレッシュの仕組みを備えています。
- DuckDB のテーブル作成は冪等であり、init_schema は既存のテーブルがあっても安全に実行できます。
- ETL は Fail-Fast ではなく、各ステップのエラーを集約して返します（ETLResult.errors / quality_issues を参照）。呼び出し側でログ出力やアラート処理を行ってください。
- 監査ログは削除しない前提（ON DELETE RESTRICT など）で設計しています。すべての TIMESTAMP は UTC を前提に保存されます。

---

## 今後の拡張案（参考）

- strategy: 複数戦略のプラグイン機構、戦略バージョン管理
- execution: ブローカーアダプタ（kabuステーション・証券会社 API）の実装、注文リトライ・部分約定対応
- monitoring: Slack 等へのアラート通知、ETL のメトリクス収集
- テスト: ユニットテスト・統合テスト（特に ETL の差分ロジック・品質チェック）

---

この README はコードベースの主要機能と導入手順をまとめたものです。実運用時は各 API トークン・パスワードの管理、バックアップ、権限設定、監査・ログの保存方針を必ず整備してください。