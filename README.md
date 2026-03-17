KabuSys
======

バージョン: 0.1.0

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。J-Quants API や RSS を用いたデータ収集、DuckDB を使ったデータ格納・スキーマ管理、ETL パイプライン、データ品質チェック、マーケットカレンダー管理、監査ログなどの機能を提供します。

主な目的
- J-Quants からの株価・財務・マーケットカレンダーの取得と DuckDB への永続化（冪等保存）
- RSS を用いたニュース収集と記事・銘柄紐付け
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー（営業日判定・前後営業日取得）
- 監査ログ向けスキーマ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェックの実装（欠損・重複・スパイク・日付不整合）

機能一覧
- 環境変数 / .env 自動読み込み（.env, .env.local、自動読み込み無効化可）
- J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ、ページネーション）
- DuckDB スキーマ初期化（raw / processed / feature / execution / audit 層）
- ETL パイプライン（run_daily_etl, 個別 ETL：価格・財務・カレンダー）
- ニュース収集（RSS フィード取得、安全対策：SSRF, XML 攻撃対策, サイズ制限）
- ニュース→銘柄コード抽出（4桁コード抽出、重複除去）
- データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）
- マーケットカレンダー管理（営業日判定、次/前営業日、期間内営業日取得）
- 監査ログ初期化（signal_events, order_requests, executions テーブル等）

セットアップ手順（ローカル開発用）
- 前提
  - Python 3.10 以上（ソースでの型記法により 3.10+ を想定）
  - git, pip 等

1) リポジトリをクローン（既にコードがある場合は不要）
   git clone <repo-url>

2) 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  （Windows PowerShell: .venv\Scripts\Activate.ps1）

3) 必要なライブラリをインストール
   pip install duckdb defusedxml

   - 補足: コードは標準ライブラリの urllib を HTTP クライアントとして使っています。追加で必要な外部依存は上記が主です。

4) 環境変数を準備
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（既存の OS 環境変数は保護されます）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用など）。

  例: .env.example（プロジェクトルートに置く想定）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    KABU_API_PASSWORD=your_kabu_api_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

  必須の環境変数（Settings による必須チェック）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

  オプション / デフォルト
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で .env 自動読み込みを無効化

使い方（主な例）
- DuckDB スキーマ初期化
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  # デフォルトの settings.duckdb_path（例: data/kabusys.duckdb）にファイル作成してスキーマを初期化
  conn = init_schema(settings.duckdb_path)

  - メモリ上 DB を使うとき:
    conn = init_schema(":memory:")

- 日次 ETL 実行（株価・財務・カレンダーの差分取得＋品質チェック）
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 個別 ETL 実行（例: 価格のみ）
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 1))

- カレンダー更新バッチ
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)

- ニュース収集（RSS 取り込みと DB 保存）
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn)  # DEFAULT_RSS_SOURCES を使う
  print(results)

  - 銘柄紐付けを行うには known_codes を指定（set[str]）:
    known_codes = {"7203", "6758", ...}
    run_news_collection(conn, known_codes=known_codes)

- データ品質チェック（単体実行）
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i.check_name, i.severity, i.detail)

- 監査ログスキーマ初期化（audit テーブル群）
  from kabusys.data.audit import init_audit_schema
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn)

実装上の重要ポイント（設計メモ）
- J-Quants クライアント
  - API レート制御（120 req/min 固定間隔）
  - リトライ（指数バックオフ、最大 3 回）、401 での自動リフレッシュを行う
  - ページネーション対応、fetched_at による取得時刻（UTC）保存
  - DuckDB への保存は ON CONFLICT で冪等に実施
- ニュース収集
  - URL 正規化とトラッキングパラメータ除去（SHA-256 先頭32文字を記事IDに）
  - defusedxml を使った XML パース、SSRF 対策（リダイレクト検査・プライベート IP 拒否）
  - レスポンスサイズ上限（10MB）でメモリ DoS を防止
  - DB への保存はトランザクションでまとめ、INSERT ... RETURNING を利用
- ETL
  - 差分更新（最終取得日を基に自動算出）、バックフィル（デフォルト 3 日）で API 側の後出し修正を吸収
  - 品質チェックは Fail-Fast ではなく全件収集し、呼び出し元が判断する
- カレンダー管理
  - market_calendar が未取得のときは曜日ベースのフォールバック（土日を休場）
  - next_trading_day / prev_trading_day / get_trading_days は DB 値優先で未登録日は曜日フォールバック

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                    # 環境変数読み込みと Settings 定義
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント（fetch/save 等）
    - news_collector.py          # RSS ニュース収集・保存
    - pipeline.py                # ETL パイプライン（run_daily_etl 等）
    - schema.py                  # DuckDB スキーマ定義・初期化
    - calendar_management.py     # カレンダー管理（営業日判定・更新ジョブ）
    - audit.py                   # 監査ログ（signal/order/execution）初期化
    - quality.py                 # データ品質チェック
  - strategy/                     # 戦略関連（未実装のプレースホルダ）
    - __init__.py
  - execution/                    # 発注・実行関連（未実装のプレースホルダ）
    - __init__.py
  - monitoring/                   # 監視関連（未実装のプレースホルダ）

追加メモ
- ログ: settings.log_level によるログレベル制御。環境変数 LOG_LEVEL で設定できます。
- 環境自動読み込み:
  - プロジェクトルートは .git または pyproject.toml を起点に検出されます。
  - 読み込み順: OS 環境 > .env.local > .env
  - テストなどで自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に作成されます。必要に応じて settings.duckdb_path を .env で上書きしてください。

貢献・拡張
- strategy / execution / monitoring フォルダは戦略実装・発注実装・監視機能の拡張ポイントです。
- 単体テスト、CI、パッケージング（pyproject.toml）を追加すると運用がしやすくなります。

ライセンスや連絡先はリポジトリ側の指示に従ってください。README に含めたい追加情報（例: 実運用時のセキュリティ注意点、運用フロー例など）があれば教えてください。