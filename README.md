# KabuSys

日本株向け自動売買／データ基盤ライブラリ KabuSys の README。

このリポジトリは、J-Quants 等の外部データソースからデータを取得し、DuckDB に保存・整形し、品質チェックや監査ログを備えた自動売買基盤のコア機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価・財務・カレンダー取得（レートリミット・リトライ・トークン自動更新対応）
- RSS ベースのニュース収集と記事 — 銘柄紐付け
- DuckDB を用いたスキーマ定義・ETL（差分取得・冪等保存）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー管理（営業日判定等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 環境変数ベースの設定管理（.env 読込自動化）

設計上の特徴：
- API レート制御（固定間隔スロットリング）
- 冪等性（INSERT ... ON CONFLICT で重複を排除）
- セキュリティを考慮した RSS 取得（SSRF 対策、defusedxml 利用、サイズ制限）
- テストしやすい設計（トークン注入やモック可能な内部関数）

---

## 機能一覧

主なモジュールと提供機能：

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）
  - Settings クラス（J-Quants トークン、kabu API、Slack、DB パス、環境フラグ等）
- kabusys.data.jquants_client
  - J-Quants API クライアント（ID トークンリフレッシュ、ページネーション、リトライ、レート制御）
  - fetch/save: daily_quotes, financial_statements, market_calendar
- kabusys.data.news_collector
  - RSS フィード取得、記事整形、ID 付与（URL 正規化 + SHA-256）、DuckDB への保存、銘柄抽出
  - SSRF・gzip・XML ボム対策、受信サイズ上限
- kabusys.data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema / get_connection
- kabusys.data.pipeline
  - 日次 ETL（差分取得・バックフィル・品質チェック）
  - run_daily_etl, 個別 ETL: run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.calendar_management
  - 営業日判定・next/prev trading day・calendar_update_job 等
- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
  - QualityIssue データクラス
- kabusys.data.audit
  - 監査ログ用テーブル初期化（signal_events, order_requests, executions）
- kabusys.execution / kabusys.strategy / kabusys.monitoring
  - プレースホルダ（パッケージ構造上のモジュール）

---

## 前提条件（推奨）

- Python 3.10 以上（型注釈に | を使用）
- 必要パッケージ（最低限）:
  - duckdb
  - defusedxml

インストール例：
pip install duckdb defusedxml

（プロジェクトとして配布する場合は requirements.txt / pyproject.toml を利用してください）

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. 依存ライブラリをインストール
   - 例:
     pip install duckdb defusedxml

3. 環境変数 / .env を準備
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みはデフォルトで有効）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   推奨される環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu API のパスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時 data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite のパス（省略時 data/monitoring.db）
   - KABUSYS_ENV: 開発環境 (development / paper_trading / live)（省略時 development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）（省略時 INFO）

   `.env.example` を参考に作成してください（README の例としては上記キーを記載）。

4. DuckDB スキーマ初期化
   - Python REPL もしくはスクリプトで実行:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
   - 監査ログを別 DB にしたい場合:
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   - 既に接続済み conn に対して監査スキーマを追加する:
     audit.init_audit_schema(conn)

---

## 使い方（簡単なコード例）

- 設定の参照:
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  if settings.is_live:
      # 本番フラグが立っているかを確認

- DuckDB スキーマ初期化:
  from kabusys.data import schema
  conn = schema.init_schema(settings.duckdb_path)

- 日次 ETL 実行:
  from kabusys.data import pipeline
  from kabusys.config import settings
  conn = schema.get_connection(settings.duckdb_path)  # または init_schema で取得した conn
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())  # ETL の結果サマリ

- カレンダー更新ジョブ（夜間バッチ向け）:
  from kabusys.data import calendar_management
  conn = schema.get_connection(settings.duckdb_path)
  saved = calendar_management.calendar_update_job(conn)
  print("saved:", saved)

- RSS ニュース収集と保存:
  from kabusys.data import news_collector
  conn = schema.get_connection(settings.duckdb_path)
  results = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
  print(results)

- 個別 J-Quants API 呼び出し（トークンを明示的に渡す例）:
  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings から自動取得
  quotes = jq.fetch_daily_quotes(id_token=id_token, code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  jq.save_daily_quotes(conn, quotes)

- 品質チェックだけ実行:
  from kabusys.data import quality
  issues = quality.run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)

注意:
- run_daily_etl 等は内部で例外を個別に捕捉して継続する設計ですが、戻り値の ETLResult に errors や quality_issues が入るため必ず結果を確認してください。
- テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読み込みを無効化できます。

---

## ディレクトリ構成

主要なファイル / モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       # 環境変数・設定管理（.env 自動ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py              # J-Quants API クライアント（fetch/save）
    - news_collector.py             # RSS 取得・記事整形・保存・銘柄抽出
    - schema.py                     # DuckDB スキーマ定義・初期化
    - pipeline.py                   # ETL パイプライン（差分更新・日次ETL）
    - calendar_management.py        # カレンダー管理・営業日判定・更新ジョブ
    - audit.py                      # 監査ログテーブル初期化
    - quality.py                    # データ品質チェック
  - strategy/
    - __init__.py                    # 戦略用プレースホルダ（実装は別途）
  - execution/
    - __init__.py                    # 発注実行プレースホルダ（実装は別途）
  - monitoring/
    - __init__.py                    # 監視関連プレースホルダ（実装は別途）

README に記載のない補助点:
- ログは標準的な logging を利用（LOG_LEVEL で制御）
- DB 初期化は冪等（既存テーブルがあればスキップ）
- テスト用に各種内部関数（例: _urlopen）をモック可能に設計

---

## 注意事項 / ベストプラクティス

- 本システムは実際の売買に使う際は十分な検証が必要です（特に execution 層の実装・安全対策）。
- 本番環境（live）を扱う場合は KABUSYS_ENV を `live` に設定し、ログや通知の取り扱いに注意してください。
- J-Quants の API レート制限を尊重してください（ライブラリは 120 req/min を想定して制御しますが、運用側でも設計を確認すること）。
- DuckDB ファイルはバックアップと保守を行ってください。必要に応じて監査ログ専用 DB を分離することを推奨します。

---

もし README に追加してほしい具体的な例（cron ジョブサンプル、docker-compose、CI 設定、細かい .env.example 等）があれば教えてください。必要に応じて追記します。