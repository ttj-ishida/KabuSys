# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ（プロトタイプ）

概要
- KabuSys は J-Quants API を中心に日本株の市場データを取得・保存し、品質チェックや監査ログ、ETL パイプラインを提供するモジュール群です。
- 主にデータ収集（Data）、戦略（Strategy）、約定（Execution）、監視（Monitoring）のレイヤに分かれた設計を想定しています。
- データ保存先には DuckDB を採用し、冪等的な保存（ON CONFLICT DO UPDATE）・レート制御・リトライ・トレーサビリティを重視しています。

主な機能
- J-Quants API クライアント（data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）を守る内部 RateLimiter
  - 再試行（指数バックオフ、最大 3 回）および 401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録（Look-ahead Bias 対策）
  - DuckDB への冪等保存関数（save_*）
- DuckDB スキーマ定義と初期化（data/schema.py）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル DDL を定義
  - テーブル作成（init_schema）と接続取得ユーティリティ
- ETL パイプライン（data/pipeline.py）
  - 差分更新（最終取得日＋バックフィル）、市場カレンダー先読み、品質チェックとの一括実行
  - run_daily_etl により日次 ETL を簡単に実行可能
- 品質チェック（data/quality.py）
  - 欠損、スパイク（前日比）、重複、日付不整合（未来日付・非営業日データ）検出
  - 問題は QualityIssue オブジェクトのリストで返却（Fail-Fast ではなく収集）
- 監査ログ（data/audit.py）
  - シグナル→発注要求→約定までを UUID でチェーンする監査テーブル群
  - 発注の冪等性（order_request_id）と各種ステータス管理
- 設定管理（config.py）
  - .env / .env.local / OS 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の明示チェック（未設定時は ValueError）
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証

動作環境 / 依存
- Python >= 3.10（型注釈で | を使用）
- 必須パッケージ
  - duckdb
- （任意）Slack 通知や kabu API 連携を行う場合は別途該当ライブラリを追加してください。

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数の準備
   - プロジェクトルートに .env（または .env.local）を作成します。自動で読み込まれる順序は OS 環境 > .env.local > .env です。
   - 例（.env.example 相当）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_station_password
     # KABU_API_BASE_URL は省略可（デフォルト: http://localhost:18080/kabusapi）
     SLACK_BOT_TOKEN=your_slack_bot_token
     SLACK_CHANNEL_ID=your_slack_channel_id
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   - 自動ロードを無効化したい場合（テストなど）:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース初期化
   - Python REPL やスクリプトで DuckDB スキーマを作成します:
     from kabusys.config import settings
     from kabusys.data.schema import init_schema
     conn = init_schema(settings.duckdb_path)
   - 監査ログを別 DB として初期化する場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

基本的な使い方（例）
- J-Quants の ID トークンを取得
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用して POST で取得

- 日次 ETL を実行（簡易）
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)
  print(result.to_dict())

- 個別ジョブ実行
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

  # target_date を指定して差分 ETL 実行
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  fetched_fin, saved_fin = run_financials_etl(conn, target_date=date.today())

- 品質チェックを単体で実行
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)

設定についての注意
- 必須環境変数は Settings プロパティ経由で要求時に検証されます。未設定だと ValueError が発生します。
  - 必須例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかである必要があります。
- LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれかである必要があります。
- settings.duckdb_path は省略時 "data/kabusys.duckdb" を使用します。

ディレクトリ構成
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント、取得・保存ロジック
    - schema.py             — DuckDB スキーマ定義と初期化（Raw/Processed/Feature/Execution）
    - pipeline.py           — ETL パイプライン（差分取得・保存・品質チェック）
    - quality.py            — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py              — 監査ログ（signal/order_request/executions）初期化
    - (その他): audit/ pipeline 関連
  - strategy/
    - __init__.py           — 戦略モジュール（拡張点）
  - execution/
    - __init__.py           — 発注 / 約定処理（拡張点）
  - monitoring/
    - __init__.py           — 監視 / メトリクス（拡張点）

設計上の重要なポイント
- 冪等性: API から得たデータは DuckDB に対して INSERT ... ON CONFLICT DO UPDATE を用い冪等保存するため、再実行による重複登録を防ぎます。
- レート制御: J-Quants API 呼び出しは 120 req/min を守るため固定間隔スロットリングを行います。
- リトライ・トークンリフレッシュ: HTTP 408/429/5xx に対する指数バックオフリトライ、401 を受けたら refresh トークンで再取得して 1 回リトライします。
- 品質チェック: ETL 後にデータ品質を自動検査し、問題を収集して返却します（ETL は可能な限り継続します）。
- 監査トレーサビリティ: シグナルから約定まで UUID を連鎖させ監査可能にします（削除不可、UTC タイムスタンプ）。

開発・運用のヒント
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、必要な環境変数をテストプロセス側で制御すると便利です。
- 大量のバックフィルや初回ロード時は API レート制限を考慮し、バッチ処理や時間帯分散を検討してください。
- production（live）モードでは KABUSYS_ENV=live を設定し、ログレベルや外部サービスのエンドポイント設定に注意してください。

今後の拡張案（参考）
- strategy、execution、monitoring 層の具体実装（ポートフォリオ生成、注文送信、Slack/Prometheus 連携など）
- 並列化・ジョブスケジューラ（Airflow / Dagster 等）との統合
- メトリクス収集・ダッシュボード化

問い合わせ・貢献
- イシューやプルリクエストはリポジトリ上で受け付けてください。ドキュメントの改善やテスト追加、戦略モジュールの寄稿も歓迎します。

--- 
README 以上。必要であれば .env.example や簡単なスクリプトサンプル、CI 設定サンプルを追加で作成します。どの部分を詳しく追加しますか？