README
=====

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買プラットフォーム向けユーティリティ群です。本リポジトリは主にデータプラットフォーム部分（J-Quants からのデータ取得、DuckDB スキーマ定義、ETL パイプライン、データ品質チェック、監査ログ初期化 等）を提供します。

主な設計方針・特徴:
- J-Quants API から株価（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得
- API レート制御（120 req/min）やリトライ／トークン自動リフレッシュを組み込み
- データは DuckDB に層構造（Raw / Processed / Feature / Execution）で保存
- ETL は差分更新（バックフィル対応）・冪等保存（ON CONFLICT DO UPDATE）・品質チェックを実施
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用テーブルを提供
- 環境変数/ .env の自動読み込み機能を備え、設定は Settings から参照可能

機能一覧
--------
- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可能）
  - 必須環境変数取得のヘルパー（未設定時は例外）
  - KABUSYS_ENV, LOG_LEVEL 等のバリデーション

- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token（リフレッシュトークン → idToken）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - レート制限（120 req/min）、指数バックオフリトライ、401 時自動トークン更新
  - DuckDB への冪等保存 save_* 関数（raw_prices, raw_financials, market_calendar）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義
  - init_schema(db_path) で DB を初期化（冪等）
  - get_connection(db_path) で接続を取得

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新・バックフィル・lookahead を備えた日次 ETL（run_daily_etl）
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
  - 品質チェックを呼び出して結果を ETLResult として返却

- 品質チェック（kabusys.data.quality）
  - 欠損データ検出、スパイク検出、重複検出、日付不整合（未来日付・非営業日）検出
  - 問題は QualityIssue オブジェクトのリストで返却（severity: error|warning）

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions 等の監査用テーブル定義
  - init_audit_schema / init_audit_db による初期化

セットアップ手順
----------------
前提:
- Python 3.10 以上（型注釈で | ユニオンを使用）
- ネットワーク環境（J-Quants API へのアクセスが必要）

1) 仮想環境を作成・有効化（任意）
- python -m venv .venv
- Windows: .venv\Scripts\activate
- Unix/macOS: source .venv/bin/activate

2) 必要パッケージのインストール
- 本コードベースは外部依存を最小化していますが、DuckDB を使用します:
  - pip install duckdb

（将来的に追加パッケージがあれば requirements.txt を用意してください）

3) 環境変数の準備
- プロジェクトルートに .env（または .env.local）を作成します。以下のキーを設定してください。

必須（実行機能による）:
- JQUANTS_REFRESH_TOKEN=（J-Quants のリフレッシュトークン）
- SLACK_BOT_TOKEN=（Slack 通知を行う場合）
- SLACK_CHANNEL_ID=（Slack 通知を行う場合）
- KABU_API_PASSWORD=（kabu API を使用する場合のパスワード）

任意（デフォルトあり）:
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
- LOG_LEVEL=INFO|DEBUG|...  （デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  （自動 .env 読み込みを無効化）

例 (.env)
- JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C0123456789
- KABU_API_PASSWORD=your_password
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development

環境変数の自動読み込み:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）から .env/.env.local を自動で読み込みます。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（簡単な例）
------------------

1) DuckDB スキーマ初期化（永続 DB）
Python REPL やスクリプトから:
- from kabusys.data.schema import init_schema
- conn = init_schema("data/kabusys.duckdb")

インメモリでテスト:
- conn = init_schema(":memory:")

2) 日次 ETL を実行して結果を取得
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn)  # target_date を省略すると本日（ローカル日）を基準に実行
- print(result.to_dict())

例: コマンドライン一行実行
- python -c "from kabusys.data.schema import init_schema; from kabusys.data.pipeline import run_daily_etl; conn = init_schema('data/kabusys.duckdb'); print(run_daily_etl(conn).to_dict())"

3) 監査ログテーブルの初期化（データベースに追加）
- from kabusys.data.audit import init_audit_schema
- init_audit_schema(conn)

4) J-Quants API を直接使う
- from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
- token = get_id_token()
- quotes = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))

5) 品質チェックを個別に実行
- from kabusys.data.quality import run_all_checks
- issues = run_all_checks(conn, target_date=date(2024,1,1))
- for i in issues: print(i)

注意点（実運用向け）
- J-Quants API レート制限: 120 req/min。jquants_client は内部で固定間隔スロットリングとリトライを行いますが、実運用では呼び出し頻度設計に注意してください。
- トークン自動リフレッシュ: get_id_token によりリフレッシュが行われます。401 受信時は一度トークンを更新して再試行します。
- ETL は各ステップで例外をキャッチして処理を継続します。結果オブジェクト ETLResult の errors や quality_issues を確認して運用側で判断してください。
- DuckDB ファイルのバックアップやパス管理は運用側で行ってください。

ディレクトリ構成
----------------
以下は本リポジトリ内の主要モジュール構成（src/kabusys 配下）です。説明は各モジュールの役割です。

- src/kabusys/
  - __init__.py                 : パッケージ宣言（__version__ 等）
  - config.py                   : 環境変数 / 設定管理（Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py         : J-Quants API クライアント（取得・保存ロジック）
    - schema.py                 : DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py               : ETL パイプライン（差分更新、品質チェック、run_daily_etl）
    - audit.py                  : 監査ログ（signal/order/execution）用スキーマ初期化
    - quality.py                : データ品質チェック（欠損、スパイク、重複、日付不整合）
  - strategy/
    - __init__.py               : 戦略関連（将来的な拡張ポイント）
  - execution/
    - __init__.py               : 発注・約定関連（将来的な拡張ポイント）
  - monitoring/
    - __init__.py               : 監視・メトリクス関連（将来的な拡張ポイント）

各ファイルの詳細はファイル冒頭の docstring を参照してください。

開発・テスト補助
----------------
- 自動 .env 読み込みを無効化する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB をインメモリで利用すれば一時的なテストが容易:
  - conn = init_schema(":memory:")

拡張ポイント
-------------
- strategy と execution パッケージは軽量のスケルトンです。独自戦略、リスク管理、ブローカー連携はここに実装してください。
- Slack 通知やモニタリング連携（Prometheus / Grafana 等）を追加する場合は monitoring パッケージに機能を追加してください。

ライセンス / 貢献
----------------
- 本 README ではライセンス記載がありません。実際のプロジェクトでは LICENSE ファイルをリポジトリに追加してください。
- 修正・機能追加は Pull Request を送ってください。変更はテストとドキュメントを伴うことを推奨します。

お問い合わせ
------------
実装や利用方法で不明点があれば、コード中の docstring を参照するか、リポジトリの issue を立ててください。