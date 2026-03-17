# KabuSys

日本株自動売買のためのデータプラットフォーム / ETL / 監査ライブラリ群です。  
本リポジトリは J-Quants API からの市場データ取得、RSS ニュース収集、DuckDB ベースのスキーマ初期化・保存、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定トレーサビリティ）などを提供します。

---

## 主要な特徴（概要）

- J-Quants API クライアント
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダー取得
  - レート制限（120 req/min）、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - 取得時刻（fetched_at）の記録、重複排除（冪等保存）
- ETL パイプライン
  - 差分取得（最終取得日からの再取得 / backfill）
  - 市場カレンダー先読み、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL を統合する `run_daily_etl`
- ニュース収集
  - RSS から記事を収集して正規化・前処理し DuckDB に保存
  - SSRF / XML Bomb / Gzip Bomb 対策、トラッキングパラメータ除去、記事 ID は SHA-256（先頭32文字）
  - 記事と銘柄コードの紐付け機能
- カレンダー管理
  - JPX カレンダーによる営業日判定・前後営業日の計算・期間内営業日列挙
  - 夜間バッチ更新ジョブ `calendar_update_job`
- 監査ログ（Audit）
  - シグナル→発注要求→約定までのトレーサビリティテーブル（UUID ベース）
  - 発注の冪等キー（order_request_id）を扱う設計
- DuckDB を用いたスキーマ定義（Raw / Processed / Feature / Execution / Audit）
- データ品質チェックモジュール（複数チェックを集約して返却）

---

## 機能一覧（モジュール別）

- kabusys.config
  - .env 自動読み込み（プロジェクトルートを探索）
  - 環境変数アクセスラッパー（必須キーは未設定時に例外）
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB への冪等保存）
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
  - 全テーブル DDL を定義（インデックス含む）
- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
  - ETL の差分取得・バックフィル・品質チェックの統合
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
  - RSS 取得・XML パース、テキスト前処理、記事保存、銘柄抽出
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(path)
- kabusys.execution / kabusys.strategy / kabusys.monitoring
  - パッケージプレースホルダ（実装拡張用）

---

## セットアップ手順

1. システム要件
   - Python 3.10 以上（型記法 x | y を使用）
   - DuckDB（Python パッケージとして使用）
   - ネットワークアクセス（J-Quants / RSS）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（最低限）
   - pip install duckdb defusedxml

   （実際の requirements.txt がある場合はそちらを利用してください）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` / `.env.local` が自動読み込みされます。
   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>    (必須)
   - KABU_API_PASSWORD=<kabu_station_api_password>        (必須)
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi    (任意・デフォルトあり)
   - SLACK_BOT_TOKEN=<slack_bot_token>                    (必須)
   - SLACK_CHANNEL_ID=<slack_channel_id>                  (必須)
   - DUCKDB_PATH=data/kabusys.duckdb                       (任意・デフォルト)
   - SQLITE_PATH=data/monitoring.db                        (任意・デフォルト)
   - KABUSYS_ENV=development|paper_trading|live             (任意・デフォルト: development)
   - LOG_LEVEL=INFO|DEBUG|...                               (任意・デフォルト: INFO)

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. DuckDB スキーマ初期化
   - 下記の例を参照してデータベースを初期化してください（親ディレクトリは自動作成されます）。

---

## 使い方（サンプル）

以下は Python スクリプトからライブラリを利用する基本例です。

- スキーマ初期化（DuckDB）

```python
from kabusys.data.schema import init_schema

# ファイルパス、または ":memory:" でインメモリ
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

- 日次 ETL 実行（株価/財務/カレンダー取得 + 品質チェック）

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集ジョブ（RSS→raw_news、銘柄紐付け）

```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 既知銘柄コードセット
stats = run_news_collection(conn, known_codes=known_codes)
print(stats)  # {source_name: saved_count, ...}
```

- カレンダー夜間更新ジョブ

```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} calendar records")
```

- 監査スキーマの初期化（監査専用テーブルを既存 DB に追加）

```python
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

- J-Quants の id_token を明示的に取得（デバッグ用）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って refresh
print(token)
```

注意点:
- jquants_client は内部でレートリミット・リトライ・トークンリフレッシュを扱います。大量取得時はレート制限に注意してください。
- save_* 系関数は ON CONFLICT を使って冪等保存を行うため、何度実行しても重複データが残りません。

---

## ディレクトリ構成

このリポジトリの主なツリー（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py         # J-Quants API クライアント（取得＆保存）
      - news_collector.py        # RSS ニュース収集・保存
      - schema.py                # DuckDB スキーマ定義・初期化
      - pipeline.py              # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py   # マーケットカレンダー管理・ジョブ
      - audit.py                 # 監査ログ（signal/order/execution）の初期化
      - quality.py               # データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（実装の拡張ポイント）
- strategy/：戦略アルゴリズムや特徴量生成ロジックを配置
- execution/：発注ロジック・ブローカー連携を配置
- monitoring/：状態監視・アラート連携を配置

---

## 運用上の注意点 / ベストプラクティス

- 環境変数の管理は .env / .env.local を利用し、シークレットは Git 管理しないでください。
- DB（DuckDB）ファイルは定期的にバックアップしてください。監査ログは削除前提ではありません。
- J-Quants のレート制限を順守してください。大量取得・バッチ化を行う場合は適切にスケジューリングすること。
- RSS フィードソースは信頼できるものを選び、プライベートアドレスへの SSRF を阻止するロジックが実装されていますが、それでも外部ソースには慎重に対応してください。
- 本ライブラリはトランザクション管理・エラーハンドリングを行いますが、外部でジョブ監視（失敗時の再実行・アラート）を用意することを推奨します。

---

## 参考・拡張案

- Slack 通知や監視ダッシュボードと組み合わせて ETL/品質チェック結果を通知する
- DuckDB から Parquet 等へのエクスポートを行い分析基盤に連携する
- execution モジュールにブローカー API 実装を追加して自動発注ワークフローを完成させる

---

## ライセンス / 貢献

本 README ではソースコードの動作説明を中心に記載しています。実際のライセンス情報・貢献ガイドラインはリポジトリルートの LICENSE / CONTRIBUTING を参照してください。

---

必要であれば、README にサンプル .env.example、より詳細な API リファレンス（各関数の引数/戻り値の表）やデプロイ例（systemd / cron / Airflow）を追加できます。どの情報を優先して追加しますか？