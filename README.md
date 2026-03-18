# KabuSys

日本株向け自動売買基盤（ライブラリ） — データ取得、ETL、ニュース収集、マーケットカレンダー管理、品質チェック、監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム開発を支援するライブラリ群です。主に以下を提供します。

- J-Quants API を用いた株価・財務・カレンダーの取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたスキーマ定義と冪等なデータ保存
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策、トラッキング除去）
- マーケットカレンダー管理（営業日判定、次/前営業日算出）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ / トレーサビリティ用テーブル群（シグナル→発注→約定の追跡）

設計上の特徴として、API レート制御、リトライ、Look-ahead バイアス防止のための fetched_at 記録、DuckDB への冪等保存を重視しています。

---

## 主な機能一覧

- 環境設定管理（.env 自動読み込み、必須項目チェック）
- J-Quants クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - リトライ・レートリミット・トークン管理
- DuckDB スキーマと初期化（raw / processed / feature / execution / audit レイヤ）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS -> raw_news、記事IDは正規化URLのSHA-256先頭32文字）
- 銘柄コード抽出（テキストから4桁コード抽出、known_codes フィルタ）
- マーケットカレンダー管理（営業日判定・next/prev/get_trading_days）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（signal_events / order_requests / executions 等の初期化）

---

## 動作要件・依存ライブラリ

- Python 3.10+
- 必須パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, gzip, hashlib, logging など

インストール例（仮にパッケージ化していれば setuptools 等で管理しますが、最低限の依存は手動インストールできます）:

```bash
python -m pip install "duckdb" "defusedxml"
```

プロジェクトをローカルで編集して使う場合は、プロジェクトルートで:

```bash
python -m pip install -e .
```

（setup / pyproject がある前提）

---

## セットアップ手順

1. Python 3.10 以上を用意する。

2. 依存パッケージをインストールする:

   ```bash
   python -m pip install duckdb defusedxml
   ```

3. 環境変数を設定する（.env を使うのが推奨）  
   プロジェクトルートに `.env`（または`.env.local`）を置くと、自動的に読み込まれます（読み込みは .git または pyproject.toml を基準にプロジェクトルートを探索します）。自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack ボットトークン（通知用途）
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   任意・デフォルト値あり:

   - KABUSYS_ENV: development / paper_trading / live （デフォルト development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL （デフォルト INFO）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: SQLite パス（デフォルト data/monitoring.db）

   .env の例:

   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   ```

4. DuckDB スキーマ初期化（例）:

   Python REPL またはスクリプトで:

   ```py
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

   監査ログ専用 DB を初期化する場合:

   ```py
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要 API 例）

以下はライブラリの主要な利用例です。プロダクションで使う際は適切なロギング・例外処理を追加してください。

- J-Quants の ID トークン取得:

  ```py
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- DuckDB スキーマ作成 / 接続:

  ```py
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")
  # 既存 DB に接続する場合:
  # conn = get_connection("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（株価・財務・カレンダー取得と品質チェック）:

  ```py
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # ETLResult が返る
  print(result.to_dict())
  ```

- ニュース収集（RSS）と保存:

  ```py
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 例: 既知銘柄コードセット
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: 新規保存数}
  ```

- カレンダー夜間更新ジョブ:

  ```py
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 品質チェックを個別に実行:

  ```py
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

- 監査ログスキーマの初期化（既存 conn に追加）:

  ```py
  from kabusys.data.audit import init_audit_schema
  # 既に init_schema() で conn を取得している場合
  init_audit_schema(conn)
  ```

注意: 上記はライブラリ API の一部です。モジュール内により細かい関数・パラメータの説明があります。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（rate limiting / retry / token refresh / 保存関数）
    - news_collector.py
      - RSS 取得、前処理、raw_news 保存、news_symbols 紐付け
    - schema.py
      - DuckDB の DDL と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - calendar_management.py
      - マーケットカレンダー更新・営業日判定ロジック
    - audit.py
      - 監査ログ用テーブル定義と初期化
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - strategy/
    - __init__.py （戦略関連モジュール群のエントリ）
  - execution/
    - __init__.py （発注・約定・ポジション管理のエントリ）
  - monitoring/
    - __init__.py （監視・メトリクス関連）

---

## 設計上の注意点 / セキュリティ

- .env 自動読み込み: プロジェクトルートの `.env` と `.env.local` が自動で読み込まれます。テスト時や明示的に読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ニュース収集時の SSRF 対策: リダイレクト先のスキームとホスト（プライベートIPか否か）を検証します。また受信データ量に上限を設け、gzip の解凍後もサイズチェックを行います。
- J-Quants API 呼び出し: リトライ・指数バックオフ・429 の Retry-After 尊重・401 のトークン自動リフレッシュを行います。
- DuckDB への挿入は冪等性（ON CONFLICT）を意識した実装になっています。

---

## 開発・テストに関するヒント

- テスト時は環境変数の自動読み込みを無効化すると安定します:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- news_collector の HTTP 呼び出しは内部で `_urlopen` によって行われています。ユニットテストではこの関数をモックしてレスポンスを差し替えることが容易です。
- DuckDB をインメモリで使う場合は `":memory:"` を db_path に渡すと便利です。

---

## 今後の拡張案（参考）

- CLI や Scheduler（cron/airflow）向けのラッパーコマンドを追加（run_daily_etl を簡単に呼べる bin）
- Strategy / Execution 層の実装（現状はパッケージ構成が用意されています）
- より詳細な監視・メトリクス出力（Prometheus / Grafana 連携）
- テスト・CI の充実（モックを用いた外部 API のテスト）

---

もし特定の利用シナリオ（例えば「ローカルで毎朝 ETL を走らせるスクリプト」や「監査ログのクエリ例」）が必要であれば、その目的に応じたサンプルを追加で作成します。どのように使いたいか教えてください。