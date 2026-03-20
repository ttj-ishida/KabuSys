KabuSys
=======

日本株向け自動売買基盤のライブラリ（部分実装）。  
主にデータ収集（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、監査用スキーマなどを含むモジュール群を提供します。

概要
----
KabuSys は日本株の quantitative trading に必要なデータプラットフォーム／戦略モジュール群を集めたパッケージです。主な目的は以下です。

- J-Quants API からの株価／財務／カレンダー取得（レートリミット・リトライ・トークン自動更新対応）
- DuckDB を用いたローカルデータベースのスキーマ定義・初期化・保存（冪等）
- ETL パイプライン（差分更新・バックフィル・品質チェック）の実装
- 研究用ファクター計算、特徴量正規化、戦略シグナル生成ロジック
- RSS ベースのニュース収集と記事→銘柄紐付け
- 発注／約定／監査用スキーマ（監査ログ保存、UUID ベースのトレーサビリティ設計）
- 環境変数管理（.env 自動ロード機能を含む）

主な機能一覧
--------------
- 環境設定
  - .env / .env.local をプロジェクトルートから自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - 必須環境変数のアクセサを提供（settings オブジェクト）

- データレイヤ（DuckDB）
  - スキーマ定義と初期化（init_schema）
  - raw / processed / feature / execution 層のテーブル定義
  - インデックス定義

- J-Quants API クライアント（kabusys.data.jquants_client）
  - トークン取得・自動リフレッシュ、固定間隔レート制御、リトライ（指数バックオフ）
  - 日足・財務・カレンダー取得および DuckDB へ冪等保存関数

- ETL（kabusys.data.pipeline）
  - 日次 ETL ジョブ run_daily_etl（カレンダー→株価→財務→品質チェック）
  - 差分取得、バックフィル、品質チェックとの統合

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理（URL 正規化・トラッキングパラメータ除去）
  - SSRF 対策、XML の安全パース（defusedxml）
  - raw_news / news_symbols への冪等保存

- 研究・特徴量（kabusys.research / kabusys.strategy）
  - ファクター計算（momentum / volatility / value）
  - クロスセクション Z スコア正規化
  - 戦略特徴量生成（build_features）
  - シグナル生成（generate_signals）：コンポーネントスコアの合成、Bear レジーム抑制、BUY/SELL ルール、エグジット判定

- 補助ユーティリティ
  - 統計ユーティリティ（zscore_normalize 等）
  - マーケットカレンダー管理（営業日判定・next/prev/get_trading_days）
  - 監査ログスキーマ（signal_events / order_requests / executions 等）

動作環境・依存
---------------
- Python 3.10 以上（PEP 604 の Union 型記法 (|) を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリで実装済の箇所が多いですが、上記は必須です。
- J-Quants API を使うには J-Quants のリフレッシュトークンが必要です。

セットアップ手順
----------------
1. リポジトリをクローン / プロジェクトルートへ移動:

   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境を作成・有効化（例）:

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール:

   pip install duckdb defusedxml

   （プロジェクトが pyproject.toml を含む場合は pip install -e . や pip install . を利用できます）

4. 環境変数を設定（.env 推奨）
   プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（package import 時）。
   主要な環境変数:

   - JQUANTS_REFRESH_TOKEN  (必須) -- J-Quants リフレッシュトークン
   - KABU_API_PASSWORD      (必須) -- kabuステーション API パスワード
   - KABU_API_BASE_URL      (任意, デフォルト http://localhost:18080/kabusapi)
   - SLACK_BOT_TOKEN        (必須) -- Slack 通知用トークン
   - SLACK_CHANNEL_ID       (必須) -- Slack チャネル ID
   - DUCKDB_PATH            (任意, デフォルト data/kabusys.duckdb)
   - SQLITE_PATH            (任意, 監視用 DB デフォルト data/monitoring.db)
   - KABUSYS_ENV            (任意, default=development) 値: development, paper_trading, live
   - LOG_LEVEL              (任意, default=INFO) 値: DEBUG, INFO, WARNING, ERROR, CRITICAL

   テストなどで自動読み込みを無効にする場合:
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマ初期化（Python REPL またはスクリプトで）:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

使い方（基本例）
----------------

- 日次 ETL を実行する（市場カレンダー・株価・財務を取得して保存）:

  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量を構築して features テーブルに保存:

  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date.today())
  print(f"features upserted: {count}")

- シグナル生成（features / ai_scores / positions を参照して signals を更新）:

  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date.today(), threshold=0.60)
  print(f"signals generated: {total}")

- ニュース収集ジョブの実行例:

  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は prices_daily 等から抽出可能。None にすると銘柄紐付けはスキップ。
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
  print(results)

注意点・設計上のポイント
-----------------------
- スキーマ定義・保存処理は可能な限り冪等（ON CONFLICT）で実装されています。
- J-Quants クライアントはレートリミット・リトライ・401 時のトークン自動更新を実装済みです。
- ニュース収集部分は SSRF 対策、XML の安全パーサ、最大受信サイズ制限を備えています。
- research / strategy 層は「ルックアヘッドバイアス」を避ける設計で、target_date 時点のデータだけを使用します。
- KABUSYS_ENV によって本番（live）/ ペーパー（paper_trading）/ 開発（development）の挙動を切替え可能（設定に応じた安全チェック等を想定）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py               -- 環境変数・設定管理（.env 自動ロード含む）
- data/
  - __init__.py
  - jquants_client.py     -- J-Quants API クライアント（fetch/save）
  - schema.py             -- DuckDB スキーマ定義・初期化
  - pipeline.py           -- ETL パイプライン（run_daily_etl 等）
  - news_collector.py     -- RSS ニュース収集・DB 保存
  - features.py           -- features 用ユーティリティ（zscore 再エクスポート）
  - stats.py              -- 統計ユーティリティ（zscore_normalize）
  - calendar_management.py-- カレンダ管理（is_trading_day / next_trading_day 等）
  - audit.py              -- 監査ログ用スキーマ DDL
  - pipeline_quality.py?  -- （品質チェックモジュール参照箇所あり、未列挙）
- research/
  - __init__.py
  - factor_research.py    -- momentum/volatility/value の計算
  - feature_exploration.py-- 将来リターン・IC・統計サマリ
- strategy/
  - __init__.py
  - feature_engineering.py-- features テーブル作成（build_features）
  - signal_generator.py   -- generate_signals（BUY/SELL 判定）
- execution/               -- 発注/実行層（パッケージ化用ディレクトリ）
- monitoring/              -- モニタリング用（SQLite等）/未実装箇所あり

（上記は主要モジュールのみ抜粋。プロジェクトに合わせてさらにファイルが存在します）

環境変数のサンプル (.env)
-------------------------
以下は最低限必要なキー例（実際の値は各自で設定）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

サポート / 開発メモ
-------------------
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して自動 .env 読み込みを抑止できます。
- DuckDB を ":memory:" で渡すとインメモリ DB を使用できます（テスト用）。
- strategy や execution 層は外部ブローカー API（kabuステーション等）への接続実装と統合することが想定されていますが、本コードは API 呼び出し依存を限定しています（特に研究/feature 関数は DB のみ参照）。

貢献
----
プルリクエスト、Issue を歓迎します。大きな設計変更は事前に Issue にて相談してください。

ライセンス
----------
（ここにプロジェクトのライセンス表記を追加してください）

以上

必要であれば、README に「具体的なコマンド例」や「よくあるトラブルシュート」セクションを追加できます。どの程度の詳細が必要か教えてください。