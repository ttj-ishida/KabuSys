# KabuSys

日本株自動売買システム向けのユーティリティライブラリ / データプラットフォームコンポーネントです。  
このリポジトリはデータ取得（J-Quants）、ETL、データ品質チェック、DuckDB スキーマ定義、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

バージョン: src/kabusys/__init__.py の __version__ = "0.1.0"

---

## 主な特徴（概要）

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - API レート制限（120 req/min）を尊重する固定間隔レートリミッタ
  - 自動リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ（1 回）
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を抑制

- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution / Audit（監査）レイヤのテーブルを定義
  - 冪等性（ON CONFLICT DO UPDATE）を考慮した保存処理

- ETL パイプライン
  - 差分更新（最終取得日からの差分のみ取得）
  - backfill による後出し修正吸収
  - 市場カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- データ品質チェック
  - 欠損（OHLC 欄）検出・重複検出・スパイク検出・日付不整合検出
  - 問題は QualityIssue オブジェクトのリストで返却（重大度: error/warning）

- 監査ログ（audit）
  - signal → order_request → execution に至る UUID ベースのトレーサビリティ
  - 発注の冪等キー、ステータス管理、UTC タイムスタンプ

---

## 機能一覧（抜粋）

- kabusys.config.Settings: 環境変数管理（.env 自動ロード、必要な設定の検証）
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar (DuckDB への保存)
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, ...), run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(db_path)

---

## 前提条件 / 依存関係

- Python 3.10+（型ヒントに | 型を使用しているため）
- 必要ライブラリ（例）:
  - duckdb
  - （標準 urllib/json/logging 等は標準ライブラリ）
- J-Quants API アクセス用のリフレッシュトークン、kabuステーション API、Slack（通知など）を利用する場合はそれぞれの資格情報

※ 実際のプロジェクトで使う際は pyproject.toml / requirements.txt を確認してください。

---

## セットアップ手順

1. リポジトリをクローンして開発環境にインストール（Editable インストール例）
   ```
   git clone <this-repo>
   cd <this-repo>
   pip install -e ".[dev]"   # or pip install -e .
   ```
   （パッケージ名はプロジェクトに合わせてください）

2. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml がある階層）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（Settings により取得／検証されるもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト `INFO`
     - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH — デフォルト `data/monitoring.db`
   - .env のパース仕様（主な挙動）
     - export KEY=val 形式に対応
     - シングル/ダブルクォート内はエスケープを考慮して正しく読み込む
     - クォート無しの場合は `#` の直前に空白があるとコメント開始とみなす

   簡単な .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマ初期化
   - まずはスキーマを作成して DB を初期化します。

   Python 例:
   ```python
   from kabusys.data import schema
   from kabusys.config import settings

   # settings.duckdb_path は環境変数から決定される（デフォルト data/kabusys.duckdb）
   conn = schema.init_schema(settings.duckdb_path)
   ```

   監査ログ（audit）スキーマ追加:
   ```python
   from kabusys.data import audit
   audit.init_audit_schema(conn)
   # または独立 DB にしたい場合
   # audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な例）

- 日次 ETL の実行（市場カレンダー → 株価 → 財務 → 品質チェック）

  ```python
  from kabusys.data import schema, pipeline
  from kabusys.config import settings
  from datetime import date

  conn = schema.init_schema(settings.duckdb_path)
  result = pipeline.run_daily_etl(conn)  # target_date を省略すると今日
  print(result.to_dict())
  ```

- 個別ジョブ実行（例: 株価 ETL を特定日で実行）

  ```python
  from datetime import date
  from kabusys.data import pipeline, schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)  # 既存 DB 接続
  fetched, saved = pipeline.run_prices_etl(conn, target_date=date(2025, 1, 10))
  print(f"fetched={fetched}, saved={saved}")
  ```

- J-Quants から直接データを取得する（テストや個別利用）

  ```python
  from kabusys.data import jquants_client as jq
  data = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 品質チェックを単体で実行

  ```python
  from kabusys.data import quality, schema
  from kabusys.config import settings
  from datetime import date

  conn = schema.get_connection(settings.duckdb_path)
  issues = quality.run_all_checks(conn, target_date=date(2024,1,31))
  for i in issues:
      print(i)
  ```

---

## 注意点 / 設計上のポイント

- レート制限
  - J-Quants API のレート（120 req/min）を _RateLimiter（固定間隔スロットリング）で遵守します。
- リトライ・認証
  - ネットワークエラーや 408/429/5xx 系に対して指数バックオフで最大 3 回リトライ。
  - 401 が返ったらリフレッシュトークンから idToken を再取得して 1 回だけリトライ。
- 時刻管理
  - 取得系のタイムスタンプ（fetched_at、created_at 等）は UTC を想定して記録します（監査ログは SET TimeZone='UTC' を実行）。
- 冪等性
  - データ保存は ON CONFLICT DO UPDATE を利用して同じ PK の重複挿入を避けます。
- 環境変数の自動ロード
  - パッケージロード時にプロジェクトルートの `.env` -> `.env.local` を自動で読み込みます（既存 OS 環境変数は保護）。テスト時などで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 環境（KABUSYS_ENV）は `development | paper_trading | live` のいずれか。値が不正だと例外になります。
- ログレベルは `LOG_LEVEL`（大文字）で指定可能：DEBUG/INFO/WARNING/ERROR/CRITICAL。

---

## ディレクトリ構成（このリポジトリ内の主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - execution/
    - __init__.py
  - strategy/
    - __init__.py
  - monitoring/
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント & 保存ロジック
    - schema.py                      — DuckDB スキーマ定義・初期化
    - pipeline.py                    — ETL パイプライン
    - quality.py                     — データ品質チェック
    - audit.py                       — 監査ログスキーマと初期化

（上位に pyproject.toml / .git / README.md 等がある想定）

---

## 追加情報

- logging を適切に設定すると ETL の実行状況や品質チェックの結果を参照しやすくなります。
- DuckDB のパスを共有ストレージに置くことで複数プロセスからの読み取りが容易になりますが、同時書き込みの扱いには注意してください（運用設計が必要です）。
- このモジュール群は「データ基盤」「監査」「ETL」等の基盤機能を提供します。実際の戦略ロジックやブローカー連携（kabu API への発注実装）は execution/ や strategy/ に実装して利用してください。

---

何か特定のサンプルスクリプト、CI 設定、あるいは .env.example を出力するテンプレートが必要であれば教えてください。