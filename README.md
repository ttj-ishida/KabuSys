# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォームの基盤ライブラリです。  
データ取得（J-Quants）、ETL、マーケットカレンダー管理、ニュース収集、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）など、戦略実行に必要な基盤機能を提供します。

---

## 概要

主な設計方針・特徴:

- J-Quants API を利用した株価・財務・マーケットカレンダーの取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いた階層化データスキーマ（Raw / Processed / Feature / Execution / Audit）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS を用いたニュース収集（トラッキングパラメータ除去、SSRF対策、XML注入対策、サイズ制限）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ用スキーマ（シグナル→発注要求→約定を UUID でトレース）
- 簡易なマーケットカレンダー操作ユーティリティ（営業日判定・前後の営業日取得 等）

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー）
  - レート制御、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存関数（raw_prices / raw_financials / market_calendar）
- data/schema.py
  - DuckDB のスキーマ定義と初期化（多層テーブル定義とインデックス）
  - init_schema() / get_connection()
- data/pipeline.py
  - 日次 ETL（run_daily_etl）および個別 ETL ジョブ（prices/financials/calendar）
  - 差分更新、バックフィル、品質チェックの統合
- data/news_collector.py
  - RSS 取得・正規化・前処理・記事保存（raw_news）と銘柄紐付け（news_symbols）
  - SSRF 対策・defusedxml による XML 攻撃対策・受信サイズ制限など
- data/calendar_management.py
  - カレンダー差分更新ジョブ（calendar_update_job）
  - 営業日判定・前後営業日・期間内の営業日取得関数
- data/quality.py
  - 欠損・スパイク・重複・日付不整合チェック（run_all_checks）
- data/audit.py
  - 監査ログ用スキーマの初期化（init_audit_schema / init_audit_db）
- config.py
  - 環境変数読み込み（.env / .env.local 自動読み込み、無効化フラグあり）
  - Settings クラス（J-Quants トークン、kabu API、Slack、DB パス、環境設定 等）

---

## セットアップ手順

前提:
- Python 3.10 以上（typing | union 型などを利用）
- DuckDB を利用するためネイティブライブラリが必要（pip でインストールされます）

1. リポジトリをクローン / ダウンロード

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）
   - pip install duckdb defusedxml

   （パッケージ管理用の setup.py / pyproject.toml がある場合は pip install -e . を使って開発インストールしてください）

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただしテスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します）。
   - 必須環境変数（Settings により取得されます）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabu ステーション等の API パスワード
     - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID : Slack チャンネル ID
   - 任意 / デフォルト値:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - DUCKDB_PATH : DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトから利用する最小例です。

- DuckDB スキーマ初期化:
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集を実行（既定の RSS ソース）:
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)  # {source_name: 新規保存件数}
  ```

- 監査ログスキーマの初期化:
  ```python
  from kabusys.data.audit import init_audit_schema
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- J-Quants から株価のみを差分取得して保存:
  ```python
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched}, saved={saved}")
  ```

注意点:
- run_daily_etl は複数ステップ（カレンダー→株価→財務→品質チェック）を順に実行し、各ステップは独立してエラーハンドリングされます。戻り値の ETLResult から詳細（品質問題やエラー）を確認できます。
- jquants_client はレート制御（120 req/min）・再試行（最大 3 回）・401 時のトークンリフレッシュを行います。テスト時は id_token を引数で注入して挙動を制御できます。

---

## 重要な設計・セキュリティ考慮

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector は SSRF 対策として:
  - リダイレクト先のスキームとホストの検証（private IP 拒否）
  - URL スキームは http/https のみ許可
  - defusedxml を利用して XML 攻撃を防ぐ
  - 受信サイズ上限（10 MB）を設けてメモリ DoS を防ぐ
- DuckDB 構成は冪等性を重視（ON CONFLICT ... DO UPDATE / DO NOTHING を利用）しています。
- すべてのタイムスタンプは UTC を前提（audit.init_audit_schema は SET TimeZone='UTC' を実行します）。

---

## ディレクトリ構成

主要なファイル／モジュール構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得 + 保存）
    - news_collector.py       — RSS ニュース収集・保存
    - schema.py               — DuckDB スキーマ定義・初期化
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  — マーケットカレンダー管理
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログスキーマ
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

補足:
- strategy, execution, monitoring の各パッケージは初期化用の __init__.py があり、戦略・発注系の実装を配置する想定です（現状は空のモジュール）。

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルトあり:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1で自動ロード無効化)

---

## 開発上のヒント

- テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを抑制し、必要な環境変数はテストコード側で注入してください。
- jquants_client の HTTP 呼び出しは urllib を使っています。テストでは urllib のオープン関数や module レベルの _urlopen / _RateLimiter をモックして制御するとよいでしょう（news_collector も _urlopen を差し替え可能）。
- DuckDB 接続は軽量でインメモリ（":memory:"）もサポートします。ユニットテストでは :memory: を使うと便利です。

---

この README はコードベース内の docstring と設計ノートに基づいて作成しています。実際の運用時は .env.example（プロジェクトに存在する場合）や外部ドキュメント（DataPlatform.md 等）が参照される想定です。必要なら運用手順や CI/CD、バックアップ・リストア方法、監視・アラート設定の追加ドキュメントも作成できます。