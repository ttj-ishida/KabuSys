# KabuSys

日本株向け自動売買プラットフォームの骨組み（ライブラリ）です。  
データ収集（J-Quants）、DuckDBスキーマ定義、ETLパイプライン、データ品質チェック、監査ログ等の基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を主目的とした内部ライブラリ群です。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- DuckDB に対するスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェックを含む日次パイプライン）
- データ品質チェックモジュール（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティを担保するテーブル群）

設計上の特徴:
- API 利用は 120 req/min を守る固定間隔スロットリング
- 指数バックオフによるリトライ（408/429/5xx 対象、最大 3 回）
- 401 の場合はリフレッシュして再試行（1回のみ）
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- ETL は差分取得を基本とし、後出し修正を吸収するためのバックフィルをサポート

---

## 機能一覧

- 環境変数 / .env 自動読み込み（プロジェクトルート基準、.env.local > .env、無効化フラグあり）
- settings: アプリ設定のラッパー（必須環境変数チェックを含む）
- J-Quants クライアント（fetch / save の機能）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- DuckDB スキーマ管理
  - init_schema(db_path), get_connection(db_path)
  - テーブル: raw_prices, raw_financials, market_calendar, features, signals, orders, trades, positions, ... 等多数
- ETL パイプライン
  - run_daily_etl(conn, target_date=..., run_quality_checks=True, ...)
  - 個別: run_prices_etl, run_financials_etl, run_calendar_etl
- データ品質チェック
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks(conn, ...)
- 監査ログ（audit）
  - init_audit_schema(conn), init_audit_db(db_path)
  - テーブル: signal_events, order_requests, executions（UUID を用いたトレーサビリティ）

---

## 動作要件

- Python >= 3.10（型ヒントで | 記法を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - （その他ネットワーク・ログ関連は標準ライブラリで実装されているため、追加パッケージはプロジェクト要件に応じて導入）

requirements.txt 等がある場合はそれに従ってください。

---

## 環境変数

必須（アプリ実行に必須）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルト値がある／任意）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: ライブラリ起動時の .env 自動ロードを無効化

.env の自動読み込み
- プロジェクトルートは __file__ の親階層で `.git` または `pyproject.toml` を探して判定
- 読み込み順: OS 環境変数 > .env.local > .env
- .env 解析は export KEY=val, quoted values, inline comments 等に対応

---

## セットアップ手順

1. リポジトリをチェックアウト

   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例: duckdb）

   ```
   pip install duckdb
   ```

   開発用途ならプロジェクトルートで editable インストール:

   ```
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成し、必須変数を設定してください。
   - 例 (.env):

     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     LOG_LEVEL=INFO
     ```

   - 自動ロードを無効にする場合:

     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（簡単な例）

以下はライブラリの主要ユースケースのコード例です。

1) DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path はデフォルト "data/kabusys.duckdb" を指す
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL の実行（J-Quants から取得して保存・品質チェックまで）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())
```

3) 監査ログテーブルを追加する

```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
init_audit_schema(conn)  # 既存接続へ監査テーブルを追加
```

4) 個別のデータ取得（テストや手動取得）

```python
from kabusys.data import jquants_client as jq

# トークンを明示的に渡すことも可能（省略時は settings.jquants_refresh_token が使われる）
id_token = jq.get_id_token()
quotes = jq.fetch_daily_quotes(id_token=id_token, code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
```

5) 品質チェックを単独で実行

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

ログレベルと環境は環境変数で制御できます（LOG_LEVEL, KABUSYS_ENV）。

---

## API の運用上の注意点

- J-Quants API は 120 req/min 制限を守るため、モジュール内に固定間隔のレートリミッタを実装しています。
- ネットワークエラーや 429/408/5xx に対して指数バックオフで最大 3 回までリトライします。429 の場合は Retry-After ヘッダを優先。
- 401 を受けた場合はリフレッシュトークンを用いて id_token を再取得し 1 回だけリトライします（無限再帰を防止）。
- データ保存は冪等で、重複は ON CONFLICT 句で更新されます。
- ETL は各ステップでエラーを捕捉し、可能な限り残りのステップを継続します（Fail-Fast ではない）。

---

## ディレクトリ構成

プロジェクトの主要なファイル構成（重要なファイルのみ抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py               — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py     — J-Quants API クライアント（fetch / save）
      - schema.py             — DuckDB スキーマ定義と init_schema/get_connection
      - pipeline.py           — ETL パイプライン（run_daily_etl 等）
      - audit.py              — 監査ログテーブル初期化 / init_audit_db
      - quality.py            — データ品質チェック
      - pipeline.py
    - strategy/
      - __init__.py           — 戦略層（拡張ポイント）
    - execution/
      - __init__.py           — 発注・執行層（拡張ポイント）
    - monitoring/
      - __init__.py           — 監視周り（拡張ポイント）

（上記以外に pyproject.toml / setup.cfg などのビルド関連ファイルが存在する想定）

---

## 開発メモ / 拡張ポイント

- strategy/、execution/、monitoring/ は実装の拡張を想定したプレースホルダです。戦略ロジック、注文実行アダプタ（証券会社 API）、監視アラート送信などをここに実装してください。
- DuckDB スキーマは DataPlatform.md / DataSchema.md に基づく3層（Raw/Processed/Feature）＋ Execution 層を想定しています。既存のDDL／インデックスは典型的なクエリパターンを想定して作成されていますが、用途に応じて調整してください。
- audit モジュールはトレーサビリティを重視しています。order_request_id を冪等キーとして扱い、外部コールバックや再送に耐える設計です。

---

## トラブルシュート

- .env 自動読み込みが期待通りに動作しない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
  - プロジェクトルートが .git または pyproject.toml のどちらかを含んでいるかを確認
- DuckDB 接続で権限やファイルパスのエラーが出る場合:
  - DUCKDB_PATH のディレクトリが存在するか、プロセスに書き込み権限があるか確認
- J-Quants の認可エラー（401）が頻発する場合:
  - リフレッシュトークン（JQUANTS_REFRESH_TOKEN）の有効性を確認

---

## 最後に

この README はコードベースの現状（データ取得・保存・ETL・品質・監査を網羅するライブラリ）に基づいて作成しています。実運用時はセキュリティ（機密情報の管理）、テスト（単体・統合）、CI/CD、監視・アラートの整備を行ってください。

必要であれば、README に実際のセットアップスクリプト例（Docker Compose、systemd ユニット、cron / Airflow のジョブ定義）や、より詳細な設定例を追加します。どの情報を優先して追加しますか？