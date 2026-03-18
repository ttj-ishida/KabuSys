# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants API や RSS ニュース等からのデータ収集、DuckDB を用いたスキーマ管理・ETL、データ品質チェック、マーケットカレンダー管理、監査ログ（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

主な目的は「データ駆動の日本株自動売買システム基盤」を提供することです。  
設計上の特徴：

- J-Quants API から株価（日足）・財務データ・マーケットカレンダーを取得（レートリミット・リトライ・トークンリフレッシュ対応）
- RSS からニュース収集（SSRF対策、XMLセキュリティ、トラッキングパラメータ除去、記事IDハッシュ化）
- DuckDB による三層（Raw / Processed / Feature）+ Execution / Audit スキーマ
- ETL（差分取得、バックフィル、品質チェック）の実装
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- マーケットカレンダーの管理・営業日判定ユーティリティ
- 監査ログ（signal → order → execution のトレーサビリティ）
- 設定は環境変数 / .env ファイルから読み込み（自動ロード機能あり）

なお、strategy、execution、monitoring パッケージはプロジェクト構造上用意されていますが、ここに含まれるコードは本リポジトリのサンプル・骨組みを表しています。

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（トークン管理、自動リフレッシュ、ページネーション、レート制御、リトライ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への冪等保存（save_daily_quotes 等）

- data/news_collector.py
  - RSS フィード取得・前処理・記事ID生成（SHA-256）・DuckDB への保存
  - SSRF 対策、gzip 上限チェック、defusedxml による XML 安全パース
  - 銘柄コード抽出（4桁数字、既知銘柄フィルタ）

- data/schema.py
  - DuckDB スキーマ（Raw / Processed / Feature / Execution）定義と初期化
  - インデックス、外部キー、冪等なテーブル作成

- data/pipeline.py
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - run_daily_etl: 日次 ETL の一括実行

- data/calendar_management.py
  - market_calendar の差分更新ジョブと営業日判定ユーティリティ
  - next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day

- data/quality.py
  - 欠損・スパイク・重複・日付不整合チェック
  - run_all_checks: 全チェックの実行

- data/audit.py
  - 監査ログ用スキーマ（signal_events / order_requests / executions）
  - init_audit_db / init_audit_schema（UTC固定、トランザクションオプション）

- config.py
  - 環境変数および .env 自動読み込み（.env / .env.local）
  - 必須設定の検査（_require）
  - settings オブジェクトによる集中管理

---

## 前提条件 / 必要なもの

- Python 3.10 以上（union 型表記 (X | None) を使用しているため）
- 以下の主要依存パッケージ（最低限）
  - duckdb
  - defusedxml

必要に応じて追加のパッケージ（Slack 通知等）が必要になる機能があります。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 開発環境にパッケージをインストール
   - プロジェクトが pyproject.toml / setup.py を含む場合:
     ```
     pip install -e .
     ```
   - 依存パッケージだけを個別にインストールする場合:
     ```
     pip install duckdb defusedxml
     ```

4. 環境変数の設定
   - 必須（環境に合わせて設定してください）:
     - JQUANTS_REFRESH_TOKEN  : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD       : kabu ステーション API パスワード（実行機能を使う場合）
     - SLACK_BOT_TOKEN         : Slack ボットトークン（通知を使用する場合）
     - SLACK_CHANNEL_ID        : Slack チャンネル ID
   - オプション / デフォルト:
     - KABUSYS_ENV             : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL               : DEBUG/INFO/...（デフォルト: INFO）
     - DUCKDB_PATH             : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH             : 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - .env 自動読み込み:
     - プロジェクトルートの .env と .env.local が自動的に読み込まれます（OS 環境変数優先）。
     - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. DB スキーマ初期化（例）
   - Python REPL やスクリプトで以下を実行:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # ファイル DB
     # またはインメモリ:
     # conn = schema.init_schema(":memory:")
     ```

6. 監査ログ DB 初期化（監査を別 DB に分ける場合）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主要な例）

- 日次 ETL 実行（最小例）
  ```python
  from kabusys.data import schema, pipeline
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)
  # 初回のみ schema.init_schema(settings.duckdb_path)

  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- DuckDB を初期化して ETL 実行（新規セットアップ）
  ```python
  from kabusys.data import schema, pipeline
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)
  res = pipeline.run_daily_etl(conn)
  print(res.prices_fetched, res.prices_saved)
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes に有効銘柄コードセットを渡すと記事と銘柄を紐付ける
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved calendar rows:", saved)
  ```

- J-Quants API を直接呼ぶ（テスト・ユーティリティ）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  from kabusys.config import settings

  # settings.jquants_refresh_token が設定されていれば自動で token を取得して実行
  rows = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,2,1))
  ```

- 品質チェックを単体で実行
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")

  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

テスト時には id_token を外部から注入すること（jquants_client の関数は id_token を引数で受け取れる）で外部 API をモックしやすく設計されています。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須 for execution) — kabu API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite モニタリング DB（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — ログレベル

.env の自動読み込みはプロジェクトルート（.git または pyproject.toml を起点）を探索して行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

以下は主要ファイル／モジュール構成（src レイアウト）です。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（取得・保存）
    - news_collector.py        # RSS ニュース収集
    - schema.py                # DuckDB スキーマ定義・初期化
    - pipeline.py              # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   # マーケットカレンダー関連ユーティリティ
    - audit.py                 # 監査ログスキーマ（signal/order/execution）
    - quality.py               # データ品質チェック
  - strategy/
    - __init__.py              # 戦略層（拡張用）
  - execution/
    - __init__.py              # 発注/約定層（拡張用）
  - monitoring/
    - __init__.py              # 監視・アラート用（拡張用）

プロジェクトルートには .env/.env.local/.env.example を置き、機密情報は .env.local に置くのが推奨です（.env.local を .gitignore に含める）。

---

## 運用上の注意 / セキュリティ

- .env に認証情報を含める場合は必ずリポジトリにコミットしないでください（.gitignore を利用）。
- RSS フィード取得では SSRF 対策や Gzip サイズチェック等を実施していますが、外部フィードの扱いには注意してください。
- DuckDB ファイルのバックアップ・権限管理を適切に行ってください。
- 実運用での発注（live 環境）では必ず paper_trading で十分にテストを行ってください。
- 監査ログは削除しない設計（ON DELETE RESTRICT）になっています。保持方針は運用要件に従ってください。

---

## 補足 / 今後の拡張案

- strategy / execution / monitoring の具体実装（注文送信、ポートフォリオ最適化、リアルタイム監視）
- Slack 等への通知機能の実装
- CI/CD や自動バッチ（cron / Airflow）向けの実行ラッパー
- 統計・ダッシュボード（監視用 DB へのデータ投入や可視化）

---

何か特定の使い方、設定ファイルのテンプレート、または strategy/execution 層の実装例が必要でしたらお知らせください。README の補強（例: .env.example の自動生成、CLI コマンド追加など）も対応できます。