# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。J-Quants API からマーケットデータや財務データ、JPX カレンダーを取得して DuckDB に保存し、ETL・データ品質チェック・監査ログを提供します。売買戦略（strategy）、発注処理（execution）、監視（monitoring）のための骨組みを含みます。

---

## 概要（Project overview）

- J-Quants API を利用して株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得します。
- 取得データは DuckDB に層構造（Raw / Processed / Feature / Execution）で保存します。
- ETL パイプライン（差分更新・バックフィル・品質チェック）を提供します。
- 監査ログ（signal → order_request → execution の連鎖）を別途初期化可能です。
- レート制限（120 req/min）、リトライ（指数バックオフ）、401 の自動トークンリフレッシュ、Look-ahead バイアス対策（fetched_at の記録）、冪等性（ON CONFLICT DO UPDATE）などを考慮した設計。

---

## 機能一覧（Features）

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定）
  - 必須環境変数の取得と検証（J-Quants / kabu / Slack 等）
  - KABUSYS_ENV（development / paper_trading / live）とログレベル検証

- データ取得（data.jquants_client）
  - get_id_token（リフレッシュトークンから idToken を取得）
  - fetch_daily_quotes（株価日足、ページネーション対応）
  - fetch_financial_statements（財務データ）
  - fetch_market_calendar（JPX カレンダー）
  - レートリミット制御、リトライ、トークンキャッシュ

- DuckDB スキーマ（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義・初期化
  - インデックス定義
  - init_schema / get_connection

- ETL パイプライン（data.pipeline）
  - 差分更新ロジック（最終取得日 + backfill）
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 品質チェック呼び出し（quality モジュールを利用）
  - ETL 結果を ETLResult で返却（取得数・保存数・品質問題・エラー等）

- 品質チェック（data.quality）
  - 欠損データ検出（OHLC 欠損）
  - スパイク検出（前日比閾値、デフォルト 50%）
  - 重複チェック（主キー重複）
  - 日付不整合（未来日付、非営業日のデータ）
  - run_all_checks でまとめて実行

- 監査ログ（data.audit）
  - signal_events / order_requests / executions テーブル
  - 冪等キー（order_request_id）、UTC タイムスタンプ、インデックス
  - init_audit_schema / init_audit_db

---

## 必要条件（Requirements）

- Python 3.9+
- パッケージ依存（主に）
  - duckdb
- 標準ライブラリ：urllib、json、logging、datetime 等は標準で使用

実際のプロジェクトでは requirements.txt / pyproject.toml に依存を明記してください。

---

## 環境変数（推奨設定例）

必須（少なくとも以下は設定してください）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（execution 連携で使用）
- SLACK_BOT_TOKEN: Slack 通知用トークン（任意機能用）
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意（デフォルトが設定されているもの）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

データベースパス（デフォルト）:
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db

.env の例（.env.example を参考に作成してください）:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意: パッケージは起点ファイル位置からプロジェクトルート（.git または pyproject.toml）を探し、.env / .env.local を自動ロードします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## セットアップ手順（Setup）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2. 依存パッケージをインストール
   - pip install duckdb
   - （プロジェクト配布形式に合わせて pip install -e . や pip install -r requirements.txt）

3. 環境変数の準備
   - プロジェクトルートに .env（または .env.local）を配置して必要な環境変数を設定

4. DuckDB スキーマの初期化（Python REPL またはスクリプト）
   - 例:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

5. 監査ログ DB 初期化（任意）
   - 例:
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（Usage）

以下は典型的な利用例です。実行は Python スクリプトか REPL で行います。

- DuckDB スキーマ初期化
  - Python:
    from kabusys.data import schema
    conn = schema.init_schema("data/kabusys.duckdb")

- J-Quants の id_token を取得（明示的に）
  - Python:
    from kabusys.data import jquants_client as jq
    id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用

- 単発のデータ取得（例：ある銘柄の日足を取得）
  - Python:
    records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))

- 取得データを DuckDB に保存
  - Python:
    saved = jq.save_daily_quotes(conn, records)

- 日次 ETL を実行（推奨：スケジューラから毎日実行）
  - Python:
    from kabusys.data import pipeline
    result = pipeline.run_daily_etl(conn)
    print(result.to_dict())

  run_daily_etl は内部で:
    1) 市場カレンダーを先読み（デフォルト 90 日先）
    2) 株価日足の差分取得（最終取得日から backfill_days デフォルト 3 日で再取得）
    3) 財務データの差分取得
    4) 品質チェック（run_quality_checks=True）

  戻り値は ETLResult。quality で検出された問題やエラーは result.quality_issues / result.errors に格納されます。

- 品質チェックを個別実行
  - Python:
    from kabusys.data import quality
    issues = quality.run_all_checks(conn, target_date=date.today(), spike_threshold=0.5)
    for i in issues:
        print(i)

- 監査ログテーブルを初期化（既存スキーマに追加）
  - Python:
    from kabusys.data import audit
    audit.init_audit_schema(conn)  # conn は schema.init_schema が返した接続でも可

- 自動 .env 読み込みを無効化
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてプロセスを起動

補足（設計上の注意）
- J-Quants のレート制限（120 req/min）を守るためモジュール内でレートリミット制御されています。
- HTTP エラー（408/429/5xx）に対する再試行（最大 3 回、指数バックオフ）を行います。
- 401 エラーを受けた場合は id_token を自動リフレッシュして 1 回再試行します。
- データ保存は ON CONFLICT DO UPDATE により冪等です。

---

## ディレクトリ構成（Directory structure）

プロジェクト内の主要ファイル群（提供されたコードベースに基づく）:

- src/
  - kabusys/
    - __init__.py                 # パッケージ定義（__version__ = "0.1.0"）
    - config.py                   # 環境変数 / 設定管理（.env 自動読み込み等）
    - data/
      - __init__.py
      - jquants_client.py         # J-Quants API クライアント (fetch / save / auth / rate limit)
      - schema.py                 # DuckDB スキーマ定義と初期化
      - pipeline.py               # ETL パイプライン（run_daily_etl 等）
      - audit.py                  # 監査ログ（signal/order_request/execution）
      - quality.py                # データ品質チェック
    - strategy/
      - __init__.py               # 戦略関連（実装箇所）
    - execution/
      - __init__.py               # 発注実行関連（実装箇所）
    - monitoring/
      - __init__.py               # 監視関連（実装箇所）

注: strategy / execution / monitoring の具象実装は骨組みが用意されており、個別戦略・ブローカー連携ロジックを実装して拡張します。

---

## 開発メモ / 運用上の注意

- DuckDB のファイルパスはデフォルトで data/kabusys.duckdb。バックアップや権限管理に注意してください。
- 全ての TIMESTAMP は基本的に UTC 扱い（audit.init_audit_schema は SET TimeZone='UTC' を実行）。
- ETL の品質チェックは Fail-Fast ではなく全問題を収集するため、検出結果に応じて外側で停止/通知判断をしてください。
- 本ライブラリは J-Quants / kabu / Slack 等の外部システムとの連携を前提としているため、実運用時は資格情報の管理を厳格に行ってください。

---

必要に応じて README を拡張して、具体的な CLI / systemd / Airflow スケジュール例、テスト手順、CI 設定なども追加できます。追加で欲しいセクションがあれば教えてください。