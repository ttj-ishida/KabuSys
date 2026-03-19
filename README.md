# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（開発中）

KabuSys は J-Quants や RSS 等から市場データを収集・保存し、特徴量生成・ファクター分析・ETL・監査ログなどを提供する Python コードベースです。DuckDB を中心にデータレイヤーを構成し、Strategy / Execution / Monitoring 層と分離された設計を採っています。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェックとユーティリティ（settings）
- データ取得 / 保存（J-Quants API クライアント）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの取得（ページネーション対応）
  - レート制限、リトライ、401 トークン自動リフレッシュを組み込んだ堅牢な HTTP クライアント
  - DuckDB への冪等保存（ON CONFLICT を利用）
- ETL パイプライン
  - 差分取得（バックフィル対応）・保存・品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 日次 ETL 実行エントリポイント（run_daily_etl）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 各レイヤーのテーブル定義と初期化ユーティリティ
- 監査ログ（Audit）
  - signal → order_request → execution まで UUID ベースでトレース可能な監査スキーマと初期化
- ニュース収集（RSS）
  - RSS フィードの安全な取得（SSRF 対策、gzip サイズ制限、defusedxml 使用）
  - 記事 ID は正規化 URL の SHA-256 で冪等性を担保
  - 記事と銘柄コードの紐付け機能（extract_stock_codes / news_symbols 保存）
- 研究（Research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー
  - Z-score 正規化ユーティリティの提供
- セーフティ / 設計方針
  - 本番発注 API に直接アクセスしない研究モジュール設計
  - Look-ahead bias 防止のため fetched_at を UTC で記録
  - 大規模データ取り扱いのためのチャンク処理・トランザクション管理

---

## セットアップ

前提
- Python 3.9+（コードは型注釈や一部機能が新しめのバージョンを想定）
- DuckDB が利用できる環境

1. リポジトリをクローン / コピーしてプロジェクトルートに移動

2. 必要パッケージのインストール（例）
   - pip を使う場合（仮想環境推奨）:
     ```
     python -m venv .venv
     source .venv/bin/activate   # Windows: .venv\Scripts\activate
     pip install -U pip
     pip install duckdb defusedxml
     ```
   - 開発用にローカルインストールする場合:
     ```
     pip install -e .
     ```
   ※ requirements ファイルが無い場合は、上記の主要依存（duckdb, defusedxml）を手動で追加してください。

3. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成すると、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 主な環境変数
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD      : kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL     : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : SQLite（監視等に使用）（デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : 実行環境 (development | paper_trading | live)（デフォルト: development）
     - LOG_LEVEL             : ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）

---

## 使い方（基本例）

以下は主要な API の使い方サンプルです。プロジェクトに合わせて適宜スクリプト化してください。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
  ```

- 監査ログ専用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- ETL（日次パイプライン）を実行
  ```python
  from datetime import date
  import kabusys.data.pipeline as pipeline
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema 済みを想定
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から株価・財務を直接取得して保存（テスト用）
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print("saved", saved)
  ```

- ニュース収集ジョブを実行
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes は既知の銘柄コードセットを渡すと記事への紐付けを実行
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from kabusys.research import calc_momentum
  from kabusys.data import schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2024,1,31))
  # momentum は dict のリスト: {"date":..., "code":..., "mom_1m":..., ...}
  ```

- 将来リターンと IC 計算の例
  ```python
  from kabusys.research import calc_forward_returns, calc_ic
  from kabusys.research import calc_momentum
  from kabusys.data import schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  fwd = calc_forward_returns(conn, target)
  factors = calc_momentum(conn, target)
  ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

---

## 注意点 / 実装上のポイント

- J-Quants クライアントはレート制限（120 req/min）を内部的に厳守します。大量リクエスト時は注意してください。
- API 呼び出しで 401 が返ると自動でリフレッシュし、1 回再試行します（リフレッシュ失敗時は例外）。
- DuckDB への保存は冪等（ON CONFLICT ... DO UPDATE / DO NOTHING）で設計されています。
- ニュース収集は SSRF 対策、gzip サイズチェック、XML パースの脆弱性対策（defusedxml）等の安全機構を備えています。
- 研究モジュール（research）は本番発注 API にアクセスしない設計です。安全にローカル分析が行えます。
- 自動的に .env をロードしますが、テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

---

## ディレクトリ構成

（主なファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         : 環境変数管理（settings）
  - data/
    - __init__.py
    - jquants_client.py                : J-Quants API クライアント + 保存
    - news_collector.py                : RSS ニュース収集・保存・銘柄抽出
    - schema.py                        : DuckDB スキーマ定義と初期化
    - stats.py                         : 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                      : ETL パイプライン（run_daily_etl 等）
    - features.py                      : 特徴量インターフェース（再エクスポート）
    - calendar_management.py           : 市場カレンダー管理ユーティリティ
    - audit.py                         : 監査ログスキーマ初期化
    - etl.py                           : ETL 公開 API（ETLResult 再エクスポート）
    - quality.py                       : 品質チェック
  - research/
    - __init__.py
    - feature_exploration.py           : 将来リターン, IC, 統計サマリ
    - factor_research.py               : モメンタム/ボラティリティ/バリュー計算
  - strategy/                           : 戦略実装用パッケージ（雛形）
  - execution/                          : 発注 / 約定管理（雛形）
  - monitoring/                         : 監視モジュール（雛形）

---

## 開発・テスト上のヒント

- settings は import 時に .env を自動読み込みします。テストで環境を固定したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB の初期化は `data.schema.init_schema()` を使います。テストでは ":memory:" を使うと高速です。
- network 呼び出しを伴うモジュール（jquants_client, news_collector）はモック化しやすいよう id_token 注入や _urlopen の差し替えポイントを用意しています。

---

必要であれば、利用例（CLI スクリプト、cron 用ジョブ定義、Dockerfile、CI 例）のテンプレートや、各モジュールの詳細ドキュメント（関数一覧・引数仕様・戻り値例）も作成します。どの部分を優先してほしいか教えてください。