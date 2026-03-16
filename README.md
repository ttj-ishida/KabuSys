# KabuSys

日本株向けの自動売買プラットフォーム（KabuSys）の軽量実装。  
データ取得（J-Quants）、ETLパイプライン、DuckDBスキーマ、データ品質チェック、監査ログ基盤を提供します。戦略・実行・監視のための基礎ライブラリ群を含み、実運用・ペーパー取引・開発用途に対応する設計になっています。

主な設計方針
- Look-ahead Bias を防ぐフェッチ時刻（fetched_at）記録
- API レート制限（J-Quants: 120 req/min）に基づくスロットリング
- リトライ（指数バックオフ）・401 時のトークン自動リフレッシュ対応
- データ保存は冪等（ON CONFLICT DO UPDATE）
- ETL は差分更新＋バックフィル＋品質チェックで堅牢に

---

## 機能一覧
- J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - レートリミット管理、リトライ、トークン自動リフレッシュ
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 監査ログ（signal_events / order_requests / executions）テーブルの初期化
- ETL パイプライン（差分取得、バックフィル、保存、品質チェック）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 環境変数/.env の自動読み込みと設定管理（settings オブジェクト）

---

## 要件
- Python 3.10 以上（Union 型の `X | None` を使用）
- 必要パッケージ例
  - duckdb
- （プロジェクトに合わせて追加パッケージを導入してください）

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. 仮想環境を作成して有効化
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 依存パッケージをインストール（例）
   - pip install duckdb

   プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください。

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動的にロードされます（デフォルト）。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（README 用の例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabuステーションのベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（モニタリングDB）パス（省略時: data/monitoring.db）
   - KABUSYS_ENV: 実行環境（development / paper_trading / live、省略時: development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、省略時: INFO）

   例 .env（最小）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=zzzz
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方

以下は代表的な使用例。プロジェクトからインポートして使います。

1) DuckDB スキーマの初期化
```python
from pathlib import Path
from kabusys.data import schema

db_path = Path("data/kabusys.duckdb")
conn = schema.init_schema(db_path)  # テーブルを作成して接続を返す
```

2) 監査ログ用テーブルの初期化（既存接続に追加）
```python
from kabusys.data import audit

# schema.init_schema() で得た conn を渡す
audit.init_audit_schema(conn)
```

3) J-Quants の ID トークン取得（内部で refresh token を settings から参照）
```python
from kabusys.data import jquants_client as jq

id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
```

4) ETL の実行（デイリーETL）
```python
from datetime import date
from kabusys.data import pipeline, schema

# 事前に init_schema() で conn を取得しておく
conn = schema.get_connection("data/kabusys.duckdb")

# 当日分の ETL を実行（デフォルトで品質チェックを実行）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

5) 個別の ETL ジョブを呼ぶ
- 株価差分取得:
  pipeline.run_prices_etl(conn, target_date=date.today())
- 財務データ差分取得:
  pipeline.run_financials_etl(conn, target_date=date.today())
- カレンダー取得:
  pipeline.run_calendar_etl(conn, target_date=date.today())

6) 品質チェックの実行
```python
from kabusys.data import quality

issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

ログ出力やモニタリングへの通知（Slack等）は別モジュールで統合できます（SLACK_* 環境変数を参照）。

注意点
- run_daily_etl() は内部で市場カレンダーを先に取得し、対象日を営業日に調整してから株価/財務の差分取得を実行します。
- ETL は差分更新＋バックフィル（デフォルト 3 日）を行い、J-Quants の後出し修正を吸収できる設計です。
- J-Quants への HTTP リクエストではレートリミットやリトライ、401 のトークン自動更新を行います。

---

## ディレクトリ構成

主なファイル/モジュール構成（ソースは src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数 / .env 管理）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch_*, save_*）
      - レートリミット / retry / token refresh
    - schema.py
      - DuckDB の DDL 定義、init_schema(), get_connection()
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）の定義と初期化
  - strategy/
    - __init__.py
    - （戦略ロジックはここに実装）
  - execution/
    - __init__.py
    - （発注・ブローカー連携ロジックはここに実装）
  - monitoring/
    - __init__.py
    - （モニタリング / アラート機能はここに実装）

---

## 開発メモ / 設計上の注意
- DuckDB の初期化は idempotent（既存テーブルがあればスキップ）です。
- audit.init_audit_schema() は UTC タイムゾーンの設定 (SET TimeZone='UTC') を行います。
- jquants_client の ID トークンはモジュールレベルでキャッシュされ、ページネーション呼び出し間で共有されます。必要に応じて force_refresh を使えます。
- .env のパースはシェル風の export 形式、クォート、コメントなどに対応しています。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかのみ有効です。

---

## よくある操作例
- データベースを初期化して ETL を1回だけ実行する（スクリプト例）
```python
# scripts/run_etl.py
from pathlib import Path
from kabusys.data import schema, pipeline

db = Path("data/kabusys.duckdb")
conn = schema.init_schema(db)
res = pipeline.run_daily_etl(conn)
print(res.to_dict())
```

- テスト用にインメモリ DB を使う
```python
from kabusys.data import schema
conn = schema.init_schema(":memory:")
```

---

これで README の概要は以上です。必要に応じて以下の情報を追加できます：
- 具体的な依存パッケージ一覧（requirements.txt）
- CI / デプロイ手順
- サンプル .env.example ファイル
- 戦略実装テンプレートや execution ブリッジの実装例

追加したい項目や、README の英語版が必要であれば教えてください。