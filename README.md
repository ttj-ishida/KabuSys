# KabuSys

日本株の自動売買・データ基盤ライブラリ（簡易README）

本リポジトリは、日本株のデータ取得・品質管理・ETL、監査ログ、実行（発注）連携のための内部ライブラリ群を提供します。J-Quants API を用いたマーケットデータ取得や、DuckDB を用いたローカルDBスキーマの初期化・ETLパイプラインを含みます。

## 特長（概要）
- J-Quants API クライアント（OHLCV / 財務 / JPX カレンダー）を提供
  - API レート制限（120 req/min）を守る RateLimiter 実装
  - リトライ（指数バックオフ）・401 時の自動トークンリフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアスを排除
- DuckDB を用いた3層データスキーマ（Raw / Processed / Feature）と実行・監査テーブル
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 環境変数ベースの設定管理（.env / .env.local 自動読み込み）

## 機能一覧
- data/jquants_client.py
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB への冪等保存）
- data/schema.py
  - init_schema(db_path) / get_connection(db_path)
  - 各層テーブル・インデックスの定義
- data/pipeline.py
  - run_daily_etl（市場カレンダー・株価・財務の差分ETL + 品質チェック）
  - 個別 ETL: run_prices_etl, run_financials_etl, run_calendar_etl
- data/quality.py
  - 欠損、スパイク、重複、日付不整合のチェック（run_all_checks）
- data/audit.py
  - 監査用テーブルの初期化（init_audit_schema / init_audit_db）
- config.py
  - 環境変数から設定を読み込む Settings と自動 .env ロードロジック
- execution / strategy / monitoring の骨組み（将来的な拡張点）

## 前提
- Python 3.10 以上（typing のユニオン型や | を使用）
- duckdb（pip からインストール）
- ネットワークから J-Quants API にアクセス可能

## セットアップ手順（ローカル）
1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 最低限 duckdb が必要です。パッケージ管理に pyproject.toml があればそれに従ってください。
   ```bash
   pip install duckdb
   # 開発時はソースを editable install する場合:
   pip install -e .
   ```

4. 環境変数を用意する
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` と任意で `.env.local` を置くと自動的に読み込まれます。
   - 自動読み込みを無効化したい場合: `export KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
   - 必須環境変数（実行に必要）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

   `.env` の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

## 使い方（簡単なコード例）

- 設定を参照する
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema(settings.duckdb_path)  # ファイル作成とテーブル初期化を行い接続を返す
  ```

  インメモリ DB を使う場合:
  ```python
  conn = init_schema(":memory:")
  ```

- 監査スキーマの初期化（既存接続へ追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  # または別DBとして初期化
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 日次 ETL を実行する（最も一般的なエントリポイント）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 省略時は target_date = today, id_token は内部で取得
  print(result.to_dict())
  if result.has_errors:
      # ログやアラート処理
      print("ETL 中にエラーがあります:", result.errors)
  if result.has_quality_errors:
      print("品質チェックで致命的な問題があります")
  ```

- 低レベル API（必要に応じて）
  ```python
  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # 明示的に取得（通常は pipeline 側で自動的に扱われる）
  records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,3,1))
  saved = jq.save_daily_quotes(conn, records)
  ```

## 主要 API の説明（短縮）
- config.Settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.slack_channel_id
  - settings.duckdb_path / sqlite_path
  - settings.env (development / paper_trading / live), .is_live, .is_paper, .is_dev

- data.schema
  - init_schema(db_path) → DuckDB 接続（テーブルを全て作成）
  - get_connection(db_path) → 既存 DB への接続（初期化は行わない）

- data.jquants_client
  - get_id_token(refresh_token: Optional[str]) → idToken を取得（POST /token/auth_refresh）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar （DuckDB へ ON CONFLICT DO UPDATE で保存）

- data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...) → ETLResult

- data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5) → list[QualityIssue]

## 動作設計に関するポイント
- .env 自動読み込み:
  - 実行時、プロジェクトルート（.git または pyproject.toml を親階層から検索）を基に `.env` と `.env.local` を読み込みます。
  - 読み込み順: OS 環境変数（優先） > .env > .env.local（.env.local は override=True として読み込まれるため最優先）
  - テストや特殊環境で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants クライアント:
  - レート制限: 120 req/min（内部でスロットリング）
  - リトライ: 指数バックオフ、最大3回（408/429/5xx を対象）、401 時は1回トークンをリフレッシュして再試行
  - ページネーション対応: pagination_key による自動ページ取得
  - 取得データは fetched_at（UTC）を付与して保存することで「いつ知り得たか」をトレース可能
- DuckDB スキーマ:
  - Raw / Processed / Feature / Execution / Audit のテーブルを定義
  - init_schema は冪等（既存テーブルはスキップ）
  - audit.init_audit_schema は UTC タイムゾーンをセットして監査テーブルを作成

## ディレクトリ構成（主要ファイル）
プロジェクトの主要なファイル/ディレクトリ構成は次のとおりです（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - schema.py
    - pipeline.py
    - quality.py
    - audit.py
    - (その他: raw / helper モジュール等)
  - strategy/
    - __init__.py
    - (戦略ロジックを置く)
  - execution/
    - __init__.py
    - (発注・ブローカ連携ロジックを置く)
  - monitoring/
    - __init__.py
    - (監視・アラート用ロジックを置く)

（リポジトリルート）
- .env.example (推奨: サンプル env ファイル)
- pyproject.toml / setup.cfg / requirements.txt （存在する場合は依存管理）

## トラブルシューティング
- .env が読み込まれない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
  - プロジェクトルートの検出は .git または pyproject.toml を基に行うため、該当ファイルが存在するか確認
- DuckDB の初期化に失敗:
  - 指定した DUCKDB_PATH の親ディレクトリが作成されますが、権限やパスの誤りに注意
  - インメモリなら ":memory:" を使用
- J-Quants API エラー:
  - 401 が返る場合は JQUANTS_REFRESH_TOKEN の有効性を確認
  - Rate limit に到達している場合はロギングで Retry-After を確認

---

さらに詳しい仕様（DataPlatform.md / DataSchema.md 等）や戦略・実行の実装は、各モジュールのドキュメント・コードコメントを参照してください。質問や補足があれば、どの箇所のドキュメントを詳しく出力するか教えてください。