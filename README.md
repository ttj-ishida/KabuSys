# KabuSys

日本株向け自動売買基盤ライブラリ（未完成プロジェクト）。  
データ取得・ETL、DuckDB スキーマ、データ品質チェック、監査ログなど、基盤となる機能群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。主な目的は以下です。

- J-Quants API からの市場データ（株価日足、財務データ、マーケットカレンダー）取得
- DuckDB を用いたデータスキーマ定義と永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定 のトレーサビリティ）
- 設定管理（.env / 環境変数自動読み込み、必須項目チェック）

設計上のポイント:
- API レート制限・リトライ・トークン自動更新を備えた J-Quants クライアント
- ETL は冪等（ON CONFLICT DO UPDATE）で再実行可能
- 品質チェックは全件収集し、呼び出し元で重大度に応じた対処を行う

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数の検証
- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - レートリミット（120 req/min）、リトライ（指数バックオフ）、401 時の自動リフレッシュ
  - DuckDB への保存用 save_* 関数（冪等）
- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - init_schema / get_connection
- ETL パイプライン（kabusys.data.pipeline）
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - 差分取得、バックフィル、品質チェック統合
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブルやインデックスを初期化
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合検出
  - QualityIssue による問題収集

（strategy / execution / monitoring モジュールは骨組みのみ）

---

## 動作要件

- Python 3.10+
  - （型アノテーションで `|` を使用しているため 3.10 以上が必要）
- 必須パッケージ
  - duckdb

インストール例（仮）:
pip install duckdb
（プロジェクトをパッケージ化している場合は `pip install -e .` を利用）

---

## セットアップ手順

1. リポジトリをクローンして、ソースが `src/` 以下にある状態にしてください。

2. Python 仮想環境を作成・有効化し、依存パッケージをインストールします。
   - 例:
     python -m venv .venv
     source .venv/bin/activate
     pip install duckdb

3. 環境変数を設定します（またはプロジェクトルートに `.env` を作成）。
   - 自動読み込みの優先順: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須): kabu API のパスワード
   - KABU_API_BASE_URL (任意): デフォルト "http://localhost:18080/kabusapi"
   - SLACK_BOT_TOKEN (必須): Slack 通知用トークン
   - SLACK_CHANNEL_ID (必須): Slack 通知先チャンネル
   - DUCKDB_PATH (任意): DuckDB ファイルパス（例: data/kabusys.duckdb）
   - SQLITE_PATH (任意): 監視用 SQLite（例: data/monitoring.db）
   - KABUSYS_ENV (任意): development / paper_trading / live（デフォルト development）
   - LOG_LEVEL (任意): DEBUG / INFO / WARNING / ERROR / CRITICAL

   .env の例（プロジェクトルート `.env.example` を参考に作成してください）:
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

4. DuckDB スキーマを初期化します。
   - Python で:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - これにより必要なテーブルとインデックスが作成されます。

5. 監査ログテーブルを追加で初期化する場合:
   - 既存の conn を用いる:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
   - または監査専用 DB を作成:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")

---

## 使い方（簡易例）

1) J-Quants トークン取得（例）
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用

2) DuckDB スキーマ初期化
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

3) 日次 ETL 実行（run_daily_etl）
from kabusys.data.pipeline import run_daily_etl
from datetime import date
result = run_daily_etl(conn, target_date=date.today())
# ETLResult オブジェクトで取得件数・品質問題・エラー履歴を確認
print(result.to_dict())

4) 個別ジョブ（株価 ETL）
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date.today())

5) 保存済みデータの品質チェックを個別に実行
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i.check_name, i.severity, i.detail)

6) 監査ログの記録（概念）
- シグナル生成時に signal_events に UUID を付与して INSERT
- 発注時に order_requests テーブルへ冪等キー（order_request_id）で INSERT
- 証券会社からのコールバックで executions に記録

（実際のレコード操作用のユーティリティ関数は現状実装されていません。用途に応じて DB 操作を実装してください。）

---

## 設計上の注意点

- J-Quants API はレート制限を厳守（120 req/min）。ライブラリでは固定間隔スロットリングを実装しています。
- HTTP エラーに対するリトライ（最大 3 回）と指数バックオフ、429 の場合は Retry-After を優先。
- 401 受信時はリフレッシュトークンで自動的に ID トークンを再取得して 1 回だけリトライします。
- ETL は冪等性を重視：DuckDB への INSERT は ON CONFLICT DO UPDATE を使用。
- 品質チェックは Fail-Fast ではなく問題をすべて収集して返します。呼び出し元のポリシーで処理を決定してください。
- すべての TIMESTAMP は UTC の使用が前提（監査ログ初期化で SET TimeZone='UTC' を実行）。

---

## 主要モジュール・ディレクトリ構成

src/kabusys/
- __init__.py
- config.py  — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント（取得・保存ロジック）
  - schema.py  — DuckDB スキーマ定義と初期化
  - pipeline.py  — ETL パイプライン
  - audit.py  — 監査ログ（signal/order/execution）スキーマ
  - quality.py  — データ品質チェック
- strategy/
  - __init__.py  — 戦略層（未実装）
- execution/
  - __init__.py  — 発注実行層（未実装）
- monitoring/
  - __init__.py  — 監視関連（未実装）

その他:
- .env.example（プロジェクトルートに置く想定、環境変数の例を記載）

---

## よくある運用フロー（例）

1. 毎朝バッチ（またはスケジューラ）で:
   - DB 接続を取得して run_daily_etl を実行
   - ETLResult を Slack 等に通知（SLACK_BOT_TOKEN を使用）
   - 品質エラーがあればアラートを上げる

2. 戦略実行:
   - features / ai_scores を元にシグナルを生成し signal_events に記録
   - order_requests を作成し冪等性を担保してブローカーへ送信
   - 約定コールバックで executions を記録し、positions / portfolio_performance を更新

---

## 補足

- このリポジトリは基盤のコア機能に重点を置いており、実際の戦略ロジックやブローカー連携（kabu API 呼び出しラッパー等）、Slack 通知実装、バッチ運用スクリプト等は別途実装する必要があります。
- テスト時に自動 .env 読み込みを無効化したい場合は、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

---

必要であれば README に含めるサンプル .env.example、ユニットテストの実行方法、CI/CD の簡易ガイド、または各 API の詳細使用例（関数ごとの引数/戻り値を含む）を追加で作成します。どの情報を追加しますか？