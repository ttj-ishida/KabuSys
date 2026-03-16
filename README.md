# KabuSys — 日本株自動売買システム

KabuSys は日本株の自動売買プラットフォーム向けのデータ取得・ETL・監査ログ基盤のコアライブラリです。J-Quants API から市場データや財務データを取得して DuckDB に保存、品質チェックや監査ログ（発注→約定のトレーサビリティ）を提供します。

主な設計方針:
- API レート制御（J-Quants: 120 req/min）とリトライ/トークン自動リフレッシュ
- Look-ahead bias を防ぐための fetched_at/UTC タイムスタンプ
- DuckDB を用いた冪等（ON CONFLICT DO UPDATE）保存
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注履歴・約定をトレース可能にする監査スキーマ

---

## 機能一覧
- J-Quants API クライアント
  - 日次株価（OHLCV）取得（ページネーション対応）
  - 四半期財務データ取得（ページネーション対応）
  - JPX マーケットカレンダー取得
  - トークン自動リフレッシュとリトライ / バックオフ処理
  - 固定間隔スロットリング（レート制限の順守）
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブル群
  - インデックス定義
- ETL パイプライン
  - 差分取得（最終取得日からの再取得・バックフィル）
  - 保存（冪等）
  - 品質チェックの実行（欠損・スパイク・重複・日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）
- 監査ログ（audit）
  - signal_events / order_requests / executions の監査テーブルとインデックス
  - 発注 → 約定までの UUID 連鎖によるフルトレーサビリティ
- データ品質モジュール
  - QualityIssue 型で複数チェック結果を集約（Fail-Fast ではない）

---

## セットアップ手順（クイックスタート）

前提:
- Python 3.10+
- duckdb ライブラリ（requirements に含めてください）

1. リポジトリをクローンしてインストール
   - 開発中: pip install -e .
   - あるいはプロジェクトの仮想環境に依存パッケージ（duckdb など）をインストールしてください。

2. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）ファイルを作成するか、OS 環境変数として設定します。
   - 主に必要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（使用する場合）
     - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID（使用する場合）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite のパス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）
   - 自動で .env を読み込ませない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。

3. DuckDB スキーマの初期化
   - Python REPL またはスクリプトで:
     ```
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```
   - 監査ログ用テーブルは既存接続へ追加する場合:
     ```
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```

4. 日次 ETL の実行（例）
   - 簡単な実行例:
     ```
     from kabusys.data.schema import init_schema
     from kabusys.data.pipeline import run_daily_etl
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     result = run_daily_etl(conn)
     print(result.to_dict())
     ```
   - run_daily_etl は市場カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック の順で実行します。
   - 詳細パラメータ（target_date, id_token, backfill_days, run_quality_checks 等）を渡して挙動を調整できます。

---

## 使い方（主要 API と例）

- J-Quants トークン取得:
  ```
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使って取得
  ```

- 株価・財務・カレンダーの直接取得:
  ```
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar

  quotes = fetch_daily_quotes(code="7203", date_from=... , date_to=...)
  financials = fetch_financial_statements(code="7203", date_from=..., date_to=...)
  calendar = fetch_market_calendar()
  ```

- DuckDB への保存は jquants_client の save_* 関数を使用:
  ```
  saved = save_daily_quotes(conn, quotes)
  saved_fin = save_financial_statements(conn, financials)
  ```

- ETL 全体を実行（推奨）:
  ```
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=..., backfill_days=3)
  if result.has_errors:
      # ログやアラートの発行など
  ```

- データ品質チェックを個別に実行:
  ```
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=...)
  for i in issues: print(i)
  ```

- 監査ログ初期化（別 DB を使う場合など）:
  ```
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.db")
  ```

---

## 設定（環境変数の詳細）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token の元）
- KABU_API_PASSWORD — kabu API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン（使用する場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（使用する場合）

任意（デフォルトは括弧内）:
- KABUSYS_ENV (development | paper_trading | live) — (development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — (INFO)
- DUCKDB_PATH — (data/kabusys.duckdb)
- SQLITE_PATH — (data/monitoring.db)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — (未設定) .env 自動読み込みを無効化するには 1 をセット

.env ファイルパーサにはシングル/ダブルクォート、コメント、export プレフィックスに対応しています。

---

## ディレクトリ構成（概要）
以下は src 配下の主要ファイル/モジュール構成です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存ロジック）
    - schema.py               — DuckDB スキーマ定義と初期化
    - pipeline.py             — ETL パイプライン（差分取得・保存・品質チェック）
    - audit.py                — 監査ログテーブル定義・初期化
    - quality.py              — データ品質チェック
  - execution/
    - __init__.py             — 発注関連（将来の実装位置）
  - strategy/
    - __init__.py             — 戦略関連（将来の実装位置）
  - monitoring/
    - __init__.py             — 監視・アラート関連（将来の実装位置）

主要ファイルの役割:
- config.py: .env 自動読み込み、必須値チェック、settings オブジェクト提供
- jquants_client.py: HTTP リトライ / レートリミッタ / ページネーション / DuckDB への保存関数
- schema.py: Raw/Processed/Feature/Execution 層の DDL と init_schema
- pipeline.py: 差分 ETL のオーケストレーション（run_daily_etl）

---

## 開発メモ / 注意点
- J-Quants のレート制限（120 req/min）を順守するため固定間隔スロットリングを行っています。大量リクエストを投げる際は注意してください。
- HTTP エラー 401 の場合はトークンを自動リフレッシュして 1 回だけリトライします（無限再帰を防止）。
- DuckDB の初期化は冪等であり、既存テーブルは上書きされません（CREATE IF NOT EXISTS）。監査テーブルは init_audit_schema で追加できます。
- 品質チェックは Fail-Fast ではなく、すべての問題を収集して返します。呼び出し側で重大度に応じたアクションを実装してください。
- すべてのタイムスタンプは UTC を前提に保存する設計です（特に監査ログでは SET TimeZone='UTC' を実行）。

---

この README はコードベース（src/kabusys 以下）に基づいて作成しました。追加の使用例や CLI / 実運用ジョブ（スケジューリング、監視、Slack 通知等）はプロジェクト固有のユースケースに合わせて実装してください。必要であれば README にサンプル .env.example、起動スクリプト、ユニットテスト手順などを追記できます。