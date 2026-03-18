KabuSys
=======

日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants や RSS などから市場データ・ニュースを取得して DuckDB に保存し、ETL、品質チェック、マーケットカレンダー管理、監査ログなどを提供します。

主な目的
- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存
- RSS ベースのニュース収集と銘柄紐付け
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー判定ユーティリティ（営業日/半日/SQ 判定、次/前営業日取得）
- 監査ログ（シグナル→発注→約定のトレース）用スキーマ提供

機能一覧
- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数検証（settings オブジェクト経由で参照）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX カレンダー取得
  - レート制限管理（120 req/min）、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT による更新）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック、バックフィル、品質チェック統合（quality モジュール）
  - run_daily_etl による一括実行
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、URL 正規化、トラッキングパラメータ除去、SSRF 防止
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成、raw_news へ冪等保存
  - 銘柄コード抽出（4桁）と news_symbols への紐付け
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・前後営業日取得・期間内営業日列挙、夜間カレンダー更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブルとインデックス
  - 全 TIMESTAMP を UTC で保存する設定
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合の検出
  - QualityIssue オブジェクトリストで問題を返す

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone ...（省略）

2. Python 環境（推奨: 3.9+）を準備
   - 仮想環境を作成して有効化してください。

3. 依存パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクト配布時に requirements.txt / pyproject.toml があればそれに従ってください）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（デフォルト）。  
     自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必要な環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN       : Slack ボットトークン（必須）
     - SLACK_CHANNEL_ID      : Slack チャンネルID（必須）
   - 任意 / デフォルト有り
     - KABU_API_BASE_URL     : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : environment（development / paper_trading / live）デフォルト: development
     - LOG_LEVEL             : ログレベル（DEBUG/INFO/...）デフォルト: INFO

   - 例 .env（参考）
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

使い方（主要な API と実行例）
- 設定参照
  - from kabusys.config import settings
  - settings.jquants_refresh_token 等のプロパティで環境変数を取得。未設定なら ValueError が発生します。

- DuckDB スキーマ初期化
  - Python REPL / スクリプトで:
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
  - ":memory:" を渡すとインメモリ DB。

- 監査スキーマ初期化（既存接続へ追加）
  - from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)

- 日次 ETL の実行
  - from datetime import date
    from kabusys.data.schema import get_connection, init_schema
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn)  # 今日分を取得して品質チェックまで実行
    print(result.to_dict())

  - オプション例:
    result = run_daily_etl(conn, target_date=date(2025,1,10), backfill_days=5, run_quality_checks=True)

- ニュース収集（RSS）
  - 単一フィードの取得:
    from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  - DB への保存と銘柄紐付け:
    from kabusys.data.news_collector import save_raw_news, run_news_collection
    conn = get_connection("data/kabusys.duckdb")
    # 単体保存
    new_ids = save_raw_news(conn, articles)
    # 全ソース収集（既定の RSS ソースを利用）
    run_news_collection(conn, known_codes={"7203","6758",...})

- J-Quants API 呼び出し
  - get_id_token()、fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar() を直接利用可能。
  - 取得データは save_* 関数で DuckDB に保存できます。

- 品質チェック
  - from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=None)
    # issues は QualityIssue のリスト

注意点 / 設計上の挙動
- 自動 .env ロード
  - パッケージ import 時に .env/.env.local を自動読み込みします（プロジェクトルートに .git または pyproject.toml がある場合）。
  - テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 読み取り順序: OS 環境変数 > .env.local（上書き可） > .env（未上書き）
- J-Quants API の制限
  - 120 req/min を守るため内部でレートリミッタを使用します。大量取得時は時間がかかります。
  - 401 を検出した場合は自動で refresh token から id_token を再取得して 1 回リトライします。
- ニュース収集のセキュリティ
  - defusedxml を使用して XML 攻撃を防御
  - SSRF 対策としてホストがプライベートアドレスかどうかを検査し、許可しません
  - レスポンスサイズ制限（デフォルト 10MB）を超える場合はスキップします
- DuckDB スキーマは冪等（CREATE TABLE IF NOT EXISTS / ON CONFLICT）を意識して設計されています

ディレクトリ構成（概要）
- src/
  - kabusys/
    - __init__.py
    - config.py                    -- 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py          -- J-Quants API クライアント + DuckDB 保存
      - news_collector.py         -- RSS ニュース収集と保存
      - pipeline.py               -- ETL パイプライン（run_daily_etl 等）
      - schema.py                 -- DuckDB スキーマ定義と初期化
      - calendar_management.py    -- マーケットカレンダー管理ユーティリティ
      - audit.py                  -- 監査ログ（signal / order / execution）スキーマ
      - quality.py                -- データ品質チェック
    - strategy/                     -- 戦略関連のエントリポイント（未実装の初期化）
      - __init__.py
    - execution/                    -- 発注実行関連（未実装の初期化）
      - __init__.py
    - monitoring/                   -- 監視系モジュール（未実装の初期化）

拡張ポイント（開発者向け）
- strategy/ と execution/ はアプリ固有の戦略・発注ロジックを実装する場所です。signal の生成、order_queue 管理、broker adapter（kabuステーション／証券会社API）を実装してください。
- monitoring モジュールはメトリクス収集や Slack 通知、Prometheus エクスポーターなどを実装する想定です。
- テスト時は settings の自動 .env 読み込みを無効化して、テスト専用の環境を注入してください（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

ライセンス / 責任
- このドキュメントはコードベースの概要説明です。実稼働での取引に用いる場合は十分なテストとレビュー、法令順守を行ってください。金融取引にはリスクがあります。

フィードバック・貢献
- バグ報告や機能提案は Issue を立ててください。プルリク歓迎です。

以上。必要であれば README に含めるサンプル .env.example や CI 実行例、より詳細な API リファレンス（各関数の引数・戻り値の表）を追加します。どの情報を拡張しますか？