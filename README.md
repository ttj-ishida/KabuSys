kabusys
=======

KabuSys は日本株向けの自動売買プラットフォーム（データプラットフォーム＋ETL＋監査ログ）を想定したライブラリ群です。  
このリポジトリは主に以下を提供します。

- J-Quants API からのデータ取得クライアント（株価日足、財務データ、JPX カレンダー）
- DuckDB を用いたスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL（差分取得・保存・品質チェック）パイプライン
- 監査ログ（シグナル→発注→約定のトレーサビリティ）テーブル初期化
- 環境変数による設定管理（.env 自動ロード、必須キーの検証）
- レート制御・リトライ・トークン自動リフレッシュ等の堅牢な API 呼び出しロジック

主なユースケース:
- J-Quants から市場データを差分で取得して DuckDB に蓄積
- データ品質チェックを行い、戦略用の特徴量基盤を準備
- 戦略・発注・約定の監査ログ基盤を初期化してトレーサビリティを確保

特徴一覧
--------
- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務、マーケットカレンダーを取得
  - レート制限（120 req/min）に対応する内部 RateLimiter
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 監査用テーブル（signal_events / order_requests / executions）別途初期化可能
  - 必要なインデックスを作成
- ETL パイプライン
  - 差分更新（最終取得日からの差分）、バックフィル（デフォルト 3 日）
  - カレンダーの先読み（デフォルト 90 日）による営業日調整
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 各ステップを独立して実行・エラーハンドリング（1 ステップ失敗でも継続）
- データ品質チェック
  - 欠損データ検出（OHLC）
  - 異常値（スパイク）検出（前日比）
  - 主キー重複検出
  - 日付不整合（未来日付・非営業日のデータ）検出
- 設定管理
  - .env / .env.local をプロジェクトルートから自動ロード（CWD 非依存）
  - 環境変数の必須チェックと型検証
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

動作環境 / 依存
---------------
- Python 3.10 以上（PEP 604 の型注釈（X | None）を使用）
- 主な依存ライブラリ（例）
  - duckdb
- 実行環境によっては標準ライブラリに加えて urllib 等を使用

セットアップ手順
--------------
1. リポジトリをクローン（またはパッケージをインストール）
   - 例: git clone <repo-url>

2. Python 仮想環境の作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install duckdb
   - （プロジェクトで requirements.txt を用意している場合は pip install -r requirements.txt）

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env または .env.local を配置すると自動ロードされます。
   - 自動ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必要な環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）

   任意 / デフォルトあり
   - KABU_API_BASE_URL: kabu API のベース URL（既定: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（既定: data/monitoring.db）
   - KABUSYS_ENV: 環境 (development|paper_trading|live)（既定: development）
   - LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）（既定: INFO）

   .env の例:
   - JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   - KABU_API_PASSWORD=your_kabu_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C01234567
   - DUCKDB_PATH=data/kabusys.duckdb
   - KABUSYS_ENV=development

5. DuckDB スキーマの初期化
   - Python REPL やスクリプトから以下を実行:

     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)

   - 監査ログテーブルを追加で初期化する場合:

     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)

使い方
------
以下は代表的な利用例です。実運用ではアプリケーション側でラッパー CLI やジョブスケジューラから呼び出して使います。

- J-Quants の ID トークンを取得する
  - from kabusys.data.jquants_client import get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を使用して POST で取得

- DuckDB スキーマ初期化（上記）
  - conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)
  - result は ETLResult オブジェクト。to_dict() で辞書化可能。品質チェック結果やエラー情報を参照できます。

- 個別 ETL ジョブを実行（株価のみ、財務のみ、カレンダーのみ）
  - from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  - run_prices_etl(conn, target_date=date.today())
  - run_financials_etl(...)
  - run_calendar_etl(...)

- 品質チェックを単独で実行
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date.today())
  - issues は QualityIssue オブジェクトのリスト（severity: "error" | "warning"）

実例スクリプト（簡易）
- etl_run.py:

  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

運用上の注意点
-------------
- API レート制限: J-Quants の上限 120 req/min を Respect するため内部でスロットリングしています。大量ページネーションの処理などは注意してください。
- トークン管理: get_id_token はリフレッシュトークンから ID トークンを取得し、モジュール内でキャッシュします。401 時は自動リフレッシュを試みます。
- 品質チェック: run_daily_etl では品質チェックの結果を収集しますが、重大度に応じた運用判断（処理中止／通知など）は呼び出し側で行ってください。
- タイムゾーン: 監査ログ初期化では TimeZone を UTC に設定しています。すべての TIMESTAMP は UTC 想定です。
- 自動 .env ロード: プロジェクトルート（.git または pyproject.toml を探索）を起点に .env/.env.local を自動読込します。テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

ディレクトリ構成
---------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 -- 環境変数 / 設定管理（.env 自動ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント（取得・保存ロジック）
    - schema.py               -- DuckDB スキーマ定義と初期化
    - pipeline.py             -- ETL パイプライン（差分取得・保存・品質チェック）
    - quality.py              -- データ品質チェック
    - audit.py                -- 監査ログ（signal/order/execution）定義・初期化
    - audit.py
  - strategy/
    - __init__.py             -- 戦略層（雛形）
  - execution/
    - __init__.py             -- 発注 / 実行層（雛形）
  - monitoring/
    - __init__.py             -- 監視用コード（雛形）

開発・貢献
----------
- バグ報告・機能提案は issue を立ててください。
- コードスタイル、テスト、CI の追加は歓迎します。
- 自動環境ロードや設定の挙動に関しては config.py を参照してください（プロジェクトルート判定は __file__ を起点に上位ディレクトリを探索します）。

ライセンス / その他
-------------------
- 本リポジトリ内のライセンスファイルに従ってください（この README では特定のライセンスを仮定していません）。

以上が簡易 README です。必要であれば「CLI のサンプル」「運用チェックリスト」「.env.example の完全なテンプレート」「ETL のスケジュール例（Airflow / cron）」などを追加で作成できます。どちらを優先しましょうか？