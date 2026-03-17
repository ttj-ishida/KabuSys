# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。J-Quants API や RSS フィードからデータを収集・保存し、ETL（差分取得・品質チェック）やマーケットカレンダー管理、ニュース収集、監査ログなどを通じて戦略／実行層に必要なデータ基盤を提供します。

主な設計方針は「冪等性」「トレーサビリティ」「セキュリティ（SSRF/XML攻撃対策等）」「APIレート制限遵守」「品質チェックの可視化」です。

---

## 主な機能

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPXマーケットカレンダー取得
  - レート制限（120 req/min）・再試行（指数バックオフ）・トークン自動リフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS フィードの安全な取得（defusedxml、SSRF対策、受信サイズ制限）
  - URL 正規化とトラッキングパラメータ除去、SHA-256 による記事ID生成（冪等）
  - DuckDB へのバルク保存（INSERT ... RETURNING）と銘柄コード抽出・紐付け

- ETL パイプライン
  - 差分更新（最終取得日からの差分 + バックフィル）
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- マーケットカレンダー管理
  - 営業日判定、前後の営業日取得、期間内の営業日列挙
  - 夜間バッチでの差分更新（バックフィル・健全性チェック）

- データスキーマ／初期化
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - 初期化ユーティリティ（init_schema / init_audit_schema / init_audit_db）

- 監査ログ
  - シグナル→発注→約定のトレーサビリティ（UUID 連鎖）
  - 発注要求の冪等キー（order_request_id）や状態管理

- データ品質チェック
  - 欠損（OHLC）、スパイク（前日比閾値）、重複（PK 重複）、日付不整合（未来日・非営業日）検出

---

## 要求環境 / 依存パッケージ

- Python 3.10 以上（型ヒントに | 演算子を使用）
- 主要依存（例）
  - duckdb
  - defusedxml

（上記はコードから必要と推測される最小集合です。実運用では追加の依存や開発用パッケージが必要になる場合があります。）

---

## セットアップ手順（開発環境向け簡易ガイド）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - pyproject.toml / setup がある場合（編集したい場合）:
     ```
     pip install -e .
     ```
   - あるいは最低限の依存を直接インストール:
     ```
     pip install duckdb defusedxml
     ```

4. 環境変数を設定
   - ルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（自動ロードはデフォルトで有効）。
   - 必須環境変数（アプリ実行に必須）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH （デフォルト: data/monitoring.db）
   - 自動 .env ロードを無効化する:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   例 `.env`（参考）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要な API と実行例）

以下は Python スクリプトや REPL 内での使用例です。各関数は duckdb 接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

- スキーマ初期化（DuckDB ファイルを作成しテーブルを作る）
  ```python
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)
  ```

- 日次 ETL 実行（市場カレンダー更新 → 株価・財務差分取得 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema
  from kabusys.config import settings
  from datetime import date

  conn = schema.get_connection(settings.duckdb_path)  # 既存 DB に接続
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブの実行（RSS 収集と保存、銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 事前に保有する銘柄リストなど
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source: 新規保存件数}
  ```

- マーケットカレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 監査ログスキーマの初期化（audit）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- J-Quants の ID トークン取得（テストやデバッグ用）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使う
  ```

注意:
- ネットワーク呼び出しは urllib を使って行われます。プロキシやファイアウォール設定がある環境では適切に設定してください。
- J-Quants API はレート制限があります。jquants_client は内部で固定間隔スロットリングとリトライを行いますが、運用側でもスケジュールや同時実行数に注意してください。

---

## 設計上の注意点 / 運用上のヒント

- 自動 .env ロード:
  - プロジェクトルートは .git または pyproject.toml を基準に探索します。CWD に依存しません。
  - テスト時など自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- ID トークン管理:
  - jquants_client はモジュール内で ID トークンをキャッシュし、401 を検出すると自動リフレッシュを一度試みます。

- DuckDB:
  - init_schema() は親ディレクトリを自動作成します。
  - インメモリ DB を使うには db_path に ":memory:" を渡します（テスト用）。

- ニュース収集の安全性:
  - defusedxml を使い XML 攻撃を防ぎます。
  - SSRF 対策としてスキーム検証・DNS 解決によるプライベートIP検査・リダイレクト検査を実施します。
  - レスポンス上限（10MB）を超えたコンテンツはスキップします。

- 品質チェック:
  - run_all_checks は Fail-Fast ではなく全チェックを実行し、検出結果を返します。呼び出し元で致命度に応じた対応を行ってください。

---

## ディレクトリ構成（主要ファイル）

（抜粋）プロジェクトのソースは `src/kabusys` 以下にあります。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（自動 .env 読み込み、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py
      - RSS 取得・前処理・記事保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL（差分取得、品質チェック）および run_daily_etl
    - calendar_management.py
      - マーケットカレンダー管理、営業日判定、calendar_update_job
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）と初期化
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py  (戦略層の拡張ポイント)
  - execution/
    - __init__.py  (発注・実行層の拡張ポイント)
  - monitoring/
    - __init__.py  (監視周りの拡張ポイント)

---

## 貢献 / 拡張ポイント

- strategy や execution の各モジュールは空のパッケージとして用意されています。独自戦略やブローカー接続はここに実装してください。
- news_collector の RSS ソースや銘柄抽出ロジックはプロジェクトごとに調整が必要です（known_codes の管理や NLP による抽出精度向上など）。
- 品質チェックやアラート連携（Slack 通知等）は monitoring / 監視層で組み合わせる想定です。

---

README は以上です。追加したい使い方（例: systemd / cron のジョブ設定、Slack 通知統合、CI 流れなど）があれば、例を追記します。