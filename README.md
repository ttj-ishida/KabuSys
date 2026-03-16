# KabuSys

日本株向け自動売買基盤（ライブラリ）。  
データ収集（J-Quants）、ETL、データ品質チェック、DuckDBスキーマ、監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムの基盤モジュール群です。主に以下を目的としています。

- J-Quants API から株価・財務・市場カレンダーを取得
- DuckDB に対する冪等的なスキーマ定義とデータ保存
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質検査（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計上のポイント:
- API レート制限（120 req/min）やリトライ・トークン自動リフレッシュに対応
- DuckDB への挿入は ON CONFLICT DO UPDATE により冪等化
- 品質チェックは Fail-Fast ではなく全件収集し、呼び出し元が対応を決定可能

---

## 主な機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ保存する save_* 関数（raw_prices, raw_financials, market_calendar）
  - レートリミット、リトライ、トークンキャッシュ対応
- data.schema
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - init_schema / get_connection
- data.pipeline
  - 日次 ETL（run_daily_etl）および個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 差分更新ロジック、バックフィル、品質チェック連携
- data.quality
  - check_missing_data, check_duplicates, check_spike, check_date_consistency, run_all_checks
  - 問題は QualityIssue オブジェクトで返却（severity = error / warning）
- data.audit
  - 監査ログテーブル（signal_events, order_requests, executions）と初期化関数
- config
  - 環境変数管理、.env 自動ロード（.env.local / .env）、必須設定の検証（Settings クラス）

---

## 前提（依存関係）

- Python 3.10 以上（typing の `|` を使用）
- duckdb
- 標準ライブラリ（urllib 等）

インストール例（プロジェクトに pyproject / setup がある前提）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb
pip install -e .    # 開発インストール（pyproject / setup が存在する場合）
```

もしパッケージとして未公開の場合は、requirements に duckdb を含めて下さい。

---

## 環境変数と .env の自動ロード

パッケージは起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、以下の順で .env を読み込みます（OS 環境変数が最優先）:

1. OS 環境変数
2. .env.local（存在すれば上書き）
3. .env

自動ロードを無効化するには環境変数を設定します:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主な環境変数（Settings で参照されるもの）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (省略可, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (省略可, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. 仮想環境の作成と依存ライブラリのインストール
   - Python 3.10+ を用意
   - pip で duckdb 等をインストール

2. 環境変数を設定（.env / .env.local）
   - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須

3. DuckDB スキーマ初期化
   - デフォルトのパスは data/kabusys.duckdb。親ディレクトリが無ければ自動作成されます。
   - Python から初期化:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)  # Path を渡すことができる
     ```
   - 監査ログ（audit）を追加する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```

4. （任意）監視用 SQLite の準備
   - settings.sqlite_path を使用

---

## 使い方（簡易ガイド）

- J-Quants トークンの取得:
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- 株価・財務データの取得（直接呼び出し）:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  records = fetch_daily_quotes(code="7203", date_from=..., date_to=...)
  ```

- 日次 ETL を実行（推奨）:
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # 省略時は today が対象日
  print(result.to_dict())
  ```

- 個別 ETL（例: 株価のみ）:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  # conn は init_schema で取得済みとする
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- 品質チェックのみ実行:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  ```

- 監査 DB 初期化（専用 DB として）:
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

注意点:
- J-Quants API は 120 req/min の制限があり、jquants_client は固定間隔スロットリングとリトライを行います。
- get_id_token はリフレッシュトークンから ID トークンを取得し、401 を検出した場合は自動で再取得を試みます（1 回のみ）。

---

## 主要 API の説明（抜粋）

- data.schema.init_schema(db_path) -> duckdb.Connection
  - スキーマ（全テーブル／インデックス）を作成して接続を返す。冪等。

- data.schema.get_connection(db_path) -> duckdb.Connection
  - 既存 DB への接続（スキーマ初期化は行わない）。

- data.jquants_client.fetch_daily_quotes(...)
  - 日足データ取得（ページネーション対応）

- data.jquants_client.save_daily_quotes(conn, records) -> int
  - raw_prices に ON CONFLICT DO UPDATE で保存。挿入・更新したレコード数を返す。

- data.pipeline.run_daily_etl(conn, target_date=None, ...)
  - 市場カレンダー→株価→財務→品質チェックの順で日次 ETL を実行し ETLResult を返す。

- data.quality.run_all_checks(conn, target_date=None, reference_date=None)
  - 品質チェックをまとめて実行し QualityIssue のリストを返す。

---

## ディレクトリ構成

プロジェクトは src パッケージ構成です（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定読み込み
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント、保存ロジック
      - schema.py              # DuckDB スキーマ定義と初期化
      - pipeline.py            # ETL パイプライン（差分・バックフィル・品質チェック）
      - audit.py               # 監査ログテーブルと初期化
      - quality.py             # データ品質チェック
    - strategy/
      - __init__.py            # 戦略関連（拡張ポイント）
    - execution/
      - __init__.py            # 発注 / ブローカー実装の拡張ポイント
    - monitoring/
      - __init__.py            # 監視・アラート連携（将来的に拡張）

各モジュールはテストしやすいように id_token の注入や接続オブジェクトを引数で受け取る設計になっています。

---

## 開発・運用上の注意点

- 環境変数の取り扱いに注意してください（機密情報は .env に平文で置くのではなく、Secrets 管理を検討）。
- DuckDB ファイルはローカルファイルなのでバックアップ戦略や排他制御（複数プロセスからの同時書き込み）を考慮してください。
- run_daily_etl は各ステップで例外をハンドリングし続行するため、戻り値の ETLResult.errors / quality_issues を必ず確認して下さい。
- KABUSYS_ENV によって実稼働（live）/ ペーパー（paper_trading）/ 開発（development）の区別が可能です。is_live / is_paper / is_dev のプロパティで判定できます。

---

## 追加情報

- ロギングレベルは LOG_LEVEL 環境変数で調整可能（標準的な Python ログレベルを使用）。
- .env のパースはシェル風の export やクォート、インラインコメントに対応しています。プロジェクトルートが特定できない場合は自動ロードをスキップします。

---

必要があれば、README に以下を追記できます:
- 具体的な .env.example ファイル
- CI / GitHub Actions の設定例（ETL の定期実行）
- ブローカー連携（kabu API）や Slack 通知の使用例

必要な追加事項があれば教えてください。