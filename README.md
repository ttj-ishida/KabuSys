# KabuSys

日本株向けの自動売買基盤ライブラリ（プロトタイプ）。  
J-Quants API から市場データを取得して DuckDB に保存する ETL、品質チェック、監査ログなどの基盤処理を提供します。

---

## 概要

KabuSys は以下の目的で設計されています。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する ETL 処理
- データ品質チェック（欠損、スパイク、重複、日付不整合）の実行
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマの提供
- 将来的な戦略実装・発注実装のための基盤モジュール群（strategy / execution / monitoring）

設計上のポイント（主要抜粋）

- API のレートリミット（120 req/min）を尊重するレートリミッタを内蔵
- リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ対応
- データ取得時に取得時刻（UTC）を記録して Look-ahead Bias を防止
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）

---

## 機能一覧

- J-Quants クライアント
  - 株価日足（OHLCV）取得
  - 財務（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - トークン取得 / 自動リフレッシュ
  - レート制御とリトライロジック

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル DDL
  - インデックス定義
  - スキーマの初期化関数（init_schema）

- ETL パイプライン
  - 差分取得（最終取得日からの差分）、バックフィル（デフォルト 3 日）
  - カレンダー先読み（デフォルト 90 日）
  - 品質チェックとの連携（欠損・スパイク・重複・日付不整合）
  - run_daily_etl による一括実行

- データ品質チェック
  - 欠損（OHLC）検出
  - スパイク（前日比）検出
  - 主キー重複検出
  - 将来日付 / 非営業日データ検出

- 監査ログ（audit）
  - signal_events / order_requests / executions のスキーマと初期化
  - 発注の冪等性保持、トレーサビリティ確保

---

## 必要条件

- Python 3.10 以上（typing の新しい構文や union 型を使用）
- 主要依存パッケージ（例）
  - duckdb
- ネットワークアクセス（J-Quants API）

（プロジェクトの requirements.txt がある場合はそちらを利用してください）

---

## 環境変数 / 設定

設定は環境変数またはルートに置いた `.env` / `.env.local` から読み込まれます。自動ロードはデフォルトで有効（プロジェクトルートは `.git` か `pyproject.toml` を基準に探索）。

自動ロードを無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

必須の環境変数（Settings で必須とされるもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

その他（省略時はデフォルト値あり）
- KABUSYS_ENV (development|paper_trading|live) — デフォルト `development`
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト `INFO`
- DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
- SQLITE_PATH — デフォルト `data/monitoring.db`

.env の読み込みルール
- 優先順位: OS 環境変数 > .env.local > .env
- `.env` 内の `export KEY=val` 形式に対応
- クォートやエスケープ、インラインコメントなど基本的な対応あり

例（.env の一部）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージをインストール
   - 例（ある程度の最小セット）:
     ```
     pip install duckdb
     ```
   - プロジェクトに requirements.txt や pyproject.toml があればそちらを使用してください。

3. 環境変数を設定
   - ルートに `.env`（または `.env.local`）を作成し、上記必須値を設定してください。

4. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトから:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - `":memory:"` を渡すとインメモリ DB を使用できます。

5. 監査ログ（audit）テーブルを追加する場合:
   ```python
   from kabusys.data import audit, schema
   conn = schema.init_schema("data/kabusys.duckdb")
   audit.init_audit_schema(conn)
   ```

---

## 使い方（例）

- J-Quants の ID トークン取得：
  ```python
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を使って POST で取得
  ```

- 日次 ETL の実行（デフォルトで当日を対象）：
  ```python
  from kabusys.data import pipeline, schema
  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- 個別ジョブ（株価 ETL）の実行：
  ```python
  from kabusys.data import pipeline, schema
  from datetime import date
  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
  fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
  ```

- 品質チェックのみ実行：
  ```python
  from kabusys.data import quality, schema
  from datetime import date
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  ```

- J-Quants からデータ取得 → DuckDB に保存（低レベル呼び出し）：
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
  jq.save_daily_quotes(conn, records)
  ```

実装上の注意
- jquants_client はレート制御とリトライを行いますが、API 制限や接続状況に注意してください。
- fetch 系関数はページネーションに対応しており、pagination_key を使って全データを取得します。
- save_* 系関数は ON CONFLICT DO UPDATE により冪等になっています。

---

## よく使う API（抜粋）

- kabusys.config.settings
  - 設定や必須環境変数を取得します（例: settings.jquants_refresh_token）。

- kabusys.data.schema
  - init_schema(db_path) — 全テーブルを作成して DuckDB 接続を返す
  - get_connection(db_path) — 既存 DB へ接続

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...) -> ETLResult
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...)

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## ディレクトリ構成

リポジトリ内の主要ファイル/モジュール（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数・設定管理
    - execution/                # 発注・実行関連（拡張ポイント）
      - __init__.py
    - strategy/                 # 戦略実装（拡張ポイント）
      - __init__.py
    - monitoring/               # 監視モジュール（拡張ポイント）
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py       # J-Quants API クライアント（取得・保存）
      - schema.py               # DuckDB スキーマ定義・初期化
      - pipeline.py             # ETL パイプライン（差分取得・バックフィル・品質チェック）
      - audit.py                # 監査ログ（signal/order/execution）スキーマ
      - quality.py              # データ品質チェック

この README は上記ファイル群に基づいて構成されています。

---

## 運用上の注意 / ベストプラクティス

- 本ライブラリだけで発注（実際の資金運用）を行う場合は、十分なテストとバックテスト、監査ログの整備を行ってください。特に live 環境（KABUSYS_ENV=live）での運用は慎重に。
- 秘密情報（トークン・パスワード）は `.env` で管理し、リポジトリには含めないでください。
- DuckDB ファイルは定期的にバックアップを取ることを推奨します（監査ログ等は消さない前提）。
- ETL 実行はスケジューラ（cron / airflow 等）で定期実行する運用が想定されています。

---

## 貢献 / 開発

- strategy / execution / monitoring は拡張ポイントです。戦略やブローカー接続を実装する際は既存の監査設計（order_request_id の冪等性など）を順守してください。
- 自動環境読み込みを無効化したい単体テスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

以上。必要であれば README に含めるサンプル .env.example、requirements.txt、または運用手順（cron/airflow のサンプル）を追加で作成します。どの情報を追加したいか教えてください。