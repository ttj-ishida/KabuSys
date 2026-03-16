# KabuSys

日本株向け自動売買プラットフォーム用のユーティリティ群（データ取得・ETL・品質チェック・監査ログ・スキーマ初期化など）

このリポジトリは、J-Quants API からの市場データ取得、DuckDB へ保存するスキーマ定義、日次 ETL パイプライン、データ品質チェック、および発注／約定に関する監査ログ管理を提供します。

---

## 主要な特徴（Highlights）

- J-Quants API クライアント
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レートリミット（120 req/min）を守るスロットリング実装
  - リトライ（指数バックオフ、最大 3 回）、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead バイアスを回避
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）

- DuckDB スキーマ
  - 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義
  - インデックスや外部キーを考慮した DDL を用意
  - スキーマ初期化ユーティリティ（init_schema, init_audit_schema, init_audit_db）

- ETL パイプライン
  - 差分更新（最終取得日からの差分を自動算出）
  - backfill による数日前再取得で後出し修正を吸収
  - 市場カレンダーの先読み（デフォルト 90 日）
  - 品質チェック（欠損・重複・スパイク・日付不整合）を一括実行

- データ品質チェック
  - 欠損（OHLC）/ 重複 / スパイク（前日比） / 日付不整合（未来日・非営業日）検出
  - 問題は QualityIssue のリストで返却（Fail-Fast ではなく全件収集）

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 まで UUID でトレースできる監査テーブル
  - 発注の冪等処理（order_request_id）を考慮
  - すべての TIMESTAMP は UTC 保存を前提

---

## 動作前提

- Python 3.10 以上（型注釈で `X | None` を使用しているため）
- 必要な Python パッケージ（最低限）:
  - duckdb
- ネットワーク接続（J-Quants API など）

実際の運用では他にログ送信（Slack 等）や kabuステーション連携用のクライアントが必要です（本リポジトリは基盤部分を提供）。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリのインストール
   - 最低限:
     ```
     pip install duckdb
     ```
   - パッケージを編集可能モードでインストールできる場合（pyproject.toml がある想定）:
     ```
     pip install -e .
     ```

4. 環境変数／.env の準備
   - プロジェクトルートの `.env` および `.env.local` が自動読み込みされます（優先順: OS 環境変数 > .env.local > .env）。
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルトあり）:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) (デフォルト: development)
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (デフォルト: INFO)

   例: `.env`（簡易）
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

## 使い方（簡単なコード例）

以下は主要な操作のサンプルです。Python スクリプト内または REPL で実行してください。

- DuckDB スキーマ初期化（DB を作成してテーブルを生成）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ":memory:" でも可
  ```

- 監査ログテーブルの初期化（既存接続へ追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  # あるいは監査専用 DB を作る場合:
  # from kabusys.data.audit import init_audit_db
  # audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- J-Quants から日足データを取得して保存する（jquants_client を直接使う例）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=None, date_to=None)  # 引数は任意
  saved = jq.save_daily_quotes(conn, records)
  print(f"保存件数: {saved}")
  ```

- 日次 ETL パイプラインを実行する（推奨）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date 等は引数で指定可
  print(result.to_dict())
  ```

- 品質チェックを単独で実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

- J-Quants の ID トークンを明示的に取得する
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用
  ```

---

## 主要なモジュール・関数

- kabusys.config
  - settings: 環境変数から設定を取得するオブジェクト（必須キーを要求するユーティリティ含む）
  - 自動で .env / .env.local をプロジェクトルートから読み込む実装

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token（リフレッシュトークンから ID トークンを取得）
  - レート制御、リトライ、ページネーション対応

- kabusys.data.schema
  - init_schema(db_path) / get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - run_daily_etl（ETL の統合エントリポイント）

- kabusys.data.quality
  - check_missing_data, check_duplicates, check_spike, check_date_consistency
  - run_all_checks（すべての品質チェックを実行）

- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(path)

---

## ディレクトリ構成

（ソースは src/layout 想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数と設定管理
    - data/
      - __init__.py
      - jquants_client.py        — J-Quants API クライアント + 保存ロジック
      - schema.py                — DuckDB スキーマ定義・初期化
      - pipeline.py              — ETL パイプラインの実装
      - quality.py               — データ品質チェック
      - audit.py                 — 監査ログ（トレーサビリティ）スキーマ
      - audit.py                 — 監査ログ（テーブル定義 / 初期化）
      - pipeline.py              — ETL 実行ロジック（差分、backfill、品質チェック）
    - strategy/                   — 戦略関連のプレースホルダ（拡張用）
    - execution/                  — 発注/約定管理のプレースホルダ（拡張用）
    - monitoring/                 — 監視系のプレースホルダ

（各ファイルの役割は上記の「主要なモジュール・関数」を参照）

---

## 運用上の注意点

- 環境変数はセキュアに管理してください（トークン等は Git 管理しない）。
- DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）は読み書き可能な場所にしてください。
- J-Quants の API レート制限（120 req/min）を超えないよう実装上で制御していますが、大量の同時実行は避けること。
- ETL は各ステップでエラーハンドリングされ、1 ステップの失敗が他に波及しない設計ですが、エラー内容は ETLResult に蓄積されます。ログを確認して対応してください。
- 本パッケージは「基盤」実装を提供します。実際の取引（実運用）には追加のリスク管理・注文検証・テストが必須です。特に live 環境（KABUSYS_ENV=live）での使用は慎重に。

---

## 追加・拡張

- strategy / execution / monitoring の各モジュールは拡張用にプレースホルダがあります。戦略ロジック、ポートフォリオ管理、ブローカー連携などはここに実装してください。
- 監査ログ（audit）は発注から約定までのトレーサビリティを満たす設計になっていますが、ブローカー側コールバックや外部通知（Slack など）との統合を追加することが想定されています。

---

この README はコードベースの現状（主要ファイル）に基づいて記載しています。実運用・本番環境に移行する前に、十分なテストとセキュリティ対策（認証トークンの保護、権限管理、監査ログの保存ポリシーなど）を行ってください。