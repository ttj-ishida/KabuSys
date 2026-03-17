# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ

---

## プロジェクト概要

KabuSys は日本株の自動売買やデータパイプラインを支援する Python ライブラリです。  
J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する ETL、RSS からのニュース収集、データ品質チェック、監査ログ用スキーマなどを備え、戦略層・実行層と連携できるデータ基盤を提供します。

設計上の特徴:
- J-Quants API のレート制御（120 req/min）・リトライ・トークン自動リフレッシュ対応
- DuckDB を利用した冪等的なデータ保存（ON CONFLICT / トランザクション）
- RSS ニュース収集時の SSRF・XML 攻撃対策、トラッキングパラメータ除去、記事IDのハッシュ化
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 発注・約定の監査ログスキーマ（トレーサビリティ）

---

## 主な機能一覧

- J-Quants クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レートリミット・リトライ・トークン更新・fetched_at による取得時刻記録

- ETL パイプライン
  - 差分取得（既存データの最終日からの差分）
  - backfill による後出し修正吸収
  - 市場カレンダー先読み
  - 品質チェックとの統合（日次 ETL 実行関数）

- ニュース収集
  - RSS フィード取得・前処理（URL除去・空白正規化）
  - 記事ID を正規化URLの SHA-256 先頭で生成（冪等性）
  - SSRF 対策、Gzip サイズ制限、defusedxml による安全な XML パース
  - raw_news / news_symbols への保存（チャンク・トランザクション）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 監査ログ（signal_events, order_requests, executions）用スキーマ初期化

- 品質チェック
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合の検出
  - QualityIssue オブジェクトで問題を集約

---

## 必要条件

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml

（パッケージはプロジェクト側で requirements.txt / pyproject.toml を用意してください。ここでは最低限の依存を列挙しています。）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # またはプロジェクトの requirements.txt / pyproject.toml を使う
   ```

3. 環境変数の設定
   - プロジェクトルートの `.env`（および `.env.local`）を利用可能。パッケージは自動で .env を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN -- J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD -- kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN -- Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID -- Slack チャンネル ID（必須）
   - オプション:
     - KABUS_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxx
     KABU_API_PASSWORD=yyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ初期化
   - Python スクリプトまたは REPL で実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ（audit）テーブルを追加する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```

---

## 使い方（基本例）

以下はライブラリをプログラムから利用する簡単な例です。

1. 日次 ETL を実行する
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. ニュース収集ジョブを実行する
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "6501"}  # 例: 有効な銘柄コード集合
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)  # {source_name: saved_count, ...}
   ```

3. J-Quants の ID トークンを直接取得する
   ```python
   from kabusys.data.jquants_client import get_id_token
   token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を参照
   print(token)
   ```

4. 個別 API 呼び出し（株価取得・保存）
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,31))
   saved = save_daily_quotes(conn, records)
   print("保存件数:", saved)
   ```

注意: 各関数は DuckDB 接続オブジェクトを受け取ります。init_schema はテーブル作成を行い接続を返すため、初回は init_schema を使うのが安全です。

---

## 主要 API / モジュール概要

- kabusys.config
  - settings: 環境変数を読み取り、プロパティでアクセス（例: settings.jquants_refresh_token）
  - 自動 .env ロード機構（プロジェクトルートの .env / .env.local）

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
  - 内部的にレート制御・リトライ・トークン自動更新を実装

- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - run_daily_etl: 一括 ETL 実行（品質チェック統合）

- kabusys.data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
  - RSS の安全な取得（SSRF 検査、gzipサイズ制限、defusedxml）

- kabusys.data.schema / audit
  - init_schema(db_path), get_connection(db_path)
  - init_audit_schema(conn), init_audit_db(db_path)

- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks

---

## ディレクトリ構成

（この README はコードベースのサンプルから生成しています。実際のリポジトリでは pyproject.toml / setup 等が存在する場合があります。）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主要なファイルの役割:
- config.py: 環境変数・設定の読み込みと検証
- data/: データ取得・保存・ETL・品質チェック・スキーマ管理・ニュース収集
- strategy/, execution/, monitoring/: 戦略・発注・監視に関する拡張ポイント（骨組み）

---

## 運用上の注意 / ベストプラクティス

- 環境変数は `.env` / `.env.local` に置き、機密情報は安全に管理する（CI / secrets）。
- DuckDB ファイルはバックアップを取り、複数プロセスから同時に書き込む際は注意する（排他制御）。
- J-Quants のレートリミットやリトライの設計はあるが、実運用ではさらに上位のスロットリングやモニタリングを導入する。
- ニュース収集は外部 RSS に依存するため、ソースごとの失敗をログに残しつつ継続する設計になっています。
- ETL 実行ログや品質チェック結果は運用監視（Slack など）へ通知すると良い。

---

## 付録: よく使う環境変数一覧

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略可, default: data/kabusys.duckdb)
- SQLITE_PATH (省略可, default: data/monitoring.db)
- KABUSYS_ENV (development/paper_trading/live)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 をセットすると自動 .env ロードを無効化)

---

必要があれば README に含めるサンプルスクリプトや、CI 用のジョブ定義（例: 日次 ETL の cron / workflow）を追加します。どの項目を詳しく載せたいか教えてください。