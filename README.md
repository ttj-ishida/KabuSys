# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリセットです。データ収集（J‑Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなど、運用に必要な主要コンポーネントを含みます。

概要
- DuckDB を用いたローカルデータベース設計（Raw / Processed / Feature / Execution 層）
- J‑Quants API からの差分取得・保存（レート制限・リトライ・トークン自動更新対応）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）と Z スコア正規化
- 戦略向け特徴量作成（build_features）と最終スコアによるシグナル生成（generate_signals）
- RSS ベースのニュース収集・記事→銘柄紐付け機能（SSRF/サイズ制限/トラッキング除去対応）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- ETL の統合ジョブ（run_daily_etl）と監査ログスキーマ

機能一覧
- data.jquants_client
  - J‑Quants API 呼び出し、ページネーション、トークン更新、保存ユーティリティ（raw_prices / raw_financials / market_calendar）
- data.schema
  - DuckDB のスキーマ定義と初期化（init_schema / get_connection）
- data.pipeline
  - 差分 ETL（run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl）
- data.news_collector
  - RSS 取得、記事整形、raw_news 保存、銘柄コード抽出、news_symbols への紐付け
- data.calendar_management
  - 営業日判定、前後営業日取得、カレンダー夜間更新ジョブ
- data.stats / data.features
  - Z スコア正規化などの統計ユーティリティ
- research.*
  - ファクター計算（calc_momentum / calc_volatility / calc_value）と解析ユーティリティ（forward returns / IC / summary）
- strategy.feature_engineering
  - ファクターの統合・フィルタリング・正規化・features テーブルへの UPSERT（build_features）
- strategy.signal_generator
  - features / ai_scores / positions を用いて final_score 計算、BUY/SELL シグナル生成（generate_signals）
- audit / execution / monitoring（スキーマ・骨組みあり）
- config
  - .env / 環境変数の自動読み込み、必須設定のラッパー（settings）

動作要件
- Python 3.10 以上（PEP 604 の型記法などを使用）
- 必須パッケージ（最低限の例）:
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, datetime, logging, math, hashlib, gzip 等

セットアップ手順

1. リポジトリを取得
   - git clone してプロジェクトルートに移動してください。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install duckdb defusedxml
   - その他 CI/要件があれば requirements.txt を用意して pip install -r requirements.txt

4. 環境変数の準備
   - プロジェクトルートに .env（または .env.local）を作成してください。
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（config.Settings で要求されるもの）:

     - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID

   - 任意 / デフォルト:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live。デフォルト: development)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL。デフォルト: INFO)

   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

5. データベース初期化
   - Python REPL またはスクリプトで以下を実行して DuckDB スキーマを作成します。

     from kabusys.data import schema
     from kabusys.config import settings
     conn = schema.init_schema(settings.duckdb_path)

使い方（代表的な操作例）

- 日次 ETL を実行してデータ取得・品質チェックを行う
  - 例: 当日分の ETL（run_daily_etl は run_prices_etl 等を順に実行します）

    from datetime import date
    from kabusys.data import pipeline, schema
    from kabusys.config import settings

    conn = schema.get_connection(settings.duckdb_path)  # init_schema で既に作成済みの場合
    result = pipeline.run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- 特徴量（features）を構築する
  - build_features は DuckDB 接続と target_date を受け取り、features テーブルへ日付単位で置換挿入します。

    from datetime import date
    from kabusys.strategy import build_features
    from kabusys.data import schema
    from kabusys.config import settings

    conn = schema.get_connection(settings.duckdb_path)
    count = build_features(conn, target_date=date(2024, 1, 15))
    print(f"{count} 銘柄を features に保存しました")

- シグナル生成（generate_signals）
  - features / ai_scores / positions を参照して BUY/SELL シグナルを生成し signals テーブルへ保存します。

    from datetime import date
    from kabusys.strategy import generate_signals
    from kabusys.data import schema
    from kabusys.config import settings

    conn = schema.get_connection(settings.duckdb_path)
    total = generate_signals(conn, target_date=date(2024, 1, 15))
    print(f"{total} 件のシグナルを書き込みました")

- ニュース収集ジョブ
  - RSS フィードから記事を取得し raw_news に保存、必要なら銘柄紐付けも行います。

    from kabusys.data.news_collector import run_news_collection
    from kabusys.data import schema
    from kabusys.config import settings

    conn = schema.get_connection(settings.duckdb_path)
    results = run_news_collection(conn, sources=None, known_codes={'7203','6758'})
    print(results)

- カレンダー更新ジョブ（夜間バッチ想定）
  - calendar_update_job を cron 等から起動して市場カレンダーを最新化します。

    from kabusys.data.calendar_management import calendar_update_job
    from kabusys.data import schema
    conn = schema.get_connection(settings.duckdb_path)
    saved = calendar_update_job(conn)

運用上のポイント / 注意事項
- 自動環境変数読み込み:
  - config モジュールはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して .env / .env.local を自動ロードします。
  - テスト等で自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- トークン管理:
  - J‑Quants の idToken は内部でキャッシュ・自動リフレッシュされます。get_id_token を明示呼び出しする際は allow_refresh に注意してください（無限再帰防止）。
- データの冪等性:
  - jquants_client の保存関数は ON CONFLICT を用いて冪等に保存する設計です。ETL は差分取得＋バックフィルを行い、API の後出しを吸収します。
- セキュリティ:
  - news_collector は SSRF 対策（スキーム検証、プライベートホスト拒否、リダイレクト検査）や XML パースに defusedxml を使用しています。
- テスト / 開発:
  - 各モジュールは外部 API 依存を極力注入可能に設計されています（id_token の差し替え、_urlopen のモック等）。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        -- J‑Quants API クライアント（取得/保存）
    - news_collector.py       -- RSS ニュース収集・保存・紐付け
    - schema.py               -- DuckDB スキーマ定義・初期化
    - stats.py                -- 統計ユーティリティ（zscore_normalize）
    - pipeline.py             -- ETL パイプライン & run_daily_etl
    - calendar_management.py  -- マーケットカレンダー管理
    - audit.py                -- 監査ログスキーマ（signal_events / order_requests / executions 等）
    - features.py             -- data.features (zscore export)
  - research/
    - __init__.py
    - factor_research.py      -- calc_momentum / calc_volatility / calc_value
    - feature_exploration.py  -- forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py  -- build_features（features テーブル作成）
    - signal_generator.py     -- generate_signals（signals テーブル生成）
  - execution/                -- (発注/約定管理のためのプレースホルダ)
  - monitoring/               -- (監視用ユーティリティ等)
- pyproject.toml / setup.py 等（プロジェクトルートに配置する想定）

貢献・拡張
- 戦略の重みや閾値は signal_generator.generate_signals の引数から調整可能です。
- news_collector の RSS ソースは DEFAULT_RSS_SOURCES を拡張してください。
- execution 層（ブローカ API 結合）やリスク管理（ポジション制約）などは現状骨組みを提供しています。実ブローカ接続は安全性を十分に考慮して実装してください。

サポート / 連絡
- README の不備やバグは Issue を立ててください。運用上の質問は Slack / チャット等で共有することを推奨します。

ライセンス
- 本リポジトリに付与されるライセンスファイルに従ってください（ここでは明示していません）。

以上がこのコードベースの概要と利用方法の説明です。必要なら「実際の cron 設定例」「systemd タイマー」「より詳細な .env.example」や「サンプルデータでのワークフロー（初回ロード手順）」などの追記を作成します。どれが必要か教えてください。