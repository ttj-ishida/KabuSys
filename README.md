# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
J‑Quants API から市場データ・財務データ・カレンダーを取得し、DuckDB に格納、品質チェックや監査ログの管理、ETL パイプラインを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的で設計された内部ライブラリです。

- J‑Quants API からの株価（日足）、財務情報（四半期 BS/PL）、JPX マーケットカレンダーを取得するクライアント機能
- 取得した生データを DuckDB に保存するスキーマ定義と idempotent な保存処理
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）の提供
- データ品質チェック（欠損・スパイク・重複・日付不整合）の実装
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）のためのスキーマと初期化処理

設計上の特徴：
- API レート制限（120 req/min）厳守（固定間隔スロットリング）
- リトライ（指数バックオフ、401 の場合は自動トークンリフレッシュ）
- 取得時刻（UTC）を記録し Look‑ahead バイアスを追跡可能
- DuckDB への保存は ON CONFLICT DO UPDATE により冪等性を確保

---

## 主な機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - レートリミット・リトライ・トークンリフレッシュ対応

- data.schema
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) による初期化、get_connection()

- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - 差分取得・バックフィル・品質チェックを統合

- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks による一括実行、QualityIssue で問題を返す

- data.audit
  - 監査ログ用スキーマ（signal_events, order_requests, executions）
  - init_audit_schema / init_audit_db による初期化

- settings（kabusys.config）
  - 環境変数管理（.env/.env.local の自動読込、必要変数チェック）
  - settings オブジェクト経由で設定にアクセス

---

## システム要件

- Python 3.10 以上（| 型注釈、match 等は不要ですが union 表記 (A | B) を使用）
- 必要な Python パッケージ（最低限）
  - duckdb
- ネットワーク接続（J‑Quants API、kabuステーション API、Slack 連携などを使う場合）

※ 実行環境に応じて追加のパッケージ（Slack クライアント等）を導入してください。

---

## セットアップ手順

1. リポジトリをチェックアウト

   git clone <リポジトリURL>
   cd <リポジトリ>

2. 仮想環境作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 必要パッケージをインストール

   pip install duckdb

   追加で Slack や kabu API クライアントを使う場合はそれらのパッケージも導入してください。

4. 環境変数の準備

   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（kabusys.config が .git または pyproject.toml を起点にプロジェクトルートを検出します）。

   .env の例:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルト値あり）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB スキーマの初期化例

   Python セッションまたはスクリプト内で:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   監査ログ（audit）テーブルを初期化する場合:

   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)

---

## 使い方（簡単な例）

1) 設定取得

from kabusys.config import settings
print(settings.duckdb_path)  # Pathオブジェクト

未設定の必須環境変数にアクセスすると ValueError が発生します（例: settings.jquants_refresh_token）。

2) DuckDB スキーマ初期化

from kabusys.data.schema import init_schema
conn = init_schema(settings.duckdb_path)

3) 日次 ETL の実行（単発）

from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

ETLResult には取得件数、保存件数、品質チェック結果（QualityIssue のリスト）、エラーの要約が含まれます。

4) 個別ジョブを実行する場合

from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

# 株価だけ差分ETL
fetched, saved = run_prices_etl(conn, target_date=date.today())

# 財務データだけ
fetched_f, saved_f = run_financials_etl(conn, target_date=date.today())

# カレンダー（先読み）
fetched_c, saved_c = run_calendar_etl(conn, target_date=date.today())

5) 監査スキーマの初期化（監査用専用 DB を作る場合）

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 主要 API（抜粋）

- settings（kabusys.config.settings）
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url
  - slack_bot_token, slack_channel_id
  - duckdb_path, sqlite_path
  - env, log_level, is_live, is_paper, is_dev

- data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None) -> list[dict]
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int

- data.schema
  - init_schema(db_path) -> DuckDB connection
  - get_connection(db_path) -> DuckDB connection

- data.pipeline
  - run_prices_etl(conn, target_date, ...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(conn, target_date=None, run_quality_checks=True, ... ) -> ETLResult

- data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5) -> list[QualityIssue]
  - 個別チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency

- data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## 環境変数（必須 / 任意）

必須:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（API を使用する場合）
- SLACK_BOT_TOKEN — Slack 通知を行う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネル

任意（デフォルトあり）:
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。自動読込を無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

src/kabusys/
- __init__.py
- config.py                       — 環境変数 / 設定管理
- execution/
  - __init__.py                    — 発注実行系（将来拡張）
- strategy/
  - __init__.py                    — 戦略モジュール（将来拡張）
- monitoring/
  - __init__.py                    — 監視・メトリクス（将来拡張）
- data/
  - __init__.py
  - jquants_client.py              — J‑Quants API クライアント（取得 + 保存）
  - schema.py                      — DuckDB スキーマ定義と初期化
  - pipeline.py                    — ETL パイプライン（差分更新 / 品質チェック）
  - audit.py                       — 監査ログスキーマと初期化
  - quality.py                     — データ品質チェック

プロジェクトは src レイアウトで配置されています。パッケージとしてインストールする際は src を参照する形になります。

---

## 運用上の注意 / ベストプラクティス

- secrets（API トークン等）は .env に記載してバージョン管理に入れないでください。
- ローカル開発は KABUSYS_ENV=development、ペーパートレードは paper_trading、本番は live を使用して環境差分を制御してください。
- DuckDB ファイルはバックアップ・バージョン管理対象外にしてください（大容量になる可能性あり）。
- run_daily_etl は外部ジョブスケジューラ（cron / Airflow / Prefect 等）から呼ぶ想定です。品質チェックは ETL の最後に実行され、問題があっても ETL 自体は継続します（呼び出し側でエラー判定を行ってください）。
- J‑Quants API 利用時はレート制限を尊重してください（本ライブラリは120 req/min を守る設計です）。

---

## 参考 / 拡張ポイント

- strategy 層に戦略ロジックを実装し、signals/signal_queue を介して execution 層へ受け渡す
- execution 層で証券会社 API（kabuステーション等）と連携して発注→約定情報を監査ログへ保存
- Slack などで ETL 結果や品質アラートを通知する監視機構の実装
- DuckDB のスキーマや品質チェックはプロダクション要件に合わせて拡張可能

---

ご不明点や README に追加したい内容（例: CI/CD 手順、テスト実行方法、API キーの発行手順など）があれば教えてください。README を追補して整備します。