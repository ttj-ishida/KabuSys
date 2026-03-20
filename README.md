KabuSys
=======

バージョン: 0.1.0

KabuSys は日本株の自動売買に必要なデータ取得・ETL・特徴量作成・シグナル生成・ニュース収集・スキーマ管理を含むライブラリ群です。J-Quants API やローカル DuckDB を利用してデータの取得・整形を行い、戦略層（feature / signal）と実行層（execution / audit）用のテーブル設計を提供します。

主な設計方針
- DuckDB を中心としたローカルデータレイヤ（Raw / Processed / Feature / Execution）
- API 呼び出しはレートリミット、リトライ、トークン自動リフレッシュ対応
- ETL / 保存処理は冪等（ON CONFLICT / トランザクション）
- ルックアヘッドバイアス回避のため、計算は target_date 時点の情報のみ使用
- ニュース収集は SSRF 対策・XML 脆弱性対策・サイズ上限を備える

機能一覧
- データ取得（J-Quants）
  - 株価日足、財務諸表、JPX カレンダーのフェッチ（ページネーション対応）
  - レート制限・リトライ・トークン自動リフレッシュ
- DuckDB スキーマ定義・初期化（init_schema）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（momentum / volatility / value）
- 特徴量エンジニアリング（Z スコア正規化・ユニバースフィルタ）
- シグナル生成（コンポーネントスコア統合・売買シグナルの出力）
- ニュース収集（RSS 取得・前処理・記事保存・銘柄抽出）
- マーケットカレンダー管理（営業日判定・next/prev/get_trading_days）
- 監査ログ（signal → order → execution のトレーサビリティ設計）
- 共通ユーティリティ（統計関数、zscore 正規化等）

動作要件
- Python 3.10 以上（typing の | 演算子を利用）
- 主要依存パッケージ（最低限）:
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, datetime, logging, math, json 等

セットアップ手順（開発環境向け）
1. リポジトリを取得
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用）
4. 環境変数 (.env) を準備
   - プロジェクトルートに .env を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
   - 必須変数（Settings クラス参照）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb

基本的な使い方（Python スニペット例）
- DuckDB スキーマ初期化（初回のみ）
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可

- 日次 ETL 実行（株価 / 財務 / カレンダー）
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 研究用ファクター計算（単独実行）
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2024, 1, 31))

- 特徴量作成（features テーブルへ保存）
  from kabusys.strategy import build_features
  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, date(2024, 1, 31))
  print(f"features upserted: {count}")

- シグナル生成（signals テーブルへ保存）
  from kabusys.strategy import generate_signals
  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, date(2024, 1, 31), threshold=0.6)
  print(f"signals written: {total}")

- ニュース収集ジョブの実行
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes
  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "..."}  # 既知の銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)

- カレンダー / 営業日判定ユーティリティ
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  conn = get_connection("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2024,1,1)))
  print(next_trading_day(conn, date(2024,1,1)))

運用上のポイント
- J-Quants API のレート制限（120 req/min）をモジュール内で制御しますが、運用時の同時実行や外部スクリプトからの直接呼び出しに注意してください。
- ETL は差分取得 + backfill を行い、冪等に保存します（ON CONFLICT）。
- 特徴量・シグナル生成は target_date 時点の情報のみを使用するよう設計されており、ルックアヘッドバイアス対策が施されています。
- news_collector は SSRF / XML Bomb / 過大レスポンス等の脅威に対処する実装です。
- Settings.env の値は "development" / "paper_trading" / "live" のいずれかで、is_live フラグやログレベルに影響します。

よく使う API（抜粋）
- kabusys.config.settings: 環境変数ベースの設定取得
- kabusys.data.schema.init_schema(db_path): DuckDB スキーマ初期化
- kabusys.data.pipeline.run_daily_etl(conn, target_date): 日次 ETL
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes: データ取得・保存
- kabusys.research.calc_*: ファクター計算
- kabusys.strategy.build_features / generate_signals: 特徴量作成・シグナル生成
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection: ニュース収集

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py             — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得/保存）
    - news_collector.py   — RSS ニュース収集・保存・銘柄抽出
    - schema.py           — DuckDB スキーマ定義・初期化
    - stats.py            — zscore_normalize 等の統計ユーティリティ
    - pipeline.py         — ETL パイプライン（差分/バックフィル/品質チェック）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - audit.py            — 監査ログ（signal/order/execution のトレース）
    - features.py         — features 用インターフェース（再エクスポート）
  - research/
    - __init__.py
    - factor_research.py  — momentum/volatility/value の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成と保存
    - signal_generator.py    — final_score 計算と signals 生成
  - execution/             — （発注まわりの実装はここに配置予定）
  - monitoring/            — （監視/メトリクス用モジュール）

開発 / テスト向けメモ
- 自動で .env をプロジェクトルートから読み込みます（.git または pyproject.toml を探索）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- DuckDB の初期化は init_schema() が行います。テストでは ":memory:" を使うと便利です。
- news_collector._urlopen や jquants_client 内のネットワーク部分はモック可能な構造になっています。

ライセンス / コントリビューション
- （リポジトリに合わせて記載してください。ここでは明示していません。）

問い合わせ / 参考
- ソース内の docstring に設計意図・仕様参照（例: StrategyModel.md, DataPlatform.md, DataSchema.md）への言及があります。プロジェクト固有の設計ドキュメントが別途ある場合はそちらも参照してください。

以上。README の不足箇所や具体的な実行例（CI スクリプト、systemd ジョブ、Slack 通知の実装など）が必要であれば追記します。