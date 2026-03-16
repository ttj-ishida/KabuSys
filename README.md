# KabuSys

日本株向けの自動売買基盤ライブラリ（プロトタイプ）  
主にデータ取得・ETL、データ品質チェック、監査ログ、戦略・発注層の基盤を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための共通基盤ライブラリです。  
主な目的は次の通りです。

- J-Quants API からの市場データ（株価日足、財務データ、JPX マーケットカレンダー）の取得と永続化
- DuckDB を用いたスキーマ定義・初期化（生データ・加工層・特徴量層・実行層を含む）
- ETL パイプライン（差分更新、バックフィル、品質チェック）の提供
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）用テーブルの提供
- 環境変数ベースの設定管理（自動 .env 読み込み機能を持つ）

設計上の特徴：
- API レート制限とリトライ（J-Quants クライアント）
- データ取得時の fetched_at 記録によるトレーサビリティ（Look-ahead bias 回避）
- DuckDB への保存は冪等性（ON CONFLICT DO UPDATE）
- 品質チェックは Fail-Fast にせず全件収集して呼び出し元で判断可能

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（必要で無効化可能）
  - 必須キー取得チェック（例: JQUANTS_REFRESH_TOKEN）

- データ取得（kabusys.data.jquants_client）
  - fetch_daily_quotes: 株価日足（ページネーション対応）
  - fetch_financial_statements: 財務データ（四半期）
  - fetch_market_calendar: JPX カレンダー
  - レートリミッター・リトライ・トークン自動リフレッシュ

- データ永続化（kabusys.data.schema）
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(): DB 初期化（冪等）
  - get_connection(): 既存 DB 接続取得

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日からの差分算出）とバックフィル
  - run_daily_etl(): カレンダー → 株価 → 財務 → 品質チェックの一括実行
  - 品質チェック連携（quality モジュール）

- データ品質チェック（kabusys.data.quality）
  - 欠損データ検出（OHLC 欠損）
  - スパイク検出（前日比）
  - 主キー重複検出
  - 日付不整合（未来日付・非営業日のデータ）

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions の監査テーブル（UTCタイムスタンプ）
  - init_audit_schema()/init_audit_db()

- 戦略・発注・モニタリング基盤（パッケージ内にプレースホルダモジュールを用意）
  - kabusys.strategy, kabusys.execution, kabusys.monitoring

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントに union | を使用）
- pip

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 開発インストール（パッケージを editable にインストール）
   pip install -e .

   ※ 実際の requirements はプロジェクトに合わせて追加してください（例: duckdb）。

3. 必要パッケージ例（最低限）
   pip install duckdb

4. 環境変数設定
   プロジェクトルートに `.env` を置くか、OS 環境変数を設定します。自動読み込みはデフォルトで有効です。

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
   KABU_API_PASSWORD=kabustation_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   テストなどで自動 .env 読み込みを無効化する場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方

以下は代表的な利用例です。Python インタプリタやスクリプトから呼び出して利用します。

- DuckDB スキーマ初期化（ファイル DB）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 監査ログのみ初期化（既存接続に追加）
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.audit import init_audit_schema

  conn = init_schema("data/kabusys.duckdb")  # 既に init_schema を使っていれば不要
  init_audit_schema(conn)
  ```

- J-Quants から株価と保存（低レベル利用）
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f"saved: {saved}")
  ```

- 日次 ETL 実行（推奨: pipeline の高レベル API）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 設定取得
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  is_live = settings.is_live
  ```

注意点:
- J-Quants API はレート制限（120 req/min）があるため、jquants_client は内部でスロットリングとリトライを行います。
- get_id_token はリフレッシュトークンから idToken を取得します。401 受信時は自動リフレッシュして 1 回だけ再試行します。
- ETL の品質チェックはデフォルトで実行され、QualityIssue のリストが ETLResult に含まれます。重大度に応じた運用判断は利用者側で行ってください。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL (任意): kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): 通知先の Slack チャンネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意): 環境名（development / paper_trading / live、デフォルト development）
- LOG_LEVEL (任意): ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意): 自動 .env 読み込みを無効化する場合に 1 を設定

---

## ディレクトリ構成

（src 配下を基準）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存ロジック）
    - schema.py                  — DuckDB スキーマ定義 / init_schema / get_connection
    - pipeline.py                — ETL パイプライン（差分更新・品質チェック）
    - audit.py                   — 監査ログ用テーブルの初期化
    - quality.py                 — データ品質チェック
  - strategy/
    - __init__.py                — 戦略層（拡張用）
  - execution/
    - __init__.py                — 発注・ブローカー連携層（拡張用）
  - monitoring/
    - __init__.py                — 監視・メトリクス層（拡張用）

補足:
- Data / Audit / Quality モジュール群は DuckDB を中核として設計されています。
- strategy / execution / monitoring は本コードベースでは基盤（プレースホルダ）が用意されています。実際の戦略ロジック・ブローカー実装はこの上に構築してください。

---

## 運用上の注意

- 本ライブラリは資金・実運用を伴うため、安全なテスト（paper_trading モード）およびリスク管理を必ず行ってください。
- DB の初期化やスキーマ変更は影響が大きいためバックアップを取ることを推奨します。
- J-Quants トークンの管理は慎重に行い、漏洩対策をしてください。

---

必要に応じて README に追記します（例: 実際のインストール要件、CI/CD、実運用チェックリスト、運用時の Slack 通知連携方法など）。追加したい項目があれば教えてください。