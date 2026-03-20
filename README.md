KabuSys — 日本株自動売買基盤（README）
=====================================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・戦略・（将来的な）実行レイヤを備えた自動売買フレームワークです。  
主に次を提供します。

- J-Quants からのデータ取得と DuckDB への冪等保存（価格・財務・カレンダー等）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量構築（正規化・ユニバースフィルタ）
- シグナル生成（複数コンポーネントの加重合算、SELL/BUY 判定）
- ニュース収集（RSS → raw_news、銘柄抽出）
- DuckDB スキーマ定義と初期化ユーティリティ

設計方針の要点
- ルックアヘッドバイアス回避（target_date 時点のデータのみを使用）
- 冪等性（DB 保存は ON CONFLICT を利用）
- 外部 API 呼び出しは data 層に集中（戦略層は発注層に依存しない）
- テスト容易性（id_token 注入等）

主な機能一覧
----------------
- データ取得・保存
  - J-Quants API クライアント（fetch/save：日足、財務、カレンダー）
  - レート制限・リトライ・自動トークンリフレッシュ
- ETL パイプライン
  - run_daily_etl: カレンダー → 日足 → 財務 → 品質チェック
  - 差分更新 / バックフィル対応
- スキーマ管理
  - init_schema / get_connection（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義
- リサーチ（研究用）
  - ファクター計算: calc_momentum / calc_volatility / calc_value
  - 将来リターン計算 / IC / 統計サマリー
- 特徴量 & シグナル
  - build_features: 生ファクターを正規化し features テーブルへ保存
  - generate_signals: features + ai_scores 統合で BUY/SELL を生成し signals テーブルへ保存
- ニュース収集
  - RSS 取得（SSRF対策、gzip制限、トラッキング除去）
  - raw_news / news_symbols への冪等保存

セットアップ手順
----------------

1. Python 仮想環境を作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要なパッケージをインストール
   - プロジェクトに requirements.txt がある場合はそれを利用してください。
   - 最低限必要な主要ライブラリ（例）:
     - duckdb
     - defusedxml
   例:
     - pip install duckdb defusedxml
   パッケージ配布用に setup.cfg / pyproject.toml を用意している場合:
     - pip install -e .

3. 環境変数設定
   - プロジェクトルート（.git か pyproject.toml がある場所）に .env を置くと自動で読み込まれます（※自動読込は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須（少なくとも戦略連携や API 呼び出しで必要）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      : kabuステーション API パスワード（発注連携が必要な場合）
     - SLACK_BOT_TOKEN       : Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|...) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
   - 参考: .env.example を基に .env を作成してください（プロジェクトに同梱されている想定）。

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで初期化します。
   例:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)

使い方（主要な API サンプル）
-----------------------------

- DB 初期化（1回）
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行（市場カレンダー→日足→財務→品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

- 特徴量構築（target_date の features を作る）
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, date(2025, 1, 31))
  print(f"upserted features: {n}")

- シグナル生成（features と ai_scores を用いて signals に書き込む）
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2025, 1, 31))
  print(f"signals written: {total}")

- ニュース収集ジョブ（RSS 収集 → raw_news / news_symbols へ保存）
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)

- カレンダー更新ジョブ（夜間バッチ想定）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)

設定・運用上のポイント
- 自動 .env 読み込みはプロジェクトルートを基準に探索します。テストや CI で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV により挙動（paper_trading/live 等）を切替できます。settings.is_live / is_paper / is_dev を参照してください。
- J-Quants API のレート制限（120 req/min）や 401 リフレッシュ、リトライ戦略は jquants_client に実装済みです。
- RSS 収集は SSRF・gzip爆弾・トラッキング除去等の対策を備えています。
- DB への挿入は可能な限り冪等（ON CONFLICT）で設計されています。

ディレクトリ構成（主要ファイル）
---------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数/設定管理（settings オブジェクト）
- data/
  - __init__.py
  - jquants_client.py          — J-Quants API クライアント（fetch/save）
  - news_collector.py         — RSS 収集・前処理・DB保存
  - schema.py                 — DuckDB スキーマ定義と init_schema/get_connection
  - stats.py                  — zscore_normalize 等の統計ユーティリティ
  - pipeline.py               — ETL パイプライン（run_daily_etl 等）
  - features.py               — data 層の特徴量ユーティリティ再エクスポート
  - calendar_management.py    — カレンダー管理 / バッチ更新ジョブ
  - audit.py                  — 監査ログ（signal → order → execution のトレーサビリティ）
- research/
  - __init__.py
  - factor_research.py        — calc_momentum / calc_volatility / calc_value
  - feature_exploration.py    — 将来リターン / IC / 統計要約
- strategy/
  - __init__.py
  - feature_engineering.py    — build_features（正規化・ユニバースフィルタ）
  - signal_generator.py       — generate_signals（最終スコア算出・BUY/SELL判定）
- execution/
  - __init__.py               — 実行レイヤのスケルトン（発注連携は別途実装想定）
- （monitoring 等は将来モジュールとして想定されることがあります）

注意・既知の未実装点
- execution 層（実際のブローカー連携）の多くは骨組みで、実運用用のアダプタ（kabu API との具体的な送受信処理）は個別実装が必要です。
- 一部の監査・トレーシング DDL は設計方針に従っているものの、運用に合わせた追加カラムや FK ポリシーの調整が必要になる場合があります。
- AI スコア（ai_scores）はデータ供給側（別プロセス）が必要です。本リポジトリではスコアの読み込み・結合ロジックのみ実装しています。

開発・テスト
-------------
- settings は .env または環境変数から読み込みます。テスト時に自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。
- DuckDB のインメモリ接続は init_schema(":memory:") で利用できます（ユニットテストで便利）。
- ネットワーク呼び出しを行うモジュール（jquants_client, news_collector など）は、HTTP 層／_urlopen 等をモックしてテスト可能です。

問い合わせ / 貢献
-----------------
- 本ドキュメントはリポジトリのコードベース（src/kabusys 以下）を基に生成されています。  
- バグ報告や機能追加は Issue を使ってください。パッチは PR を歓迎します。

付録: よく使うコードスニペット
----------------------------
- settings の参照
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env, settings.log_level)

- 簡易ワーカ（ETL → feature → signal の流れ）
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.strategy import build_features, generate_signals
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)
  etl_res = run_daily_etl(conn)
  from datetime import date
  today = etl_res.target_date
  build_features(conn, today)
  generate_signals(conn, today)

以上。プロジェクトの各モジュールに詳細な docstring が付与されているため、実装の理解や拡張は各ファイル内のコメント・関数説明を参照してください。