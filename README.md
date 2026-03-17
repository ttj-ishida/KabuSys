# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
J‑Quants API や RSS ニュースを取得して DuckDB に蓄積し、ETL（差分更新）、データ品質チェック、マーケットカレンダー管理、ニュース収集、監査ログ（発注→約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

主な目的は以下です。

- J‑Quants API から株価（OHLCV）、財務データ、JPX のマーケットカレンダーを安全に取得して保存する。
- RSS フィードからニュース記事を収集して記事と銘柄コードを紐付ける。
- DuckDB を用いた三層（Raw / Processed / Feature）スキーマを提供し、ETL パイプライン・品質チェックを行う。
- 監査ログ（signal → order_request → executions）を別途保存し、発注から約定までを UUID 連鎖でトレース可能にする。
- レート制御、リトライ、トークン自動リフレッシュ、SSRF 対策、XML の安全なパースなど安全設計を重視。

設計上のポイント：

- J‑Quants のレート制限（120 req/min）を厳守するためのレートリミッタあり
- 取得時刻（fetched_at）を UTC で記録して Look‑ahead Bias を低減
- DuckDB へは冪等（ON CONFLICT DO UPDATE / DO NOTHING）で保存
- RSS の取得では SSRF・Gzip bomb・XML Bomb などに対する対策を実装

---

## 機能一覧

- 環境変数管理（.env の自動読み込み、必須値チェック）
- J‑Quants API クライアント
  - 株価日足（fetch_daily_quotes / save_daily_quotes）
  - 財務データ（fetch_financial_statements / save_financial_statements）
  - マーケットカレンダー（fetch_market_calendar / save_market_calendar）
  - id_token 自動リフレッシュとリトライ/指数バックオフ
- DuckDB スキーマ定義・初期化（data.schema.init_schema）
- ETL パイプライン（差分更新、バックフィル、品質チェック） run_daily_etl
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集（RSS 取得、正規化、記事保存、銘柄抽出・紐付け）
- マーケットカレンダー管理（営業日判定・次・前営業日取得・夜間更新ジョブ）
- 監査ログの初期化（監査用スキーマ、init_audit_db）
- 監視 / 実行 / 戦略用の空のパッケージプレースホルダ（strategy, execution, monitoring）

---

## セットアップ手順

前提:
- Python 3.10 以上（型記法に | を使用しているため）
- Git クローン済みのプロジェクトルート（.git または pyproject.toml が存在することを想定）

1. 仮想環境を作成・有効化（推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. 必要パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを使ってください）
   - 開発中にパッケージを編集しながら使う場合:
     ```
     pip install -e .
     ```
     （パッケージ配布設定がある場合）

3. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API パスワード
     - SLACK_BOT_TOKEN: Slack ボットトークン（通知用）
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）

   - 簡単な .env サンプル:
     ```
     JQUANTS_REFRESH_TOKEN="your_refresh_token"
     KABU_API_PASSWORD="your_kabu_password"
     SLACK_BOT_TOKEN="xoxb-..."
     SLACK_CHANNEL_ID="C01234567"
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

---

## 使い方（主要 API の例）

以下は Python スクリプト / REPL から使う簡単な例です。

1. DuckDB スキーマを初期化して接続を取得する
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成・初期化
   ```

2. 日次 ETL（市場カレンダー・株価・財務・品質チェック）を実行する
   ```python
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)  # target_date を指定しなければ今日を基準に実行
   print(result.to_dict())
   ```

3. ニュース収集ジョブを実行する
   ```python
   from kabusys.data.news_collector import run_news_collection

   known_codes = {"7203", "6758", "9984"}  # 抽出対象の有効銘柄コードセット（任意）
   res = run_news_collection(conn, known_codes=known_codes)
   print(res)  # {source_name: saved_count, ...}
   ```

4. 監査ログ用 DB を初期化する（監査テーブルを別 DB に分ける場合）
   ```python
   from kabusys.data.audit import init_audit_db

   audit_conn = init_audit_db("data/audit.duckdb")
   ```

5. J‑Quants データを直接取得する（必要であれば id_token を注入）
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

   token = get_id_token()  # settings.jquants_refresh_token を使って ID トークンを取得
   recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
   ```

注意点:

- run_daily_etl や各 ETL 関数は内部で例外ハンドリングを行い、可能な限り処理を継続します。戻り値（ETLResult）で品質問題や発生したエラーの概要を確認してください。
- news_collector は RSS の XML を安全にパースするため defusedxml を利用しています。

---

## 環境変数（settings の説明）

KabuSys の設定は環境変数（または .env ファイル）から読み込まれます。主要なキー:

- JQUANTS_REFRESH_TOKEN (必須) — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用するボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用途）のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動読み込みを無効化

settings オブジェクトは kabusys.config.settings から参照できます。

---

## 主要モジュール・関数（抜粋）

- kabusys.config
  - settings: 設定アクセス
  - .env 自動読み込み（プロジェクトルートから .env / .env.local）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

- kabusys.data.audit
  - init_audit_db(db_path)
  - init_audit_schema(conn, transactional=False)

---

## ディレクトリ構成

（リポジトリの src 配下を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/                # 発注実装・ブローカー連携用（プレースホルダ）
      - __init__.py
    - strategy/                 # 戦略実装用（プレースホルダ）
      - __init__.py
    - monitoring/               # 監視・メトリクス（プレースホルダ）
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py       # J‑Quants API クライアント（取得・保存ロジック）
      - news_collector.py       # RSS ニュース収集・保存・銘柄抽出
      - schema.py               # DuckDB スキーマ定義・初期化
      - pipeline.py             # ETL パイプライン（差分更新・品質チェック）
      - calendar_management.py  # マーケットカレンダー管理（営業日判定等）
      - audit.py                # 監査ログ（signal/order_request/executions）
      - quality.py              # 品質チェック（欠損・スパイク・重複・日付不整合）
- pyproject.toml (ある場合、自動的にプロジェクトルートが検出され .env を読み込む際に使われます)

---

## 注意事項 / 運用メモ

- J‑Quants API のレートリミット（120 req/min）を遵守していますが、実行環境で過度に並列リクエストを行うと制限にかかる可能性があります。並列化は注意してください。
- データ保存は冪等（ON CONFLICT）を採用していますが、スキーマ変更や外部からの改変があると問題が生じる可能性があるため、DB 管理には注意してください。
- news_collector は外部の RSS を取得するため、SSRF や大量レスポンス対策を実装しています。テスト時は _urlopen のモックが可能です。
- run_daily_etl は品質チェックで検出された問題を報告しますが、呼び出し側でどのレベルの問題で停止させるかは制御してください（fail-fast にはしていません）。
- production（ライブ）稼働では KABUSYS_ENV=live を設定し、SLACK 等で通知を組み込むと運用管理が容易になります。

---

README に記載のない詳細 API や追加のユーティリティについては、各モジュールのドキュメント文字列（docstring）を参照してください。必要であれば README を拡張して具体的な実運用手順・cron/ジョブ設定例や Slack 通知例を追記します。