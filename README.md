# KabuSys

日本株向けの自動売買システム向けユーティリティ群（ライブラリ）。  
J-Quants API からの市場データ取得、DuckDB スキーマ定義・初期化、ETL パイプライン、データ品質チェック、監査ログなどの基盤機能を提供します。

---

## 概要

KabuSys は日本株自動売買プラットフォームの基盤モジュール群です。主に次の役割を持ちます。

- J-Quants API からの株価（OHLCV）・財務データ・マーケットカレンダーの取得
- DuckDB を用いたデータベーススキーマ（Raw / Processed / Feature / Execution / Audit）の定義・初期化
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合など）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計上の特徴:
- J-Quants API のレート制限・リトライ・トークン自動リフレッシュに対応
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で二重投入を防止
- ETL は差分更新・バックフィル対応で後出し修正を吸収
- 品質チェックは全件収集し、呼び出し元で重大度に応じた対応が可能

---

## 機能一覧

- config
  - .env / 環境変数の読み込み（自動ロード、プロジェクトルート検出）
  - 設定値ラッパ（必須キーの検査、環境判定など）
- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ保存する save_* 関数（raw_prices, raw_financials, market_calendar）
  - レートリミッタ、リトライ、401 時のトークン自動リフレッシュ、fetched_at の記録
- data.schema
  - DuckDB の全スキーマ定義と初期化（init_schema）
  - get_connection（既存 DB へ接続）
- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 差分更新・バックフィルのロジック
- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks（全チェック実行、QualityIssue を返す）
- data.audit
  - 監査ログ用テーブルの初期化（init_audit_schema / init_audit_db）
  - シグナル / 発注要求 / 約定のトレーサビリティ設計
- monitoring, strategy, execution
  - パッケージ構造を用意（実装は別途追加）

---

## 必要条件

- Python 3.10+
  - （ソースで型注釈に `|` を使用しているため）
- パッケージ依存
  - duckdb
  - 標準ライブラリの urllib, json, datetime 等を使用

インストール例:
```
python -m pip install duckdb
```

（プロジェクト配布時は pyproject.toml / requirements.txt にまとめてください）

---

## セットアップ手順

1. リポジトリを取得
   - git clone など

2. Python 環境を準備
   - Python 3.10 以上を用意
   - 仮想環境を作ることを推奨

3. 依存パッケージをインストール
   - 最低限 duckdb をインストールしてください:
     ```
     pip install duckdb
     ```

4. 環境変数の設定 (.env)
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` / `.env.local` を置くと、自動で読み込まれます。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途）。
   - 必須環境変数（Settings で _require() されるもの）:
     - JQUANTS_REFRESH_TOKEN … J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD … kabuステーション API パスワード
     - SLACK_BOT_TOKEN … Slack 通知等を使う場合の Bot トークン
     - SLACK_CHANNEL_ID … Slack チャンネル ID
   - 任意・デフォルト:
     - KABUSYS_ENV … development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL … DEBUG/INFO/...（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD … 自動 .env 読み込みを無効にする（1 で無効）
     - DUCKDB_PATH … デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH … デフォルト `data/monitoring.db`

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマの初期化
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成され、テーブルが初期化される
     ```
   - 監査テーブルを追加する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```

---

## 使い方 (基本例)

- 日次 ETL の実行（最も一般的な使い方）:
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（既に初期化済みなら何もしない）
  conn = init_schema(settings.duckdb_path)

  # 日次 ETL を実行（target_date を省略すると今日を基準に実行）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 個別に J-Quants から取得して保存する:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
  saved = save_daily_quotes(conn, records)
  ```

- 品質チェックだけを実行:
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注意点:
- jquants_client はレート制限（120 req/min）・リトライ・401 トークン自動リフレッシュに対応しています。
- save_* 関数は冪等（ON CONFLICT DO UPDATE）で重複を避けます。
- ETL の差分ロジックは DB の最終取得日を基準に自動算出されます。必要なら引数で date_from 等を明示できます。

---

## 主要ファイル / ディレクトリ構成

プロジェクトの主要ソース構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント、保存関数
    - schema.py                 # DuckDB スキーマ定義・初期化
    - pipeline.py               # ETL パイプライン（差分取得、保存、品質チェック）
    - quality.py                # データ品質チェック
    - audit.py                  # 監査ログテーブル初期化
    - pipeline.py
  - strategy/
    - __init__.py               # 戦略関連（拡張用）
  - execution/
    - __init__.py               # 発注 / 約定関連（拡張用）
  - monitoring/
    - __init__.py               # 監視/アラート関連（拡張用）

README に記載の通り、スキーマは下記レイヤーを持ちます:
- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- Audit（監査）: signal_events, order_requests, executions

---

## 設定・動作に関する補足

- 自動 .env 読み込み:
  - パッケージインポート時にプロジェクトルート（.git or pyproject.toml があるディレクトリ）を起点に `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 既存 OS 環境変数は保護され、.env で上書きされません。`.env.local` は override=True で上書きを許します（ただし OS 環境変数は保護対象）。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

- Settings API:
  - settings.jquants_refresh_token（必須）
  - settings.kabu_api_password（必須）
  - settings.kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
  - settings.slack_bot_token（必須）
  - settings.slack_channel_id（必須）
  - settings.duckdb_path（デフォルト: data/kabusys.duckdb）
  - settings.sqlite_path（デフォルト: data/monitoring.db）
  - settings.env（development / paper_trading / live）
  - settings.log_level（DEBUG/INFO/...）

- ログ & エラーハンドリング:
  - ETL は個々のステップで失敗しても他のステップは継続します（呼び出し側は ETLResult の errors / quality_issues を参照して判断してください）。
  - data.quality のチェックは fail-fast ではなく全件収集します。重大度(error/warning)に応じて運用側でアクションしてください。

---

## トラブルシューティング

- ValueError: 環境変数が未設定と出る場合:
  - 必須の環境変数（JQUANTS_REFRESH_TOKEN 等）が設定されているか確認してください。
- DuckDB ファイル作成エラー:
  - `DUCKDB_PATH` の親ディレクトリが作成できない場合があります。init_schema は親ディレクトリを自動作成しますが、パーミッション等を確認してください。
- API レスポンスで 401 が返る:
  - jquants_client は 401 でトークンリフレッシュを試みますが、リフレッシュが失敗する場合は `get_id_token` の引数や環境変数を再確認してください。
- テスト実行時に .env の自動ロードを無効にしたい:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してからインポートしてください。

---

もし README に追記してほしい点（例: 実際の CI/CD 実行例、cron / Airflow での運用例、Slack 通知の実装テンプレートなど）があれば教えてください。