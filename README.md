# KabuSys

KabuSys は日本株向けの自動売買基盤のコアライブラリです。J-Quants API や RSS フィード等からデータを取得して DuckDB に格納し、ETL・品質チェック・監査ログ・カレンダー管理・ニュース収集などの機能を提供します。

主な設計方針:
- データ取得は API レート制限・リトライ・トークン自動リフレッシュを考慮
- DuckDB への保存は冪等（ON CONFLICT）で二重登録を防止
- ニュース収集は SSRF や XML 攻撃対策を実装
- 品質チェックで欠損・スパイク・重複・日付不整合を検出
- 監査ログでシグナル→発注→約定フローを完全トレース可能に

バージョン: 0.1.0

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー）
  - レート制御（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動再取得
  - DuckDB への冪等保存関数（save_daily_quotes 等）
  - fetched_at による取得時刻の記録（UTC）

- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) による初期化

- data/pipeline.py
  - 日次 ETL（run_daily_etl）：カレンダー→株価→財務→品質チェックの差分取得パイプライン
  - 差分更新・backfill 戦略をサポート

- data/news_collector.py
  - RSS フィードの取得・前処理・記事保存（raw_news）・銘柄抽出（news_symbols）
  - URL 正規化（トラッキングパラメータ削除）、記事ID = SHA-256(正規化URL) の先頭32文字
  - defusedxml を用いた安全な XML パース、SSRF/プライベートIP 回避、最大受信サイズ制限、gzip 対応

- data/calendar_management.py
  - market_calendar の管理、営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - calendar_update_job による夜間更新

- data/quality.py
  - 欠損データ、スパイク、重複、日付不整合の検出
  - QualityIssue オブジェクトで一覧を返す（severity による対応判断可能）

- data/audit.py
  - 監査ログ用テーブル（signal_events, order_requests, executions）を初期化
  - order_request_id を冪等キーとして二重発注を防止
  - init_audit_db / init_audit_schema を提供

- config.py
  - .env 自動読み込み（プロジェクトルート検出：.git または pyproject.toml）
  - 環境変数ラッパー settings（必須変数チェック、env/log_level 判定、DB パス設定）
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

その他ディレクトリ:
- strategy/: 戦略関連（初期化済みモジュール）
- execution/: 発注・ブローカー連携関連（初期化済みモジュール）
- monitoring/: 監視関連（初期化済みモジュール）

---

## 必要要件

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml
（プロジェクトの requirements.txt / pyproject.toml がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成と有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - pyproject.toml / requirements.txt がある場合はそれに従ってください。最低限:
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env`/`.env.local` を置くと自動で読み込まれます（読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（settings が参照するもの）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意 / デフォルト
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化（1）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. データベース初期化（DuckDB スキーマ）
   - Python から初期化:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```
   - 監査ログ専用 DB 初期化:
   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な例）

- 日次 ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

  - run_daily_etl は以下を順に行います:
    1. 市場カレンダー ETL（先読み）
    2. 株価日次 ETL（差分 + backfill）
    3. 財務データ ETL（差分 + backfill）
    4. 品質チェック（オプション）

- RSS ニュース収集を実行して保存する
  ```python
  import duckdb
  from kabusys.data import news_collector, schema

  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
  # 既知の銘柄コードを渡すと抽出して news_symbols へ紐付けます
  known_codes = {"7203", "6758", "9984"}
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)  # source_name -> 新規保存数
  ```

- J-Quants から特定銘柄の株価日足を直接取得して保存
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,2,1))
  saved = jq.save_daily_quotes(conn, records)
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data import calendar_management, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved:", saved)
  ```

- 監査スキーマの初期化（既存接続へ追加）
  ```python
  from kabusys.data import audit, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  audit.init_audit_schema(conn, transactional=True)
  ```

---

## 注意事項 / 実装上のポイント

- API のレート制御
  - jquants_client は 120 req/min を想定した固定間隔スロットリングを実装しています。
- リトライ
  - ネットワークエラーや 408/429/5xx 系は最大 3 回リトライ（指数バックオフ）。429 の場合は Retry-After を優先。
  - 401 受信時はトークンを自動でリフレッシュし 1 回だけ再試行します。
- 冪等性
  - DuckDB への保存は ON CONFLICT / DO UPDATE または DO NOTHING を使い冪等化しています。
- ニュース収集の安全対策
  - defusedxml を用いた XML パース、SSRF 用のリダイレクト検査、プライベート IP 拒否、最大受信サイズ制限、gzip の安全な解凍、トラッキングパラメータ除去などを備えています。
- テスト用フック
  - news_collector._urlopen などはテスト時にモックして差し替え可能です。
- 環境変数の自動読み込み
  - .env / .env.local が自動的にロードされます（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・モジュール構成（src/kabusys 下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理（settings）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント & DuckDB 保存
    - news_collector.py             — RSS ニュース収集・保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義・初期化
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        — カレンダー管理 / 夜間更新ジョブ
    - audit.py                      — 監査ログスキーマ初期化
    - quality.py                    — データ品質チェック
  - strategy/
    - __init__.py                   — 戦略関連（拡張用）
  - execution/
    - __init__.py                   — 発注/ブローカー連携（拡張用）
  - monitoring/
    - __init__.py                   — 監視関連（拡張用）

---

## 開発・拡張メモ

- strategy/ や execution/、monitoring/ は将来的に戦略や実運用連携を実装する想定で空モジュールとして置かれています。
- DuckDB を使っているため、分析・クエリの実行は高効率に行えます。大規模データや運用環境ではファイルバックアップや VACUUM 等の運用方針を検討してください。
- 本 README に記載のサンプルコードはライブラリ API の一例です。実行前に .env の設定と DB 初期化（schema.init_schema）を行ってください。

---

必要であれば README を用途に合わせて英語版に翻訳したり、運用手順（cron / systemd / Airflow での定期実行例）や CI テスト手順を追記できます。どの追加情報が必要か教えてください。