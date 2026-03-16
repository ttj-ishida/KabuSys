# KabuSys

日本株のデータ収集・品質チェック・監査ログを備えた自動売買基盤用ライブラリ群です。J-Quants API と連携して株価・財務・マーケットカレンダーを取得し、DuckDB にスキーマ／監査ログを初期化して保存するための ETL パイプラインや品質チェックを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つモジュール群を含みます。

- J-Quants API から株価（OHLCV）・財務データ・JPX マーケットカレンダーを取得するクライアント
- DuckDB に対するスキーマ定義と初期化ロジック（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得・バックフィル・保存・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定を UUID でトレースするテーブル群）
- 環境変数による設定管理（.env / .env.local の自動ロードをサポート）

設計上のポイント:

- API レート制限（J-Quants: 120 req/min）に準拠する内部 RateLimiter
- リトライ（指数バックオフ、最大3回、429/408/5xx を対象）、401 時は自動トークンリフレッシュ
- データ保存は冪等（ON CONFLICT DO UPDATE）で上書き
- 監査ログは UTC タイムスタンプで保存し削除を想定しない設計

---

## 主な機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB へ冪等保存）
  - レート制御・リトライ・トークン自動リフレッシュ対応

- data.schema
  - init_schema(db_path) : DuckDB の全スキーマ（Raw/Processed/Feature/Execution）を初期化
  - get_connection(db_path) : 既存 DB へ接続

- data.audit
  - init_audit_schema(conn) / init_audit_db(db_path) : 監査ログ用テーブルを初期化

- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl : 個別 ETL ジョブ
  - run_daily_etl : 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新、自動バックフィル、品質チェック（quality モジュール）を組み合わせた実行

- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks : 全チェック実行（QualityIssue のリストを返す）

- config
  - Settings クラス: 環境変数から各種設定を取得（J-Quants トークン、Kabu API、Slack、DB パス、環境種別など）
  - .env / .env.local の自動読み込み（プロジェクトルートの検出により行われる）

---

## セットアップ手順

前提:
- Python 3.9+（型ヒントに Path | None の記法が使われているため 3.10+ が推奨されます）
- pip が利用可能

1. リポジトリをクローン / 配布パッケージを配置
2. 依存パッケージをインストール（例）:

   pip install duckdb

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml に依存を定義してください。

3. 開発インストール（パッケージとして扱う場合）:

   pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数の例（.env）:

     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

   - 省略可能な設定（デフォルトあり）:

     KABUSYS_ENV=development        # development|paper_trading|live
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_DISABLE_AUTO_ENV_LOAD=0

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:

     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - 監査ログを別 DB に分ける場合:

     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（簡易ガイド）

- 日次 ETL 実行（最小例）:

  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
  print(result.to_dict())

- 個別 ETL（価格のみ差分取得）:

  from kabusys.data.pipeline import run_prices_etl, get_last_price_date
  conn = init_schema("data/kabusys.duckdb")
  from datetime import date
  fetched, saved = run_prices_etl(conn, target_date=date.today())

- J-Quants API を直接呼ぶ（テスト用）:

  from kabusys.data.jquants_client import fetch_daily_quotes
  records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  print(len(records))

- 品質チェックを単独で実行:

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)

- 監査テーブル初期化（既存接続に追加）:

  from kabusys.data.audit import init_audit_schema
  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn)  # UTC タイムゾーンが設定されます

注意点:

- run_daily_etl は複数ステップを独立に実行し、各ステップで発生したエラーは結果オブジェクトの errors に集約されます（Fail-Fast ではありません）。
- jquants_client は内部で ID トークンをキャッシュし、401 受信時は自動で 1 回リフレッシュして再試行します。ページネーション処理中も同一トークンを共有します。
- 保存処理は ON CONFLICT DO UPDATE を使って冪等に実装されています。
- 監査ログの TIMESTAMP は UTC で保存されます（init_audit_schema 実行時に SET TimeZone='UTC' が走ります）。
- .env の自動ロードは project root（.git または pyproject.toml のある親ディレクトリ）を起点に行われます。プロジェクトルートが見つからない場合は自動ロードをスキップします。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API のパスワード
- SLACK_BOT_TOKEN : Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID : 通知先チャネル ID

オプション（デフォルト値あり）:
- KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
- LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH : data/kabusys.duckdb
- SQLITE_PATH : data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると .env 自動ロードを無効化

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py                      # 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py            # J-Quants API クライアント（取得・保存ロジック）
  - schema.py                    # DuckDB スキーマ定義・初期化
  - pipeline.py                  # ETL パイプライン（差分・バックフィル・品質チェック）
  - audit.py                     # 監査ログテーブル初期化
  - quality.py                   # データ品質チェック
- strategy/
  - __init__.py                  # 戦略関連（未実装の枠組み）
- execution/
  - __init__.py                  # 発注・ブローカ連携（未実装の枠組み）
- monitoring/
  - __init__.py                  # 監視関連（未実装の枠組み）

主要モジュール:
- kabusys.config.settings        # 設定オブジェクトインスタンス
- kabusys.data.schema.init_schema
- kabusys.data.jquants_client.*
- kabusys.data.pipeline.run_daily_etl
- kabusys.data.quality.run_all_checks
- kabusys.data.audit.init_audit_schema / init_audit_db

---

## 開発・運用メモ

- DuckDB を用いて高速にローカル DB を扱えます。インメモリ（":memory:"）を使うことも可能です。
- J-Quants の API レート制限（120 req/min）に合わせて内部でスロットリングを行いますが、大量の並列リクエストを行う場合はさらに注意してください。
- ETL の差分ロジックはデフォルトでバックフィルを行い、後出し修正を吸収する設計です（backfill_days=3 がデフォルト）。
- 品質チェックはエラーと警告に分かれており、呼び出し側が重大度に応じて停止/通知を判断できます。
- 監査ログは削除しない方針のため、運用上はディスク管理・アーカイブ方針を設計してください。

---

## ライセンス / コントリビュート

このリポジトリにライセンス・貢献ルールがある場合はプロジェクトルートの該当ファイルを参照してください（本コードベースには明示的なライセンスファイルは含まれていません）。

貢献やバグ報告は issue / PR を通じて行ってください。

---

README は以上です。必要であれば、実行スクリプトの例や CI 用のコマンド、より詳しい .env.example を追記します。どの部分を詳しく追記しますか？