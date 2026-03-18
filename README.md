# KabuSys

KabuSys は日本株の自動売買インフラ向けに設計された Python ライブラリ群です。  
J-Quants / RSS 等からのデータ収集、DuckDB ベースのデータスキーマ、ETL パイプライン、品質チェック、ニュース収集、監査ログ用スキーマなどを提供します。

バージョン: 0.1.0

---

## 概要

主な目的は「データプラットフォーム」と「取引フローの監査性」を備えた自動売買システムの基盤提供です。  
以下を想定したモジュール群を含みます。

- J-Quants API 経由での株価・財務・マーケットカレンダーの取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- RSS からのニュース収集と銘柄コード抽出（SSRF や XML ボム対策、トラッキングパラメータ除去）
- DuckDB によるスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal -> order_request -> execution までのトレース可能なスキーマ）

設計上のポイント:
- J-Quants API のレート制限 (120 req/min) とリトライを考慮
- データの冪等性（INSERT ... ON CONFLICT）を重視
- セキュリティ対策（SSRF、XML 関連の脆弱性対策、受信サイズ制限 等）
- すべての TIMESTAMP は UTC として扱うことを意図

---

## 機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンから id_token を取得）
  - save_* 系関数で DuckDB へ冪等保存
  - レートリミッタ、指数バックオフ、401 時の自動トークンリフレッシュなどの堅牢性機能

- data.news_collector
  - RSS フィードの取得・前処理（URL 除去・空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF / private host の防止、gzip 解凍上限チェック、defusedxml による XML 対策
  - raw_news へのバルク保存、news_symbols への銘柄紐付け

- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema(db_path) でテーブルとインデックスを作成

- data.pipeline
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の一括 ETL
  - run_prices_etl / run_financials_etl / run_calendar_etl の差分更新処理
  - 差分／バックフィル／品質チェックに対応

- data.calendar_management
  - 営業日判定 / 次営業日/前営業日/期間の営業日取得
  - calendar_update_job: カレンダーの夜間差分更新ジョブ

- data.quality
  - 欠損、スパイク（前日比閾値）、重複、日付不整合の検出
  - QualityIssue による検出結果

- data.audit
  - 監査用スキーマ（signal_events, order_requests, executions）
  - init_audit_schema / init_audit_db による初期化（UTC 固定）

- 設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルートは .git または pyproject.toml を起点）
  - 必須環境変数の取得ラッパー（不足時は ValueError）
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に | を使っているため）
- Git、またはプロジェクトルートに pyproject.toml が存在する構成を想定

1. 仮想環境の作成と有効化（例: venv）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows (PowerShell): .venv\Scripts\Activate.ps1

2. 依存パッケージのインストール
   - 必須パッケージ（例）
     - duckdb
     - defusedxml
   - インストール例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt が無ければ上記を手動でインストールしてください）

3. パッケージの開発インストール（任意）
   - プロジェクトルートに setup.py / pyproject.toml があれば:
     - pip install -e .

4. 環境変数の設定
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID
   - オプション:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化

   - サンプル .env:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb

   - 自動ロードについて:
     - kabusys.config はプロジェクトルート（.git または pyproject.toml を探索）を見つけると、.env → .env.local の順で自動ロードします。
     - テストや CI で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（簡単な例）

以下は代表的な操作例です。各スクリプトは Python コードから直接呼び出せます。

- DuckDB スキーマ初期化
  - Python REPL やスクリプトで:
    from kabusys.config import settings
    from kabusys.data.schema import init_schema
    conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行
  - run_daily_etl を使って市場カレンダー、株価、財務を差分取得し品質チェックまで実行:
    from kabusys.config import settings
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema(settings.duckdb_path)
    result = run_daily_etl(conn)
    print(result.to_dict())

- ニュース収集ジョブ
  - RSS フィード群からニュース収集、raw_news 保存、銘柄紐付け:
    from kabusys.config import settings
    from kabusys.data.schema import init_schema
    from kabusys.data.news_collector import run_news_collection
    conn = init_schema(settings.duckdb_path)
    known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
    res = run_news_collection(conn, known_codes=known_codes)
    print(res)  # {source_name: 新規保存レコード数}

- J-Quants API 呼び出し（直接）
  - ID トークン取得とデータ取得:
    from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
    token = get_id_token()  # settings.jquants_refresh_token を使う
    records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- 監査スキーマ初期化（audit 用 DB）
    from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")

ログ出力やエラーハンドリングは関数内で行われます。run_daily_etl の戻り値（ETLResult）から処理状況・品質チェック結果を確認してください。

---

## よく使う API と注意点

- jquants_client._request は内部で
  - 固定間隔のレートリミッタ（120 req/min 相当）
  - 指数バックオフ（最大 3 回）
  - 401 を受けた場合は id_token を一度だけ自動リフレッシュして再試行
 などを行います。

- NewsCollector は SSFP / private host を防ぐ仕組み、max レスポンスサイズ（10MB）や gzip 解凍後のサイズチェックを持ちます。

- DuckDB への保存関数は基本的に冪等（ON CONFLICT 指定）になっているため、同じデータを再投入しても重複せず最新化されます。

- 環境変数の値が不足すると Settings のプロパティ（例: settings.jquants_refresh_token）が ValueError を送出します。CI/運用時は .env や環境変数を正しく設定してください。

---

## ディレクトリ構成

主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得/保存）
    - news_collector.py      -- RSS ニュース収集・前処理・保存
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - schema.py              -- DuckDB スキーマ定義・初期化
    - calendar_management.py -- 市場カレンダー管理（営業日判定等）
    - audit.py               -- 監査ログ（signal/order_request/execution）スキーマ
    - quality.py             -- データ品質チェック
  - strategy/
    - __init__.py            -- 戦略関連モジュール（拡張ポイント）
  - execution/
    - __init__.py            -- 発注/執行関連（拡張ポイント）
  - monitoring/
    - __init__.py            -- 監視・メトリクス（将来的な拡張）

その他:
- .env, .env.local           -- （プロジェクトルートに置く）環境変数
- data/                      -- デフォルトの DB 格納フォルダ（設定次第で変更可）

---

## 開発上の注意 / 拡張ポイント

- strategy / execution / monitoring パッケージは拡張ポイントとして空の __init__ を提供しています。実際のアルゴリズム・ブローカー接続はここに追加してください。
- DuckDB のスキーマは将来的に変更される可能性があるため、マイグレーション戦略を検討してください。
- production では KABUSYS_ENV=live、適切なログ出力（INFO→DEBUG の切り替え）と中央ログ収集を行ってください。
- 外部 API の資格情報（refresh token, broker password 等）は安全に保管し、公開リポジトリに含めないでください。

---

必要であれば、README に CI 用手順（例: GitHub Actions での ETL 定期実行）、運用時の DB バックアップ方針、Slack 通知の例などを追加します。どの情報がさらに欲しいか教えてください。