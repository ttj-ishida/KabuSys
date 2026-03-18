# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
J-Quants や RSS を用いたデータ収集、DuckDB によるスキーマ管理、ETL パイプライン、データ品質チェック、監査ログ用スキーマなどを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けに設計されたモジュール群です。  
主に以下を目的としています：

- J-Quants API からの株価・財務・カレンダー取得（レートリミット・再試行・トークン自動リフレッシュ対応）
- RSS からのニュース収集と銘柄紐付け（SSRF 対策、XML 攻撃対策、サイズ上限などの堅牢設計）
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計上のポイント：Idempotency（冪等性）、トレーサビリティ、セキュリティ（SSRF・XML Bomb 等対策）、レート制御、堅牢なエラーハンドリング。

---

## 主な機能一覧

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local 自動読み込み（無効化可能）
  - 必須環境変数の取得とバリデーション
- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - 日次株価（OHLCV）、四半期財務、マーケットカレンダー取得
  - レートリミット（120 req/min）、再試行（指数バックオフ）、401 時のトークンリフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT）
- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードの取得、前処理、記事ID生成（正規化 URL → SHA-256 前方 32 文字）
  - SSRF 対策（スキーマ検証、プライベート IP チェック、リダイレクト検証）
  - defusedxml による XML の安全なパース、受信サイズ上限
  - DuckDB への一括トランザクション保存（INSERT ... RETURNING）
  - 記事と銘柄コードの紐付け
- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義、init_schema/get_connection
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分抽出（最終取得日ベース）、バックフィル、品質チェックの統合
  - run_daily_etl: カレンダー→価格→財務→品質チェックを順に実行
- マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
  - 営業日判定、前後営業日の探索、カレンダー差分更新ジョブ
- 監査ログ（src/kabusys/data/audit.py）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化
  - UTC タイムゾーン固定、冪等キーによる二重発注防止
- 品質チェック（src/kabusys/data/quality.py）
  - 欠損、重複、スパイク、日付不整合の検出と QualityIssue レポート生成

---

## セットアップ手順

1. リポジトリをクローン／取得し、Python 仮想環境を作成・有効化します。

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要な依存パッケージをインストールします（例: duckdb, defusedxml 等）。

   例（pip）:

   ```bash
   pip install duckdb defusedxml
   ```

   実際のプロジェクトでは requirements.txt / pyproject.toml を用意している想定です。必要に応じて追加パッケージ（例えば J-Quants 用の HTTP クライアント等）を導入してください。

3. 環境変数を準備します。

   プロジェクトルートに .env または .env.local を置くと自動的に読み込まれます（src/kabusys/config.py が .git や pyproject.toml からプロジェクトルートを探索します）。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   サンプル .env:

   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here

   # kabu ステーション API
   KABU_API_PASSWORD=your_kabu_password
   # KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマを初期化します（例: Python REPL またはスクリプト）:

   ```python
   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)
   ```

   監査ログ専用 DB を初期化する場合:

   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（基本サンプル）

以下は主要な関数の使用例です。実行は仮想環境下で行ってください。

- 設定の読み取り:

  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- スキーマ初期化:

  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行:

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定しなければ本日
  print(result.to_dict())
  ```

- ニュース収集ジョブ:

  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知銘柄コードセット（例）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダー更新ジョブ（夜間バッチ用）:

  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 品質チェックの個別実行:

  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for issue in issues:
      print(issue)
  ```

注意点:
- J-Quants API はレート制限や認証トークン期限切れに対応するため、get_id_token / _request 内で自動処理します。大量取得時はレート制御を尊重してください。
- news_collector は外部 URL をフェッチするため SSRF 対策・サイズ制限・gzip 解凍制限などを行っています。テスト時は fetch 関数や _urlopen をモックすることを推奨します。

---

## ディレクトリ構成

（リポジトリの src ディレクトリを基準）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（取得 + 保存）
    - news_collector.py                — RSS ニュース収集 / 保存 / 銘柄抽出
    - schema.py                        — DuckDB スキーマ定義 / init_schema
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py           — 市場カレンダー関連ユーティリティ
    - audit.py                         — 監査ログ（signal / order / execution）
    - quality.py                       — データ品質チェック
  - strategy/
    - __init__.py                      — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                      — 実行（ブローカー連携用フック等）
  - monitoring/
    - __init__.py                      — 監視 / メトリクス（拡張ポイント）

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用（別用途）SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合 1 を設定

---

## セキュリティ・運用上の注意

- news_collector は SSRF、XML Bomb、gzip Bomb などを防ぐため複数の防御を実装しています：スキーム検証、プライベート IP チェック、defusedxml、最大レスポンスサイズチェック、gzip 解凍後サイズチェック、リダイレクト検査など。
- J-Quants API への呼び出しはモジュール内でレート制限とリトライ処理を行いますが、外部からの呼び出し頻度も考慮して運用してください。
- DuckDB ファイルは適切にバックアップしてください。監査ログは削除しない前提の設計です。
- 本コードはライブラリ的提供を想定しています。実際に取引を行う場合は別途ブローカー接続・注文周りの実装と厳格なテストが必要です（特に live 環境）。

---

## 開発時のヒント

- 環境変数読み込みの自動化は config.py によるため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用するか、必要な env をプロセス環境に設定してください。
- HTTP 呼び出しや外部依存をテストする際は、jquants_client._request / news_collector._urlopen 等をモックすると良いです。
- DuckDB に対する単体テストは ":memory:" を使うことでファイル操作を回避できます（schema.init_schema(":memory:")）。

---

もし README に追加したい「運用手順」や「デプロイ例（systemd / cron / Airflow 等）」「実際の戦略実装サンプル」などがあれば指示してください。必要に応じてサンプルスクリプトや CI 設定例も作成します。