KabuSys
=======

概要
----
KabuSys は日本株の自動売買プラットフォーム向けライブラリ群です。  
データ取得（J-Quants 等）→ データ整形（DuckDB）→ ファクター計算 → シグナル生成 → 発注トレースまでの主要コンポーネントを提供します。  
パッケージはモジュール化されており、ETL／リサーチ／戦略ロジック／実行監査の各層を分離して実装しています。

バージョン
---------
0.1.0

主な機能一覧
------------
- 環境変数・設定管理
  - .env, .env.local 自動読み込み（プロジェクトルート検出）
  - 必須設定を明確化（未設定で例外）
- データ取得・保存（data）
  - J-Quants API クライアント（ページネーション、リトライ、レート制御、トークン自動更新）
  - RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、記事ID生成）
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - ETL パイプライン（差分取得、バックフィル、品質チェックフック）
  - マーケットカレンダー管理（営業日判定、next/prev/get_trading_days、夜間更新ジョブ）
  - 監査ログ（signal → order → execution のトレーサビリティ）
  - 汎用統計ユーティリティ（Zスコア正規化等）
- リサーチ（research）
  - ファクター計算（Momentum/Volatility/Value 等）
  - 将来リターン計算、IC（Spearman）やファクター統計サマリ
- 戦略（strategy）
  - 特徴量エンジニアリング（生ファクターの正規化・ユニバースフィルタ）
  - シグナル生成（コンポーネントスコア統合、Bear レジーム抑制、BUY/SELL 判定）
- ニュース処理
  - RSS 取得・前処理・DB 保存・銘柄抽出（記事 ⇔ 銘柄紐付け）
- 発注・実行監視（audit / execution 層のスキーマ・ログ基盤）
- 冪等性とトランザクション設計（DuckDB 側で ON CONFLICT 等を使用）

必須環境変数
-------------
Settings クラスで参照する主な環境変数（プロダクション実行時は必須）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション等の API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境 ("development", "paper_trading", "live")（デフォルト development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)（デフォルト INFO）

.env 自動読み込み:
- プロジェクトルート（.git または pyproject.toml がある場所）から .env → .env.local を自動で読み込みます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト等に便利）。

セットアップ手順
---------------
前提: Python 3.9+（コードは typing / 型注釈を利用）。必須パッケージ例:

- duckdb
- defusedxml

例（仮想環境推奨）:
1. リポジトリをクローンし、パッケージをインストール
   - pip install -e .  または pip install .

2. 依存パッケージをインストール
   - pip install duckdb defusedxml

3. 環境変数を設定
   - プロジェクトルートに .env を作成する例:
     JQUANTS_REFRESH_TOKEN=your_token
     KABU_API_PASSWORD=your_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb

   - または環境変数としてエクスポートしてください。

4. DuckDB スキーマ初期化（Python REPL またはスクリプト）
   - Python 例:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)

使い方（主なユースケース）
-------------------------

1) DuckDB 初期化
- 1回だけ実行してデータベースとテーブルを作成します。

  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)

2) 日次 ETL 実行（株価・財務・カレンダー）
- run_daily_etl を使うと市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック まで実行します。

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

3) 特徴量計算（戦略用）
- DuckDB に格納された raw/processed データから features テーブルを構築します。

  from kabusys.strategy import build_features
  from datetime import date
  build_features(conn, date(2026, 1, 31))

4) シグナル生成
- features / ai_scores / positions を参照して BUY/SELL を算出し signals テーブルへ書き込みます。

  from kabusys.strategy import generate_signals
  generate_signals(conn, date(2026, 1, 31), threshold=0.6)

5) ニュース収集ジョブ
- RSS フィードを取得して raw_news と news_symbols に保存します。

  from kabusys.data.news_collector import run_news_collection
  # known_codes: 銘柄コードセットを渡すことで記事中の銘柄抽出を有効化
  results = run_news_collection(conn, known_codes={"7203", "6758"})

6) カレンダー更新ジョブ（夜間バッチ）
- calendar_update_job を呼び出して market_calendar を更新します。

  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)

設定とデバッグ
--------------
- ログレベルは LOG_LEVEL 環境変数で制御します。
- 自動 .env 読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings.is_live / is_paper / is_dev で実行環境判定ができます。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数・設定管理(.env ロード等)
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py       — RSS 取得・記事保存・銘柄抽出
  - schema.py               — DuckDB スキーマ定義・初期化
  - stats.py                — 統計ユーティリティ（zscore_normalize）
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - features.py             — data 層の特徴量ユーティリティ公開
  - calendar_management.py  — マーケットカレンダー管理
  - audit.py                — 発注/約定の監査ログ定義
  - (その他: quality 等が参照される想定)
- research/
  - __init__.py
  - factor_research.py      — Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py  — 将来リターン/IC/統計サマリ
- strategy/
  - __init__.py
  - feature_engineering.py  — 生ファクターの正規化・ユニバースフィルタ・features テーブル書込
  - signal_generator.py     — final_score 計算・BUY/SELL 生成・signals 書込
- execution/                 — 発注実行・ブローカー連携（パッケージ化済みインターフェースを想定）
- monitoring/                — 監視/メトリクス（将来的に拡張）

開発・テストのヒント
--------------------
- settings で自動 .env 読み込みが行われるため、ユニットテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してから settings をインポートすると良いです。
- DuckDB のテストは ":memory:" を使ってインメモリ DB を作成できます（init_schema(":memory:")）。
- jquants_client の外部呼び出しはネットワーク依存になるため、get_id_token / _request 等をモックしてユニットテストを行ってください。
- news_collector._urlopen などはユニットテストで差し替え可能なように設計されています。

ライセンス / 貢献
-----------------
本リポジトリにライセンス情報が含まれている場合はそれに従ってください。  
バグ報告・機能提案・プルリクエストはリポジトリの issue / PR を通じて受け付けてください。

補足
----
- 詳細な設計仕様（StrategyModel.md, DataPlatform.md, 等）はリポジトリ内のドキュメントまたは設計ファイルを参照してください。  
- 本 README はコードベースの主要機能と使い方の要約です。実運用前に十分なテスト・検証を行ってください。