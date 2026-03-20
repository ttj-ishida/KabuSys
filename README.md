# KabuSys README

バージョン: 0.1.0

日本株向けの自動売買 / データプラットフォーム用ライブラリです。J-Quants など外部データソースから市場データ・財務データ・ニュースを収集し、DuckDB に保存、研究（research）で計算した生ファクターを加工して特徴量を作成、戦略に基づくシグナルを生成する一連のモジュールを提供します。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要な API と実行例）
- 環境変数（必須 / 任意）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けのデータ取得・ETL・特徴量生成・シグナル生成・ニュース収集・カレンダー管理・監査ログなどを実現するモジュール群です。
- データ永続化は DuckDB を想定。ETL は J-Quants API（API クライアントを内蔵）に基づく差分取得・冪等保存設計になっています。
- 研究（research）モジュールは外部依存を極力使わず、戦略設計やバックテスト用のファクター計算を提供します。
- Strategy 層は Z スコア正規化済みの特徴量と AI スコアを統合して final_score を算出し、BUY / SELL シグナルを生成します。

機能一覧
- 環境変数 / .env ロード（自動読み込み、必要に応じて無効化可）
- J-Quants API クライアント（レート制限、リトライ、トークン自動リフレッシュ）
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
- 日次 ETL パイプライン（価格・財務・カレンダー差分取得、品質チェック呼び出し）
- ニュース収集（RSS 取得、前処理、記事ID生成、銘柄抽出、DB 保存）
- ファクター計算（momentum / volatility / value 等）
- 特徴量構築（正規化・ユニバースフィルタ・features テーブルへの upsert）
- シグナル生成（複数コンポーネントの重み付け、Bear レジーム対応、SELL エグジット判定）
- マーケットカレンダー管理（営業日判定 / next/prev / カレンダー更新ジョブ）
- 監査ログスキーマ（signal → order → execution のトレース用テーブル群）

セットアップ手順（ローカル開発向け）
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\Activate.ps1 / activate.bat）

2. 必要パッケージをインストール
   - duckdb と defusedxml が主なランタイム依存です。例:
     - pip install duckdb defusedxml
   - 開発時は setuptools 等を使ってパッケージを編集可能インストールすることを推奨:
     - pip install -e .

   （プロジェクトの requirements.txt / pyproject.toml がある場合はそちらを使用してください）

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置けます。自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数の一覧は次節を参照してください。

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで以下を実行して DB とテーブルを作成します（デフォルトパスは data/kabusys.duckdb）。
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")

使い方（主要 API と実行例）
- 簡易インポート例
  - from kabusys import __version__ などでパッケージ情報にアクセスできます。

- DuckDB の初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ親ディレクトリを自動作成

- 日次 ETL を実行（市場カレンダー・株価・財務データの差分 ETL と品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を指定することも可能
  - result は ETLResult（取得/保存件数・品質問題・エラー一覧）を返します

- 特徴量構築（features テーブルへ書き込み）
  - from kabusys.strategy import build_features
  - from datetime import date
  - count = build_features(conn, date(2025, 1, 1))

- シグナル生成（signals テーブルへ書き込み）
  - from kabusys.strategy import generate_signals
  - total = generate_signals(conn, date(2025, 1, 1))  # threshold / weights をオーバーライド可能

- ニュース収集ジョブ（RSS から raw_news 保存、銘柄紐付け）
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, known_codes=set_of_valid_codes)

- カレンダー更新ジョブ（夜間バッチ）
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)

- スキーマのみ既存 DB に接続する
  - from kabusys.data.schema import get_connection
  - conn = get_connection("data/kabusys.duckdb")  # init_schema は初回のみ実行

環境変数（必須 / 任意）
- 必須（Settings._require により未設定時は ValueError）
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API のパスワード（発注周りに使用）
  - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID

- 任意 / デフォルトあり
  - KABUSYS_ENV : "development" | "paper_trading" | "live"（デフォルト "development"）
  - LOG_LEVEL   : "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト "INFO"）
  - DUCKDB_PATH : DuckDB ファイルパス（settings.duckdb_path のデフォルトは data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 SQLite のパス（settings.sqlite_path のデフォルトは data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : "1" にすると自動 .env 読み込みを無効化

注意事項・設計ポイント（抜粋）
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時にロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API クライアントはレート制限・リトライ・401 リフレッシュを組み込んでいます。ID トークンはモジュール内でキャッシュされます。
- DuckDB への保存は基本的に冪等（ON CONFLICT で更新）になるよう設計されています。
- 研究モジュールは外部依存を可能な限り避け、DuckDB の SQL と標準ライブラリで計算を行います。
- シグナル生成はルックアヘッドバイアスを避けるため target_date 時点のデータのみを使用する設計です。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  (環境変数・設定)
  - data/
    - __init__.py
    - jquants_client.py    (J-Quants API クライアント + 保存ユーティリティ)
    - news_collector.py    (RSS 取得・前処理・保存・銘柄抽出)
    - pipeline.py          (ETL パイプライン)
    - schema.py            (DuckDB スキーマ定義・init_schema / get_connection)
    - stats.py             (zscore_normalize 等の統計ユーティリティ)
    - features.py          (zscore_normalize の再エクスポート)
    - calendar_management.py (マーケットカレンダー管理 / 更新ジョブ)
    - audit.py             (監査ログスキーマ: signal / order_request / executions)
    - (その他: quality.py 等が想定)
  - research/
    - __init__.py
    - factor_research.py   (momentum/volatility/value 等のファクター計算)
    - feature_exploration.py (将来リターン・IC・統計サマリ)
  - strategy/
    - __init__.py
    - feature_engineering.py (features の構築)
    - signal_generator.py    (final_score 算出・BUY/SELL シグナル生成)
  - execution/             (発注/実行関連モジュールのプレースホルダ)
  - monitoring/            (監視・メトリクス関連のプレースホルダ)

開発・拡張のヒント
- ETL をスケジュールするときは run_daily_etl を用いると calendar → prices → financials → 品質チェック の一連処理が行えます。
- 特徴量/シグナルの重みや閾値は generate_signals の引数で上書き可能です（テスト・A/B 用に便利）。
- ニュース収集での銘柄抽出は単純な 4 桁数字抽出を行っています。必要に応じて辞書ベースの拡張や NER を導入してください。
- DuckDB はローカルファイル（高速）で使いやすく、クエリのデバッグは conn.execute(...).fetchall() で簡単に検査できます。

ライセンス / 貢献
- 本リポジトリのライセンス情報はリポジトリルートに置く LICENSE / CONTRIBUTING を参照してください（この README には含めていません）。

お問い合わせ / バグ報告
- 問題や提案があればリポジトリの Issue を立ててください。README に含めたい補足やサンプルがあれば追記します。

以上。README に追加したい具体的な実行スクリプト例や CI / systemd / Airflow 連携例があれば教えてください。