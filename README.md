# KabuSys

日本株自動売買／データ基盤ライブラリ（簡易ドキュメント）

概要
- KabuSys は日本株向けのデータ基盤・リサーチ・戦略実装・発注監査を支援する Python モジュール群です。
- 主に DuckDB をデータ層に使用し、J-Quants API からのデータ取得、RSS ニュース収集、特徴量計算、品質チェック、監査ログ用スキーマ等を提供します。
- 本リポジトリは「データ収集・整形（ETL）」「特徴量生成／リサーチ」「発注監査」など自動売買システムの基盤部分を主に実装しています。

主な機能
- 環境設定
  - .env/.env.local または環境変数から設定を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
  - 必須環境変数チェック
- データ取得・保存（J-Quants）
  - 日次株価（OHLCV）・財務データ・JPX カレンダーの取得（ページネーション対応）
  - レートリミット（120 req/min）の厳守、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン
  - 差分更新（最終取得日ベース）／バックフィルによる再取得
  - 市場カレンダー取得 → 株価取得 → 財務取得 → 品質チェック の日次処理 run_daily_etl
- データ品質チェック
  - 欠損データ、主キー重複、価格スパイク、日付不整合の検出（QualityIssue オブジェクト）
- ニュース収集
  - RSS 取得（gzip 対応）、XML パースに defusedxml、SSRF 対策、URL 正規化、記事ID は正規化 URL の SHA-256（先頭32文字）
  - raw_news / news_symbols への冪等保存
- スキーマ管理
  - DuckDB のスキーマ定義・初期化（raw / processed / feature / execution 層）
  - 監査用スキーマ（signal_events / order_requests / executions）と専用初期化ユーティリティ
- リサーチ／特徴量
  - Momentum / Volatility / Value のファクター計算（prices_daily / raw_financials 参照）
  - 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー
  - z-score 正規化ユーティリティ
- 監査・トレーサビリティ
  - シグナル → 発注要求 → 約定 の流れを UUID で追跡する監査テーブル群と初期化関数

セットアップ手順（開発・ローカル）
1. 前提
   - Python 3.10 以上を推奨（typing の新しい構文を使用しているため）
   - 必要なライブラリ（例）
     - duckdb
     - defusedxml
   - 例: pip install duckdb defusedxml

2. リポジトリを取得して editable インストール（パッケージ化されている想定）
   - git clone ...
   - cd <repo>
   - pip install -e .

3. 環境変数設定
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込みます（.git/ または pyproject.toml を基点として探索）。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主な環境変数（必須/任意）:
   - JQUANTS_REFRESH_TOKEN (必須) : J-Quants の refresh token
   - KABU_API_PASSWORD (必須)    : kabuステーション API のパスワード
   - KABU_API_BASE_URL (任意)    : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN (必須)      : Slack Bot トークン（通知用）
   - SLACK_CHANNEL_ID (必須)     : 通知先 Slack チャンネル ID
   - DUCKDB_PATH (任意)          : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH (任意)          : 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV (任意)          : 実行環境 (development|paper_trading|live)（デフォルト: development）
   - LOG_LEVEL (任意)            : ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

   例（.env の例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DB スキーマ初期化
   - DuckDB スキーマを初期化して接続を得ます。
   - 例:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

   - 監査ログ専用 DB を初期化する場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")

使い方（代表的な例）

- 日次 ETL を実行する
  - 価格・財務・カレンダーを差分取得し品質チェックまで実行します。
  - 例:
    from kabusys.data import schema, pipeline
    conn = schema.init_schema("data/kabusys.duckdb")
    result = pipeline.run_daily_etl(conn)
    print(result.to_dict())

- ニュース収集ジョブを実行する
  - RSS から記事を取得し raw_news / news_symbols に保存します。
  - 例:
    from kabusys.data.news_collector import run_news_collection
    # known_codes は銘柄コード抽出用（例: {"7203","6758",...}）
    saved = run_news_collection(conn, known_codes={"7203","6758"})
    print(saved)

- ファクター計算（リサーチ）
  - calc_momentum / calc_volatility / calc_value などを使用。
  - 例:
    from datetime import date
    from kabusys.research import calc_momentum, zscore_normalize
    records = calc_momentum(conn, date(2025, 1, 10))
    normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])

- J-Quants からの直接取得（低レベル）
  - fetch_daily_quotes / save_daily_quotes 等が利用可能。
  - 例:
    from kabusys.data import jquants_client as jq
    quotes = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,10))
    jq.save_daily_quotes(conn, quotes)

- 監査スキーマの初期化
  - 既存 conn に監査テーブルを追加：
    from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)

主要モジュールと役割（抜粋）
- kabusys.config
  - 環境変数の読み込み / settings オブジェクト
- kabusys.data.jquants_client
  - J-Quants API クライアント（fetch_*/save_* を提供）
  - レート制御、リトライ、トークン自動リフレッシュを含む
- kabusys.data.schema
  - DuckDB のスキーマ定義・初期化（init_schema / get_connection）
- kabusys.data.pipeline
  - 日次 ETL（run_daily_etl）や個別 ETL ジョブ（run_prices_etl 等）
- kabusys.data.news_collector
  - RSS 収集 → raw_news 保存 → 銘柄紐付け
  - SSRF 対策、defusedxml、サイズ制限等のセキュリティ考慮あり
- kabusys.data.quality
  - 欠損、スパイク、重複、日付不整合チェック（run_all_checks）
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
- kabusys.data.audit
  - 発注〜約定までの監査用テーブル群と初期化ロジック
- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - 戦略・発注・監視用のプレースホルダモジュール（実装拡張ポイント）

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - etl.py
    - features.py
    - calendar_management.py
    - audit.py
    - stats.py
    - quality.py
  - research/
    - __init__.py
    - feature_exploration.py
    - factor_research.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

実運用上の注意
- 環境変数に API トークン等の機密情報を保存する場合は適切なアクセス制御を行ってください。
- J-Quants API のレート制限は厳守する設計ですが、運用環境ではさらに上位のレート管理・ログ監視を行ってください。
- DuckDB のファイルは定期的にバックアップしてください。監査ログなどは削除前提ではなく永続保存を想定しています。
- run_daily_etl の実行結果（ETLResult）で品質エラーが報告された場合、データステータスを確認してから downstream 処理（売買シグナル生成等）を実行することを推奨します。
- news_collector は外部フィードのスキーマ差や巨大レスポンスに対して堅牢化されていますが、未知のフォーマットはスキップされることがあります。ログを参照してください。

拡張ポイント（開発者向け）
- strategy 層に具体的なポートフォリオ生成ロジックを実装し、signals / signal_queue に登録するフローを実装可能。
- execution 層で kabu API（別実装）と接続し order_requests → executions のフローを実装することで実取引が可能になります（live 環境では十分なテストを行ってください）。
- research の出力（features, ai_scores）を strategy に接続してシグナル生成を行うパイプライン化。

ライセンス・貢献
- 本ドキュメントには記載されていません。リポジトリルートの LICENSE や CONTRIBUTING を参照してください。

----

必要であれば、README に以下を追記できます:
- CI 用の具体的なテスト実行方法
- より詳細な .env.example ファイル
- デプロイ（Airflow / Cron / Kubernetes CronJob）例
- 実行時のログ出力例・トラブルシューティング集

ご要望に合わせて README を拡張します。どの部分を詳しく書けばよいか教えてください。