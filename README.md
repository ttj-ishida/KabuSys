# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、マーケットカレンダー管理、DuckDB スキーマ／監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株アルゴリズム取引のための基盤ライブラリです。主に以下を目的としています。

- J-Quants API から株価・財務・カレンダー等を取得して DuckDB に保存する ETL パイプライン
- RSS からニュース収集して記事を保存・銘柄紐付けするニュースコレクタ
- 市場カレンダー管理（営業日判定、次/前営業日の取得等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレース用スキーマ）
- 環境変数による設定管理（.env の自動読み込み機能あり）

設計上の特徴：
- J-Quants のレート制限を守るレートリミッタ、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
- DuckDB へ冪等的に保存（ON CONFLICT を利用）
- RSS の SSRF 対策 / サイズ上限 / XML 安全パース（defusedxml）
- ETL は差分更新・バックフィルを考慮、品質チェックは全件収集型

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンから ID トークン取得）
  - save_* 系：DuckDB への冪等保存（raw_prices, raw_financials, market_calendar）

- data.news_collector
  - fetch_rss：RSS 取得（SSRF/サイズ/圧縮対応）
  - save_raw_news / save_news_symbols：DuckDB への保存（INSERT ... RETURNING）
  - extract_stock_codes：テキストから銘柄コード抽出（既知コードと照合）
  - run_news_collection：複数ソースの統合収集ジョブ

- data.schema / data.audit
  - DuckDB のスキーマ定義／初期化（Raw / Processed / Feature / Execution / Audit）
  - init_schema, init_audit_schema, init_audit_db 等

- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl：日次 ETL の統合エントリポイント（品質チェック実行可）

- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job：夜間バッチでカレンダー差分更新

- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks：すべての品質チェックを実行して QualityIssue を返す

- config
  - 環境変数管理（.env 自動読み込み、必須チェック、env 切替、ログレベル判定）

---

## セットアップ手順

前提：
- Python 3.9+（コードは型ヒントなどで 3.9+ を想定）
- Git

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 依存パッケージをインストール  
   （requirements.txt がある場合はそれを使ってください。なければ最低限 duckdb, defusedxml をインストール）
   ```bash
   pip install -U pip
   pip install duckdb defusedxml
   # さらに requests やその他のユーティリティが必要なら追加してください
   ```

4. パッケージを開発モードでインストール（任意）
   ```bash
   pip install -e .
   ```

5. 環境変数の設定  
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（デフォルト）。  
   自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（主なもの）：
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN : Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID : 通知先チャンネル ID（必須）

   任意・デフォルト値あり：
   - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV : 実行環境 (development | paper_trading | live)（デフォルト: development）
   - LOG_LEVEL : ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（簡易ガイド）

以下は Python スクリプトから KabuSys を使う基本例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリも作成
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を与えなければ今日
  print(result.to_dict())
  ```

- カレンダーの夜間更新ジョブを実行する
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print(f"saved: {saved}")
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  # known_codes は銘柄抽出に使用するコード集合（例: 4桁コードの set）
  results = run_news_collection(conn, known_codes={"7203","6758"})
  print(results)  # {source_name: saved_count, ...}
  ```

- 監査ログスキーマを初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/kabusys_audit.duckdb")
  ```

- J-Quants トークンを直接取得（テスト/手動）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

注意点：
- J-Quants API は 120 req/min のレート制限があり、jquants_client は内部で制御・リトライ・トークンリフレッシュを行います。
- ETL は差分取得とバックフィル（デフォルト 3 日）を行い、品質チェックを実行できます（run_daily_etl の引数で制御）。

---

## ディレクトリ構成

（抜粋）ソースツリーは以下のようになっています。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得／保存）
    - news_collector.py      — RSS ニュース収集・保存・銘柄紐付け
    - schema.py              — DuckDB スキーマ定義と初期化
    - pipeline.py            — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py — 市場カレンダー管理・ジョブ
    - audit.py               — 監査ログスキーマ初期化
    - quality.py             — データ品質チェック
  - strategy/                 — 戦略関連（空パッケージ）
  - execution/                — 発注／執行関連（空パッケージ）
  - monitoring/               — 監視関連（空パッケージ）

その他:
- pyproject.toml / setup.cfg / requirements.txt 等（リポジトリに合わせて）

---

## 設計に関する重要なポイント（運用メモ）

- 環境変数読み込み:
  - プロジェクトルートを .git または pyproject.toml を手がかりに探索して .env / .env.local を自動で読み込みます。テスト等で自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - .env の読み込みは OS 環境変数を保護するため .env.local が上書き可能、.env は上書き不可（OS 環境 > .env.local > .env の優先度）。

- J-Quants API:
  - レート制限（120 req/min）をモジュールレベルでスロットリングしています。
  - 401 受信時はリフレッシュトークンで自動的に id_token を再取得して 1 回リトライします。
  - 408/429/5xx 系は指数バックオフで最大 3 回リトライします。

- RSS / ニュース:
  - URL 正規化して SHA-256 の先頭 32 文字を記事 ID に使用（UTM 等は除去）。
  - SSRF 対策（スキーム検証、プライベート IP 判定、リダイレクト検査）
  - 受信サイズ上限（既定 10 MB）と gzip 解凍後の上限検査を実施。
  - DB への保存はチャンク分割してトランザクションで実行し、INSERT ... RETURNING を利用して実際に挿入された件数を返す。

- データ品質:
  - 欠損・スパイク・重複・日付不整合をチェック。チェックは全件収集型で、呼び出し元が重大度に応じて処理を判断します。

---

## 貢献・開発

- コードは型注釈を含み、ユニットテストを書くことで信頼性を高めてください。
- 外部 API（J-Quants / kabuステーション / Slack 等）との連携箇所はモック可能に設計されています。ネットワークや証券 API の呼び出しはテスト時に差し替えてください。

---

## 参考

- 環境変数キーやデフォルトパスは src/kabusys/config.py を参照してください。
- DuckDB スキーマ定義は src/kabusys/data/schema.py にまとめられています。
- ニュース処理、カレンダー、ETL、品質チェックの実装はそれぞれのモジュールを参照してください。

---

必要であれば README に以下を追加できます：
- 実行可能な CLI サンプル（cron / systemd の例）
- CI / テストの実行手順
- 依存関係の完全なリスト（requirements.txt）
- 開発向けのデバッグ・ログ設定例

追加してほしい項目があれば教えてください。