# KabuSys

日本株自動売買プラットフォーム用のライブラリ群（ミニマム実装）。
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、
および監査ログ（発注→約定トレース）用のユーティリティが含まれます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム向けに設計されたライブラリセットです。主な目的は以下です。

- J-Quants API からの市場データ（株価日足、四半期財務、マーケットカレンダー）取得と DuckDB への保存
- RSS からのニュース収集と記事の前処理・銘柄紐付け
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダーの管理（営業日判定・前後営業日検索）
- 監査ログスキーマ（シグナル→発注要求→約定のトレース可能化）
- 設定管理（.env 自動読み込み、環境変数経由の設定）

設計上のポイント：
- J-Quants API のレート制限（120 req/min）に沿ったスロットリング
- リトライ（指数バックオフ、最大3回）と 401 発生時の自動トークンリフレッシュ
- DuckDB への保存は冪等（ON CONFLICT を利用）
- ニュース収集での SSRF / XML Bomb / メモリ DoS 対策

---

## 主な機能一覧

- data/jquants_client.py
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_daily_quotes(), save_financial_statements(), save_market_calendar()
  - レートリミット制御・リトライ・トークン自動リフレッシュ
- data/schema.py
  - init_schema(db_path) — DuckDB スキーマ（Raw / Processed / Feature / Execution）の初期化
  - get_connection(db_path)
- data/pipeline.py
  - run_daily_etl(...) — 日次 ETL（calendar → prices → financials → 品質チェック）
  - run_prices_etl(), run_financials_etl(), run_calendar_etl()
- data/news_collector.py
  - fetch_rss(), save_raw_news(), save_news_symbols(), run_news_collection()
  - URL 正規化、トラッキングパラメータ除去、記事ID生成（SHA-256）、SSRF 対策、gzip サイズチェック
- data/calendar_management.py
  - is_trading_day(), next_trading_day(), prev_trading_day(), get_trading_days(), calendar_update_job()
- data/quality.py
  - 欠損データ / スパイク / 重複 / 日付不整合 のチェックと run_all_checks()
- data/audit.py
  - 監査用スキーマ初期化（signal_events / order_requests / executions）と init_audit_db()
- 設定管理: config.py
  - .env 自動読み込み（プロジェクトルート検出）と Settings オブジェクト経由での取得

その他: strategy/、execution/、monitoring/ 用のパッケージプレースホルダ（拡張用）。

---

## セットアップ手順

前提: Python 3.8+（コードは型ヒントに Python 3.10 以降の記法を用いるため、3.10+ を推奨）

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   - 例:
     ```
     git clone <repo-url>
     cd <repo>
     pip install -e .
     ```

2. 依存パッケージ（代表例）
   - duckdb
   - defusedxml
   - （依存関係は setup.py/pyproject.toml に記載されている想定）
   - 例:
     ```
     pip install duckdb defusedxml
     ```

3. 環境変数 / .env の設定
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時等）。
   - 必須の環境変数（config.Settings を参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション等の API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャネル ID（必須）
   - 任意 / デフォルト付き:
     - KABUSYS_ENV — {development, paper_trading, live}（default: development）
     - LOG_LEVEL — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（default: INFO）
     - KABU_API_BASE_URL — kabu API の base URL（default: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（モニタリング）パス（default: data/monitoring.db）

   - .env 例（簡易）
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. DuckDB スキーマ初期化
   - データベースファイルの親ディレクトリがなければ自動作成されます。
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```

5. 監査ログ用 DB 初期化（必要なら）
   - 例:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（簡易ガイド）

以下は典型的なワークフロー例です。実運用ではジョブスケジューラ（cron / systemd timer / Airflow 等）と組み合わせます。

1. 日次 ETL を実行して市場データを更新する
   ```python
   from kabusys.data.schema import init_schema, get_connection
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")  # 初回は init_schema を使う
   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

   - run_daily_etl は以下を順に実行します:
     1. マーケットカレンダー更新（先読み）
     2. 株価日足の差分取得（最終日から backfill 日数分を再取得）
     3. 財務データの差分取得
     4. 品質チェック（オプションで無効化可）

2. ニュース収集ジョブ
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.news_collector import run_news_collection

   conn = init_schema("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット（例）
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   ```

   - fetch_rss は RSS の取得時に SSRF 検査、gzip サイズ上限チェック（10MB）、
     XML の安全パースを行います。記事IDは正規化 URL の SHA-256 先頭32文字。

3. カレンダー夜間更新（calendar_update_job）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.calendar_management import calendar_update_job

   conn = init_schema("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"saved: {saved}")
   ```

4. J-Quants の ID トークンを直接取得（テスト時）
   ```python
   from kabusys.data.jquants_client import get_id_token
   token = get_id_token()
   print(token)
   ```

注意点・運用上のヒント:
- J-Quants へのリクエストはモジュール内の RateLimiter によって 120 req/min を順守するよう制御されます。
- HTTPError の 401 を受けた場合はリフレッシュトークンから自動で id_token を再取得して一度だけリトライします。
- ETL はできるだけ冪等に設計されています（ON CONFLICT DO UPDATE / DO NOTHING を使用）。
- テスト時に環境変数自動読み込みを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成 (主要ファイル)

（パッケージルート: src/kabusys）

- __init__.py
- config.py — 環境変数 / 設定管理（Settings）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 + 保存）
  - schema.py — DuckDB スキーマ定義 & init_schema, get_connection
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - news_collector.py — RSS 取得 / 前処理 / DB 保存
  - calendar_management.py — 市場カレンダー補助・ジョブ
  - quality.py — データ品質チェック
  - audit.py — 監査ログスキーマ・初期化
- strategy/
  - __init__.py — 戦略コード格納用（拡張ポイント）
- execution/
  - __init__.py — 発注実行ロジック用（拡張ポイント）
- monitoring/
  - __init__.py — モニタリング用（拡張ポイント）

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants リフレッシュトークン）
- KABU_API_PASSWORD — 必須（kabuステーション API パスワード）
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN — 必須（Slack 通知が必要な場合）
- SLACK_CHANNEL_ID — 必須（Slack 通知が必要な場合）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — development / paper_trading / live（default: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（default: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env ロードを無効化

config.Settings はこれらをプロパティとして公開しています。必須変数が未設定の場合は例外が発生します（ValueError）。

---

## 実装上の注意（開発者向け）

- DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を関数に注入する設計になっており、テストの際は ":memory:" でインメモリ DB を使えます。
- news_collector は defusedxml を使い XML 攻撃を防ぎ、HTTP リダイレクト時にプライベートアドレスへの遷移を防ぐためのカスタムリダイレクトハンドラを使用します。
- quality.run_all_checks はエラー・警告のリストを返すだけで ETL の挙動を強制停止しません（呼び出し側で運用判断をしてください）。
- audit.init_audit_schema はタイムゾーンを UTC に設定します（SET TimeZone='UTC'）。

---

## ライセンス / 貢献

（この README にライセンスや貢献ルールを追記してください。リポジトリに LICENSE があればその内容に従ってください）

---

必要であれば、利用例や CLI、Airflow / systemd 用のジョブ定義の雛形、.env.example の具体的なテンプレートを追加します。どの部分を優先して追記しましょうか？