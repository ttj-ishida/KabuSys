# KabuSys

日本株向けの自動売買 / データプラットフォームのコアライブラリ（KabuSys）。  
J-Quants や RSS 等からデータを取得し、DuckDB に蓄積、ETL・品質チェック・監査ログ等の基盤機能を提供します。

## 概要
KabuSys は以下を目的とした内部ライブラリ群です。

- J-Quants API から株価・財務・市場カレンダーを安全かつ冪等に取得・保存
- RSS からニュースを収集し記事と銘柄の紐付けを行うニュースコレクタ
- DuckDB ベースのスキーマ定義・初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- カレンダー管理・営業日判定
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上のポイント:
- API レート制御（J-Quants: 120 req/min）やリトライ（指数バックオフ、401時のトークンリフレッシュ）を実装
- DuckDB への保存は冪等（ON CONFLICT）で安全
- ニュース収集は SSRF 対策・XML 脆弱性対策（defusedxml）・受信サイズ制限あり

---

## 機能一覧
- data/jquants_client.py
  - J-Quants API クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - レートリミット、リトライ、トークン自動リフレッシュを備える
- data/news_collector.py
  - RSS フィード取得、前処理、記事ID生成（正規化URL→SHA-256）
  - SSRF 対策、gzip・最大サイズ制限、XML の安全パース
  - raw_news, news_symbols への冪等保存（チャンク/トランザクション）
  - 銘柄コード抽出ユーティリティ
- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit 用テーブル）
  - init_schema(db_path) による初期化と接続取得
- data/pipeline.py
  - 差分ETL（市場カレンダー → 株価 → 財務 → 品質チェック）の統合入口 run_daily_etl
  - バックフィル、営業日調整、品質チェックとの連携
- data/calendar_management.py
  - market_calendar 管理、営業日判定、next/prev_trading_day、calendar_update_job
- data/quality.py
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（ETL 後に使うことを想定）
- data/audit.py
  - 監査ログスキーマ（signal_events, order_requests, executions）
  - init_audit_schema / init_audit_db（UTC タイムゾーン固定）
- config.py
  - 環境変数の自動読み込み（プロジェクトルートの `.env` / `.env.local`）
  - Settings クラス経由で主要設定にアクセス
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能
- monitoring, strategy, execution パッケージ（エントリポイント、今後実装場所）

---

## セットアップ手順

1. Python 環境準備
   - 推奨: Python 3.8+（型記述を多用しているため新しめ推奨）
   - 仮想環境を作成して有効化する例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # Unix/macOS
     .venv\Scripts\activate     # Windows
     ```

2. 依存パッケージのインストール
   - 必要な主なパッケージ:
     - duckdb
     - defusedxml
   - 例（pip）:
     ```
     pip install duckdb defusedxml
     ```
   - パッケージ化されているプロジェクトであれば:
     ```
     pip install -e .
     ```

3. 環境変数 / .env ファイル
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知に使用（必須）
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - `.env` 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```

4. データベース初期化
   - DuckDB スキーマを初期化する:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```

5. 監査ログ DB（必要な場合）
   - 監査ログ専用 DB を初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（主要ユースケース）

- 日次 ETL（市場データの差分取得と品質チェック）
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  # DB 接続初期化（初回のみ）
  conn = init_schema(settings.duckdb_path)

  # 日次 ETL 実行（戻り値は ETLResult）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- RSS ニュース収集
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  # known_codes は銘柄抽出で使う有効な銘柄コードの集合（例: {"7203", "6758", ...}）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203"]))
  print(results)
  ```

- 個別 API 呼び出し（J-Quants）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  ```

- 品質チェックを単体で実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

ログ・例外:
- 各モジュールは logging を利用します。環境変数 `LOG_LEVEL` によって出力レベルを制御してください。
- ETL や収集処理は部分的な失敗をログに残しつつ可能な限り継続する設計です（呼び出し元で停止判定を行えます）。

---

## ディレクトリ構成

リポジトリの主要ファイル・ディレクトリ（本 README 作成時点）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存）
    - news_collector.py               — RSS ニュース収集・保存・銘柄抽出
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py          — 市場カレンダー管理（営業日判定、更新ジョブ）
    - schema.py                       — DuckDB スキーマ定義・初期化
    - audit.py                        — 監査ログスキーマ（シグナル→発注→約定）
    - quality.py                      — データ品質チェック
  - strategy/
    - __init__.py                     — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                     — 発注実行関連（拡張ポイント）
  - monitoring/
    - __init__.py                     — 監視・メトリクス（拡張ポイント）

---

## 注意事項 / 運用上のヒント
- J-Quants トークンは頻繁に更新される場合があるため、get_id_token の自動リフレッシュとリトライロジックを活用してください。
- ニュースコレクタは外部 URL を扱うため SSRF や大容量レスポンス対策を組み込んでいますが、実運用では収集ソースの監査を推奨します。
- DuckDB のファイルはバックアップや権限管理に注意してください（機密データが含まれる可能性があります）。
- 本ライブラリは ETL ・データ基盤の核を提供します。戦略ロジック、バックテスト、実際の発注接続は別モジュール／サービスとして実装してください。

---

## 開発 / 貢献
- 新機能やバグ修正は pull request でお願いします。
- 単体テストや CI の導入を推奨します（外部 API を叩く箇所はモック化してテストしてください）。
- 環境変数の自動読み込みを無効化してテストを行うには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

必要であれば、README にサンプル .env.example、より詳細な API 使用例、運用手順（Cron／Airflow での ETL スケジュール例）やテーブル定義ドキュメント（DataSchema.md へのリンク）などを追加できます。どの情報を優先して追記しましょうか？