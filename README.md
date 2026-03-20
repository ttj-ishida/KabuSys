KabuSys
=======

バージョン: 0.1.0

日本株向けの自動売買プラットフォーム向けライブラリの一部です。データ収集（J‑Quants）、ETL、特徴量の生成、シグナル生成、ニュース収集、監査/スキーマ管理等の機能を提供します。DuckDB を内部データストアとして利用することを前提とした設計になっています。

主な特徴
--------

- J‑Quants API クライアント（ページネーション、レートリミット、トークン自動リフレッシュ、リトライ機構）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit レイヤー）
- ETL パイプライン（差分更新、バックフィル、品質チェック連携）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ）
- シグナル生成（複数コンポーネントの統合スコア、Buy/Exit ルール、Bear レジーム抑制）
- ニュース収集（RSS 取得、URL 正規化、SSRF 対策、銘柄コード抽出）
- 監査ログ（signal → order → execution をトレース可能なテーブル群）
- 環境設定管理（.env 自動読み込み、必須環境変数検査）

必要な環境変数
--------------

必須 (実行に必要)
- JQUANTS_REFRESH_TOKEN — J‑Quants リフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション向けパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)、デフォルトは development
- LOG_LEVEL — ログレベル (DEBUG / INFO / WARNING / ERROR / CRITICAL)、デフォルト INFO

自動 .env ロード
- プロジェクトルート（.git または pyproject.toml を探索）から .env, .env.local を自動ロードします。
- 優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <リポジトリ>
2. Python バージョン
   - Python 3.9+ を推奨（コードは型注釈で modern な構文を使用）
3. 依存パッケージをインストール
   - 代表的な必要パッケージ: duckdb, defusedxml
   - 例: pip install duckdb defusedxml
   - 開発環境向けに requirements.txt / pyproject.toml があればそちらを使用してください
4. 環境変数を設定
   - .env (または .env.local) を作成して必要な値を設定してください
   - 例（.env の最小例）:
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
5. データベース初期化（DuckDB）
   - Python コンソールまたはスクリプトで schema.init_schema を呼び出してテーブルを作成します（デフォルトは data/kabusys.duckdb）。
   - 例:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

基本的な使い方
--------------

以下は代表的な操作例（Python スクリプト内で実行）です。

1) DuckDB スキーマ初期化
- schema.init_schema(db_path) が既存スキーマの有無を検査し、必要なテーブルとインデックスを作成します。

2) 日次 ETL の実行（株価 / 財務 / カレンダー）
- data.pipeline.run_daily_etl を使用して差分取得＆保存を行います。
  - 引数で target_date, id_token, backfill_days 等を制御できます。
  - ETLResult が返り、取得件数・保存件数・品質問題・エラーを確認できます。

3) 特徴量作成
- strategy.feature_engineering.build_features(conn, target_date)
  - research モジュールの生ファクターを取得 → ユニバースフィルタ → Z スコア正規化 → features テーブルへ UPSERT

4) シグナル生成
- strategy.signal_generator.generate_signals(conn, target_date, threshold=0.6, weights=None)
  - features / ai_scores / positions を参照して BUY / SELL シグナルを作成し signals テーブルへ保存します

5) ニュース収集
- data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
  - RSS フィードを取得、raw_news に保存、必要なら銘柄コードの紐付け(news_symbols) を行います

簡単なサンプルスクリプト
- DB 初期化と日次 ETL、特徴量生成、シグナル生成の流れ（概略）
  from datetime import date
  from kabusys.data import schema, pipeline
  from kabusys.strategy import build_features, generate_signals

  conn = schema.init_schema("data/kabusys.duckdb")
  etl_res = pipeline.run_daily_etl(conn, target_date=date.today())
  # ETL の成功を確認してから特徴量→シグナルを実行するのが望ましい
  build_features(conn, target_date=date.today())
  generate_signals(conn, target_date=date.today())

主要モジュール / API（抜粋）
--------------------------

- kabusys.config
  - settings: 環境変数に基づくアプリ設定アクセサ
  - 自動 .env 読み込みロジック、必須 env チェック

- kabusys.data
  - jquants_client: J‑Quants API クライアント、fetch_* / save_* 系の関数
    - fetch_daily_quotes / save_daily_quotes
    - fetch_financial_statements / save_financial_statements
    - fetch_market_calendar / save_market_calendar
  - schema: init_schema / get_connection
  - pipeline: run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - news_collector: fetch_rss / save_raw_news / run_news_collection
  - calendar_management: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - stats: zscore_normalize

- kabusys.research
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank

- kabusys.strategy
  - build_features (feature_engineering)
  - generate_signals (signal_generator)

ディレクトリ構成（主要ファイル）
------------------------------

src/kabusys/
- __init__.py
- config.py                      — 環境設定 / .env ロード
- data/
  - __init__.py
  - jquants_client.py             — J‑Quants API クライアント（取得/保存）
  - pipeline.py                   — ETL パイプライン
  - schema.py                     — DuckDB スキーマ定義・初期化
  - news_collector.py             — RSS 収集・保存・銘柄抽出
  - calendar_management.py        — マーケットカレンダー管理
  - audit.py                      — 監査ログ用スキーマ
  - stats.py                      — 統計ユーティリティ（z スコア等）
  - features.py                   — zscore_normalize の再エクスポート
- research/
  - __init__.py
  - factor_research.py            — ファクター計算（mom/vol/value 等）
  - feature_exploration.py        — IC / 将来リターン / 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py        — features テーブル生成
  - signal_generator.py           — final_score 計算と signals 生成
- execution/                       — 発注 / execution 層（パッケージは存在）
- monitoring/                      — 監視・メトリクス等（パッケージは存在）

運用上の注意 / 設計上の留意点
-----------------------------

- ルックアヘッドバイアス回避: feature / signal の計算は target_date 時点で入手可能なデータのみを使用するよう設計されています。
- 冪等性: DB 保存は ON CONFLICT / トランザクションを多用して冪等性を担保しています。
- レート制限: J‑Quants のレート制限 (120 req/min) に適合する RateLimiter を組み込んでいます。
- セキュリティ: news_collector では SSRF 対策、XML の安全パーサ（defusedxml）、レスポンスサイズ制限 を実装しています。
- テスト: config の自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能で、テスト環境での副作用を抑制できます。

トラブルシューティング
----------------------

- 環境変数不足で ValueError が発生する場合があります。settings のプロパティは必須 env をチェックします (.env.example を参照して .env を用意してください)。
- DuckDB の初期化に失敗する場合は parent ディレクトリの書き込み権限やパスの指定を確認してください。
- J‑Quants API で 401 が返る場合、get_id_token によりリフレッシュが試行されますが、refresh token が無効だとエラーになります。

ライセンス / 貢献
-----------------

- 本リポジトリのライセンスや貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

最後に
-----

この README はコードベースの現状に基づいて作成しています。実際の運用では運用手順書（運用ジョブの cron/ワーカー設定、監視・通知設定、バックアップ方針等）を追加することを推奨します。必要であれば README にサンプル .env.example、DB 初期データロード手順、CI テスト手順などを追記します。