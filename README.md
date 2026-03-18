# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（軽量実装）。  
主にデータ収集（J-Quants）、DuckDB スキーマ管理、ETL パイプライン、ニュース収集、ファクター/リサーチ、監査ログを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買基盤のための内部ライブラリ群です。主な目的は次のとおりです。

- J-Quants API からの株価・財務・カレンダー取得（Rate limit / リトライ / トークン自動リフレッシュ対応）
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL（差分更新・バックフィル・品質チェック）パイプライン
- RSS を用いたニュース収集と銘柄紐付け（SSRF 対策・サイズ制限・トラッキング除去）
- ファクター計算（Momentum / Volatility / Value 等）および研究用ユーティリティ（IC 計算・統計サマリ）
- 監査ログ（signal → order_request → executions のトレーサビリティ）

設計方針として、DuckDB と標準ライブラリを中心に依存を最小化し、実運用での冪等性・トレーサビリティ・安全性（SSRF、XML攻撃対策等）を重視しています。

---

## 機能一覧

- 環境変数の自動ロード（プロジェクトルートの .env/.env.local、ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
- settings: 必須/省略可能設定のラッパー（J-Quants, kabuステーション, Slack, DB パス, 環境モード 等）
- data/
  - jquants_client: API クライアント（ページネーション、レート制御、リトライ、token refresh）
  - schema: DuckDB の DDL と init_schema / get_connection
  - pipeline: ETL の差分取得・品質チェック・日次 ETL 実装
  - news_collector: RSS 取得 → 前処理 → raw_news 保存 → 銘柄抽出・紐付け
  - calendar_management: 市場カレンダー管理・営業日判定・夜間更新ジョブ
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - audit: 監査ログ用テーブルと初期化ユーティリティ
  - stats / features: 基本統計・Zスコア正規化
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算・IC 計算・統計サマリ
- execution, strategy, monitoring: パッケージプレースホルダ（将来の発注・監視ロジック用）

主な設計・安全対策:
- J-Quants のレート制御（120 req/min）、指数バックオフリトライ、401 時の自動トークン更新
- RSS 収集での SSRF 対策、XML パーサ防御、レスポンスサイズ制限、トラッキングパラメータ除去
- DuckDB への保存は冪等性（ON CONFLICT）を意識

---

## セットアップ手順

※ ここでは基本的なローカルセットアップ手順を示します。プロジェクトの packaging / requirements ファイルに応じて調整してください。

1. Python 環境の準備（推奨: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール（代表例）
   - pip install duckdb defusedxml

   ※ 実際のプロジェクトでは追加パッケージ（requests 等）が必要になる場合があります。requirements.txt があればそれを使用してください。

3. リポジトリのクローン / パッケージのインストール（開発モード）
   - git clone <repo>
   - cd <repo>
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を作成してください。自動で .env を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   主要な環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - KABU_API_PASSWORD=<kabu_station_api_password>
   - SLACK_BOT_TOKEN=<slack_bot_token>
   - SLACK_CHANNEL_ID=<slack_channel_id>

   DB 関連（任意、デフォルトあり）:
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db

   システム:
   - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL  (デフォルト: INFO)

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:

     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

   - 監査ログ専用 DB を分ける場合:

     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主要ユースケース）

以下は代表的な操作例です。必要に応じて logging を設定してください。

- 日次 ETL を実行する (市場カレンダー取得 → 株価/財務差分取得 → 品質チェック)

  from datetime import date
  import duckdb
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 個別 ETL（株価のみ）を実行する

  from datetime import date
  from kabusys.data import schema, pipeline
  conn = schema.get_connection("data/kabusys.duckdb")
  fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched}, saved={saved}")

- ニュース収集ジョブを実行する

  import duckdb
  from kabusys.data import news_collector as nc
  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄セット
  results = nc.run_news_collection(conn, known_codes=known_codes)
  print(results)

- ファクター計算 / リサーチ

  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2025, 1, 31)
  momentum = calc_momentum(conn, d)
  vol = calc_volatility(conn, d)
  value = calc_value(conn, d)
  fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(momentum, ["mom_1m","mom_3m","mom_6m","ma200_dev"])

- J-Quants API を直接使ってデータを取得・保存する

  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)

注意点:
- jquants_client は内部でレート制御・リトライ・トークン更新を行います。大量取得時は制限に注意してください。
- news_collector は外部 URL にアクセスするため、実行環境のネットワークポリシーを確認してください。
- DuckDB の ON CONFLICT によって保存は冪等化されています。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" をセットすると .env の自動ロードを無効化

.config モジュールの仕様:
- プロジェクトルートは __file__ の親階層から .git または pyproject.toml を探索して特定します。CWD に依存せずパッケージ配布後も動作する設計です。
- .env は OS 環境変数より低優先度で読み込まれ、.env.local は上書き（override）されます。
- _require 関数で必須変数が未設定の場合 ValueError を発生させます。

---

## ディレクトリ構成（主要ファイル・モジュール）

(リポジトリの src/kabusys 以下の主要ファイル)

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - etl.py
    - quality.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py  (拡張ポイント)
  - execution/
    - __init__.py  (拡張ポイント)
  - monitoring/
    - __init__.py  (拡張ポイント)

各モジュールの責務:
- data/*.py: データ取得・保存・ETL・スキーマ・品質・カレンダー管理
- research/*.py: ファクター算出・評価ユーティリティ
- audit.py: シグナル〜約定の監査ログスキーマ
- news_collector.py: RSS のセキュアな収集と DB 保存

---

## 開発上の注意 / ベストプラクティス

- 本システムは本番口座での発注機能（execution/strategy）は将来的に追加されることを想定しており、データ層・監査層を先に整備することで安全性を担保しています。
- J-Quants 等の API トークンは漏洩に注意し、CI 等にハードコードしないでください。
- ETL は差分取得・バックフィル設計になっています。過去データの整合性や API の後出し修正を吸収するため、バックフィル日数を適切に設定してください。
- news_collector は外部 URL を扱うため SSRF・XML Bomb 対策を施していますが、実行環境のアウトバウンド制限やプロキシ設定に合わせてカスタマイズしてください。
- DuckDB のバージョンにより一部機能（ON DELETE CASCADE / 一部制約等）が異なるため、本ライブラリはデフォルトで互換性の範囲で DDL を定義しています。

---

## ライセンス / 貢献

この README はリポジトリのコードから生成した要約です。具体的なライセンスや貢献方法はリポジトリの LICENSE / CONTRIBUTING を参照してください。

---

必要であれば、README に次の内容も追加できます:
- 具体的な requirements.txt（推奨バージョン）
- CI 実行手順（テストコマンド）
- より詳細な API 使用例（各関数のサンプル）
- デプロイ / Cron / Airflow での ETL スケジューリング例

追加希望があれば教えてください。