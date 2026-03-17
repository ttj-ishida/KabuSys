# KabuSys

日本株自動売買システムのコアライブラリ（パッケージ）。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、DuckDB スキーマ、監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤向けに設計されたライブラリ群です。主な目的は次のとおりです。

- J-Quants API からのマーケットデータ（株価、財務、取引カレンダー）取得
- RSS ベースのニュース収集と銘柄マッチング
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）のスキーマと初期化
- ETL（差分取得・バックフィル・品質チェック）パイプライン
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 市場カレンダー管理（営業日判定、next/prev_trading_day 等）

設計上の特徴：
- J-Quants API のレート制限・リトライ・トークン自動リフレッシュ対応
- ETL は冪等（ON CONFLICT / トランザクション）を意識
- ニュース収集は SSRF や XML Attack 対策、トラッキングパラメータ除去などを実装
- データ品質チェックで欠損・重複・スパイク・日付不整合を検出

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 必須環境変数チェック
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足、財務、取引カレンダー取得（ページネーション対応）
  - GET/POST リトライ、401 のトークン自動更新、レートリミット
  - DuckDB へ冪等保存（save_* 関数）
- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブルとインデックスを定義
  - init_schema / get_connection
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）：カレンダー→株価→財務→品質チェック
  - 部分的な ETL 実行（run_prices_etl / run_financials_etl / run_calendar_etl）
- ニュース収集（kabusys.data.news_collector）
  - RSS から記事取得、前処理、正規化、SHA-256 ベースの冪等 ID、DuckDB への保存
  - 銘柄コード抽出と news_symbols 登録
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、カレンダー夜間更新ジョブ
- 品質チェック（kabusys.data.quality）
  - 欠損、重複、前日比スパイク、日付不整合の検出
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions の初期化関数（init_audit_schema 等）

その他: strategy、execution、monitoring 用のパッケージプレースホルダあり。

---

## 前提 / 必要環境

- Python 3.10+
- 依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS フィード等）

（実際のインストール方法はプロジェクトの pyproject.toml / requirements を参照してください）

---

## セットアップ手順

1. リポジトリをクローンして開発環境を用意

   pip の仮想環境例:
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -U pip
   - pip install duckdb defusedxml

   開発インストール（プロジェクトに setuptools/poetry がある場合）:
   - pip install -e .

2. 環境変数を準備

   プロジェクトルートに .env（および必要に応じて .env.local）を作成します。自動ロードはデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabu API パスワード（必須）
   - KABU_API_BASE_URL     : kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN       : Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite（監視用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

3. DuckDB スキーマ初期化

   例（Python を使って）:
   ```
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

   監査用スキーマを別 DB に作る場合:
   ```
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（クイックスタート）

以下はライブラリの代表的な使い方例です。実行は仮想環境内で行ってください。

1. DuckDB を初期化して日次 ETL を実行

   ```
   from kabusys.data import schema, pipeline

   # DB 初期化（すでに存在する場合はスキップ）
   conn = schema.init_schema("data/kabusys.duckdb")

   # 日次 ETL を実行（デフォルトは今日）
   result = pipeline.run_daily_etl(conn)
   print(result.to_dict())
   ```

   run_daily_etl は:
   - market_calendar を先に取得（先読み）
   - 株価（日足）を差分で取得・保存
   - 財務データを差分で取得・保存
   - 品質チェック（デフォルト有効）を実行
   - ETLResult を返す（ファッチ／保存件数、品質問題、エラー一覧等）

2. ニュース収集ジョブ（RSS）

   ```
   from kabusys.data import schema, news_collector

   conn = schema.get_connection("data/kabusys.duckdb")
   # known_codes を与えると記事→銘柄紐付けを行う
   known_codes = {"7203", "6758", "9984"}  # 例
   results = news_collector.run_news_collection(conn, known_codes=known_codes)
   print(results)  # {source_name: 新規保存件数}
   ```

3. カレンダー夜間更新ジョブ

   ```
   from kabusys.data import schema, calendar_management

   conn = schema.get_connection("data/kabusys.duckdb")
   saved = calendar_management.calendar_update_job(conn)
   print("saved:", saved)
   ```

4. J-Quants から個別データ取得（テスト用）

   ```
   from kabusys.data import jquants_client as jq
   # トークンは settings から自動取得されるため通常は不要
   quotes = jq.fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
   ```

5. 品質チェックを単独実行

   ```
   from kabusys.data import quality, schema
   conn = schema.get_connection("data/kabusys.duckdb")
   issues = quality.run_all_checks(conn)
   for i in issues:
       print(i)
   ```

---

## 設定の動作・注意点

- .env 自動読み込み
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探索）で .env / .env.local を自動で読み込みます。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト時に便利）。
  - .env.local は .env の上書き（override=True）として読み込まれます。ただし OS 環境変数は保護されます。

- J-Quants クライアント
  - レート制限: 120 req/min（モジュール内でスロットリング）
  - リトライ: 408/429/5xx 等に対して指数バックオフで最大 3 回
  - 401 はトークン自動リフレッシュを試みて 1 回リトライ
  - 取得時には fetched_at（UTC） を付与して「いつ取得したか」を記録

- ニュース収集
  - XML パースには defusedxml を利用し XML Bomb などへの対策を実施
  - レスポンスサイズ上限（10 MB）を越えるコンテンツはスキップ
  - URL の正規化・トラッキング除去・SSRF 防止ロジックを実装
  - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保

- DuckDB スキーマ
  - init_schema は存在しない親ディレクトリを自動作成します
  - 多数の制約（CHECK/PRIMARY KEY/FOREIGN KEY）とインデックスを定義
  - 監査ログは UTC タイムゾーンで保存する想定（init_audit_schema 内で SET TimeZone='UTC' を実行）

---

## ディレクトリ構成

主要なファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - execution/
    - __init__.py
  - strategy/
    - __init__.py
  - monitoring/
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得＋保存）
    - news_collector.py        — RSS ニュースの収集・前処理・保存
    - schema.py                — DuckDB スキーマ定義・初期化
    - pipeline.py              — ETL パイプライン（差分・backfill・品質チェック）
    - calendar_management.py   — 市場カレンダー管理／営業日ユーティリティ
    - audit.py                 — 監査ログ（signal/order/execution）初期化
    - quality.py               — データ品質チェック

（上記以外にテストやドキュメントが存在することがあります）

---

## 開発・運用上の補足

- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境依存を切り分けられます。
- DuckDB を :memory: で指定するとインメモリ DB が利用できます（単体テストに便利）。
- 外部 API のキー・トークンは絶対にリポジトリに含めないでください。
- ETL のスケジュールは Cron / Airflow / Prefect 等に任せる想定です。run_daily_etl はそのままジョブとして組めます。
- 実運用（live）時は KABUSYS_ENV を `live` に設定し、ログレベル・発注挙動を切り替える実装を strategy/execution 層で行ってください。

---

この README はコードベースから抽出した機能・使用法の要約です。詳細な API や追加設定は各モジュール（kabusys.data.jquants_client、kabusys.data.schema、kabusys.data.pipeline、kabusys.data.news_collector、kabusys.data.quality、kabusys.data.audit）内のドキュメント文字列を参照してください。