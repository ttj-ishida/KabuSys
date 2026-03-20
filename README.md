KabuSys
=======

日本株向けの自動売買プラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、DuckDBベースのデータスキーマ、ETLパイプライン、ファクター計算・特徴量整備、シグナル生成、ニュース収集、カレンダー管理、監査ログなど、投資戦略の研究〜運用までの主要コンポーネントを提供します。

主な目的
- J-Quants からのデータ取得・保存（冪等）
- DuckDB を用いたローカルデータプラットフォーム（Raw / Processed / Feature / Execution 層）
- 研究（factor 計算 / 特徴量探索）と戦略（feature → signals）を分離した設計
- ニュース収集・紐付け、マーケットカレンダー管理、ETL の品質チェック

機能一覧
- 環境変数管理（kabusys.config）
  - プロジェクトルートの .env / .env.local 自動ロード（必要に応じて無効化可）
  - 必須環境変数取得ヘルパー
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント（レート制御、リトライ、トークン自動更新）
  - 株価・財務・マーケットカレンダー取得 + DuckDB へ冪等保存
- データスキーマ初期化（kabusys.data.schema）
  - DuckDB テーブル定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(db_path) による初期化
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分更新・バックフィル・品質チェックの統合
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、正規化ID生成、raw_news への冪等保存
  - 記事中の 4 桁銘柄コード抽出と news_symbols への紐付け
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days 等
  - calendar_update_job による差分更新
- 研究用ファクター計算（kabusys.research）
  - calc_momentum / calc_volatility / calc_value（prices_daily, raw_financials を参照）
  - IC 計算・将来リターン計算などの探索ユーティリティ
- 特徴量構築（kabusys.strategy.feature_engineering）
  - research 側の生ファクターを統合・正規化して features テーブルへ UPSERT
  - ユニバースフィルタ（最低株価・売買代金）や Z スコアクリップ等を実装
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出し BUY/SELL シグナルを作成
  - Bear レジーム抑制、エグジット（ストップロス等）判定、signals テーブルへの冪等保存
- 汎用統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize（クロスセクション標準化）

前提条件 / インストール
- Python 3.10+
  - （コードに | 型ヒントがあり、Python 3.10 以降が必要です）
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml

例（pip）:
  pip install duckdb defusedxml
プロジェクトをeditableインストールできる場合:
  pip install -e .

環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）

.env 自動読み込み
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を探索）を見つけると自動で .env と .env.local を読み込みます。
  - 読み込み優先: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時等に便利です）。

セットアップ手順（簡易クイックスタート）
1. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （その他、運用で必要なライブラリを適宜インストール）

2. .env を作成（例）
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

3. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
   - ":memory:" を渡すとインメモリ DB を使用できます

4. 日次 ETL を実行（例）
     from kabusys.data.pipeline import run_daily_etl
     result = run_daily_etl(conn)  # target_date を指定可能
     print(result.to_dict())

5. 特徴量構築 → シグナル生成
     from datetime import date
     from kabusys.strategy import build_features, generate_signals
     target = date.today()  # または適当な営業日
     n_feat = build_features(conn, target)         # features テーブルに書き込み
     n_signals = generate_signals(conn, target)   # signals テーブルに書き込み

6. ニュース収集（任意）
     from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
     # known_codes は銘柄抽出に使う有効銘柄コード集合（例: 全コードセット）
     results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set_of_codes)

7. カレンダー更新バッチ
     from kabusys.data.calendar_management import calendar_update_job
     saved = calendar_update_job(conn)

使い方（補足サンプル）
- 初期化および ETL → 特徴量 → シグナル生成の流れ（簡易）:

  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.strategy import build_features, generate_signals
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  # 日次 ETL（市場カレンダー・株価・財務）
  etl_result = run_daily_etl(conn)
  print(etl_result.to_dict())

  # 特徴量構築・シグナル生成（営業日を渡す）
  today = date.today()
  build_cnt = build_features(conn, today)
  signals_cnt = generate_signals(conn, today)

- ニュース収集と銘柄紐付け:
  articles_saved = run_news_collection(conn, sources=None, known_codes=known_codes_set)

注意事項 / 運用上のヒント
- J-Quants API はレートリミット（120 req/min）に従う必要があります。本クライアントは固定間隔スロットリングと再試行ロジックを備えていますが、運用量には注意してください。
- DuckDB のファイルはバックアップしてください。init_schema は既存テーブルがあれば重複作成せず安全に呼べます。
- features / signals 等は日付単位で置換（DELETE→INSERT）するため冪等です。再処理が安全に行えます。
- 開発環境 / paper_trading / live は KABUSYS_ENV で切り替えます。is_live / is_paper / is_dev のプロパティが settings に用意されています。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動ロードを抑制できます。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py            # J-Quants API クライアント + 保存関数
      - news_collector.py            # RSS 収集・前処理・保存
      - schema.py                    # DuckDB スキーマ & init_schema
      - stats.py                     # zscore_normalize 等
      - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
      - features.py                  # data.stats の再エクスポート
      - calendar_management.py       # カレンダー判定・更新ジョブ
      - audit.py                     # 監査ログ用 DDL（途中まで定義）
    - research/
      - __init__.py
      - factor_research.py           # momentum/value/volatility の計算
      - feature_exploration.py       # 将来リターン/IC/統計サマリー
    - strategy/
      - __init__.py
      - feature_engineering.py       # features テーブル構築
      - signal_generator.py          # final_score 計算 & signals 作成
    - execution/                      # 発注層（プレースホルダ）
      - __init__.py
    - monitoring/                     # 監視用モジュール（未表示ファイル群）
      (エントリや補助モジュールが配置される想定)

ドキュメント / 設計参照
- 各モジュールの docstring に設計方針や参照するドキュメント（StrategyModel.md, DataPlatform.md, DataSchema.md 等）への言及があります。実装の理解や拡張時に参照してください。

ライセンス / コントリビューション
- 本リポジトリに LICENSE ファイルがあればそちらを参照してください。コントリビュート方針はプロジェクトルートの CONTRIBUTING や ISSUE テンプレートに従ってください。

最後に
- この README はコードベースの主要な使い方とモジュール責務をまとめたものです。実運用では監視、アラート、リスク管理（ポジションサイズ管理、ドローダウン制限等）を別途実装・監査してください。必要があれば README を拡張して運用手順や例（systemd タスク、Docker / Cron での運用、Slack 通知連携方法等）を追加できます。