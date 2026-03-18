KabuSys
=======

プロジェクト概要
-------
KabuSys は日本株の自動売買プラットフォーム向けのコアライブラリ群です。  
主な目的は以下です。

- J-Quants API を用いた市場データ（株価、財務、JPX カレンダー等）の取得と DuckDB への保存
- RSS を用いたニュース収集と記事→銘柄の紐付け
- ETL（差分取得・バックフィル・品質チェック）パイプライン
- DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）の定義と初期化
- 監査ログ（信号→発注→約定のトレーサビリティ）処理のサポート

設計上の特徴：
- API レート制限・リトライ・トークン自動リフレッシュを組み込んだ堅牢なクライアント
- Look-ahead bias を防ぐための fetched_at 記録、冪等な DB 操作（ON CONFLICT）
- RSS 収集における SSRF 対策、サイズ制限、XML パースの安全化
- 品質チェック（欠損・スパイク・重複・日付不整合）を提供し ETL の健全性を評価

主な機能一覧
-------
- 環境設定管理（kabusys.config）
  - .env ファイルの自動読込（プロジェクトルート検出）をサポート
  - 必須環境変数チェック
  - KABUSYS_ENV (development|paper_trading|live) / LOG_LEVEL 等

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足、四半期財務、JPX カレンダー取得
  - レートリミッティング、指数バックオフリトライ、401 時のトークン自動更新
  - DuckDB へ冪等（ON CONFLICT）で保存する save_* 関数

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理（URL 除去・空白正規化）
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性確保
  - SSRF 防止、gzip 解凍サイズチェック、defusedxml による安全な XML パース
  - raw_news / news_symbols への保存・銘柄抽出 (4 桁数字)

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層を定義する DDL
  - インデックス定義、init_schema による初期化

- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日ベース）とバックフィル
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 品質チェック結果の収集（kabusys.data.quality）

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日の探索、夜間カレンダー更新ジョブ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions など監査用テーブルと初期化ユーティリティ
  - UTC タイムゾーン固定、冪等性を考慮した設計

セットアップ手順
-------
前提
- Python 3.10 以上（コードは | 型合成等 Python 3.10 構文を使用）
- OS に duckdb をインストールするためのビルド環境は不要（pip パッケージで動作）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトで requirements.txt を用意している場合は pip install -r requirements.txt）

4. 環境変数を準備
   - プロジェクトルートに .env を置くと自動読込されます（.git または pyproject.toml をルート判定基準に使用）
   - 主な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabuステーション API 用パスワード（必須）
     - SLACK_BOT_TOKEN       : Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID      : Slack 通知先チャンネルID（必須）
   - オプション / デフォルト
     - KABUSYS_ENV (development|paper_trading|live) : default=development
     - LOG_LEVEL : DEBUG/INFO/... default=INFO
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 : 自動 .env 読込を無効化（テスト時など）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD を使う場合は環境をプログラム側で直接設定してください
     - DUCKDB_PATH : data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH : data/monitoring.db（デフォルト）

5. DuckDB スキーマ初期化
   - Python REPL / スクリプトで：
     - from kabusys.data import schema
     - conn = schema.init_schema(settings.duckdb_path)  # settings は kabusys.config.settings
   - 監査ログ専用 DB を初期化する場合：
     - from kabusys.data.audit import init_audit_db
     - audit_conn = init_audit_db("data/audit.duckdb")

基本的な使い方
-------
以下は主要ユースケースの最小例です。実運用ではログ設定・例外処理を追加してください。

- DuckDB スキーマの初期化
  - from kabusys.data import schema
  - conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）
  - from datetime import date
    from kabusys.data import pipeline, schema
    conn = schema.init_schema("data/kabusys.duckdb")
    result = pipeline.run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- 個別 ETL（株価）
  - from kabusys.data import pipeline, schema
    conn = schema.get_connection("data/kabusys.duckdb")
    fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())

- ニュース収集ジョブ
  - from kabusys.data import news_collector, schema
    conn = schema.get_connection("data/kabusys.duckdb")
    # sources は {source_name: rss_url}。省略時は DEFAULT_RSS_SOURCES を使用
    results = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
    print(results)

- 監査ログ初期化（既存接続に対して）
  - from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)

- カレンダー夜間更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)

環境変数例（.env）
-------
以下は .env の例（実際のトークンは置き換えてください）：

JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

ディレクトリ構成
-------
（主要ファイルの抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py           # J-Quants API クライアント（取得 + 保存）
    - news_collector.py           # RSS ニュース収集・前処理・保存・銘柄抽出
    - schema.py                   # DuckDB スキーマ定義・初期化
    - pipeline.py                 # ETL パイプライン（差分/バックフィル/品質チェック）
    - calendar_management.py      # マーケットカレンダー管理（営業日判定/バッチ）
    - audit.py                    # 監査ログ（signal/order/execution）DDL・初期化
    - quality.py                  # データ品質チェック（欠損/スパイク/重複/日付不整合）
  - strategy/
    - __init__.py                 # 戦略層（拡張ポイント）
  - execution/
    - __init__.py                 # 発注/実行層（拡張ポイント）
  - monitoring/
    - __init__.py                 # 監視系（将来的に拡張）

運用上の注意・ベストプラクティス
-------
- J-Quants のレート制限（120 req/min）を尊重する必要があり、jquants_client は内部で固定間隔スロットリングを行います。ETL を高速で何度も回す設計には注意してください。
- 機密情報（トークン・パスワード）は .env に平文で置かれることが多いため、運用環境では OS のシークレットストアや CI/CD の機密管理を利用してください。
- DuckDB のファイルは排他制御が必要となる場面があります（複数プロセスでの同時更新等）。運用設計時にアクセス方式を整理してください。
- news_collector は外部 URL を取得するため SSRF 対策を施していますが、運用で追加フィードを許可する場合は URL を慎重に管理してください。
- 品質チェックは警告 / エラーを返します。ETL 停止の可否は運用のポリシーに従ってください（現行設計は Fail-Fast ではなく全件収集）。

開発・拡張ポイント
-------
- strategy/ と execution/ はプラグイン的に戦略や注文処理を追加する想定の空パッケージです。戦略は signal_events テーブルへ出力し、order_requests 経由で発注フローに繋げます。
- monitoring モジュールは監視・アラートのための拡張ポイントです（例: Slack 通知／Prometheus メトリクス）。
- DuckDB スキーマは data/schema.py に集約されているため、テーブル追加やインデックス最適化はここを更新してください。

ライセンス・貢献
-------
（この README にはライセンス情報が含まれていません。リポジトリの LICENSE を参照してください。貢献方法やコントリビューションガイドラインがある場合はそれに従ってください。）

問い合わせ
-------
実装や運用に関する質問はリポジトリの issue を利用するか、チームの内部ドキュメントに従ってください。

以上。