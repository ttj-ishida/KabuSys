KabuSys
======
バージョン: 0.1.0

日本株向けの自動売買プラットフォーム向けライブラリの骨格実装です。  
データ取得（J-Quants）、ETLパイプライン、ニュース収集、DuckDB スキーマ／監査ログの初期化、品質チェックなどを提供します。

概要
----
KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。本コードベースは以下の責務を持ちます。

- J-Quants API から株価・財務・市場カレンダーを安全かつレート制限・リトライを考慮して取得
- RSS からニュースを収集し、トラッキングパラメータ除去・SSRF 対策等を施して保存
- DuckDB 上のデータスキーマ（Raw / Processed / Feature / Execution / Audit）を定義・初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）を実行
- 監査ログ（signal → order → execution）用スキーマを提供し、トレーサビリティを担保

主な機能
--------
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンから ID トークンを取得）
  - レート制御（120 req/min）、指数バックオフリトライ、401 時の自動トークン刷新
  - DuckDB へ冪等保存する save_* 関数（ON CONFLICT ... DO UPDATE）

- ニュース収集
  - RSS 取得（gzip 対応）、XML 攻撃対策（defusedxml）、SSRF 対策（リダイレクト時検査）
  - トラッキングパラメータ除去、URL 正規化 → SHA-256（先頭32 文字）で記事ID生成
  - raw_news / news_symbols への冪等保存（INSERT ... RETURNING を利用）
  - 銘柄コード抽出（4桁コード）と既知銘柄セットによる紐付け

- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックスや外部キー、チェック制約による整合性の確保
  - init_schema / init_audit_schema / init_audit_db 等の初期化関数

- ETL パイプライン
  - 差分取得（DB の最終日を参照）、バックフィル、カレンダー先読み
  - 品質チェック（欠損・スパイク・重複・日付不整合）を実行し QualityIssue を返却
  - run_daily_etl により日次処理を統合的に実行

セットアップ手順
--------------
前提
- Python 3.10 以上（型ヒントに | 演算子等を使用）
- DuckDB を利用（pip パッケージ duckdb）
- defusedxml（RSS XML パースの安全化）

推奨手順（Unix 系の例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトがパッケージ化されている場合は pip install -e . を利用）

3. 環境変数を設定
   - プロジェクトルートに .env /.env.local を置くと自動で読み込まれます（優先度: OS 環境変数 > .env.local > .env）
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用途）

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN=あなたのJ-Quantsリフレッシュトークン
- KABU_API_PASSWORD=（kabuステーションAPIのパスワードが必要な場合）
- SLACK_BOT_TOKEN=Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID=通知先 Slack チャンネル ID

任意／デフォルト
- KABU_API_BASE_URL=http://localhost:18080/kabusapi（デフォルト）
- DUCKDB_PATH=data/kabusys.duckdb（デフォルト）
- SQLITE_PATH=data/monitoring.db（デフォルト）
- KABUSYS_ENV=development|paper_trading|live （デフォルト: development）
- LOG_LEVEL=INFO（デフォルト）

例: .env
- JQUANTS_REFRESH_TOKEN=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development
- LOG_LEVEL=DEBUG

使い方（サンプル）
-----------------

1) DuckDB スキーマ初期化
- 基本スキーマ（Raw/Processed/Feature/Execution）を作る:
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- 監査ログテーブルの初期化（既存接続へ追加）:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)

- 監査専用 DB を新規作成:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

2) J-Quants トークン取得・データ取得
- ID トークン取得:
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()

- 株価日足の取得（例）:
  from datetime import date
  from kabusys.data.jquants_client import fetch_daily_quotes
  records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))

- 取得したデータを DuckDB に保存:
  from kabusys.data.jquants_client import save_daily_quotes
  saved_count = save_daily_quotes(conn, records)

設計上の注意点:
  - API 呼び出しは内部でレートリミット・リトライを行います。
  - get_id_token はリフレッシュトークンを使用し、401 時は自動でトークンを更新します。

3) 日次 ETL 実行
- 簡単な日次実行:
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しなければ本日が対象
  print(result.to_dict())

  ETLResult には取得数・保存数・品質チェック結果・エラーのサマリが入ります。

4) ニュース収集ジョブ
- RSS フィードを取得して DB に保存:
  from kabusys.data.news_collector import run_news_collection
  # known_codes を渡すと抽出した銘柄コードとの紐付けも行う
  res = run_news_collection(conn, known_codes={"7203","6758"})
  print(res)  # {source_name: 新規保存件数}

ニュース収集のセキュリティについて:
  - URL スキームは http/https のみ許可
  - リダイレクト先がプライベート IP の場合は拒否（SSRF 対策）
  - 受信サイズ上限（10MB）および gzip 解凍後の再チェック
  - XML パースは defusedxml を使用して XML-Bomb 等を防止

5) 品質チェック
- 個別または全てのチェックを実行:
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=some_date)
  for i in issues:
      print(i)

ディレクトリ構成
----------------
（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 （環境変数・設定管理）
  - data/
    - __init__.py
    - jquants_client.py       （J-Quants API クライアント + 保存ロジック）
    - news_collector.py       （RSS ニュース収集・保存）
    - schema.py               （DuckDB スキーマ定義・初期化）
    - pipeline.py             （ETL パイプライン（差分更新・品質チェック））
    - calendar_management.py  （市場カレンダーのユーティリティ・更新ジョブ）
    - audit.py                （監査ログスキーマ & 初期化）
    - quality.py              （データ品質チェック）
  - strategy/
    - __init__.py             （戦略モジュール群のプレースホルダ）
  - execution/
    - __init__.py             （発注/約定・実行モジュールのプレースホルダ）
  - monitoring/
    - __init__.py             （監視モジュールのプレースホルダ）

開発・運用上のポイント
--------------------
- 環境切替
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかを指定します（小文字で許容）。
  - log レベルは LOG_LEVEL で調整可能（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

- .env の自動読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動判定し .env/.env.local をロードします。
  - テストなどで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

- DB 初期化は冪等（何度実行しても既存テーブルは上書きされません）
- ETL は Fail-Fast ではなく各ステップを個別に扱い、問題があっても可能な限り収集を続行する設計です。最終的な判断は呼び出し側で行ってください。

ライセンス / 貢献
----------------
このリポジトリのライセンスやコントリビューションの詳細は pyproject.toml / LICENSE 等を参照してください（本 README には含まれていません）。

付録 — よく使う API 一覧
-----------------------
- schema.init_schema(db_path) -> DuckDB 接続
- data.jquants_client.get_id_token(refresh_token=None) -> id_token
- data.jquants_client.fetch_daily_quotes(...)
- data.jquants_client.save_daily_quotes(conn, records)
- data.pipeline.run_daily_etl(conn, target_date=None, ...)
- data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- data.audit.init_audit_schema(conn)
- data.quality.run_all_checks(conn, target_date=None)

必要に応じて README に追加したい具体的な使い方（CI/CD、cron 設定例、Slack 通知例、Dockerfile、テスト実行方法など）があれば指示してください。追加情報に基づき、サンプルや運用手順を追記します。