# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのライブラリです。J-Quants や kabuステーション と連携し、データの ETL、品質チェック、ニュース収集、監査ログ、発注フローの下地を提供します。

主な設計方針は「冪等性」「トレーサビリティ」「外部 API の堅牢な扱い（レート制御・リトライ）」「SSRF / XML 攻撃対策」などで、運用環境（本番 / ペーパー / 開発）に応じた設定管理をサポートします。

## 主な機能一覧
- 環境変数管理（.env 自動読み込み / 必須変数チェック）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX カレンダーの取得
  - レート制限・リトライ・トークン自動更新対応
  - DuckDB への冪等保存関数
- ニュース収集（RSS）
  - URL 正規化・トラッキングパラメータ除去
  - SSRF / XML 攻撃対策（defusedxml、リダイレクト検査、ホスト検証）
  - DuckDB への冪等保存（INSERT ... RETURNING）
  - 銘柄コード抽出と紐付け
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理・営業日ロジック
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- 監査ログ（シグナル→発注→約定のトレーサビリティ用スキーマ）
- （骨組み）戦略・発注・監視用パッケージ構成（strategy, execution, monitoring）

---

## 動作要件
- Python 3.10 以上（PEP 604 の型注釈（|）等を使用）
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API・RSS フィード・kabuステーション など）

必要に応じて他のライブラリ（Slack 連携など）を追加でインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成と有効化
   Linux / macOS:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```
   Windows (PowerShell):
   ```
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. 必要パッケージをインストール
   requirements.txt が無い場合は最低限以下をインストールしてください:
   ```
   pip install duckdb defusedxml
   ```
   開発中は editable install が便利です:
   ```
   pip install -e .
   ```

4. 環境変数 (.env) の準備
   プロジェクトルートの `.env`（または `.env.local`）に必須設定を配置します。パッケージは自動的にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` をロードします。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   最小例（`.env`）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_api_password
   #KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意

   # Slack 通知
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   Python REPL やスクリプトからスキーマを作成します（初回のみ）:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```

---

## 使い方（代表的な例）

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り DB に読み書きします。例をいくつか挙げます。

- 設定の利用
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  is_live = settings.is_live
  db_path = settings.duckdb_path
  ```

- スキーマ初期化 / 既存 DB への接続
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.config import settings

  # 初期化＋接続
  conn = init_schema(settings.duckdb_path)

  # 既存 DB 接続（スキーマ初期化は行わない）
  conn2 = get_connection(settings.duckdb_path)
  ```

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- J-Quants から日足を直接取得して保存
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  token = jq.get_id_token()  # settings.jquants_refresh_token を使ってトークンを取得
  records = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,3,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- RSS ニュース収集と銘柄紐付け
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 事前に用意した有効銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=None, reference_date=date.today())
  for i in issues:
      print(i)
  ```

- 監査スキーマの初期化（audit 用テーブルを追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn)
  ```

---

## 設定（環境変数）
主要な環境変数は次のとおりです（README の .env 例参照）:

- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須、通知等で使用）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

自動環境変数ロードはプロジェクトルートにある `.env` / `.env.local` から読み込みます。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

主要ファイル／ディレクトリ（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - news_collector.py           — RSS ニュース収集・正規化・DB 保存
    - schema.py                   — DuckDB スキーマ定義・初期化
    - pipeline.py                 — ETL パイプライン（差分取得 / 品質チェック）
    - calendar_management.py      — 市場カレンダー管理・営業日ロジック
    - audit.py                    — 監査ログテーブル（トレーサビリティ）
    - quality.py                  — データ品質チェック
  - strategy/
    - __init__.py                 — 戦略層（拡張ポイント）
  - execution/
    - __init__.py                 — 発注・約定管理（拡張ポイント）
  - monitoring/
    - __init__.py                 — 監視・メトリクス（拡張ポイント）

この構成は、Raw → Processed → Feature → Execution といったレイヤー分離を反映しており、各モジュールは単一責務でテストしやすいよう設計されています。

---

## 注意点・運用上のヒント
- J-Quants API はレート制限（120 req/min）があります。jquants_client は固定間隔のスロットリングとリトライロジックを実装していますが、運用時は過負荷にならないよう ETL スケジュールを調整してください。
- DuckDB のファイルは排他管理に注意してください。複数プロセスで同じ DB に同時書き込みする場合の挙動・ロックを運用で確認してください。
- ニュース収集では外部からの XML や URL を扱うため SSRF / XML Bomb への対策を行っていますが、運用環境で追加制約（プロキシ、IP ホワイトリスト等）を導入することを推奨します。
- 本番環境（KABUSYS_ENV=live）の場合、API キー・パスワードは安全に管理し、.env をソース管理しないでください。
- 単体テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うと .env 自動読み込みを無効化できます。

---

必要に応じて README にサンプル .env.example、Docker / systemd の起動例、CI 設定、より詳細な API 使用方法（kabuステーション との発注フロー等）を追加できます。追加したい内容があれば指示してください。