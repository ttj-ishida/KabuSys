KabuSys
=======

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。
データ収集（J-Quants）、ETL、特徴量生成、シグナル計算、ニュース収集、マーケットカレンダー管理、
および DuckDB を用いたスキーマ／永続化ロジックを含みます。研究用（research）と実運用用（execution）を分離した設計になっています。

主な用途
- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL
- 研究で算出した生ファクターを正規化・合成して features テーブルを作成
- features と AI スコアを統合して売買シグナル（BUY/SELL）を生成
- RSS ベースのニュース収集と銘柄紐付け
- マーケットカレンダーの管理（営業日判定 / next/prev / 範囲取得）
- DuckDB スキーマ定義・初期化

機能一覧
- data/
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・リトライ・トークン自動更新）
  - pipeline: ETL（差分更新、backfill、calendar lookahead、品質チェックの統合）
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - news_collector: RSS 収集、安全対策（SSRF/サイズ制限/トラッキング除去）と DB 保存
  - calendar_management: カレンダー更新ジョブと営業日ユーティリティ
  - stats: Zスコア正規化などの統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value 等のファクター計算（prices_daily, raw_financials 参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）等の解析ユーティリティ
- strategy/
  - feature_engineering.build_features: 生ファクターを正規化して features テーブルに保存（日付単位の置換）
  - signal_generator.generate_signals: features と ai_scores を統合して signals テーブルを更新（BUY/SELL）
- execution/, monitoring/ 等のための名前空間（将来的な実装を想定）

セットアップ手順（開発環境向け）
1. Python 環境準備
   - 推奨: Python 3.9+（プロジェクト要件に合わせて調整してください）
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  # macOS / Linux
     - .venv\Scripts\activate     # Windows

2. 依存パッケージのインストール
   - duckdb, defusedxml 等を使用しています。プロジェクトに requirements.txt があればそれを使ってください。
   - 例:
     - pip install duckdb defusedxml

   （実際のパッケージ一覧はプロジェクト配布元の requirements ファイルや pyproject.toml を参照してください。）

3. 環境変数の設定
   - .env または OS 環境変数で設定できます。プロジェクトルート（.git または pyproject.toml のあるディレクトリ）にある .env/.env.local が自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードは無効化されます）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（get_id_token に利用）
     - KABU_API_PASSWORD     : kabuステーション API のパスワード（発注関連）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
   - 任意（デフォルトあり）:
     - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
     - LOG_LEVEL             : ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）
   - サンプル .env（README 用例）
     - JQUANTS_REFRESH_TOKEN=your_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb

4. DB スキーマ初期化
   - Python コンソールやスクリプトから DuckDB を初期化:
     - from kabusys.data.schema import init_schema
     - from kabusys.config import settings
     - conn = init_schema(settings.duckdb_path)
   - ":memory:" を渡すとメモリ DB を使用可能（テスト向け）。

使い方（主要 API の例）
- DuckDB 接続とスキーマ初期化
  - from kabusys.config import settings
    from kabusys.data.schema import init_schema
    conn = init_schema(settings.duckdb_path)

- 日次 ETL の実行（市場カレンダー・株価・財務）
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)
    print(result.to_dict())

- 特徴量の構築（feature engineering）
  - from kabusys.strategy import build_features
    from datetime import date
    n = build_features(conn, date(2024, 1, 5))
    print(f"features upserted: {n}")

- シグナル生成
  - from kabusys.strategy import generate_signals
    from datetime import date
    total = generate_signals(conn, date(2024, 1, 5))
    print(f"signals written: {total}")

  - 重みや閾値をカスタムで渡すことも可能:
    - weights = {"momentum": 0.5, "value": 0.2, "volatility": 0.15, "liquidity": 0.05, "news": 0.10}
    - generate_signals(conn, date.today(), threshold=0.65, weights=weights)

- ETL 内の個別ジョブ（価格/財務/カレンダー）
  - run_prices_etl / run_financials_etl / run_calendar_etl が用意されています（差分取得・backfill に対応）。

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
    print(results)

- マーケットカレンダー関連ヘルパー
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, prev_trading_day, get_trading_days

運用上の注意・設計方針（抜粋）
- ルックアヘッドバイアスの排除:
  - すべてのファクター計算・シグナル生成は target_date 時点までのデータのみ使用するよう設計されています。
  - J-Quants から取得した生データには fetched_at を付与して「いつデータが入手可能になったか」を追跡します。
- 冪等性:
  - DuckDB への保存は可能な限り ON CONFLICT / DO UPDATE / DO NOTHING を使い冪等にしています。
  - features / signals は日付単位で削除→挿入の置換を行い原子性（トランザクション）を保証しています。
- セキュリティ・堅牢性:
  - news_collector は SSRF 対策（リダイレクト検査・プライベートIPブロック）、最大レスポンスサイズ、XML パース時の defusedxml を使用。
  - jquants_client はレート制御とリトライ、401 時のトークン自動更新を備えています。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                         # 環境変数・設定管理（.env 自動ロード含む）
    - data/
      - __init__.py
      - jquants_client.py               # J-Quants API クライアント（fetch/save）
      - news_collector.py               # RSS 収集・前処理・保存
      - pipeline.py                     # ETL パイプライン（run_daily_etl 等）
      - schema.py                       # DuckDB スキーマ定義・init_schema
      - stats.py                        # zscore_normalize 等の統計ユーティリティ
      - calendar_management.py          # カレンダー更新・営業日ユーティリティ
      - audit.py                        # 監査ログ（signal_events / order_requests / executions）
      - features.py                      # data.stats の再エクスポート
    - research/
      - __init__.py
      - factor_research.py              # momentum/volatility/value の算出
      - feature_exploration.py          # 将来リターン/IC/統計サマリー
    - strategy/
      - __init__.py
      - feature_engineering.py          # build_features
      - signal_generator.py             # generate_signals
    - execution/                         # 発注実行関連（名前空間）
    - monitoring/                        # 監視・メトリクス関連（名前空間）
- README.md (このファイル)
- pyproject.toml / setup.cfg / requirements.txt（プロジェクト配布時に存在する想定）

テスト・開発ヒント
- テスト時に実 DB を使いたくない場合は DuckDB の ":memory:" を用いると簡単にインメモリ環境でテストできます。
  - conn = init_schema(":memory:")
- 自動 .env ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで制御しやすくなります）。
- jquants_client._urlopen や news_collector のネットワークリクエストはモック可能な実装になっています（テストで外部 API を叩かず検証可能）。

貢献・ライセンス
- この README はコードベースの要約です。実際に利用する際はプロジェクトの LICENSE、CONTRIBUTING、DataPlatform.md / StrategyModel.md 等の設計ドキュメントも必ず参照してください。

補足（よくある質問）
- Q: どの DB にデータが保存されますか？
  - A: デフォルトで DUCKDB_PATH に指定したファイル（data/kabusys.duckdb）へ DuckDB 形式で保存します。監視用に sqlite（SQLITE_PATH）を別途指定可能です。
- Q: 本番環境での安全対策は？
  - A: news_collector の SSRF 対策、jquants_client のレート制御・リトライ、ETL のバックフィル/品質チェック等により堅牢化を図っています。発注周りは execution 層での追加チェックが必要です。

以上。必要であれば README にサンプル .env.example や簡易 CLI スクリプト例、より詳細な API 使用例（関数引数の説明付き）を追記します。どの情報を追加したいか教えてください。