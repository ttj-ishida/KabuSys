# KabuSys

日本株向け自動売買基盤のコアライブラリ（モジュール群）です。データ取得・ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ（トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つ Python モジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する（差分取得・バックフィル対応）。
- RSS フィードからニュース記事を収集して DuckDB に保存し、銘柄コードと紐付ける。
- データ品質チェック（欠損・スパイク・重複・日付不整合）を実行する。
- マーケットカレンダーを管理し、営業日判定や前後営業日の取得を行う。
- 監査用テーブル群（シグナル、発注要求、約定ログ）を初期化・管理する。
- 環境変数ベースの設定管理（.env 自動読み込み機能を含む）。

設計上の方針として、API レート制限順守、冪等性（ON CONFLICT）、リトライや指数バックオフ、SSRF対策、XML の安全パースなどを重視しています。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可）
  - 必須値チェック / 環境別フラグ（development / paper_trading / live）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足、財務（四半期 BS/PL）、マーケットカレンダー取得
  - レートリミット制御（120 req/min）、リトライ、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存関数（save_*）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック、バックフィル、品質チェック（quality モジュール）
  - 日次 ETL 実行エントリ（run_daily_etl）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理・記事ID生成（SHA-256 ベース）、SSRF 対策、gzip 制限
  - raw_news / news_symbols への冪等保存

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、期間内の営業日列挙
  - 夜間バッチ更新ジョブ（calendar_update_job）

- スキーマ管理（kabusys.data.schema）
  - DuckDB のスキーマ初期化（Raw / Processed / Feature / Execution レイヤ）
  - init_schema, get_connection

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions など監査用テーブルの初期化
  - init_audit_schema / init_audit_db

- 品質チェック（kabusys.data.quality）
  - 欠損データ、重複、スパイク、日付不整合を検出するチェック群
  - run_all_checks でまとめて実行

---

## セットアップ手順

前提: Python 3.9+（コードは typing | None の書き方を使っているため 3.10 でも動く想定）および duckdb パッケージ等が必要です。

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -e .         （プロジェクトの setup/pyproject があることを前提）
   - 必要なライブラリの例:
     - duckdb
     - defusedxml
     - （その他 logging 等の標準ライブラリは不要）

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に .env / .env.local を置くと自動で読み込まれます（起動時）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   サンプル（.env）
   - JQUANTS_REFRESH_TOKEN=＜your_refresh_token＞
   - KABU_API_PASSWORD=＜kabu_password＞
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 任意（デフォルト）
   - SLACK_BOT_TOKEN=＜slack_token＞
   - SLACK_CHANNEL_ID=＜slack_channel＞
   - DUCKDB_PATH=data/kabusys.duckdb   # 任意（デフォルト）
   - SQLITE_PATH=data/monitoring.db     # 任意（デフォルト）
   - KABUSYS_ENV=development|paper_trading|live   # 有効値: development, paper_trading, live
   - LOG_LEVEL=INFO|DEBUG|WARNING|ERROR|CRITICAL

   注意: Settings は必須項目を _require() でチェックします（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID など）。不足時は ValueError を送出します。

5. データベース（DuckDB）スキーマ初期化
   - Python REPL / スクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")   # デフォルトパスと一致

6. 監査テーブルの初期化（任意）
   - from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

---

## 使い方（代表的な呼び出し例）

以下は簡単な利用例です。実行前に .env 等を用意しておいてください。

- DuckDB スキーマ初期化
  - Python スクリプト:
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
  - from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- ニュース収集ジョブ（RSS から収集して保存）
  - from kabusys.data.schema import init_schema
    from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    conn = init_schema("data/kabusys.duckdb")
    # known_codes: 抽出に使う有効な銘柄コード集合（例: prices テーブルや別途用意）
    known_codes = {"7203", "6758"}  # 任意
    results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
    print(results)

- カレンダー夜間更新ジョブ
  - from kabusys.data.schema import init_schema
    from kabusys.data.calendar_management import calendar_update_job
    conn = init_schema("data/kabusys.duckdb")
    saved = calendar_update_job(conn)
    print("saved:", saved)

- J-Quants の ID トークン取得（テスト等）
  - from kabusys.data.jquants_client import get_id_token
    token = get_id_token()   # settings.jquants_refresh_token を使用

- 品質チェックを個別に実行
  - from kabusys.data.schema import init_schema
    from kabusys.data.quality import run_all_checks
    conn = init_schema("data/kabusys.duckdb")
    issues = run_all_checks(conn)
    for i in issues:
        print(i)

注意:
- ETL 系は例外を内部で捕捉して続行する設計ですが、呼び出し側は戻り値（ETLResult）や出力ログで状態を判断してください。
- ネットワーク呼び出しや API レート制限の影響で実行に時間を要することがあります。

---

## 環境変数（主要）

必須（アプリケーションの基本動作に必要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack Bot Token（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

任意 / デフォルトあり
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用途の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

自動 .env 読み込みの挙動
- 起動時にプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）から `.env` → `.env.local` の順で読み込みます。
- OS 環境変数が優先され、.env.local は既存の OS 環境変数を上書きしません（ただし内部的に protected 処理あり）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

主要ファイル・モジュール（リポジトリの一例: src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py                         - 環境変数・設定管理
  - execution/                         - 発注/実行関連（パッケージ placeholder）
    - __init__.py
  - strategy/                          - 戦略関連（パッケージ placeholder）
    - __init__.py
  - monitoring/                        - 監視関連（パッケージ placeholder）
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py                - J-Quants API クライアント（取得・保存）
    - news_collector.py                - RSS ニュース収集・保存・銘柄抽出
    - schema.py                        - DuckDB スキーマ定義・初期化
    - pipeline.py                      - ETL パイプライン（run_daily_etl 等）
    - calendar_management.py           - マーケットカレンダー管理
    - audit.py                         - 監査ログ（signal/order/execution）定義・初期化
    - quality.py                       - データ品質チェック

各モジュールはコメントに設計方針・利用方法が明記されています。DuckDB のテーブル定義は data/schema.py にまとめられており、Raw / Processed / Feature / Execution といったレイヤ構造が反映されています。

---

## 開発上の注意点 / 備考

- DuckDB へは SQL のパラメータバインドを使っており、SQL インジェクションのリスクを低減していますが、実際の運用では DB のバックアップやロールバック方針を検討してください。
- NewsCollector は外部 RSS を取得するため SSRF 対策・応答サイズ制限（MAX_RESPONSE_BYTES）・defusedxml による安全パース等、セキュリティ・堅牢性に配慮しています。
- J-Quants API のレート制限やレスポンスの仕様変更に備えて、例外処理とログ監視を行ってください。
- 本 README はコードベースの実装に基づく説明です。実際の利用時は pyproject.toml / setup.py / CI 設定等のリポジトリ付随ファイルに従ってください。

---

必要であれば、導入手順の具体的なスクリプト化（systemd タイマー / cron / Airflow / GitHub Actions などでの定期実行例）や、.env.example のテンプレート、より詳細な使用例（ニュース抽出に使う known_codes の取り方、監査ログの参照方法）を追加で作成します。どちらが必要か教えてください。