KabuSys — 日本株自動売買プラットフォーム（README 日本語版）

プロジェクト概要
- KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤のライブラリです。
- DuckDB をデータレイクとして用い、J-Quants から市場データ・財務データを取得して ETL → 特徴量作成 → シグナル生成 → 発注（実装層は別）までのパイプラインを提供します。
- 研究（research）用のファクター計算、特徴量正規化、AI スコア統合、ニュース収集、マーケットカレンダー管理、監査ログなどのモジュールを含みます。

主な機能（抜粋）
- データ取得・保存
  - J-Quants API クライアント（jquants_client）
  - raw_prices / raw_financials / market_calendar 等の冪等保存（ON CONFLICT 対応）
- ETL パイプライン
  - 差分取得（バックフィル対応）と品質チェックを含む日次 ETL（data.pipeline.run_daily_etl）
- スキーマ管理
  - DuckDB スキーマ初期化（data.schema.init_schema）
- 研究・特徴量
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - Z スコア正規化（data.stats.zscore_normalize）
  - 特徴量を作成して features テーブルへ保存（strategy.feature_engineering.build_features）
- シグナル生成
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを signals テーブルへ保存（strategy.signal_generator.generate_signals）
- ニュース収集
  - RSS からニュースを取得・整形・保存し銘柄紐付けを行う（data.news_collector）
- マーケットカレンダー管理
  - 営業日判定・next/prev_trading_day 等のユーティリティ（data.calendar_management）
- 監査ログ
  - signal_events / order_requests / executions 等の監査テーブル定義（data.audit）

必要条件
- Python 3.10+
- duckdb
- defusedxml
（外部ライブラリはモジュールによって異なります。pip インストール時に必要パッケージを指定してください）

セットアップ手順（ローカル開発想定）
1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージインストール
   - pip install -e .    （プロジェクトがパッケージ化されている前提）
   - 必要に応じて duckdb, defusedxml を追加でインストール:
     - pip install duckdb defusedxml

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml を含む）に .env または .env.local を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（Settings で必須・既定値が定義されているもの）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (任意, デフォルト http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須)
     - SLACK_CHANNEL_ID (必須)
     - DUCKDB_PATH (任意, デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (任意, デフォルト data/monitoring.db)
     - KABUSYS_ENV (development/paper_trading/live, default development)
     - LOG_LEVEL (DEBUG/INFO/... , default INFO)

環境ファイルのパース挙動（補足）
- .env の行はコメント行（# 始まり）や export KEY=val 形式に対応します。
- 値のクォート、エスケープ、インラインコメント等に柔軟に対応します。
- 読み込み順: OS 環境変数 > .env.local > .env（.env.local は .env を上書き）
- プロジェクトルートが特定できない場合は自動ロードをスキップします。

データベース初期化
- DuckDB スキーマを初期化して接続を得るには data.schema.init_schema を使います。例:

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可

- init_schema は必要なテーブルをすべて作成します（冪等）。

簡単な使い方（コードスニペット）
- 日次 ETL を実行（J-Quants トークンは settings から自動取得）:

  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量作成（features テーブルに書き込む）:

  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 1, 10))
  print(f"features upserted: {n}")

- シグナル生成（signals テーブルに書き込む）:

  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025,1,10))
  print(f"signals written: {total}")

- ニュース収集ジョブ（RSS 収集→raw_news保存→news_symbols紐付け）:

  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 例: 有効銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- マーケットカレンダー更新（夜間ジョブ）:

  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

運用上の注意
- J-Quants API のレートリミット（120 req/min）を尊重する設計になっています（内部でスロットリング）。
- API リクエストはリトライ（指数バックオフ）とトークン自動リフレッシュに対応しています。
- ETL は差分取得かつバックフィルを行い、API の後出し修正に対応します。
- features / signals の各処理は「日付単位で DELETE → INSERT（トランザクション）」しており冪等性を保ちます。
- news_collector は SSRF・XML バンプ・大容量応答などの安全対策を実装しています（URL 検証、受信サイズ制限、defusedxml 等）。

ディレクトリ構成（src 以下の主なファイル・モジュール）
- src/kabusys/
  - __init__.py (パッケージ定義、バージョン)
  - config.py (環境変数・設定管理: Settings)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント)
    - news_collector.py (RSS ニュース収集 / 保存)
    - schema.py (DuckDB スキーマ定義・初期化)
    - stats.py (統計ユーティリティ: zscore_normalize)
    - pipeline.py (ETL パイプライン)
    - features.py (zscore_normalize の再エクスポート)
    - calendar_management.py (カレンダー更新・営業日ユーティリティ)
    - audit.py (監査ログテーブル定義)
  - research/
    - __init__.py
    - factor_research.py (momentum/value/volatility の計算)
    - feature_exploration.py (forward returns / IC / summaries)
  - strategy/
    - __init__.py (build_features, generate_signals の公開)
    - feature_engineering.py (features テーブル作成)
    - signal_generator.py (final_score 計算と signals 生成)
  - execution/  (発注層用（空の __init__ が存在）)
  - monitoring/  (監視用モジュール群（別ファイル想定）)

開発・テストのヒント
- 自動環境変数読み込みはプロジェクトルートの .env / .env.local を参照します。テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って無効化できます。
- DuckDB は ":memory:" を指定してインメモリ DB にすることができ、ユニットテストで便利です。
- jquants_client の HTTP 呼び出しは内部で urllib を使っているため、テストでは urllib.request.urlopen 等をモックするか、get_id_token / _request を差し替えてテスト用トークンを注入してください。
- news_collector はネットワーク・XML の扱いがあるため外部通信部分をモックすると堅牢なテストが書けます。

免責・補足
- この README はソース上の docstring / 設計メモに基づく概要ガイドです。実際の運用では API キーの管理、発注層（broker 接続）、リスク管理ルール等を適切に実装・検証してください。
- 発注（execution）・ブローカー連携はこのコードベースの一部ではありますが、実運用時はさらに安全な検証・監査が必要です。

以上です。必要であれば、具体的な利用例スクリプト（CLI 仕立てや systemd / Airflow 用のジョブ定義）も追加で作成します。どの部分のサンプルが欲しいか教えてください。