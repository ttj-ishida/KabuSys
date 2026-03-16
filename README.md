# KabuSys

日本株向けの自動売買・データ基盤ライブラリ (KabuSys)。  
J-Quants や kabuステーション 等の外部サービスからデータを取得し、DuckDB に保存・品質チェック・ETL を行うためのモジュール群を提供します。戦略・発注・監視などの層を想定したスケルトン実装を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計されたコードベースです。

- J-Quants API から株価（日足）、財務データ、JPX マーケットカレンダーを安全に取得するクライアント（レート制限・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたスキーマ設計（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 発注・監査（監査ログ用のテーブル定義、発注フロー追跡設計の基礎）

設計方針として、冪等性（ON CONFLICT DO UPDATE）、Look‑ahead Bias の防止（fetched_at を UTC で記録）、Fail‑Fast ではない全件収集型の品質チェックなどを採用しています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（レート制限、リトライ、401 時のトークン自動リフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等的に保存）
- data.schema
  - DuckDB のスキーマ定義と初期化（raw_prices / raw_financials / market_calendar / features / signals / orders / trades / positions / …）
  - init_schema(db_path) で DB と全テーブルを作成
- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェックの順で実行
  - 差分取得、バックフィル、品質チェック（quality モジュール連携）
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks でまとめて実行し QualityIssue のリストを返す
- data.audit
  - 監査ログ用のテーブル群（signal_events / order_requests / executions）
  - init_audit_schema / init_audit_db を提供
- config
  - .env または環境変数から設定を読み込む自動ローダ
  - settings オブジェクト経由で各種設定にアクセス可能
  - 自動ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

※ 以下は本リポジトリに `pyproject.toml` / `requirements.txt` 等が無いことを前提に一般的な手順を示します。実際の依存関係はプロジェクト側で管理してください。

1. Python 環境
   - Python 3.9 以上を推奨（型アノテーションで少し新しい構文を使っています）
   - 仮想環境作成（例）
     ```
     python -m venv .venv
     source .venv/bin/activate  # macOS/Linux
     .venv\Scripts\activate     # Windows
     ```

2. 必要パッケージのインストール（最低限）
   - duckdb は必須
   - 例:
     ```
     pip install duckdb
     ```

   - urllib 等は標準ライブラリで賄っています。

3. 環境変数（.env）を準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可）。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - 任意/デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト `development`）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト `INFO`）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化
     - DUCKDB_PATH（デフォルト `data/kabusys.duckdb`）
     - SQLITE_PATH（デフォルト `data/monitoring.db`）

   - 例（.env の簡易例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方

以下は主要な操作の例です。実行は Python スクリプト（または REPL）から行います。

1. DuckDB スキーマの初期化
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # デフォルト path は settings.duckdb_path
   ```

2. 監査ログ（Audit）テーブルの初期化（既存接続に付与）
   ```python
   from kabusys.data.audit import init_audit_schema

   init_audit_schema(conn)
   ```

3. J-Quants からデータ取得（クライアント直接利用）
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar

   # トークンを明示的に渡すこともできます。None の場合は settings.jquants_refresh_token を使用
   quotes = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
   financials = fetch_financial_statements(code="7203")
   calendar = fetch_market_calendar()
   ```

4. 取得データの保存（冪等）
   ```python
   from kabusys.data.jquants_client import save_daily_quotes, save_financial_statements, save_market_calendar

   saved_count = save_daily_quotes(conn, quotes)
   ```

