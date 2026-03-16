KabuSys
=======

日本株自動売買システムのコアライブラリ（データプラットフォーム・ETL・監査ログ・APIクライアントなど）。  
このリポジトリは主にデータ取得・保存・品質チェック・監査ログの初期化／ETLを提供します。戦略実行・注文送信の実装は別モジュールで拡張する想定です。

概要
----
KabuSys は日本株のマーケットデータを外部 API（J-Quants）から取得し、DuckDB に層構造（Raw / Processed / Feature / Execution）で保存するためのライブラリです。  
主に以下を提供します。

- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB スキーマ定義と初期化
- ETL パイプライン（差分取得、バックフィル、先読みカレンダー）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（シグナル→発注要求→約定のトレーサビリティ）
- 環境変数設定管理（.env 自動ロード機能）

主な機能一覧
--------------
- data/jquants_client.py
  - J-Quants から株価日足・財務データ・マーケットカレンダーを取得（ページネーション対応）
  - 120 req/min のレート制御（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回、408/429/5xx などを対象）
  - 401 受信時にリフレッシュトークンで自動再取得して 1 回リトライ
  - DuckDB に対する冪等保存関数（ON CONFLICT DO UPDATE）
- data/schema.py
  - Raw/Processed/Feature/Execution 各レイヤーのテーブル DDL を定義
  - init_schema(db_path) で DuckDB を初期化
  - get_connection() で既存 DB に接続
- data/pipeline.py
  - run_daily_etl()：市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 個別ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）を提供
  - 差分検出・バックフィル・営業日調整などを自動化
- data/quality.py
  - 欠損データ、スパイク（前日比）、重複、日付不整合を検出
  - QualityIssue オブジェクトで結果を返す（error/warning）
- data/audit.py
  - signal_events / order_requests / executions の監査テーブルを初期化
  - 監査ログは UTC タイムスタンプ、冪等キーや FK 制約を備える
- config.py
  - .env または環境変数から設定をロード（プロジェクトルート自動探索）
  - 主要な設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, Slack 情報, DB パス など）をプロパティで提供

必要要件
--------
- Python 3.10 以上（typing の構文・| 型記法を使用）
- 依存パッケージ（例）:
  - duckdb
- 標準ライブラリ: urllib, json, logging, datetime など

セットアップ手順
----------------

1. リポジトリをクローン（あるいはパッケージをインストール）
   - 開発環境であれば pip editable install:
     python -m pip install -e .

2. 依存パッケージをインストール:
   python -m pip install duckdb

3. 環境変数を用意する (.env)
   - プロジェクトルート（.git または pyproject.toml を基準）に .env を置くと自動で読み込まれます。
   - 読み込み順序: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 必要な環境変数の例 (.env.example)
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

使い方（例）
------------

1) スキーマ初期化（DuckDB）
- 永続ファイルに初期化:
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)

- インメモリ DB:
  conn = init_schema(":memory:")

2) 監査ログテーブルの初期化（既存接続へ追加）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)

3) J-Quants からデータ取得（個別）
  from kabusys.data import jquants_client as jq

  # トークンは settings.jquants_refresh_token を使用して自動的に取得される
  records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
  saved = jq.save_daily_quotes(conn, records)

4) 日次 ETL（推奨: 定期実行ジョブ）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  # ETLResult オブジェクト: target_date, prices_fetched, prices_saved, financials_fetched,... quality_issues, errors

5) 個別 ETL ジョブの実行
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  run_prices_etl(conn, target_date=date.today())
  run_financials_etl(conn, target_date=date.today())
  run_calendar_etl(conn, target_date=date.today())

6) 品質チェック単体実行
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i.check_name, i.severity, i.detail)

設定と環境変数
----------------
主要な設定は kabusys.config.settings でプロパティとして参照できます。必須の環境変数は取得時に未設定だと ValueError を投げます。

主なキー:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack bot token
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL — ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")

自動 .env 読み込みの挙動:
- プロジェクトルートを .git または pyproject.toml により探索し、見つかった場合に .env と .env.local を順に読み込みます。
- OS 環境変数は保護され、.env による上書きは基本的に行われません（.env.local は override=True で優先度が高い）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動読み込みを停止します（テスト時に便利）。

設計上の注意
------------
- J-Quants クライアントは 120 req/min の制約を遵守するために固定間隔のスロットリングを行います。
- リトライはネットワーク・サーバー系エラーを対象に行い、401 はトークンリフレッシュの対象になります（1 回のみ自動リフレッシュして再試行）。
- DuckDB への保存は ON CONFLICT DO UPDATE を使って冪等性を保証しています。
- ETL は Fail-Fast ではなく、各ステップのエラーを集約して結果を返します。品質チェックでの問題は QualityIssue として返され、呼び出し元が扱いを決定します。
- 監査ログは削除しない運用を想定し、FK は ON DELETE RESTRICT を採用しています。すべての TIMESTAMP は UTC で保存するように設定します。

ディレクトリ構成
-----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py                      - パッケージ初期化、__version__
  - config.py                        - 環境変数・設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py              - J-Quants API クライアント（取得・保存）
    - schema.py                      - DuckDB スキーマ定義と初期化
    - pipeline.py                    - ETL パイプライン（差分更新・品質チェック含む）
    - quality.py                     - データ品質チェック
    - audit.py                       - 監査ログ用テーブルの定義・初期化
    - audit.py
    - pipeline.py
  - strategy/
    - __init__.py                     - 戦略層用のプレースホルダ
  - execution/
    - __init__.py                     - 発注/実行関連のプレースホルダ
  - monitoring/
    - __init__.py                     - 監視・メトリクス関連のプレースホルダ

開発者メモ
-----------
- 型注釈と dataclass を利用しているため、静的解析ツール（mypy 等）で検査しやすい設計です。
- jquants_client の内部トークンキャッシュはページネーション間で共有されます。get_id_token は allow_refresh=False で呼ばれることがあるため再帰に注意しています。
- DuckDB の初期化は冪等なので、定期的にスクリプトで init_schema() を呼ぶだけでスキーマを保てます。

ライセンス
---------
（実プロジェクトではライセンス情報をここに記載してください）

問い合わせ・貢献
----------------
バグ報告や機能提案は Issue を立ててください。Pull Request は歓迎します。README の改善提案も歓迎です。