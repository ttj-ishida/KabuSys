KabuSys — 日本株自動売買プラットフォーム（README）
=================================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・戦略・発注監査を含む自動売買システムのコードベースです。本リポジトリは以下の機能をモジュール化して提供します。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いたデータスキーマと永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）と記事→銘柄の紐付け
- 研究（factor 計算、IC/リターン計算、特徴量探索）
- 特徴量エンジニアリング（クロスセクション正規化、ユニバースフィルタ）
- シグナル生成（複数コンポーネントを統合した final_score 計算、BUY/SELL 判定）
- 発注・監査用スキーマ（監査ログ／order_requests／executions）
- 設定管理（.env / 環境変数の自動読み込み）

主な機能一覧
-------------
- data.jquants_client
  - J-Quants API クライアント（認証、自動リフレッシュ、ページネーション、リトライ、レートリミット）
  - fetch/save 関数: fetch_daily_quotes / save_daily_quotes, fetch_financial_statements / save_financial_statements, fetch_market_calendar / save_market_calendar
- data.schema
  - DuckDB 用スキーマ定義と初期化（init_schema / get_connection）
  - Raw / Processed / Feature / Execution 層のテーブルを定義
- data.pipeline
  - 日次 ETL（run_daily_etl）・個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 差分取得・バックフィル・品質チェックを実装
- data.news_collector
  - RSS フィード取得（SSRF 対策・gzip/サイズ制限・XML 安全パース）
  - raw_news 保存、news_symbols への紐付け、自動重複排除
- data.calendar_management
  - 営業日判定、next/prev_trading_day、calendar_update_job 等
- research.*
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns, calc_ic（Spearman）、factor_summary, rank
- strategy.feature_engineering
  - 生ファクターのマージ、ユニバースフィルタ、Z スコア正規化、features テーブルへの UPSERT（冪等）
- strategy.signal_generator
  - features と ai_scores を組み合わせ final_score を計算して BUY/SELL シグナルを作成し signals テーブルへ保存
- config
  - .env 自動読み込み（プロジェクトルート検出）と Settings クラス（settings オブジェクト）による一元管理

動作環境・依存
----------------
- Python 3.10+
  - 理由: 新しい型注釈（X | Y）等を使用しているため
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, logging, datetime, json 等）

セットアップ手順
----------------
1. リポジトリをクローン／配置
   - 例: git clone <repo>

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （開発用: pip install -e . が使える場合は packaging に従ってください）

4. 環境変数設定（.env）
   - プロジェクトルートに .env または .env.local を作成します。config モジュールが自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャネル ID（必須）
   - オプション:
     - KABUSYS_ENV — 開発モード: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）

5. DB スキーマ初期化（DuckDB）
   - Python REPL またはスクリプトで:
     from kabusys.data import schema
     from kabusys.config import settings
     conn = schema.init_schema(settings.duckdb_path)
   - init_schema はテーブル作成を冪等に行います。":memory:" 指定でメモリ DB を利用可能。

基本的な使い方（コード例）
-------------------------
以下は代表的なワークフローのサンプルです。

1) DuckDB 接続とスキーマ初期化
- 例:
  from kabusys.data import schema
  from kabusys.config import settings
  conn = schema.init_schema(settings.duckdb_path)

2) 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
- 例:
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

3) 特徴量構築（feature テーブル作成）
- 例:
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")

4) シグナル生成
- 例:
  from kabusys.strategy import generate_signals
  total_signals = generate_signals(conn, target_date=date.today())
  print(f"total signals written: {total_signals}")

5) ニュース収集ジョブ
- 例:
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 事前に利用可能な銘柄コードセットを用意
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

6) カレンダー更新バッチ
- 例:
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

重要な設計上の注意点
-------------------
- ルックアヘッドバイアス回避: 研究・特徴量計算・シグナル生成はすべて target_date 时点のデータのみを参照する設計です。
- 冪等性: DB への保存は ON CONFLICT/UPSERT を多用しており、同一データの重複投入に強い実装です。
- ネットワーク安全: news_collector は SSRF 対策、受信サイズ制限、defusedxml による XML 安全処理を行います。
- API リトライとレート制御: jquants_client は指数バックオフ、HTTP ステータスに基づくリトライ、固定間隔スロットリング（120 req/min）を実装しています。
- 環境変数の自動ロード: config モジュールはプロジェクトルート（.git または pyproject.toml）を検出して .env/.env.local を自動読み込みします。テストで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

設定項目（主な環境変数）
-----------------------
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUS_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化（値を設定すると無効）

ディレクトリ構成
----------------
（主要ファイル／モジュールと簡単な説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - news_collector.py     — RSS ニュース収集と保存
    - schema.py             — DuckDB スキーマ定義と init_schema/get_connection
    - stats.py              — zscore_normalize 等の統計ユーティリティ
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py— カレンダー更新・営業日判定
    - features.py           — features 用ラッパー（zscore 再エクスポート）
    - audit.py              — 発注／約定の監査ログ DDL（部分ファイル）
    - execution/ (パッケージ)
  - research/
    - __init__.py
    - factor_research.py    — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py— calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py — features 構築（build_features）
    - signal_generator.py    — シグナル生成（generate_signals）
  - execution/ (将来的な発注実装用)
  - monitoring/ (監視・メトリクス用)

ライセンス・貢献
----------------
- 本ドキュメントにはライセンス情報を含めていません。実際のリポジトリに LICENSE ファイルがある場合はそれを参照してください。
- コントリビューションはプルリクエスト／イシューでお願いします。設計ドキュメント（StrategyModel.md / DataPlatform.md 等）を参照しつつ、既存のインタフェース設計を尊重してください。

トラブルシューティング
---------------------
- .env が読み込まれない:
  - プロジェクトルートが .git または pyproject.toml で検出されるか確認してください。
  - 自動読み込みを無効にしている場合（KABUSYS_DISABLE_AUTO_ENV_LOAD）には手動で環境変数を設定してください。
- DuckDB の接続や権限エラー:
  - DUCKDB_PATH の親ディレクトリが作成されているか、ファイルアクセス権限を確認してください。
- J-Quants API 401 エラー:
  - JQUANTS_REFRESH_TOKEN を確認し、get_id_token が正常に動作するかテストしてください。jquants_client は 401 時にトークンを自動更新しますが、設定が正しい必要があります。

最後に
-----
本 README はコードベースの主要部分を簡潔にまとめたものです。各モジュールの詳細はソースコードの docstring とコメントを参照してください。さらに詳しい運用手順や設計ドキュメント（StrategyModel.md / DataPlatform.md / DataSchema.md 等）がある場合は併せて参照してください。

必要であれば、具体的な運用スクリプト例（cron / GitHub Actions / systemd unit）や、より詳細な ETL 運用手順・監査ワークフローの README も作成します。ご希望があれば教えてください。