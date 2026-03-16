# KabuSys

日本株向けの自動売買プラットフォーム向けコンポーネント群です。  
データ収集（J-Quants）・ETL・データ品質チェック・DuckDB スキーマ定義・監査ログ（発注→約定のトレーサビリティ）など、データプラットフォーム側の主要機能を提供します。

主な設計方針:
- Look‑ahead bias を防ぐため、取得時刻（UTC）を記録
- API レート制限・リトライに対応（J-Quants クライアント）
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- ETL は差分更新・バックフィル対応、品質チェックは全件収集型

---

## 機能一覧

- 環境変数・設定管理
  - `.env` / `.env.local` の自動読み込み（プロジェクトルート検出）
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN）
  - 実行環境フラグ（development / paper_trading / live）とログレベル検証

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX 市場カレンダー取得
  - レート制限（120 req/min）制御
  - 再試行（指数バックオフ, 指定ステータスでリトライ）
  - 401 時の自動トークンリフレッシュ（1 回のみ）
  - ページネーション対応

- DuckDB スキーマ
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義、外部キーを考慮した作成順序
  - 監査ログ用テーブル（signal_events / order_requests / executions）

- ETL パイプライン
  - 日次 ETL の実装（カレンダー→株価→財務→品質チェック）
  - 差分更新・バックフィル（デフォルト 3 日）
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- データ品質チェック
  - 欠損データ（OHLC）の検出（重大: error）
  - 主キー重複の検出（重大: error）
  - スパイク検出（前日比、デフォルト閾値 50%）（警告: warning）
  - 将来日・非営業日データ検出

- 監査・トレーサビリティ
  - 発生から約定まで UUID 連鎖で追跡可能なテーブル群
  - 発注要求は冪等キー（order_request_id）をサポート
  - すべての TIMESTAMP を UTC で保存（init_audit_schema は TimeZone を UTC に設定）

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の | union を利用）
- duckdb を利用するためビルド可能な環境（通常 pip install で十分）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 最低依存: duckdb
     - pip install duckdb
   - （プロジェクトに応じて requests 等の追加パッケージが必要になる可能性があります）

4. 環境変数を準備
   - プロジェクトルートに `.env`（または `.env.local`）を配置すると自動読み込みされます。
   - 自動ロードを無効化する場合は、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 必須環境変数（.env の例）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C...
   - （オプション）
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

---

## 使い方（簡易ガイド）

以下は Python インタプリタやスクリプトから使うサンプルです。

- DuckDB スキーマ初期化（全テーブル作成）
  - from kabusys.data import schema
  - conn = schema.init_schema("data/kabusys.duckdb")

- 監査ログテーブルの初期化（既存接続に追加）
  - from kabusys.data import audit
  - audit.init_audit_schema(conn)

- J-Quants の ID トークン取得（任意）
  - from kabusys.data.jquants_client import get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を使用して取得

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
  - from kabusys.data import pipeline, schema
  - conn = schema.init_schema("data/kabusys.duckdb")
  - result = pipeline.run_daily_etl(conn)
  - print(result.to_dict())  # ETLResult の要約を取得

- 個別 ETL ジョブ（例: 株価のみ）
  - from datetime import date
  - fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())

- データ品質チェックを個別実行
  - from kabusys.data import quality
  - issues = quality.run_all_checks(conn, target_date=date.today())
  - for i in issues: print(i)

運用上のヒント:
- ETL はスケジューラ（cron / Airflow / Prefect 等）で毎営業日実行する想定です。
- run_daily_etl はカレンダーを先読みするため、営業日判定を行ったうえで株価・財務を取得します。
- ETLResult.has_errors / has_quality_errors を見て運用判断を行ってください。
- J-Quants API に対するリクエストは内部でレート制限とリトライを処理します。大量取得やバッチ取得の際は注意してください。

---

## 主要モジュールの説明（抜粋）

- kabusys.config
  - .env 自動読み込み（.git または pyproject.toml を基準にプロジェクトルートを検出）
  - Settings クラスで各種環境変数をプロパティとして提供
  - KABUSYS_ENV の妥当性チェック（development, paper_trading, live）

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - 内部: _RateLimiter、_request（リトライ・401 リフレッシュ対応）

- kabusys.data.schema
  - init_schema(db_path) で全テーブル / インデックスを作成
  - get_connection(db_path) で接続取得（スキーマ初期化は行わない）

- kabusys.data.pipeline
  - run_daily_etl：一連の差分 ETL と品質チェックを実行
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別ジョブ

- kabusys.data.quality
  - データ品質チェック群（欠損・重複・スパイク・日付不整合）
  - QualityIssue データクラスで問題を集約して返す

- kabusys.data.audit
  - 監査ログ用テーブルの初期化（order_requests は冪等キーをサポート）
  - init_audit_schema / init_audit_db を提供

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/           (発注・約定ロジック用のパッケージ)
      - __init__.py
    - strategy/            (戦略実装用のパッケージ)
      - __init__.py
    - monitoring/          (監視用モジュール)
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py   (J-Quants API クライアント)
      - pipeline.py        (ETL パイプライン)
      - schema.py          (DuckDB スキーマ定義・初期化)
      - audit.py           (監査ログ初期化)
      - quality.py         (データ品質チェック)

補足:
- デフォルトの DuckDB ファイルパス: data/kabusys.duckdb（Settings.duckdb_path）
- 監視用 SQLite ファイルパス: data/monitoring.db（Settings.sqlite_path）
- パッケージは src/layout を採用しています。インストール時は通常の Python パッケージ手順に従ってください。

---

## 注意事項 / 運用上のポイント

- 環境変数の自動ロードはプロジェクトルート検出に依存します。ユニットテストなどで自動ロードを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のテーブルは CREATE IF NOT EXISTS を利用して冪等に作成します。初回だけ init_schema を実行してください。
- J-Quants API はレート制限と HTTP エラーへの対処が組み込まれていますが、運用で大量リクエストを行う場合はさらに調整が必要です。
- 監査ログは削除しない前提（FK は ON DELETE RESTRICT）。データの永続性を重視します。
- 本リポジトリはデータレイヤー中心の実装を提供します。実際の発注（ブローカ接続）や戦略ロジックは execution / strategy 以下で実装してください。

---

必要であれば、README にサンプルの .env.example、cron 設定例、Airflow や Prefect と組み合わせた運用例、さらに CI 設定などの追加を作成します。どの情報を追記しますか？