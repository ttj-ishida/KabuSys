# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買／データプラットフォームライブラリです。J-Quants からのマーケットデータ取得、DuckDB によるデータ保存、ETL パイプライン、特徴量計算（ファクター）、ニュース収集、品質チェック、監査ログなど一連のワークフローをサポートします。

## 概要（Project overview）

- J-Quants API から株価・財務・カレンダー等を取得して DuckDB に蓄積する ETL 機能を提供します。
- DuckDB 上に Raw / Processed / Feature / Execution 層のスキーマを定義し、冪等性（ON CONFLICT）を保った保存を行います。
- ファクター（Momentum / Value / Volatility 等）の計算、将来リターン（forward returns）や IC（Information Coefficient）計算、Z スコア正規化などのリサーチ機能を備えています。
- RSS フィードからニュースを収集し、記事 → 銘柄紐付け（news_symbols）まで実装しています（SSRF 対策、トラッキングパラメータ削除等）。
- データ品質チェック（欠損・重複・スパイク・日付不整合）と監査ログ（signal → order → execution のトレース）を提供します。

## 機能一覧（Features）

- データ取得 / ETL
  - J-Quants API クライアント（ページネーション・レート制御・リトライ・自動トークンリフレッシュ）
  - 差分更新 / バックフィル対応の ETL（prices / financials / market_calendar）
  - DuckDB スキーマ初期化（Raw / Processed / Feature / Execution / Audit）
- データ保存
  - 冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）
  - raw_prices / raw_financials / market_calendar / raw_news / news_symbols 等
- リサーチ / 特徴量
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials ベース）
  - calc_forward_returns, calc_ic（Spearman ランク相関）, factor_summary
  - zscore_normalize（クロスセクション Z スコア正規化）
- ニュース収集
  - RSS フィード取得（gzip対応、XML防御、SSRF対策）
  - 記事正規化、記事ID生成（正規化 URL の SHA-256）および保存
  - 記事→銘柄コード抽出・紐付け
- 品質管理 / 監査
  - 欠損・重複・スパイク・日付不整合チェック
  - 監査ログ（signal_events / order_requests / executions）テーブル群
- ユーティリティ
  - market_calendar を使った営業日判定（next/prev/get_trading_days 等）
  - 設定管理（環境変数 / .env 自動ロード）

## セットアップ手順（Setup）

前提: Python 3.9+（typing の一部に 3.10 構文が使われているため、環境に合わせて適宜調整してください）

1. リポジトリをクローン（またはパッケージソースを配置）

2. 仮想環境を作成して有効化（任意）
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 必要パッケージをインストール
   - 最低依存:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - 開発時はパッケージを editable でインストール:
     - pip install -e .

   （プロジェクトの setup/pyproject ファイルがある場合はそちらを使って依存をインストールしてください）

4. 環境変数（.env）の準備
   - プロジェクトルートに .env 或いは .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須項目:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（発注機能を使う場合）
     - SLACK_BOT_TOKEN — Slack 通知（使う場合）
     - SLACK_CHANNEL_ID — Slack チャネル ID（使う場合）
   - 任意 / デフォルトあり:
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - 例 .env（テンプレート）
     - JQUANTS_REFRESH_TOKEN=your_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトから:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")
   - 監査ログ専用 DB 初期化（オプション）:
     - from kabusys.data import audit
     - audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

## 使い方（Usage）

いくつかの基本的な利用例を示します。実運用ではログ設定やエラーハンドリングを適切に行ってください。

1. DuckDB スキーマの初期化（再掲）
   - Python:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")

2. 日次 ETL を実行する（市場カレンダー取得 → 株価/財務取得 → 品質チェック）
   - 例スクリプト:
     - from datetime import date
       from kabusys.data import pipeline, schema
       conn = schema.init_schema("data/kabusys.duckdb")
       result = pipeline.run_daily_etl(conn, target_date=date.today())
       print(result.to_dict())
   - ETLResult に取得数・保存数・品質問題の一覧が格納されます。

3. J-Quants から株価を直接取得して保存する
   - from kabusys.data import jquants_client as jq
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
     saved = jq.save_daily_quotes(conn, records)

4. ニュース収集ジョブを実行する
   - from kabusys.data import news_collector
     conn = schema.get_connection("data/kabusys.duckdb")
     known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
     results = news_collector.run_news_collection(conn, known_codes=known_codes)
     print(results)  # {source: saved_count}

5. ファクター / リサーチ関数の呼び出し
   - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
     conn = schema.get_connection("data/kabusys.duckdb")
     from datetime import date
     moment = calc_momentum(conn, date(2024,1,31))
     fwd = calc_forward_returns(conn, date(2024,1,31))
     ic = calc_ic(moment, fwd, factor_col="mom_1m", return_col="fwd_1d")

6. データ品質チェック
   - from kabusys.data import quality
     issues = quality.run_all_checks(conn, target_date=date.today())
     for i in issues:
         print(i)

7. 設定の参照
   - from kabusys.config import settings
     token = settings.jquants_refresh_token
     is_live = settings.is_live

注意点:
- J-Quants API はレート制限（120 req/min）や認証トークン寿命があるため、jquants_client は内部でレート制御と自動リフレッシュを行います。
- ETL の差分計算やバックフィルは pipeline モジュール内で自動化されています。必要に応じて引数で日付や backfill_days を調整してください。

## 環境変数（主要なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（発注関連を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu api base（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH — monitoring 用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化

## ディレクトリ構成（Directory structure）

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - execution/                — 発注・実行に関するパッケージ（未実装箇所のプレースホルダ）
  - strategy/                 — 戦略関連（プレースホルダ）
  - monitoring/               — 監視関連（プレースホルダ）
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py  — 将来リターン計算 / IC / サマリー
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API client（取得・保存ユーティリティ）
    - news_collector.py       — RSS ニュース収集・保存
    - schema.py               — DuckDB スキーマ定義と init_schema()
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - features.py             — features の再エクスポート
    - calendar_management.py  — market_calendar 管理 / 営業日ユーティリティ
    - audit.py                — 監査ログ初期化・DDL
    - etl.py                  — ETLResult の再エクスポート
    - quality.py              — データ品質チェック

（その他）README の内容はリポジトリの実装に合わせて随時更新してください。

## 開発・貢献

- コード品質: DuckDB の SQL はパラメータバインド（?）を使用し、外部 API 呼び出しは最小化する設計です。
- テスト: 各ネットワーク I/O 部分（_urlopen, jquants_client._request 等）はモック可能な設計になっています。
- 貢献: バグ修正・機能追加は PR を送ってください。ドキュメントの更新も歓迎します。

---

必要であれば README に具体的なサンプルスクリプトや .env.example、運用時の注意（本番口座での safety checks、paper_trading フラグの使い方）等を追記します。どの情報を追加したいか教えてください。