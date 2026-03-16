# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータ取得・加工・品質管理・監査を念頭に置いた自動売買システムのコアライブラリです。J-Quants API から市場データや財務データを取得し、DuckDB に格納して、戦略・発注フローに渡すためのスキーマ・ユーティリティ・品質チェック・監査ログ機能を提供します。

主な設計方針:
- Look-ahead bias 防止（取得時刻を UTC の fetched_at として記録）
- API レート制限・リトライ・トークン自動更新対応
- DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）
- 監査ログでシグナル→発注→約定のトレーサビリティを保証
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 機能一覧

- 環境設定読み込みと管理
  - .env / .env.local の自動ロード（必要に応じて無効化可能）
  - 必須環境変数の取得ヘルパー
- J-Quants API クライアント（data/jquants_client.py）
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - ページネーション対応、レートリミット（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - DuckDB への保存（raw_prices / raw_financials / market_calendar）を冪等に実行
- DuckDB スキーマ管理（data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義
  - インデックス定義とスキーマ初期化関数（init_schema, get_connection）
- 監査ログ（data/audit.py）
  - signal_events, order_requests, executions などの監査テーブルを初期化
  - 監査専用 DB 初期化補助（init_audit_schema, init_audit_db）
  - トレーサビリティのための UUID ベース階層（strategy_id → signal_id → order_request_id → broker_order_id）
- データ品質チェック（data/quality.py）
  - 欠損データ検出、スパイク（前日比）検出、重複チェック、日付不整合チェック
  - 複数チェックをまとめて実行する run_all_checks を提供

---

## セットアップ手順（開発・実行環境）

前提:
- Python 3.10 以上を推奨（型ヒントに | を使用）
- duckdb を使用（DuckDB を Python パッケージとして利用）

1. リポジトリをクローン（ローカル開発）
   - git clone … (省略)

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb
   - （プロジェクト内に requirements.txt / pyproject.toml があればそれに従ってください）
   - 開発しながら利用する場合:
     - pip install -e .

4. 環境変数の用意
   - プロジェクトルートに .env または .env.local を作成することで自動ロードされます（デフォルトの読み込み順は OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（ライブラリ内で _require により参照される）環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（API 認証用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 送信先チャンネル ID

任意 / デフォルト値あり:
- KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live")、デフォルトは "development"
- LOG_LEVEL: ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")、デフォルト "INFO"
- KABUSYS_DISABLE_AUTO_ENV_LOAD: auto load 無効化フラグ（1 で無効化）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite の監視 DB パス（デフォルト: data/monitoring.db）

例 (.env)
    JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development

---

## 使い方（主要 API と例）

以下はライブラリを直接インポートして利用する際の簡単な例です。実行前に環境変数を用意してください。

- 設定アクセス
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path などでアクセスできます。
  - settings.is_live / is_paper / is_dev で環境判定ができます。

- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)
  - これにより必要なテーブルとインデックスが作成されます。

- J-Quants からデータ取得と保存
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  - records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
  - conn = get_connection(settings.duckdb_path)  # または init_schema で取得した conn
  - save_daily_quotes(conn, records)

  特徴:
  - API リクエストは 120 req/min に制御されます。
  - 408/429/5xx の場合は指数バックオフで再試行します（最大 3 回）。
  - 401 を受け取るとリフレッシュトークンで id_token を更新し 1 回だけ再試行します。

- 監査ログの初期化
  - from kabusys.data.audit import init_audit_schema, init_audit_db
  - conn = init_schema(settings.duckdb_path)
  - init_audit_schema(conn)
  - または監査専用 DB を作る場合: audit_conn = init_audit_db("data/audit.duckdb")

- データ品質チェック
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2024,1,1))
  - issues は QualityIssue オブジェクトのリスト（check_name, table, severity, detail, rows）で返ります。
  - 呼び出し元は severity に応じて ETL 停止や通知（Slack など）を行ってください。

サンプルスクリプト（概念例）:
    from datetime import date
    from kabusys.config import settings
    from kabusys.data.schema import init_schema
    from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    from kabusys.data.quality import run_all_checks

    conn = init_schema(settings.duckdb_path)
    recs = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
    save_daily_quotes(conn, recs)
    issues = run_all_checks(conn, target_date=date(2023,12,31))
    for i in issues:
        print(i)

---

## 注意事項 / 実装上のポイント

- .env 自動読み込み
  - パッケージは起点ファイルの親ディレクトリを探索し、.git または pyproject.toml を見つけた場所をプロジェクトルートとして .env/.env.local を自動ロードします。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- トークン管理
  - J-Quants の id_token はモジュールレベルでキャッシュされ、ページネーション間で共有されます（get_id_token, _get_cached_token）。
- レート制限 / リトライ
  - _RateLimiter により固定間隔（最小インターバル）でスロットリングします。
  - Retry の挙動は J-Quants API のレスポンスコードに依存し、429 の場合は Retry-After を優先使用します。
- DuckDB への保存は基本的に ON CONFLICT DO UPDATE を使って冪等に実行します。
- 監査テーブルは削除しない方針（ON DELETE RESTRICT）で設計されています。updated_at はアプリ側で更新する必要があります。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py                  (パッケージメタ情報: __version__ = "0.1.0")
  - config.py                    (環境変数・設定管理)
  - data/
    - __init__.py
    - jquants_client.py          (J-Quants API クライアント、保存ロジック)
    - schema.py                  (DuckDB スキーマ定義・初期化)
    - audit.py                   (監査ログスキーマ・初期化)
    - quality.py                 (データ品質チェック)
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

---

## よくある質問（FAQ）

Q: .env のパース方法はどのような仕様ですか？
A: export KEY=val 形式に対応し、引用符内のバックスラッシュエスケープを考慮したパースを行います。行頭の # または 空行は無視されます。引用なしの場合、コメントは '#' の直前が空白またはタブの場合のみコメントとして扱います。

Q: DuckDB の初期化は複数回呼んでも安全ですか？
A: はい。init_schema は CREATE TABLE IF NOT EXISTS を使っており冪等です。既存テーブルがある場合はスキップされます。

Q: J-Quants の API レートはどのように守られますか？
A: モジュール内で _RateLimiter により最小間隔 (60 / 120) 秒のスロットリングを掛けています。複数プロセスでの実行や分散実行時はプロセス間での調停が別途必要です。

---

必要に応じて README を拡張できます（例: CI / テスト手順、デプロイ方法、サンプル ETL ジョブ、Slack 通知フローなど）。追加したい項目があれば教えてください。