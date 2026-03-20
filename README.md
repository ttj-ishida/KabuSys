KabuSys — 日本株自動売買プラットフォーム（README）
=================================

概要
----
KabuSys は日本株のデータプラットフォームと戦略層を備えた自動売買システムのコアライブラリです。
主に以下を提供します。

- J-Quants API からのデータ取得（株価日足・財務・市場カレンダー）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution）
- factor（モメンタム／ボラティリティ／バリュー等）計算と Z スコア正規化
- 特徴量の構築（features テーブル）→ シグナル生成（signals テーブル）
- ニュース収集（RSS）と銘柄紐付け
- ETL パイプライン（差分取得・保存・品質チェック）
- マーケットカレンダー管理、監査ログ（audit）など運用機能

主な設計方針は「ルックアヘッドバイアス回避」「冪等性」「外部依存最小化（可能な限り標準ライブラリ）」「運用を考慮した堅牢性」です。

主な機能一覧
-------------
- data.jquants_client
  - J-Quants API クライアント（レート制御、指数バックオフ、トークン自動更新）
  - fetch / save 関数群（daily quotes, financials, market calendar）
- data.schema
  - DuckDB のスキーマ定義と初期化（init_schema）
- data.pipeline
  - 日次 ETL（run_daily_etl）および個別 ETL（prices/financials/calendar）
- data.news_collector
  - RSS 取得、前処理、raw_news 保存、銘柄抽出と紐付け
- data.calendar_management
  - 営業日判定、翌/前営業日取得、カレンダー更新ジョブ
- research.factor_research / research.feature_exploration
  - ファクター計算（mom/vol/value）、将来リターン、IC、統計要約
- strategy.feature_engineering
  - 生ファクターの正規化・ユニバースフィルタ・features テーブルへの保存
- strategy.signal_generator
  - features + ai_scores を統合して final_score を算出し BUY/SELL シグナル生成
- execution / monitoring / audit（実行・監視・監査用テーブル・雛形あり）

動作環境 / 必要要件
------------------
- Python 3.10 以上
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS）
- 環境変数に API トークン等を設定すること（下記参照）

セットアップ手順
----------------

1. リポジトリを取得
   - git clone <リポジトリURL>

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （開発用に setuptools / wheel 等を追加）

   ※ プロジェクトに pyproject.toml / requirements.txt があればそちらからインストールしてください。

4. パッケージのインストール（ローカル）
   - pip install -e .

5. 環境変数設定（.env）
   - プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）に .env/.env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須変数（実行に必要なもの）
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=your_slack_bot_token
     - SLACK_CHANNEL_ID=your_slack_channel_id
   - 任意／デフォルト
     - KABUSYS_ENV=development|paper_trading|live  (default: development)
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - DUCKDB_PATH=data/kabusys.duckdb (default)
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO

   例 (.env)
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=passwd
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG

6. DuckDB スキーマ初期化
   - Python から実行:
     from kabusys.data.schema import init_schema, get_connection, settings
     conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成されスキーマが作られます

使い方（簡単な実行例）
---------------------

- DB 初期化 + 日次 ETL 実行
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量構築（build_features）
  from datetime import date
  from kabusys.strategy import build_features
  conn = init_schema("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2025, 1, 1))
  print("features upserted:", count)

- シグナル生成（generate_signals）
  from datetime import date
  from kabusys.strategy import generate_signals
  conn = init_schema("data/kabusys.duckdb")
  n = generate_signals(conn, target_date=date(2025, 1, 1), threshold=0.6)
  print("signals written:", n)

- ニュース収集ジョブ（RSS）
  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # あらかじめ有効銘柄コードを用意
  results = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(results)

- カレンダー更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved calendar rows:", saved)

運用上の注意・トラブルシューティング
-----------------------------------
- .env の自動読み込みはプロジェクトルート検出に依存します。CI やテストで制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境変数を注入してください。
- J-Quants の API レートはモジュール内で制御しています（_RateLimiter）。ただし大量取得や並列実行する場合は追加の配慮が必要です。
- DuckDB のファイルパスを共有ファイルシステムで複数プロセスが同時に書き込むと問題が起きる可能性があります。運用では排他制御を検討してください。
- news_collector は外部 RSS を取得するため、SSRF 対策・gzip サイズ制限・XML ディフェンスを実装しています。プロキシ環境や認証の必要な RSS は別途対応が必要です。
- run_daily_etl は各ステップで例外を捕捉し続行する方針です。戻り値の ETLResult を確認して問題を検出してください。

ディレクトリ構成（主要ファイル）
------------------------------
以下は本パッケージの主要モジュールと役割の概略です（src/kabusys 以下）。

- __init__.py
  - バージョン定義・サブパッケージの公開

- config.py
  - 環境変数読み込み（.env サポート）、設定アクセス用 settings オブジェクト

- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント + 保存ユーティリティ
  - news_collector.py — RSS 取得・前処理・DB 保存・銘柄紐付け
  - schema.py — DuckDB スキーマ定義 / init_schema / get_connection
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — マーケットカレンダー管理、ジョブ
  - audit.py — 監査ログ用スキーマ（signal_events / order_requests / executions 等）
  - features.py — 公開インターフェース（zscore_normalize の再エクスポート）

- research/
  - __init__.py
  - factor_research.py — モメンタム／ボラティリティ／バリュー等の計算
  - feature_exploration.py — IC / forward returns / summary 等

- strategy/
  - __init__.py (build_features, generate_signals を公開)
  - feature_engineering.py — 特徴量合成・正規化・アップサート
  - signal_generator.py — final_score 計算、BUY/SELL 生成、signals テーブル書込

- execution/
  - （発注・実行関連の雛形：今後の実装想定）

- monitoring/
  - （監視・アラート関連の雛形）

ドキュメント参照（設計資料）
----------------------------
コード中で参照・準拠している想定ドキュメント（プロジェクトルートに別途存在することが想定される）:

- DataPlatform.md
- StrategyModel.md
- DataSchema.md

これらにはスキーマ設計・ETL フロー・戦略数式などの詳細が記載されています。実装を理解する際に併せて参照してください。

最後に
-----
この README はコードベースの主要機能と導入手順をまとめたものです。実運用にあたっては API キー・シークレットの管理、ジョブのスケジューリング（cron / Airflow 等）、モニタリング・アラート設計、バックテスト・ペーパートレードによる検証を必ず行ってください。質問や改善点があればお知らせください。