5. 日次 ETL を実行（推奨: スケジュール実行）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を指定しなければ本日
   print(result.to_dict())
   ```

   run_daily_etl の挙動:
   - market_calendar を先に取得して営業日判定に使用
   - 株価・財務は差分（DB の最終取得日）を基に取得。バックフィル日数はデフォルト 3 日
   - 品質チェックは data.quality.run_all_checks を呼び出す（デフォルトで有効）

6. 品質チェックを単独実行
   ```python
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn, target_date=None)
   for issue in issues:
       print(issue)
   ```

---

## 設定 / 環境変数

主要な設定は `kabusys.config.settings` 経由で取得します。自動で `.env` や `.env.local` をプロジェクトルートから読み込みます（CWD ではなく __file__ を基準にプロジェクトルートを探索）。

- 必須 (未設定時に ValueError を送出)
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

- 任意 / デフォルト値
  - KABUSYS_ENV: development | paper_trading | live（デフォルト `development`）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト `INFO`）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 に設定すると自動ロードを無効化

自動ロードの優先順位:
- OS 環境変数 > .env.local > .env

注意: .env のパースはシェル形式に準拠した扱い（export prefix、クォート、インラインコメントの取り扱い）を行っています。

---

## 開発者向け情報 / 内部設計の要点

- J-Quants クライアント実装ポイント
  - レート制限: 120 req/min（固定間隔スロットリング）
  - リトライ: 最大 3 回、指数バックオフ。408/429/5xx をリトライ対象
  - 401 受信時はリフレッシュトークンで id_token を再取得して 1 回リトライ
  - ページネーション対応、pagination_key を利用
  - 取得時刻 fetched_at は UTC ISO8601 形式で保存（Look‑ahead 防止）

- DuckDB スキーマ
  - Raw / Processed / Feature / Execution / Audit の 3+ 層設計（Feature・AI スコア列など含む）
  - ON CONFLICT DO UPDATE を用いた冪等保存
  - インデックスを主要クエリに合わせて作成

- ETL の方針
  - 差分更新を基本（最終取得日を参照）
  - backfill_days による小さな遡及取得で API の後出し修正を吸収
  - 品質チェックは収集型（重大度は呼び出し元が判断）

- 監査ログ (audit)
  - order_request_id を冪等キーとして二重発注を防止
  - 全ての監査テーブルは削除しない前提（FK は ON DELETE RESTRICT）
  - TIMESTAMP は UTC で保存

---

## ディレクトリ構成

（パッケージの主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（fetch/save）
      - schema.py                    — DuckDB スキーマ定義 & init_schema / get_connection
      - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
      - quality.py                   — データ品質チェック
      - audit.py                     — 監査ログ用テーブル定義 & init_audit_schema
      - pipeline.py
    - strategy/
      - __init__.py
      (戦略関連モジュールの配置想定)
    - execution/
      - __init__.py
      (発注・約定管理の実装想定)
    - monitoring/
      - __init__.py
      (監視・アラート等の実装想定)

実際には strategy / execution / monitoring はスケルトン（__init__.py のみ）ですが、システム設計上の層として準備されています。

---

## よくある運用フロー（例）

1. CI / 初回セットアップで
   - init_schema(settings.duckdb_path) を実行してデータベースとテーブルを作成
   - init_audit_schema(conn) を実行して監査テーブルを有効化

2. 毎朝（あるいは定期）に ETL を実行
   - run_daily_etl(conn) をスケジューラ（cron / Airflow / Prefect 等）でキック
   - 結果の ETLResult を保存・Slack 通知・監視に使用

3. 戦略実行・発注
   - features / ai_scores を生成して signals を作り signal_queue / order 作成、order_requests を監査ログとして永続化
   - 発注は冪等キー（order_request_id）を使用して安全に送信

---

## ライセンス / 貢献

この README に記載のコードはサンプル実装であり、実運用に用いる場合は追加のテスト、セキュリティ対策、エラーハンドリング、キー／シークレット管理、各種レート制限や利用規約の遵守が必要です。貢献や仕様の拡張は歓迎します。

---

必要であれば、README に以下を追加できます：
- 実行例スクリプト（CLI）
- requirements.txt の推奨内容
- CI / デプロイ手順
- 詳細なテーブル定義（DataSchema.md へのリンク）