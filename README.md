# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）の README。  
本リポジトリはデータ収集（J-Quants / RSS）、ETLパイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ用スキーマなどを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。主な目的は次の通りです。

- J-Quants API からの株価（日足）・財務データ・マーケットカレンダーの取得
- RSS フィードからのニュース収集と銘柄紐付け
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution / Audit）の定義と初期化
- ETL（差分取得・冪等保存）パイプラインとデータ品質チェック
- マーケットカレンダーの管理（営業日判定、前後営業日探索など）
- 監査ログ（signal → order → execution のトレース）用スキーマ

設計上の特徴：
- API レート制御（J-Quants: 120 req/min）と再試行（指数バックオフ）
- トークン自動リフレッシュ（401 時に1回リトライ）
- DuckDB への保存は冪等（ON CONFLICT ... DO UPDATE / DO NOTHING）
- RSS 収集は SSRF・XML Bomb 等に配慮（defusedxml、リダイレクト検査、受信サイズ制限）
- 品質チェックで欠損・スパイク・重複・日付不整合を検出

---

## 機能一覧

- data.jquants_client
  - J-Quants API クライアント（株価、財務、カレンダー取得）
  - RateLimiter / リトライ / id_token リフレッシュ
  - DuckDB への保存関数（save_daily_quotes 等）
- data.news_collector
  - RSS 取得、記事整形、記事ID生成（正規化URL→SHA-256）、DuckDB への保存
  - URL 正規化、トラッキングパラメータ削除、SSRF対策
- data.schema
  - DuckDB のテーブルDDL（Raw / Processed / Feature / Execution）定義と init_schema()
- data.pipeline
  - 差分ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 日次ETL 実行エントリ run_daily_etl()
  - 差分・バックフィル・品質チェック統合
- data.calendar_management
  - market_calendar 管理、営業日判定、next/prev_trading_day、get_trading_days
  - カレンダー夜間更新ジョブ calendar_update_job()
- data.quality
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - run_all_checks()
- data.audit
  - 監査ログ（signal_events / order_requests / executions）DDL、init_audit_schema / init_audit_db
- 設定管理（config.py）
  - 環境変数の自動読み込み（.env, .env.local）と Settings オブジェクト
  - 必須環境変数の検証
- monitoring, strategy, execution パッケージ（スケルトン）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository_url>
   cd <repository_root>
   ```

2. Python 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージをインストール（本プロジェクトで使われている主な外部依存）
   ```
   pip install duckdb defusedxml
   ```
   ※必要に応じてその他の依存（例えばテストフレームワークなど）を追加してください。

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（config.py の自動ロード機能）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例（.env.example）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   # KABU_API_BASE_URL=http://localhost:18080/kabusapi  # デフォルトあり

   # Slack (通知等)
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_channel_id

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境 / ログ
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化（例）
   - Python REPL もしくはスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイル DB を作成して接続を返す
   ```
   - 監査ログ専用 DB を初期化する場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要 API と例）

以下は代表的な利用例です。実行は Python スクリプトやジョブランナーから行う想定です。

- J-Quants の ID トークン取得（通常は内部で自動処理される）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
```

- 日次 ETL を実行（market calendar → prices → financials → 品質チェック）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")  # 初回は init_schema を推奨
result = run_daily_etl(conn)
print(result.to_dict())
```

- 市場カレンダー夜間更新ジョブ
```python
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved", saved)
```

- RSS ニュース収集（保存と銘柄紐付け）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# sources を省略するとデフォルト RSS ソースを使用
# known_codes は銘柄抽出に使う有効コードセット（例: {"7203", "6758"}）
result = run_news_collection(conn, known_codes={"7203","6758"})
print(result)  # {source_name: 新規保存件数}
```

- データ品質チェックを個別実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
```

- DuckDB をインメモリで使う（テスト）
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

注意点:
- jquants_client はレート制限・リトライを内部で処理します。大量取得時は間隔に注意してください。
- config.Settings は必須の環境変数が未設定だと ValueError を投げます。
- news_collector は外部 URL を取得するためネットワークアクセスが必要です。SSRF 対策として非 http(s) は拒否されます。

---

## 環境変数一覧 (主なもの)

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（現在のコードベースでは利用箇所がある想定）
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — execution 環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するフラグ（値は任意。存在すれば無効）

---

## ディレクトリ構成

主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py        — RSS ニュース収集と DB 保存・銘柄抽出
    - pipeline.py              — ETL パイプライン（差分・バックフィル・品質チェック）
    - calendar_management.py   — マーケットカレンダー管理（営業日判定等）
    - schema.py                — DuckDB スキーマ定義と init_schema()
    - audit.py                 — 監査ログスキーマ（signal / order / execution）
    - quality.py               — データ品質チェック群
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

説明:
- data/schema.py は DB のすべてのDDL（Raw / Processed / Feature / Execution）を持ち、init_schema() で初期化します。
- data/jquants_client.py は API とのやりとりと DuckDB 保存ロジックを担います（レート制御・再試行・token refresh）。
- data/news_collector.py は RSS を安全に取得して raw_news 等へ保存、銘柄コード抽出までを行います。
- data/pipeline.py は日次ETL の統合ロジック（run_daily_etl）を提供します。
- data/audit.py はトレーサビリティ用の監査テーブルを生成するユーティリティです。

---

## 注意事項 / 運用メモ

- DuckDB のトランザクションや RETURNING を多用しており、実行時の例外では適切に rollback を行う実装が組まれています。ETL実行時はログと結果（ETLResult）を確認してください。
- NewsCollector は外部 HTTP の取得を行うため、運用環境ではプロキシ・ネットワークポリシーに注意してください。
- 本リポジトリはライブラリ層の実装が中心で、実行用 CLI やデプロイ用の runner スクリプトは含まれていません。運用ジョブ（cron / Airflow / Prefect 等）から上記 API を呼ぶことを想定しています。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD をセットして自動 .env 読み込みを無効化し、環境を制御することを推奨します。

---

## さらに

- ドキュメント（DataPlatform.md, API 使用方針等）が別途あることを想定しています。本 README はコードベースから読み取れる主要機能と基本的な使い方をまとめたものです。
- 追加のユーティリティ（Slack への通知、監視 DB 連携、注文実行ロジック等）は execution / monitoring パッケージに実装を追加してください。

---

フィードバックや補足したい点があれば教えてください。README を実際の運用手順や CI/CD に合わせて調整できます。