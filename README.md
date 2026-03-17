# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants）、ETL、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ定義、監査ログなど、取引システムの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買に必要なデータ基盤と補助機能をまとめた Python パッケージです。主に以下をサポートします。

- J-Quants API からの株価・財務・カレンダーデータ取得（レート制御／リトライ／トークン自動更新対応）
- DuckDB を用いたスキーマ（Raw / Processed / Feature / Execution / Audit）の定義と初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策、Gzip/サイズ制限、トラッキング削除）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（トレーサビリティ: signal → order → execution の追跡）

設計上、冪等性（ON CONFLICT での上書きなど）、Look-ahead bias 回避のための fetched_at 管理、外部に依存する操作の堅牢化（サイズ制限、SSRF 対策、XML の安全パース）に重点を置いています。

---

## 機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（refresh token から id token を取得）
  - save_* 系で DuckDB へ冪等保存
  - レート制限（120 req/min）・リトライ・401 自動リフレッシュ対応
- data.schema
  - DuckDB 用の包括的な DDL（raw_prices, raw_financials, raw_news, market_calendar, features, signals, orders, trades, positions, audit テーブル等）
  - init_schema / get_connection
- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - 差分更新・バックフィル・品質チェック統合
- data.news_collector
  - fetch_rss / save_raw_news / save_news_symbols / run_news_collection
  - RSS の正規化、トラッキング除去、SSRF・Gzip・XML 脆弱性対策
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチでカレンダー差分更新）
- data.audit
  - 監査用テーブル DDL と init_audit_schema / init_audit_db（UTC 固定）
- data.quality
  - 欠損・重複・スパイク・日付不整合チェック（QualityIssue を返す）

---

## 動作環境（概要）

- Python 3.9+
- 主要依存: duckdb, defusedxml
- ネットワークアクセス: J-Quants API、RSS フィード等

（実際の requirements はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

以下はローカル開発向けの一般的な手順例です。

1. リポジトリをクローンする
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - プロジェクトに requirements.txt / pyproject.toml がある場合はそれを使用してください。
   - 例（最低限のパッケージ）:
     ```
     pip install duckdb defusedxml
     ```
   - 編集開発用にパッケージをインストールする場合:
     ```
     pip install -e .
     ```

4. 環境変数の準備（.env）
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化）。
   - 必須の環境変数（コード内 Settings 参照）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト有り:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL（DEBUG / INFO / ...、デフォルト: INFO）

   例 `.env`（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマを初期化
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data import schema
     from kabusys.config import settings

     conn = schema.init_schema(settings.duckdb_path)
     # 以降 conn を使って ETL 等を実行
     ```

6. 監査ログ用 DB の初期化（任意）
   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（よく使う API）

以下は典型的な利用例です。実行前に必ず設定（.env）を整えてください。

- 日次 ETL 実行（市場カレンダー取得 → 株価差分 → 財務差分 → 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import pipeline, schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)  # 既存 DB に接続
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブを走らせる
  ```python
  from kabusys.data import news_collector, schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  # known_codes は銘柄コードセット（例: {'7203','6758'}）を渡すと抽出・紐付けを行う
  stats = news_collector.run_news_collection(conn, known_codes=None)
  print(stats)
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print(f"Saved calendar rows: {saved}")
  ```

- J-Quants から直接データを取る（テスト用）
  ```python
  from kabusys.data import jquants_client as jq
  # id_token を省略すると内部キャッシュ / refresh ロジックが動作する
  prices = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 品質チェックの個別実行
  ```python
  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i)
  ```

ログは環境変数 `LOG_LEVEL` で制御されます。また `KABUSYS_ENV` により挙動（paper/live/dev）を分岐できます（コード内で参照）。

---

## ディレクトリ構成

主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py       — RSS ベースのニュース収集・保存
    - schema.py               — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py             — ETL パイプライン（差分・バックフィル・品質チェック）
    - calendar_management.py  — マーケットカレンダー管理（営業日判定等）
    - audit.py                — 監査ログ用 DDL と初期化
    - quality.py              — データ品質チェック
  - strategy/
    - __init__.py  (戦略層のためのプレースホルダ)
  - execution/
    - __init__.py  (発注・実行層のためのプレースホルダ)
  - monitoring/
    - __init__.py  (監視用プレースホルダ)

その他:
- README.md（本ドキュメント）
- .env.example（プロジェクトルートに置く想定のテンプレート、存在する場合参照）

---

## 補足 / 運用上の注意

- 環境変数の自動読み込み
  - package の config モジュールはプロジェクトルート（.git または pyproject.toml を探す）を基準に `.env` → `.env.local` の順でロードします。OS 環境変数は `.env` で上書きされません（`.env.local` は上書き）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- トークン管理
  - J-Quants の refresh token を `JQUANTS_REFRESH_TOKEN` に設定してください。jquants_client が id_token を自動で取得・更新します。
- DuckDB パス
  - デフォルトで `data/kabusys.duckdb` を使用します。別途ファイルにしたい場合は `DUCKDB_PATH` を環境変数で調整してください。
- セキュリティ設計
  - news_collector は SSRF、XML Bomb、巨大レスポンス等の攻撃を緩和する機構を備えています。外部 URL を利用する際は注意を継続してください。
- テスト
  - 本リポジトリにテストファイルは含まれていませんが、各関数は id_token 注入や _urlopen のモックなどテストしやすい設計になっています。

---

以上。実運用や公開 API の拡張、戦略・発注ロジックの実装は strategy/ と execution/ 下にて実装してください。README に不足する点や、サンプルの追加・運用手順の細分化が必要であれば教えてください。