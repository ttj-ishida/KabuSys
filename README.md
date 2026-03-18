# KabuSys

日本株自動売買 / データプラットフォーム用ライブラリ。  
J-Quants や RSS 等から市場データ・ニュースを収集し、DuckDB に蓄積、品質チェック・ETL・監査ログ機能を備えています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python モジュール群です。

- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを取得して DuckDB に保存する
- RSS などからニュース記事を収集し、記事 → 銘柄の紐付けを行う
- データ品質チェック（欠損、スパイク、重複、日付不整合）を DuckDB 上で実行する
- ETL パイプライン（差分更新、バックフィル、カレンダー先読み）を提供する
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマを提供する
- レート制限・リトライ・SSRF 対策など現実運用を意識した実装が施されています

設計の特徴：
- レート制限（J-Quants: 120 req/min）に従う RateLimiter
- リトライ（指数バックオフ、特定ステータスで再試行）とトークン自動リフレッシュ
- DuckDB に対する冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）
- RSS のパースで defusedxml、SSRF 防止、サイズ制限など安全対策

---

## 機能一覧

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（fetch_daily_quotes / save_daily_quotes）
  - 財務データ（fetch_financial_statements / save_financial_statements）
  - マーケットカレンダー（fetch_market_calendar / save_market_calendar）
  - 認証トークン取得・自動リフレッシュ（get_id_token）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（fetch_rss）
  - 記事の前処理（URL 除去・空白正規化）
  - raw_news / news_symbols の冪等保存
  - 記事IDは正規化 URL の SHA-256 先頭32文字
  - SSRF / XML 攻撃 / Gzip bomb / 大容量レスポンス対策
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のDDLを定義
  - init_schema() による初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）
  - 差分更新・バックフィル・カレンダー先読み
  - ETL 実行結果を ETLResult で返却（品質問題やエラーを含む）
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、期間内営業日列挙
  - カレンダーの夜間更新ジョブ（calendar_update_job）
- 品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク、重複、日付不整合の検出
  - run_all_checks で総合実行
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events, order_requests, executions 等の監査テーブル
  - init_audit_schema / init_audit_db による初期化
- 設定管理（kabusys.config）
  - .env（プロジェクトルート）自動読み込み（無効化可）
  - Settings クラスで環境変数を型付きプロパティで取得

---

## セットアップ手順

前提
- Python 3.10 以上（type union 表記 (A | B) を使用しているため）
- Git リポジトリ内にプロジェクトルートを置く（.env 自動読み込みに使用）

1. リポジトリをクローンして仮想環境を作成

   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール

   以下は最低限の依存例です（プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）。

   ```
   pip install duckdb defusedxml
   ```

   他に標準ライブラリ外のパッケージがある場合は同様にインストールしてください。

3. 環境変数 (.env) を用意

   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（デフォルト、OS環境変数が優先され .env.local は上書き）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例: .env（最低限必要な値）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須（Settings クラスの _require により未設定時はエラー）
   - KABUSYS_ENV は development / paper_trading / live のいずれか
   - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL

4. データベース初期化

   Python REPL やスクリプトで DuckDB スキーマを初期化します。デフォルトの DB パスは settings.duckdb_path（例: data/kabusys.duckdb）です。

   例:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # 初期化済みの DuckDB 接続を取得
   ```

   監査ログ専用 DB を作る場合:
   ```python
   from kabusys.data.audit import init_audit_db
   conn_audit = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方

以下は代表的な利用例です。実装はライブラリとして呼び出す前提です。

1. 日次 ETL を実行（市場カレンダー・株価・財務の差分更新 + 品質チェック）

   ```python
   from datetime import date
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema(settings.duckdb_path)
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

   - run_daily_etl は ETLResult を返します。result.has_errors / has_quality_errors で要注意状態を判定できます。

2. ニュース収集ジョブ実行（RSS → raw_news 保存、銘柄紐付け）

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = init_schema(settings.duckdb_path)
   known_codes = {"7203", "6758", "9432"}  # 事前に用意した有効銘柄セット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)  # {source_name: saved_count, ...}
   ```

3. カレンダー更新ジョブ（夜間バッチ向け）

   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print("saved:", saved)
   ```

4. 品質チェックを単体で実行

   ```python
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn)
   for i in issues:
       print(i.check_name, i.severity, i.detail)
   ```

5. J-Quants クライアントを直接利用（認証・ページネーション対応）

   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
   token = get_id_token()  # settings を参照してリフレッシュトークンから取得
   records = fetch_daily_quotes(id_token=token, date_from=date(2024, 1, 1), date_to=date(2024, 3, 31))
   ```

ログレベルは環境変数 `LOG_LEVEL` で制御します（例: LOG_LEVEL=DEBUG）。

---

## 設定（主な環境変数）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabu API パスワード
- KABU_API_BASE_URL (任意): kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意): development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意): DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動読み込みを無効化

設定は kabusys.config.Settings から参照できます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成

リポジトリ（要点のみ）

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（取得・保存）
      - news_collector.py      # RSS ニュース収集・保存・銘柄抽出
      - schema.py              # DuckDB スキーマ定義・初期化
      - pipeline.py            # ETL パイプライン（差分更新・日次ETL）
      - calendar_management.py # カレンダー管理（営業日判定、更新ジョブ）
      - audit.py               # 監査ログスキーマ（signal/order/execution）
      - quality.py             # データ品質チェック
    - strategy/                # 空のパッケージ（戦略ロジック配置想定）
    - execution/               # 空のパッケージ（発注実装置き場）
    - monitoring/              # 空のパッケージ（監視・メトリクス）
- .env.example (想定)          # 実運用では .env.example を参照して .env を作成

各モジュールは単体でも利用可能で、ETL や収集ジョブはアプリケーション側でスケジューラ（cron / Airflow / Prefect 等）から呼び出す想定です。

---

## 注意事項 / 運用上のヒント

- J-Quants の API レートや認証トークンの制約を守ること（ライブラリは制御を入れているが、運用方針も重要）。
- DuckDB ファイルは共有ロック周りの制約があるため、複数プロセスからの同時書き込みには注意してください。
- ニュース収集は外部 URL にアクセスするため SSRF、gzip bomb、XML 攻撃を想定した防御を行っていますが、ソース追加時は信頼できるフィードを利用してください。
- 品質チェックで重大なエラーが検出された場合は ETL の結果を自動停止させるかどうかは運用決定に任せています（run_all_checks は検出だけ行います）。
- テストや CI では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動ロードを無効化できます。

---

## 開発 / 貢献

- 新機能やバグ修正はモジュールごとにユニットテストを追加してください（DuckDB の :memory: を使うと高速にテスト可能）。
- 外部 API 呼び出しはモック化してテストすること（例: kabusys.data.jquants_client._request や news_collector._urlopen のモック）。
- セキュリティやパフォーマンスに関わる変更（SQL、リダイレクト処理、外部通信）は慎重にレビューしてください。

---

必要に応じて README に含めるチュートリアルやより詳細な設定例（kabuステーション連携、Slack通知、ジョブスケジューラ統合）を追加します。どの部分を深掘りしますか？