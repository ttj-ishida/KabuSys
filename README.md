# KabuSys

日本株向けの自動売買・データプラットフォーム用 Python ライブラリです。J-Quants / kabuステーション など外部 API からデータを取得して DuckDB に保存し、ETL、品質チェック、ニュース収集、監査ログ（発注/約定トレース）などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つモジュール群をまとめたパッケージです。

- J-Quants API から時系列データ（株価日足、財務、マーケットカレンダー）を安全かつ冪等に取得
- RSS からニュースを収集し、銘柄コード抽出と DB への冪等保存を実施
- DuckDB ベースのスキーマ（Raw / Processed / Feature / Execution / Audit）を提供し、簡単に初期化可能
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）を実装
- 市場カレンダーの管理・営業日判定ロジック、監査ログ（シグナル→発注→約定のトレース）を提供
- ネットワーク・セキュリティおよびデータ品質に配慮した設計（レート制御・リトライ・SSRF対策・XML攻撃防御・サイズ制限など）

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（レート制限、リトライ、トークン自動リフレッシュ）
  - fetch/save: 日足、財務、マーケットカレンダー
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- data.news_collector
  - RSS フィード取得、前処理、記事ID生成（正規化 URL → SHA256 ハッシュ）、SSRF 対策、gzip 上限チェック
  - raw_news / news_symbols への冪等保存（トランザクション、INSERT RETURNING）
  - 銘柄コード抽出（4桁数字）
- data.schema / data.audit
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema、init_audit_db による初期化
- data.pipeline
  - 差分 ETL（市場カレンダー → 株価 → 財務）、バックフィル、品質チェックの統合エントリ（run_daily_etl）
- data.calendar_management
  - 営業日判定、前後営業日の取得、カレンダー夜間更新ジョブ
- data.quality
  - 欠損・スパイク・重複・日付不整合のチェック（QualityIssue を返す）
- config
  - .env 自動読み込み（プロジェクトルート検出）と Settings（必須環境変数のラッパ）

---

## 必要条件

- Python 3.10 以上（型ヒントに | union を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml

（プロジェクト配布に pyproject.toml / requirements.txt があればそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン／取得

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係インストール（例）
   - pip install duckdb defusedxml

   またはプロジェクトに pyproject.toml / requirements.txt があれば:
   - pip install -e .
   - pip install -r requirements.txt

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

   .env の例（実際のトークンは安全に管理してください）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   # KABU_API_BASE_URL は省略可（デフォルト http://localhost:18080/kabusapi）
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id

   # DB パス（省略時 data/kabusys.duckdb）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境: development / paper_trading / live
   KABUSYS_ENV=development

   # ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマの初期化
   - Python REPL またはスクリプトで実行:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # ファイル DB
     # またはメモリ DB:
     # conn = schema.init_schema(":memory:")
     ```
   - 監査テーブル（order_events 等）を別 DB に初期化する場合:
     ```python
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（サンプル）

- 日次 ETL を実行する最小例
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import schema, pipeline

  # DB 初期化（既に初期化済みならコネクションを取得しても可）
  conn = schema.init_schema("data/kabusys.duckdb")

  # 日次 ETL を実行（target_date を省略すると今日）
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- RSS ニュース収集ジョブの実行例
  ```python
  import duckdb
  from kabusys.data import news_collector as nc

  conn = duckdb.connect("data/kabusys.duckdb")
  # 既知の有効銘柄コードセットがあれば渡す（extract_stock_codes で利用）
  known_codes = {"7203", "6758", "9984"}
  res = nc.run_news_collection(conn, sources=None, known_codes=known_codes)
  print(res)  # {source_name: 新規保存件数}
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data import calendar_management
  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print(f"saved: {saved}")
  ```

- J-Quants から直接データを取得して保存
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,1))
  saved = jq.save_daily_quotes(conn, records)
  ```

---

## 設定項目（環境変数）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 sqlite path（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — ログレベル（DEBUG/INFO/...。デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化

設定は kabusys.config.settings を通じて参照できます:
```python
from kabusys.config import settings
tok = settings.jquants_refresh_token
```

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（fetch/save）
    - news_collector.py        — RSS ニュース収集・DB 保存
    - schema.py                — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — カレンダー管理・営業日判定・更新ジョブ
    - audit.py                 — 監査ログ（signal/order/execution）スキーマ & 初期化
    - quality.py               — データ品質チェック（missing/spike/duplicate/date）
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（README に含まれるのは主要モジュールの一覧です。実装は src 内の各ファイルを参照してください）

---

## 設計上の注意点 / 運用メモ

- レート制御・リトライ
  - J-Quants クライアントは 120 req/min を固定間隔スロットリングで守ります。また一部ステータスで指数バックオフを実施し、401 ではリフレッシュを試みます。
- セキュリティ
  - news_collector は defusedxml を用いた XML パース、SSRF 対策（リダイレクト時のホスト検証）、受信サイズ上限、トラッキングパラメータ除去などを備えています。
- 冪等性
  - データ保存は ON CONFLICT DO UPDATE / DO NOTHING を活用し、再実行に耐えられる設計です。
- 品質チェック
  - ETL 実行後に run_all_checks を呼ぶことで欠損・重複・スパイク・日付不整合を検出できます。重大度エラーが出ても ETL は全体を続行する設計です（呼び出し元で判断してください）。
- 環境管理
  - .env 自動読み込みはプロジェクトルート検出に基づき行われます（.git または pyproject.toml が基準）。テスト時などは KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して無効化できます。

---

## 開発／テストについて

- 単体テストを作成する際、ネットワーク依存箇所（_urlopen、_request など）はモック可能なよう設計されています（モジュール関数を差し替えてテストしやすくする）。
- DB 周りは DuckDB をインメモリで利用して高速にテストできます（db_path=":memory:"）。

---

質問や追加したい項目（例: CLI、サービスデプロイ手順、CI 設定サンプルなど）があれば教えてください。README を用途に合わせて拡張します。