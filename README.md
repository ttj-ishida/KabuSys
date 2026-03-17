# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ）です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、監査ログ（発注〜約定のトレーサビリティ）など、量的投資運用に必要な基盤モジュールを提供します。

主な設計方針の要点：
- Look-ahead bias を避けるため、取得時刻（UTC）を記録する
- API レート制限とリトライ（指数バックオフ）を組み込み
- DuckDB を用いた冪等なデータ保存（ON CONFLICT で更新）
- RSS ニュース収集は SSRF 対策・XML 攻撃対策・サイズ制限を実装
- データ品質チェックで欠損・スパイク・重複・日付不整合を検出

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルート検出）、環境変数経由で設定可能
  - 必須設定は `Settings` 経由で取得し、未設定時は例外を投げる

- J-Quants API クライアント（kabusys.data.jquants_client）
  - トークン取得（リフレッシュ）、株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レートリミッタ、リトライ、401 時の自動トークンリフレッシュ、ページネーション対応
  - DuckDB への保存用 save_* 関数（冪等）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（last date を参照）、バックフィルオプション、カレンダー先読み
  - 品質チェック（kabusys.data.quality）呼び出しと結果集約
  - 日次 ETL エントリポイント: run_daily_etl

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、URL 正規化（トラッキング除去）、記事 ID 生成（SHA-256 先頭32文字）
  - SSRF や XML 攻撃対策、受信サイズ制限、DuckDB への冪等保存（INSERT ... RETURNING）
  - 銘柄コード抽出・紐付けロジック

- DuckDB スキーマ初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義とインデックス
  - init_schema(), get_connection(), init_audit_schema(), init_audit_db() を提供

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の監査テーブルとインデックス
  - 発注フローの UUID 連鎖による完全トレースを想定

- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比）、重複、日付不整合を検出し QualityIssue を返す

注: strategy/execution/monitoring パッケージは初期構成（プレースホルダ）です。

---

## システム要件

- Python 3.10 以上（typing の新構文や型注釈を利用しています）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

実際のプロジェクトでは requirements.txt / pyproject.toml に依存を明記してください。

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repository-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS / Linux: source .venv/bin/activate

3. 依存パッケージをインストール
   - 例（最小）:
     pip install duckdb defusedxml

   - プロジェクトに requirements.txt / pyproject.toml があればそれを使用してください:
     pip install -r requirements.txt
     または
     pip install .

4. 環境変数の設定
   - プロジェクトルートに `.env` を配置すると自動で読み込まれます（.env.local が優先で上書き）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

   推奨の環境変数（最低限必要なもの）:
   - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD：kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN：Slack 通知用ボットトークン（必須）
   - SLACK_CHANNEL_ID：通知先チャンネルID（必須）
   - KABU_API_BASE_URL：kabuステーションのベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH：DuckDB ファイルパス（省略可、デフォルト data/kabusys.duckdb）
   - SQLITE_PATH：SQLite 監視 DB（省略可、デフォルト data/monitoring.db）
   - KABUSYS_ENV：development / paper_trading / live（省略時 development）
   - LOG_LEVEL：DEBUG/INFO/...（省略時 INFO）

   サンプル .env（例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB スキーマを初期化
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     # 監査テーブルを追加する場合
     from kabusys.data import audit
     audit.init_audit_schema(conn)
     ```

---

## 使い方（主要 API の例）

ここでは代表的な使い方を示します。

- 日次 ETL の実行（株価・財務・カレンダーの差分取得と品質チェック）
  ```python
  from datetime import date
  import kabusys
  from kabusys.data import schema, pipeline

  # DB 初期化（既に初期化済みなら既存ファイルを開くだけ）
  conn = schema.init_schema("data/kabusys.duckdb")

  # J-Quants トークンは環境変数から自動取得されるため省略可
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants クライアントを直接利用する例
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  # 直近の期間の日足を取得して保存
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  jq.save_daily_quotes(conn, records)
  ```

- RSS ニュース収集ジョブの実行
  ```python
  from kabusys.data import news_collector
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")

  # デフォルト RSS ソースを使用して収集し、記事を保存
  results = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
  print(results)  # { source_name: 新規保存件数, ... }
  ```

- スキーマの監査テーブル初期化
  ```python
  from kabusys.data import schema, audit
  conn = schema.init_schema("data/kabusys.duckdb")
  audit.init_audit_schema(conn)
  ```

---

## よくあるトラブルとヒント

- 環境変数が足りない（ValueError）
  - `settings` プロパティは未設定の必須環境変数で ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。`.env` を作るか環境変数を設定してください。

- .env の自動読み込み
  - パッケージ内の config モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` / `.env.local` を読み込みます。
  - OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
  - 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- J-Quants API のレート制限・エラー
  - モジュールはデフォルトで 120 req/min のレート制限を守るよう設計されています。
  - 408/429/5xx に対してはリトライ（最大3回）を行い、429 の場合は Retry-After ヘッダを尊重します。
  - 401 を受けた場合はリフレッシュトークンを使って id_token を自動更新し 1 回リトライします。

- RSS 取得でエンコードや大きなレスポンスに失敗する場合
  - gzip 解凍後や Content-Length に対してサイズチェックが行われます（最大 10 MB）。超過するとスキップされます。
  - defusedxml を使って XML 攻撃を防いでいます。フィードの不正フォーマットは警告ログが出て空リストを返します。

---

## ディレクトリ構成

（主要ファイルのみを抜粋）

- src/kabusys/
  - __init__.py
    - パッケージのトップ。__version__ を定義。
  - config.py
    - 環境変数・設定管理。.env 自動読み込み、Settings クラスを提供。
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得 + 保存ロジック）
    - news_collector.py
      - RSS 取得・前処理・DuckDB 保存・銘柄紐付け
    - pipeline.py
      - ETL パイプライン（差分取得、保存、品質チェック）
    - schema.py
      - DuckDB スキーマ定義と初期化（Raw/Processed/Feature/Execution）
    - audit.py
      - 監査ログテーブル（signal/order_request/executions）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py
    - （戦略ロジックを実装するためのモジュール群を配置）
  - execution/
    - __init__.py
    - （ブローカ接続・発注ロジックを実装）
  - monitoring/
    - __init__.py
    - （運用監視・アラート機能を実装）

---

## 開発・拡張のポイント

- strategy / execution 層はプロジェクト固有のロジックを実装するための拡張ポイントです。
- DuckDB スキーマは data.schema で集中管理しています。追加テーブル・インデックスはこのモジュールを編集して反映してください。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` にして環境依存を切り離すと便利です。
- ネットワーク呼び出しはモジュール内でラッパー関数（例: news_collector._urlopen）を使っているため、テスト時はモック差替えが容易です。

---

必要なら README に実際の requirements.txt、pyproject.toml やサンプルスクリプト、さらに詳しい API リファレンス（各関数の引数/戻り値例）を追記します。どの部分を詳しく書くか指示してください。