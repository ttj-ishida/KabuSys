# KabuSys

日本株の自動売買プラットフォーム向けユーティリティ群（ライブラリ）
（この README はコードベースのソースを元にした概要・使い方ドキュメントです）

概要
- KabuSys は日本株の市場データ取得・ETL、データ品質チェック、DuckDB スキーマ定義、監査ログ（発注→約定のトレーサビリティ）等を提供するモジュール群です。
- J-Quants API を利用した日次株価（OHLCV）、財務（四半期 BS/PL）、JPX 市場カレンダーの取得／保存、差分 ETL、品質チェック、監査テーブル初期化などを含みます。
- 設計上のポイント:
  - API レート制御（120 req/min）とリトライ（指数バックオフ、401 の自動リフレッシュ対応）
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
  - データ取得時刻（fetched_at）を記録して Look-ahead Bias を防止
  - 品質チェックは全件収集型（Fail-Fast ではない）

主な機能一覧
- 環境変数／設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須設定の取得（例: JQUANTS_REFRESH_TOKEN 等）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（/prices/daily_quotes）・財務（/fins/statements）・カレンダー取得
  - レートリミッタ、リトライ（408/429/5xx）、401 の自動トークン更新
  - 保存ユーティリティ：save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB 用）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブルを定義・初期化
  - init_schema(db_path) で DB 初期化（冪等）
  - get_connection(db_path) で既存 DB へ接続
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日ベース、デフォルトで backfill_days=3）
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl（全体実行）
  - 品質チェック呼び出し（kabusys.data.quality）
- データ品質チェック（kabusys.data.quality）
  - 欠損データ検出、スパイク（前日比）検出、重複チェック、日付不整合（未来日 / 非営業日）検出
  - QualityIssue データ構造で問題を集約（severity=error|warning）
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions など監査用テーブルを初期化
  - すべて UTC タイムスタンプ、冪等性と参照整合性を重視

必要条件
- Python 3.10 以上（型アノテーションの union 形式や新しい構文を使用）
- 主要依存：
  - duckdb
  - （標準ライブラリ: urllib, json, logging, datetime など）
- 実運用では J-Quants の認証情報、kabu ステーション API の認証情報等が必要

セットアップ手順（開発環境向けの一例）
1. リポジトリをクローン
   - git clone <repository-url>
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb
   - （プロジェクトに requirements.txt / pyproject.toml があれば pip install -e . や pip install -r requirements.txt）
4. 環境変数を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env または .env.local を作成すると自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須)
     - SLACK_CHANNEL_ID (必須)
     - DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (任意、デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live、デフォルト: development)
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
   - 例 .env:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
5. DuckDB スキーマ初期化
   - Python REPL やスクリプト内で:
     ```
     from kabusys.data import schema
     from kabusys.config import settings
     conn = schema.init_schema(settings.duckdb_path)
     ```
   - 監査ログを別 DB に初期化する場合:
     ```
     from kabusys.data import audit
     conn_audit = audit.init_audit_db("data/audit.duckdb")
     ```
   - 既存 DB へ接続するだけなら get_connection()

基本的な使い方（例）
- J-Quants の ID トークン取得
  ```
  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
  ```
- ETL（単発で日次 ETL を実行）
  ```
  from datetime import date
  from kabusys.data import schema, pipeline
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)  # まだなら初期化
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```
- 個別ジョブの呼び出し（差分取得やテスト）
  ```
  # 株価のみ
  from kabusys.data import pipeline
  fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())

  # 財務のみ
  fetched, saved = pipeline.run_financials_etl(conn, target_date=date.today())
  ```
- 品質チェック単体実行
  ```
  from kabusys.data import quality
  issues = quality.run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

API（主要な公開関数 / クラス）
- kabusys.config
  - settings: Settings インスタンス（プロパティ経由で環境変数取得）
  - 主要プロパティ: settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path, settings.env, settings.log_level, settings.is_live / is_paper / is_dev
- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None = None) -> str
  - fetch_daily_quotes(id_token: str | None = None, code: str | None = None, date_from: date | None = None, date_to: date | None = None) -> list[dict]
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int
- kabusys.data.schema
  - init_schema(db_path) -> duckdb connection
  - get_connection(db_path) -> duckdb connection
- kabusys.data.pipeline
  - run_prices_etl(conn, target_date, ...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
  - ETLResult クラス（実行結果を保持）
- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5) -> list[QualityIssue]
  - 個別チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

設計上の注意点 / 運用メモ
- 自動 .env ロードはプロジェクトルート (.git 或いは pyproject.toml が基準) を起点に行われます。テスト時や環境制御したい場合、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制限（120 req/min）を守るため、クライアント側で固定間隔のスロットリングを実施しています。並列化する場合は注意してください。
- データの保存は ON CONFLICT DO UPDATE により冪等化されています（重複挿入での二重化を回避）。
- 品質チェックで severity="error" の検出があった場合は運用で ETL を停止するかどうかを決める必要があります（ライブラリは問題を収集して返します）。
- 監査ログは原則削除せず、全てのイベントを永続化する前提です（FK は ON DELETE RESTRICT）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得 + 保存）
    - schema.py                 — DuckDB スキーマ定義・初期化
    - pipeline.py               — ETL パイプライン（差分更新 / run_daily_etl）
    - quality.py                — データ品質チェック
    - audit.py                  — 監査ログ（signal/order/execution）初期化
    - audit.py, schema.py の DDL に基づき tables/indexes を作成
  - strategy/
    - __init__.py               — 戦略モジュール用プレースホルダ（実装はここに追加）
  - execution/
    - __init__.py               — 発注 / ブローカー連携用プレースホルダ
  - monitoring/
    - __init__.py               — 監視（Prometheus / メトリクス / Slack 通知等を実装予定）

今後の拡張提案
- 実際の発注実行コンポーネント（kabu ステーションとの通信、注文再送/状態同期）
- 戦略層の実装例（単純モメンタム戦略、AI スコアの生成パイプライン）
- Slack / Observability（メトリクス、Prometheus, Sentry 等）連携
- CI での DB スキーマ / 品質チェックの自動実行

サポート / 貢献
- 本リポジトリは技術ドキュメントに基づくコードベースの README であり、実環境に導入する場合は API キーや認証情報の管理、テスト、監視を十分に行ってください。
- バグ修正や機能追加は Pull Request を歓迎します。変更の際は既存の DDL や互換性に注意してください。

以上。

（必要であれば、README に含めるサンプルスクリプトやより詳細な環境変数一覧、運用フロー例（cron, Airflow, Docker Compose）を追加します。どのレベルの運用ドキュメントが必要か教えてください。）