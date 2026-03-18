# KabuSys

日本株向けの自動売買基盤ライブラリ（モジュール群）です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、DuckDBスキーマ定義、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

## プロジェクト概要
- 目的: 日本株の自動売買システムに必要なデータ基盤と補助機能を提供すること。
- 主な技術:
  - J-Quants API による市場データ取得（株価・財務・カレンダー）
  - DuckDB を用いたオンディスク／インメモリのデータ保存とスキーマ
  - RSS からのニュース収集と銘柄抽出
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - 発注・約定の監査ログ（監査テーブル群）
- 設計上の配慮:
  - API レート制御（J-Quants: 120 req/min）
  - 冪等性（ON CONFLICT を利用した保存）
  - 再試行（指数バックオフ、401 時のトークン自動リフレッシュ）
  - セキュリティ対策（RSS の SSRF 防止、defusedxml を利用した XML パース保護）
  - 監査可能性（UTC タイムスタンプ、UUID ベースのトレーサビリティ）

## 機能一覧
- data/
  - jquants_client: J-Quants API クライアント（株価・財務・カレンダー取得、DuckDB 保存関数）
    - レートリミッタ・リトライ・トークン自動リフレッシュを実装
  - pipeline: 日次ETL（差分取得、バックフィル、品質チェック）
  - schema: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - news_collector: RSS 取得、前処理、記事の冪等保存、銘柄コード抽出
  - calendar_management: 営業日判定や夜間カレンダー更新ジョブ
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 発注〜約定の監査ログ用スキーマ（order_requests / executions 等）
- strategy/: 戦略層のための名前空間（将来的な実装箇所）
- execution/: 発注実行層のための名前空間（将来的な実装箇所）
- monitoring/: 監視・アラート関連の名前空間（将来的な実装箇所）
- config.py: 環境変数から各種設定を読み込み、Settings を提供
  - .env / .env.local 自動ロード（プロジェクトルート検出: .git または pyproject.toml）
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

## 必要条件（概略）
- Python 3.9+（型注釈に Path | None などを用いているため）  
- 依存ライブラリ（少なくともプロジェクト機能を使う場合）:
  - duckdb
  - defusedxml
  - （標準ライブラリ: urllib, json, logging, datetime, gzip, hashlib, ipaddress, socket 等）
- J-Quants のリフレッシュトークン、kabu API パスワードなど外部サービスの資格情報

## 環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV: 環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視 DB 用の SQLite パス。デフォルト: data/monitoring.db

.env の自動ロード:
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` と `.env.local` を自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - .env.local は .env を上書き可能（override）
- 自動ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

## セットアップ手順
1. リポジトリをクローン
   - 例: git clone <repo_url>
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ配布用の setup/pyproject があれば pip install -e . など）
4. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成し、必須変数を記載
   - 例:
     - JQUANTS_REFRESH_TOKEN=xxxx
     - KABU_API_PASSWORD=xxxx
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - これにより必要テーブルとインデックスが作成されます
6. 監査ログ用スキーマの初期化（必要に応じて）
   - from kabusys.data.audit import init_audit_schema, init_audit_db
   - init_audit_schema(conn)  # 既存 conn に追加
   - または init_audit_db("data/kabusys_audit.duckdb") で専用 DB を作成

## 使い方（基本例）
- 日次 ETL を実行する（プログラム的に）
  - 例:
    - from kabusys.data.schema import init_schema, get_connection
    - from kabusys.data.pipeline import run_daily_etl
    - conn = init_schema("data/kabusys.duckdb")  # 存在しなければ作成
    - result = run_daily_etl(conn)
    - print(result.to_dict())
  - オプション:
    - run_daily_etl(..., target_date=..., run_quality_checks=True, backfill_days=3, spike_threshold=0.5)

- ニュース収集ジョブを実行する
  - from kabusys.data.news_collector import run_news_collection
  - conn = init_schema("data/kabusys.duckdb")
  - known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット（抽出に利用）
  - results = run_news_collection(conn, known_codes=known_codes)
  - results は各ソースごとの新規保存件数の辞書

- J-Quants API 呼び出し（個別）
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  - conn = get_connection("data/kabusys.duckdb")
  - records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  - save_daily_quotes(conn, records)

- カレンダーや営業日ロジック
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day
  - is_trading_day(conn, date(2024,1,1))

## 設計上の重要ポイント（運用メモ）
- J-Quants のレート制御:
  - 120 req/min（固定間隔スロットリング）、モジュール内 _RateLimiter が制御
- リトライ:
  - 指数バックオフ、最大 3 回。408/429/5xx は再試行対象
  - 401 は自動的にトークンをリフレッシュして 1 回だけリトライ
- 保存の冪等性:
  - DuckDB への保存関数は ON CONFLICT (PK) DO UPDATE / DO NOTHING を使用し重複を排除
- ニュース収集セキュリティ:
  - defusedxml を使用した XML パース
  - リダイレクト先のスキームとホストのチェック（SSRF 防止）
  - 受信サイズ上限（10MB）と GZip 解凍後のチェック（Gzip bomb 対策）
  - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で冪等性を確保
- 環境切替:
  - KABUSYS_ENV による環境（development / paper_trading / live）切替
  - settings.is_live / is_paper / is_dev を使用して実行時に振る舞いを制御可能

## ディレクトリ構成（概要）
プロジェクトの主要ファイル／モジュール一覧（抜粋）:

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
      - calendar_management.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（実際のレポジトリでは上記に加えて README.md、pyproject.toml / setup.cfg、.env.example 等がある想定です）

## 例: よく使うコードスニペット
- DuckDB スキーマ初期化と ETL を一度に実行する
  - from kabusys.data.schema import init_schema
  - from kabusys.data.pipeline import run_daily_etl
  - conn = init_schema("data/kabusys.duckdb")
  - res = run_daily_etl(conn)
  - print(res.to_dict())

- ニュース収集と銘柄抽出
  - from kabusys.data.news_collector import run_news_collection
  - conn = init_schema("data/kabusys.duckdb")
  - known_codes = {"7203", "6758", "9984"}
  - stats = run_news_collection(conn, known_codes=known_codes)
  - print(stats)

## テスト・デバッグ時の注意
- 自動で .env を読み込む機能は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テストで os.environ を直接操作したい場合など）。
- jquants_client 内のネットワークや _urlopen 等はモック可能な設計になっています（テスト容易性を考慮して関数分離されています）。

---

この README はライブラリの利用／運用のための導入ドキュメントです。プロジェクト固有の運用手順（CI、デプロイ、Cron ジョブ、Slack 通知テンプレート等）は別途記載してください。必要であれば、README に含めるサンプル .env.example やデプロイ手順、よくあるトラブルシュートを追加します。どの情報を追記しましょうか？