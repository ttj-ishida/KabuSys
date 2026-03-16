# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。本リポジトリはデータ取得（J-Quants）、ETL パイプライン、DuckDB ベースのスキーマ、監査ログ、データ品質チェックなどを提供します。戦略・実行・監視モジュールの骨組みも含まれます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたコンポーネント群を持つ小さなフレームワークです。

- J-Quants API からの市場データ（OHLCV、財務情報、JPX カレンダー）取得
- 取得した生データを DuckDB に Idempotent（ON CONFLICT DO UPDATE）で保存
- ETL（差分更新／バックフィル）パイプラインの提供
- データ品質チェック（欠損／重複／スパイク／日付不整合）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）用スキーマ
- 環境変数ベースの設定管理（.env 自動読み込み機能）

設計方針として、API のレート制限やリトライ、トークン自動リフレッシュ、Look‑ahead bias 対策（UTC の fetched_at 保存）、および冪等性を重視しています。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得（不足時は例外）
- J-Quants クライアント
  - ID トークン取得（リフレッシュ）
  - 日次株価（OHLCV）、財務諸表、マーケットカレンダー取得（ページネーション対応）
  - API レート制限（120 req/min）制御、リトライ（指数バックオフ・401 で自動トークン更新）
  - DuckDB に保存するための save_* 関数（冪等）
- DuckDB スキーマ（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 初期化ユーティリティ（init_schema）
- ETL パイプライン（data.pipeline）
  - 日次 ETL（run_daily_etl）によるカレンダー・株価・財務の差分更新と品質チェック
  - 差分取得ロジック（最終取得日からのバックフィル）
- データ品質チェック（data.quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合などの検出
  - QualityIssue オブジェクトで問題を収集
- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等の監査スキーマ
  - init_audit_schema / init_audit_db を提供

---

## 要件

- Python 3.10 以上（型注釈に | 演算子を使用）
- duckdb（DB 操作用）
- （利用する機能に応じて）ネットワークアクセス（J-Quants API）、および必要なサードパーティクライアント（例: Slack 連携等を追加する場合）

必要最低限のインストール例:

pip install duckdb

パッケージとして開発環境で使う場合（リポジトリのルートに setup / pyproject があれば）:

pip install -e .

---

## セットアップ手順

1. Python（推奨 3.10+）をインストールする。

2. 依存ライブラリをインストールする（最低限）:

   pip install duckdb

3. 環境変数を設定する
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成すると、ライブラリ起動時に自動読み込みされます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

   推奨の `.env`（例）:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   # KABU_API_BASE_URL は省略可（デフォルト: http://localhost:18080/kabusapi）
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   必須項目は get でチェックされ、未設定時は ValueError が発生します:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

4. データベース初期化（DuckDB）:

   - 全スキーマ（データプラットフォーム用）を作成する:

     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - 監査ログのみを追加する（既存 conn に対して）:

     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)

---

## 使い方（主要な例）

以下は一般的なワークフローの例です。

- DuckDB スキーマ初期化

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（デフォルトは今日を対象）

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  # ETLResult オブジェクトが返り、保存件数や品質問題・エラーが確認できます
  print(result.to_dict())

- J-Quants の生API呼び出し例

  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

  token = get_id_token()  # settings.jquants_refresh_token を使用
  records = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))

- 品質チェックの単体実行

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)

- 監査スキーマの初期化（専用 DB）

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")

注意点:
- run_daily_etl は内部で market_calendar を先に取得し、取得後に「営業日か」を判定して株価・財務 ETL の対象日を調整します（非営業日は直近の過去営業日に調整）。
- J-Quants API へのリクエストは内部でレート制御・リトライ・トークンリフレッシュを行います。アプリ側でこれらを意識する必要は基本的にありませんが、API 制限は遵守してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 で無効）

.env ファイルはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から自動検出して読み込まれます。

.env のパースはコメント・クォート・export プレフィックス等の一般的な形式に対応します。

---

## ディレクトリ構成

リポジトリ内の主要ファイルとモジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - schema.py              — DuckDB スキーマ定義 & 初期化
    - pipeline.py            — ETL パイプライン（差分更新・品質チェック）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログスキーマ & 初期化
  - strategy/
    - __init__.py            — 戦略モジュール（骨組み）
  - execution/
    - __init__.py            — 発注・ブローカー連携（骨組み）
  - monitoring/
    - __init__.py            — 監視用モジュール（骨組み）

（上記以外にユーティリティや将来的な機能が追加される想定です）

---

## 開発・運用上の注意点

- Python バージョンは 3.10 以上推奨。
- J-Quants API のレート制限（120 req/min）を守るため、クライアントは内部でスロットリングを行います。複数プロセスで同一トークンを使う場合は注意が必要です。
- get_id_token() はリフレッシュトークンから ID トークンを取得し、401 発生時に自動リフレッシュを行います。無限再帰を避けるため内部的に allow_refresh フラグで制御しています。
- DuckDB の初期化は冪等（何度呼んでも安全）です。init_schema() を初回に必ず呼んでください。
- 品質チェックは Fail‑Fast ではなく全件収集を行います。ETL の停止/継続判断は呼び出し元で行ってください。

---

## 参考と拡張

- 戦略（strategy）や発注（execution）、監視（monitoring）モジュールは拡張ポイントです。ここにアルゴリズム実装やブローカーAPIのラッパー、Slack/監視連携を追加してください。
- ロギングや observability の拡張（メトリクス、Prometheus、Sentry など）を統合すると運用が容易になります。

---

必要があれば README に含めるサンプル .env.example、さらに詳しい API 使用例、または CI / デプロイ手順（Docker Compose や Airflow でのスケジューリング例）を追加します。どの情報を優先して追記しますか？