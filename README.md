# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。  
データ取得・保存（DuckDB）、スキーマ定義、監査ログ、データ品質チェックなどの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、自動売買システムの基盤となる共通モジュール群です。主な目的は次のとおりです。

- J-Quants API からの市場データ・財務データ・取引カレンダーの取得と保存
- DuckDB によるスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 発注・約定のトレーサビリティを確保する監査ログ（監査スキーマ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 環境変数管理（.env 自動ロード、必須値チェック）

設計上のポイント:
- API レート制限・リトライ・トークン自動リフレッシュを備えた J-Quants クライアント
- DuckDB の INSERT は ON CONFLICT DO UPDATE により冪等性を確保
- すべてのタイムスタンプは UTC を想定（監査ログなど）

---

## 主な機能一覧

- config
  - .env / 環境変数の自動ロード（プロジェクトルート検出）
  - 必須設定の取得・検証（Settings クラス）
- data.jquants_client
  - get_id_token: リフレッシュトークンから id_token 取得（自動リフレッシュ対応）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar: ページネーション対応でデータ取得
  - save_daily_quotes / save_financial_statements / save_market_calendar: DuckDB へ冪等的に保存
  - 内部でレートリミッタ・リトライ（指数バックオフ）を実装
- data.schema
  - init_schema(db_path): DuckDB スキーマ（全テーブル・インデックス）を初期化
  - get_connection(db_path): 既存 DB への接続
- data.audit
  - init_audit_schema(conn) / init_audit_db(db_path): 監査ログ（signal_events / order_requests / executions）を初期化
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks: すべての品質チェックを実行し QualityIssue のリストを返す
- package エクスポート
  - kabusys.__all__ = ["data", "strategy", "execution", "monitoring"]

注: strategy / execution / monitoring パッケージはこのリポジトリ内での骨組みを提供します（実装は拡張して利用）。

---

## 要件

- Python 3.10+
- 依存パッケージ（最低限）
  - duckdb

※ 実運用で Slack 通知や他外部サービスを使う場合はそれらの SDK が必要になります（本コードベースでは Slack クライアントは含まれていませんが、設定変数は用意されています）。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストールします。

   ```bash
   pip install duckdb
   # 追加パッケージがあれば requirements.txt を用意して `pip install -r requirements.txt` を利用
   ```

3. 環境変数を設定します。
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で使用）。

   例: `.env`（実運用では秘密情報は安全に管理してください）

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password_here
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DB スキーマを初期化します（下記の使用例を参照）。

---

## 使い方（基本例）

以下はライブラリを使った典型的なワークフロー例です。

- DuckDB スキーマを初期化して接続を得る

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # :memory: も可
```

- J-Quants から日足を取得して保存する

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

- 監査ログ（audit）を追加で初期化する（既存接続に対して）

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

- データ品質チェックを実行する

```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn)
for issue in issues:
    print(issue.check_name, issue.table, issue.severity, issue.detail)
    for row in issue.rows:
        print("  sample:", row)
```

- 既存 DB に接続する（スキーマ初期化は行わない）

```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

注意点:
- fetch 系関数はページネーションと API レート制御、リトライ、トークン自動リフレッシュを組み合わせて実装されています。
- save_* 関数は ON CONFLICT DO UPDATE により冪等にデータを格納します。

---

## 設定（Environment variables）

主要な環境変数（Settings クラスで使用／検証されます）:

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
  - SLACK_BOT_TOKEN: Slack ボットトークン（通知に使用する場合）
  - SLACK_CHANNEL_ID: Slack チャネル ID
- 任意（デフォルトあり）
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
  - LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL、デフォルト: INFO）
- 自動 .env 読み込みを無効にする:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

設定が不足している（必須キーが未設定）の場合は Settings プロパティが ValueError を送出します。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・モジュール構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - schema.py
      - audit.py
      - quality.py
      - (その他: raw / processed / feature / execution 層向けのDDLやユーティリティ)
    - strategy/
      - __init__.py
      - (戦略関連モジュールを配置)
    - execution/
      - __init__.py
      - (発注・約定関連モジュールを配置)
    - monitoring/
      - __init__.py
      - (監視・メトリクス関連モジュールを配置)

各ファイルの役割（概要）
- config.py: .env の自動ロード、Settings クラス（環境変数の取得と検証）
- data/jquants_client.py: J-Quants API クライアント、データ取得・保存ロジック
- data/schema.py: DuckDB スキーマ定義と初期化関数
- data/audit.py: 監査ログ用スキーマと初期化
- data/quality.py: データ品質チェック実装
- strategy/, execution/, monitoring/: 上位レイヤ（拡張ポイント）

---

## 注意事項 / 運用上のヒント

- J-Quants API のレート制限（120 req/min）に注意してください。本クライアントはスロットリングを実装していますが、複数プロセスで同時アクセスする場合は工夫が必要です。
- 秘密情報（トークン・パスワード）は .env 等に保存する場合でも適切に権限・管理を行ってください。
- DuckDB ファイルはデフォルトで `data/kabusys.duckdb` に保存されます。バックアップ・スキーママイグレーションの運用を検討してください。
- 監査ログは削除しない前提で設計されています（FK は ON DELETE RESTRICT）。監査テーブルの扱いには注意してください。

---

必要であれば、README にサンプル ETL スクリプト、CI 用の DB 初期化手順、ローカル開発用の .env.example ファイルなどの追加を行います。どの情報を優先的に追加したいか教えてください。