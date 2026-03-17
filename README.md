# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買プラットフォームのコアライブラリ群です。データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、監査ログ（発注→約定トレーサビリティ）、マーケットカレンダー管理などの基盤機能を提供します。

主な設計方針：
- データの冪等性（ON CONFLICT / DO UPDATE / DO NOTHING）を重視
- API レートリミット遵守、リトライ、トークン自動リフレッシュ
- Look-ahead bias を防ぐための fetched_at トレーサビリティ
- SSRF / XML Bomb 等のセキュリティ対策（news_collector）
- DuckDB を主たる永続ストアとして利用

---

## 機能一覧

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN 等）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダー取得
  - レートリミット制御、リトライ、トークン自動リフレッシュ
  - DuckDB への安全な保存（冪等性）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日から未取得分のみ取得）
  - バックフィル機能（後出し修正の吸収）
  - 品質チェックの実行（quality モジュール）
  - 日次 ETL エントリ run_daily_etl
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日検索、夜間カレンダー更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS 収集、URL 正規化、トラッキングパラメータ除去、記事ID生成（SHA-256）
  - SSRF 保護、レスポンスサイズ制限、XML セーフパース
  - raw_news / news_symbols テーブルへの冪等保存
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合チェック
  - QualityIssue を返却して呼び出し側で判断可能
- 監査ログ（kabusys.data.audit）
  - signal → order_request → execution のトレーサビリティ用テーブル
  - 監査用スキーマの初期化関数
- スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema / get_connection を提供

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに | 記法を使用）
- Git がインストールされていること

1. リポジトリをクローン
   - git clone <リポジトリURL>
   - cd <project>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 推奨依存例（本プロジェクトで明示的に使われる主要パッケージ）
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   ※ 実際の requirements.txt / pyproject.toml がある場合はそれに従ってください。

4. 環境変数 (.env) を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須項目（Settings にて必須とされているもの）
     - JQUANTS_REFRESH_TOKEN=xxxxxxxx
     - KABU_API_PASSWORD=xxxx
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C0123456789
   - 任意 / デフォルト
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
     - LOG_LEVEL=INFO
     - DUCKDB_PATH=data/kabusys.duckdb  （デフォルト）
     - SQLITE_PATH=data/monitoring.db

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXXXXXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（クイックスタート）

以下は Python REPL あるいはスクリプトから実行する例です。

- 基本設定読み込み
  - 自動で .env / .env.local を読み込みます。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 設定は kabusys.config.settings から取得可能:
    ```python
    from kabusys.config import settings
    print(settings.duckdb_path)  # Path オブジェクト
    ```

- DuckDB スキーマの初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # デフォルトのファイルパスを使用
  ```

  - インメモリ DB を使う場合:
    conn = init_schema(":memory:")

- 監査ログスキーマの初期化（監査用テーブルを追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  # conn は init_schema で得た接続
  init_audit_schema(conn, transactional=True)
  ```
  または専用 DB として初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- J-Quants の id_token を取得（手動）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を参照して POST で取得
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェックをまとめて実行）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト
  print(result.to_dict())
  ```

  - 引数で target_date, id_token, backfill_days 等を指定できます。

- 市場カレンダーの夜間更新ジョブ（個別）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  ```

- ニュース収集（RSS を取得し raw_news に保存）
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes: 銘柄抽出用の有効な4桁コードセット（例: {"7203","6758",...}）
  stats = run_news_collection(conn, known_codes=set_of_codes)
  print(stats)  # {source_name: saved_count, ...}
  ```

- データ品質チェックを個別実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

- 低レベル API（必要なとき）
  - jq.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - jq.save_daily_quotes / save_financial_statements / save_market_calendar

---

## 主要アーキテクチャ / 注意点

- .env 自動ロード
  - プロジェクトルートは .git または pyproject.toml により検出されます（__file__ ベースの探索）。見つからない場合は自動ロードをスキップします。
  - ロード順: OS 環境変数 > .env.local > .env
  - テストで自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

- J-Quants クライアント
  - レート制限: 120 req/min を固定間隔スロットリングで遵守
  - リトライ: 指数バックオフ（最大 3 回）、408/429/5xx を再試行
  - 401 受信時は自動でトークンをリフレッシュし 1 回だけ再試行

- ニュース収集安全対策
  - defusedxml による XML パース
  - レスポンスサイズ上限（デフォルト 10 MB）
  - URL 正規化・トラッキングパラメータ除去
  - SSRF 対策（スキーム検証、リダイレクト先のホストがプライベートIPでないことを検査）

- DuckDB スキーマは冪等に作成されます（CREATE TABLE IF NOT EXISTS / ON CONFLICT を多用）

---

## ディレクトリ構成

以下は主要ファイル・モジュールの一覧（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数・設定管理
  - execution/                     -- 発注・取引関連の拡張モジュール（空 init）
  - strategy/                      -- 戦略モジュール（空 init）
  - monitoring/                    -- 監視モジュール（空 init）
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（取得・保存）
    - news_collector.py            -- RSS ニュース収集・保存
    - schema.py                    -- DuckDB スキーマ定義・初期化
    - pipeline.py                  -- ETL パイプライン（差分更新・日次ETL）
    - calendar_management.py       -- マーケットカレンダー管理
    - audit.py                     -- 監査ログ（トレーサビリティ）初期化
    - quality.py                   -- データ品質チェック

---

## 開発 / テストのヒント

- settings から環境を判断できます（settings.is_dev / is_paper / is_live）。
- ログレベルは LOG_LEVEL 環境変数で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- テスト時に .env の自動読み込みを止めたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB をインメモリで使えば副作用を避けやすくなります（":memory:"）。

---

## ライセンス・貢献

（この README にはプロジェクト固有のライセンス情報や貢献方法を追記してください）

---

README は以上です。必要であれば、手順のスクリプト化（systemd / cron / Airflow などへの組み込み例）や具体的な requirements.txt や pyproject.toml の雛形も作成できます。どの情報を優先して追加しますか？