README
======

概要
----
KabuSys は日本株向けのデータプラットフォームと戦略基盤を備えた自動売買補助ライブラリです。  
J-Quants API からの市場データ取得、DuckDB を用いたデータスキーマ管理、特徴量（features）構築、シグナル生成、RSS ニュース収集などの機能を提供します。設計は「ルックアヘッドバイアス排除」「冪等性」「ネットワーク／セキュリティ対策」を重視しています。

主な特徴
--------
- J-Quants API クライアント
  - 日足（OHLCV）、財務（四半期）、マーケットカレンダー取得
  - レートリミットとリトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- データスキーマ管理（DuckDB）
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義
  - init_schema による初期化（冪等）
- ETL パイプライン
  - 差分更新（最終取得日に基づく）、バックフィル、品質チェック連携
  - 日次 ETL run_daily_etl（カレンダー／価格／財務／品質チェック）
- 特徴量エンジニアリング（feature_engineering）
  - 研究モジュールの生ファクターを正規化・合成し features テーブルへ UPSERT
  - ユニバースフィルタ（最低株価・売買代金）、Z スコア正規化、±3 クリップ
- シグナル生成（signal_generator）
  - features と ai_scores を統合して final_score を計算
  - Bear レジーム検出、BUY/SELL シグナルの生成および signals テーブル保存
  - 重み指定や閾値カスタマイズ対応
- ニュース収集（news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、記事ID（SHA-256）による冪等保存
  - 記事と銘柄コードの紐付け（news_symbols）
- 研究ユーティリティ
  - 将来リターン計算、IC（スピアマンρ）、ファクターサマリー、Z スコア正規化等
- その他ユーティリティ
  - マーケットカレンダー管理、ログ・監査スキーマなど

動作環境・依存
---------------
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, json, logging, datetime 等）を多用

セットアップ
-----------
1. リポジトリをチェックアウト:
   git clone <repo_url>
   cd <repo>

2. 仮想環境を作成・有効化（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .\.venv\Scripts\activate   # Windows (PowerShell)

3. 必要パッケージをインストール:
   pip install "duckdb>=0.6" defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）
   開発インストール（編集可能）:
   pip install -e .

4. 環境変数設定
   プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   .env の例:
   JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
   KABU_API_PASSWORD=あなたの_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development  # development|paper_trading|live
   LOG_LEVEL=INFO

  注意:
  - Settings クラスは必須の環境変数が未設定だと ValueError を投げます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
  - KABUSYS_ENV の有効値: development / paper_trading / live

使い方（よく使う操作例）
-----------------------

1) DuckDB スキーマ初期化
   Python REPL やスクリプトで:
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリも作成される

2) 日次 ETL 実行（J-Quants から価格・財務・カレンダー取得）
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())

   run_daily_etl は内部で品質チェック（quality モジュール）を呼び出します（オプションで無効化可能）。

3) 特徴量の構築（features テーブルへ保存）
   from datetime import date
   from kabusys.data.schema import get_connection, init_schema
   from kabusys.strategy import build_features
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   n = build_features(conn, target_date=date.today())
   print(f"upserted features: {n}")

   - build_features は prices_daily / raw_financials を参照して Z スコア正規化などを行い features テーブルに日付単位で置換（冪等）します。

4) シグナル生成
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.strategy import generate_signals

   conn = init_schema(settings.duckdb_path)
   total = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals generated: {total}")

   - generate_signals は features / ai_scores / positions を参照し、BUY/SELL を判定して signals に日付単位で置換します。
   - weights 引数で component weights をカスタム可能（辞書）。不正値は無視され、合計が 1 にリスケールされます。

5) ニュース収集（RSS）
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット（任意）
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)  # {source_name: 新規保存数}

   - fetch_rss は SSRF 防御、gzip サイズ制限、XML デフューズ 等の安全対策を実装しています。

API（主要関数）
----------------
- kabusys.config.settings
  - settings.jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level など

- データ
  - kabusys.data.schema.init_schema(db_path) -> DuckDB 接続（テーブルを作成）
  - kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
  - kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
  - kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection

- 研究 / 特徴量
  - kabusys.research.calc_momentum, calc_volatility, calc_value
  - kabusys.data.stats.zscore_normalize
  - kabusys.research.calc_forward_returns, calc_ic, factor_summary, rank

- 戦略
  - kabusys.strategy.build_features(conn, target_date)
  - kabusys.strategy.generate_signals(conn, target_date, threshold, weights)

設計上の注意点
--------------
- ルックアヘッドバイアス対策:
  - 特徴量計算 / シグナル生成は target_date 時点の情報のみを用いる設計です。
  - J-Quants データは fetched_at を UTC で保存し「いつそのデータを知り得たか」をトレースできます。
- 冪等性:
  - API保存処理は ON CONFLICT による更新（UPSERT）を採用し、同一データ重複挿入を防ぎます。
  - features / signals などは日付単位で削除して再挿入する原子的処理を行います（トランザクション利用）。
- セキュリティ:
  - RSS収集は SSRF 対策、gzip/サイズ制限、defusedxml を利用して XML 攻撃を防止しています。
  - J-Quants クライアントはトークン自動更新とリトライ（exponential backoff）を備えています。

ディレクトリ構成（主要ファイル）
-------------------------------
src/
  kabusys/
    __init__.py
    config.py                     # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py           # J-Quants API クライアント + 保存ユーティリティ
      news_collector.py           # RSS 収集と保存
      schema.py                   # DuckDB スキーマ定義・初期化
      stats.py                    # 統計ユーティリティ（zscore_normalize 等）
      pipeline.py                 # ETL パイプライン（run_daily_etl 等）
      calendar_management.py      # マーケットカレンダー管理
      audit.py                    # 監査ログスキーマ
      features.py                 # features 公開インターフェース
    research/
      __init__.py
      factor_research.py          # mom/vol/value 計算
      feature_exploration.py      # IC / forward returns / summary
    strategy/
      __init__.py
      feature_engineering.py      # features 作成（正規化・フィルタ等）
      signal_generator.py         # final_score 計算と signals 生成
    execution/                     # 発注・execution 層（空または未実装モジュール）
    monitoring/                    # 監視・Slack 通知など（場所確保）

サンプルワークフロー
------------------
1. init_schema で DB 初期化
2. run_daily_etl で当日分のデータを取得・保存（market_calendar 先読み含む）
3. build_features で特徴量を作成して features テーブルへ保存
4. （AI）ai_scores を外部で計算して ai_scores テーブルに保存（別途実装）
5. generate_signals でシグナル生成 → signals テーブルへ保存
6. （実際の注文は execution 層／ブローカー接続で実行）

サポート / 開発
----------------
- バグ報告や機能要望は Issue を立ててください。
- テストや CI の定義はリポジトリにあればそちらに従ってください。
- 本 README は実装から推測してまとめています。実運用前に必ずコードと環境変数の確認・テストを行ってください。

ライセンス
---------
（プロジェクトに付随する LICENSE ファイルをご確認ください）

付記
----
この README はリポジトリ内のソースコード（config / data / research / strategy 等）をもとに作成しています。個別関数の詳細や追加オプションについては該当モジュールの docstring を参照してください。