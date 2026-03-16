# KabuSys

日本株向け自動売買 / データプラットフォーム（ライブラリ）  
（簡易説明：J-Quants / kabuステーション 等からデータを取得し、DuckDB に格納、品質チェック・監査ログを備えた ETL / 実行基盤のスケルトン）

---

## プロジェクト概要

KabuSys は日本株のデータ取得・保存・品質検査・監査ログを想定した Python モジュール群です。主な役割は以下の通りです。

- J-Quants API から株価（OHLCV）、財務データ、マーケットカレンダーを取得
- DuckDB に対するスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプラインによる差分更新・バックフィル・品質チェック
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用テーブルの初期化
- 環境変数ベースの設定管理（.env 自動読み込み機構を含む）

設計上の特徴：
- J-Quants API のレート制限（120 req/min）に合わせたスロットリング
- リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ対応
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で安全に上書き
- 品質チェックは Fail-Fast ではなく、問題を全件収集して呼び出し元に返す

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得ラッパー
  - KABUSYS_ENV（development / paper_trading / live）やログレベル検証

- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - レート制御、リトライ、トークンキャッシュを内蔵

- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path)
  - get_connection(db_path)
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス

- ETL パイプライン（kabusys.data.pipeline）
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl(...)：日次 ETL の統合入口（品質チェックオプション付き）
  - 差分取得・バックフィル・品質チェックを行う

- 品質チェック（kabusys.data.quality）
  - 欠損データ検出、スパイク検出、重複検出、日付不整合検出
  - QualityIssue 型で問題を集約して返す

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査用テーブル初期化
  - init_audit_schema(conn) / init_audit_db(db_path)

---

## セットアップ手順

前提：Python（推奨 3.9+）および pip が利用可能であること。

1. リポジトリをクローンして、パッケージとしてインストール（開発時）:
   ```bash
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 依存パッケージ（最低限）:
   - duckdb
   - （標準ライブラリの urllib 等を使用しているため他は最小限）

   例:
   ```bash
   pip install duckdb
   ```

3. 環境変数の設定（.env の作成）  
   プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。必須キーは以下：

   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - SLACK_BOT_TOKEN（必須）
   - SLACK_CHANNEL_ID（必須）

   オプション:
   - KABU_API_BASE_URL（既定: http://localhost:18080/kabusapi）
   - DUCKDB_PATH（既定: data/kabusys.duckdb）
   - SQLITE_PATH（既定: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、既定: development）
   - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、既定: INFO）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_password_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB スキーマ初期化:
   Python からスキーマを初期化します（ファイル DB または ":memory:" が使用可）:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path オブジェクト
   ```

5. 監査ログ専用の初期化（必要なら）:
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   # または別 DB に分ける場合:
   # from kabusys.data.audit import init_audit_db
   # audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方

以下は代表的な利用例です。実運用ではエラーハンドリング・ログ設定などを追加してください。

- 日次 ETL の実行（デフォルトで当日を対象に実行）:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 個別 ETL（株価のみ）:
  ```python
  from kabusys.data.pipeline import run_prices_etl
  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- J-Quants トークン取得（明示的に）:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- 手動で品質チェックのみ実行:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

- ETL の戻り値（ETLResult）:
  - target_date, prices_fetched/saved, financials_fetched/saved, calendar_fetched/saved
  - quality_issues（QualityIssue のリスト）
  - errors（処理中に発生したエラーメッセージ）
  - has_errors / has_quality_errors プロパティで要チェック

注意点（実運用向け）:
- J-Quants API は 120 req/min のレート制限に合わせて内部で間隔を置いています。大量の並列リクエストは避けてください。
- get_id_token は 401 の際に自動リフレッシュし、モジュール内キャッシュを使ってページネーション間でトークンを共有します。
- DuckDB への保存は ON CONFLICT DO UPDATE を利用し冪等性を確保していますが、スキーマが合わない等の場合にはエラーとなるため schema の初期化を忘れずに。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 & 保存）
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（差分更新・品質チェック）
    - audit.py               — 監査ログ（信頼able トレーサビリティ）
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略モジュールのエントリ（今後拡張）
  - execution/
    - __init__.py            — 発注実行モジュールのエントリ（今後拡張）
  - monitoring/
    - __init__.py            — 監視用モジュール（今後拡張）

---

## 実装上の補足 / 注意事項

- .env 自動読み込み:
  - 実装はパッケージのファイル位置を起点に親ディレクトリをさかのぼり、.git または pyproject.toml が見つかったディレクトリをプロジェクトルートとします。
  - 読み込み順は OS 環境変数 > .env.local > .env（.env.local は .env を上書き可能）。
  - テスト等で自動ロードを停止するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- settings の検証:
  - KABUSYS_ENV は "development", "paper_trading", "live" のいずれかでなければ ValueError を送出します。
  - LOG_LEVEL は標準的なログレベル名で検証されます。

- J-Quants client の動作:
  - レート制御（120 req/min）を実施
  - リトライ: 最大 3 回、指数バックオフ、408/429/5xx を対象。429 の場合は Retry-After を優先的に参照。
  - 401 を受けた場合はトークンをリフレッシュして一度だけ再試行（無限再帰防止あり）
  - ページネーション対応。pagination_key を利用して完全取得。

- 品質チェック:
  - 各チェックは全件を収集して QualityIssue のリストとして返すため、呼び出し側で致命度（severity）に応じた対応を行ってください（ETL 停止/通知など）。

---

## 今後の拡張案（参考）

- strategy / execution / monitoring モジュールの実装（注文送信ロジック・約定フィードの取り込み・Slack 通知等）
- 標準的なロギング設定テンプレートの提供
- CI / テスト用のモック J-Quants サーバや fixture の整備
- Web UI / ダッシュボード連携（ポートフォリオ監視）

---

以上。必要であれば README に含める追加の利用例、.env.example のテンプレート、あるいはデプロイ手順（systemd / cron / Airflow など）を追記します。どの情報を優先して補足しますか？