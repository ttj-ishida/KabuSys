# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）  
このリポジトリは、データ取得・ETL・品質チェック・ニュース収集・市場カレンダー管理・監査ログなど、自動売買システム構築に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含む Python パッケージです。

- J-Quants API からの市場データ（株価、財務、マーケットカレンダー）取得
- DuckDB を用いたデータスキーマ定義と永続化
- ETL（差分更新／バックフィル）パイプラインと品質チェック
- RSS ベースのニュース収集と銘柄抽出
- マーケットカレンダー管理（営業日判定、前後営業日検索）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 将来的な戦略/実行/監視モジュールのプレースホルダ

設計上のポイント:
- J-Quants API のレート制限（120 req/min）やリトライ・トークン自動更新に対応
- DuckDB に対して冪等性のある保存（ON CONFLICT）を行う
- ニュース収集はセキュリティ（SSRF 対策、XML 攻撃対策、サイズ制限）に配慮

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンから idToken を取得）
  - DuckDB へ保存する save_* 関数（raw_prices / raw_financials / market_calendar）
  - レートリミッタ、リトライ（指数バックオフ）、401 の自動リフレッシュ対応
- data.schema
  - DuckDB の全テーブル定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) / get_connection(db_path)
- data.pipeline
  - 差分ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 統合日次ETL（run_daily_etl）と品質チェックの実行
- data.news_collector
  - RSS フィード取得（fetch_rss）、前処理、記事保存（save_raw_news）、銘柄紐付け（save_news_symbols）
  - SSRF・XML脆弱性対策、トラッキングパラメータ除去、ID の冪等生成
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間カレンダー差分更新）
- data.quality
  - 欠損・スパイク・重複・日付不整合のチェック（run_all_checks）
- data.audit
  - 監査用テーブル初期化（init_audit_schema / init_audit_db）

---

## 必要条件（推奨）

- Python 3.10+
- 主要依存ライブラリ（一部）
  - duckdb
  - defusedxml

（プロジェクトの requirements.txt があればそちらを使用してください）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# その他、プロジェクト固有の依存があれば追加でインストール
```

---

## 環境変数（設定）

config.Settings クラスで使用する環境変数:

必須:
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD
  - kabuステーション API のパスワード（実行モジュールで使用）
- SLACK_BOT_TOKEN
  - Slack 通知用の Bot トークン
- SLACK_CHANNEL_ID
  - 通知先の Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) (default: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (default: INFO)

自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml）を検出して `.env` / `.env.local` を自動読み込みします。
- 自動読み込みを無効にするには環境変数を設定:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. 仮想環境作成＆依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   # プロジェクトの requirements.txt があれば: pip install -r requirements.txt
   ```

2. 環境変数設定
   - プロジェクトルートに `.env` を作成するか、環境変数で設定します（上記参照）。

3. DuckDB スキーマ初期化
   - スクリプトから呼ぶ例:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ用テーブルを追加する場合:
     ```python
     from kabusys.data import audit
     audit.init_audit_schema(conn)  # conn は init_schema の返り値
     # または専用DBで init_audit_db("data/kabusys_audit.duckdb")
     ```

4. （任意）テーブルが正しく作成されたことを確認:
   - DuckDB CLI や Python から SELECT で確認できます。

---

## 使い方（主な API と簡単な例）

以下は最小限の利用例です。実運用ではログ設定・例外処理・ジョブスケジューラ（cron / Airflow 等）を組み合わせてください。

1. 日次 ETL を実行する（市場カレンダー取得→株価→財務→品質チェック）:
```python
from datetime import date
import logging
from kabusys.data import schema, pipeline

logging.basicConfig(level=logging.INFO)
conn = schema.init_schema("data/kabusys.duckdb")

# 今日分の ETL を実行（settings から id_token を取得するため、環境変数は必須）
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2. ニュース収集ジョブを実行する:
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# デフォルト RSS ソースを使う場合は sources=None
# known_codes: 銘柄コード抽出に使う有効コード集合（例: {'7203','6758',...}）
res = news_collector.run_news_collection(conn, known_codes={'7203','6758'})
print(res)  # {source_name: 新規保存件数}
```

3. カレンダー夜間更新ジョブ:
```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved={saved}")
```

4. J-Quants の id_token を明示的に取得:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
print(token)
```

5. 監査ログ初期化（別DBに作る場合）:
```python
from kabusys.data import audit
conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## スケジューリング / 運用のヒント

- 日次 ETL は営業日判定（market_calendar）に依存します。calendar_update_job を先に実行しておくとより正確です。
- J-Quants API のレート制限（120 req/min）に注意してください。jquants_client は内部でスロットリングとリトライを行います。
- 環境を切り替えるには KABUSYS_ENV を使用（development / paper_trading / live）。 live では実際の発注処理を有効にするなどの振る舞い分岐を想定しています。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、自前で環境設定を行うとよいです。

---

## ディレクトリ構成

リポジトリ内のおおまかな構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定の読み込み
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント & 保存
      - news_collector.py      # RSS 収集・前処理・DB保存
      - schema.py              # DuckDB スキーマ定義・初期化
      - pipeline.py            # ETL パイプライン（差分更新 / 日次ETL）
      - calendar_management.py # マーケットカレンダー管理
      - quality.py             # データ品質チェック
      - audit.py               # 監査ログ（シグナル/発注/約定）
    - strategy/
      - __init__.py            # 戦略関連モジュールのプレースホルダ
    - execution/
      - __init__.py            # 発注・ブローカー連携のプレースホルダ
    - monitoring/
      - __init__.py            # 監視 / メトリクスのプレースホルダ

---

## 注意事項 / 補足

- この README はコードベースの概要と利用方法を説明するためのもので、実際の取引を行う前に十分な検証が必要です。
- セキュリティ関連（APIトークン・パスワード）は環境変数や安全なシークレットストレージで管理してください。
- DuckDB のファイルパスに対するアクセス権やバックアップ戦略は運用要件に応じて設計してください。
- strategy / execution / monitoring は実装の拡張が想定されているため、プロダクション化する際は追加実装・テストが必要です。

---

質問や追加で README に含めたい内容（例: 実行スクリプト例、CI 設定、テストの実行方法など）があれば教えてください。必要に応じて追記します。