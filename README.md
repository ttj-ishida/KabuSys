# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
J-Quants API から市場データを取得して DuckDB に保存し、品質チェック・ETL・監査ログ・発注フローの基盤を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール化された Python パッケージです。

- J-Quants API からの株価・財務・マーケットカレンダー取得（ページネーション対応）
- DuckDB ベースの3層データスキーマ（Raw / Processed / Feature）と監査ログ
- 差分 ETL パイプライン（バックフィル対応）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注・約定監査テーブル（監査トレースのための UUID 連鎖）
- 環境変数を用いた設定管理（.env の自動読み込み対応）

設計上のポイント:
- API レート制御（120 req/min の固定間隔スロットリング）
- リトライ（指数バックオフ、最大 3 回。401 はトークン自動リフレッシュを試行）
- 取得時刻（fetched_at）を UTC で保存し、Look-ahead バイアスを防止
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を排除

---

## 機能一覧

- 環境・設定管理（kabusys.config.Settings）
  - 必須/省略可能な環境変数を型付きで取得
  - プロジェクトルートの .env / .env.local を自動読み込み（無効化可）
- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_daily_quotes(), save_financial_statements(), save_market_calendar()
  - レートリミッター、リトライ、トークンキャッシュ機構
- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path) で DB とテーブル（Raw/Processed/Feature/Execution）を初期化
  - get_connection(db_path)
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl(conn, ...)：カレンダー→株価→財務→品質チェック の一括 ETL
  - 差分取得、バックフィル、品質チェック（quality モジュール）を統合
- 品質チェック（kabusys.data.quality）
  - 欠損（missing_data）、スパイク（spike）、重複（duplicates）、日付不整合（future/non_trading）
  - run_all_checks(conn, ...)
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions を含む監査テーブルの初期化・追加
  - init_audit_schema(conn), init_audit_db(db_path)

---

## 要件

必須ライブラリ（代表的なもの）
- Python 3.10+
- duckdb

（その他、標準ライブラリのみで動作するコードが多いですが、実行環境に応じて依存を追加してください）

インストール（開発時）例:
- プロジェクトルートに pyproject.toml がある想定で:
  - pip install -e .
- もしパッケージインストールができない場合:
  - PYTHONPATH に `src/` を追加して読み込む

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得

2. 依存パッケージをインストール
   - pip install duckdb
   - （必要に応じて他パッケージを追加）

3. 環境変数（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
   - 以下は省略可能（デフォルトあり / 調整可）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）

   環境変数はプロジェクトルートの `.env` と `.env.local` を自動で読み込みます。
   自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. `.env.example` を元に `.env` を作成（リポジトリに例がない場合は上記キーを設定）

---

## 初期化と使い方（例）

以下は Python REPL やスクリプトからの基本的な使い方例です。

- DuckDB スキーマ初期化（初回）:

  python
  from kabusys.data import schema
  from kabusys.config import settings

  # settings.duckdb_path はデフォルトで data/kabusys.duckdb
  conn = schema.init_schema(settings.duckdb_path)

- 監査ログテーブルを追加する（既存 conn に対して）:

  from kabusys.data import audit
  audit.init_audit_schema(conn)

- 日次 ETL の実行:

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)  # 一度 init_schema しておく
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- J-Quants トークン取得・直接データ取得（テスト用）:

  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
  prices = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,1,31))

- 品質チェックの手動実行:

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)

注意点:
- run_daily_etl は複数のステップで例外を個別にキャッチし、処理を継続します。戻り値の ETLResult に errors と quality_issues が格納されます。
- jquants_client 内のリクエストはレート制御・リトライ・自動トークン更新を行います。大量取得時はレート制限に注意してください。

---

## 環境変数（一覧）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

推奨 / 省略可:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動読み込みを無効化)

---

## ディレクトリ構成

リポジトリの主要ファイル / モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得/保存）
    - schema.py                  — DuckDB スキーマ定義と初期化
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - audit.py                   — 監査ログテーブルの定義 / 初期化
    - quality.py                 — データ品質チェック
  - strategy/
    - __init__.py                — 戦略関連（プレースホルダ）
  - execution/
    - __init__.py                — 発注実行関連（プレースホルダ）
  - monitoring/
    - __init__.py                — 監視・メトリクス関連（プレースホルダ）

主要機能は `kabusys.data` 以下に集約されています。`strategy` / `execution` / `monitoring` は拡張用の名前空間として用意されています。

---

## 開発・テスト時のヒント

- 自動 .env 読み込みはパッケージ初期化時に行われます。ユニットテストなどで環境を制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- jquants_client のテストでは get_id_token をモックするか、id_token を外部から注入するとテストしやすくなります（fetch_* 関数は id_token の注入をサポート）。
- DuckDB を一時的に使う場合は db_path に ":memory:" を指定してインメモリ DB を使うことができます。

---

## 貢献・ライセンス

この README はコードベースの概要説明です。詳細な CONTRIBUTING ガイドや LICENSE はリポジトリに応じて追加してください。

---

以上。必要であれば README に記載する `.env.example` のテンプレートや、より細かい API 使用例（関数シグネチャごとの説明・戻り値の例）を追記します。どの情報を補足しますか？