# KabuSys

日本株向け自動売買・データ基盤ライブラリ（部分実装）

このリポジトリは、J-Quants 等から市場データ・財務データ・ニュースを取得して DuckDB に保存し、ETL パイプライン・品質チェック・監査ログを提供するためのライブラリ群を含みます。売買戦略（strategy）や実行（execution）、監視（monitoring）用の受け皿モジュールも用意されています。

---

## プロジェクト概要

KabuSys は以下を目的とした内部用ライブラリです。

- J-Quants API からの株価（日次 OHLCV）・財務（四半期 BS/PL）・マーケットカレンダー取得
- RSS からのニュース収集と記事→銘柄の紐付け
- DuckDB ベースのデータスキーマ定義と初期化
- 日次 ETL パイプライン（差分更新、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev 等）
- 監査ログ用スキーマ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）

設計上の留意点（抜粋）：
- J-Quants API 呼び出しはレート制限（120 req/min）を守るためスロットリングを実装。
- リトライ、指数バックオフ、401 トークン自動リフレッシュなどの堅牢化。
- DuckDB への保存は冪等（ON CONFLICT）になるよう実装。
- RSS 収集は SSRF 対策・XML 攻撃対策・レスポンスサイズ制限等を実施。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート基準）、必須変数チェック
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB 保存）
  - レートリミット、リトライ、トークンリフレッシュ対応
- RSS ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、テキスト前処理、記事ID生成（URL 正規化＋SHA-256）
  - SSRF 対策、gzip 上限、defusedxml によるパース保護
  - raw_news / news_symbols への冪等保存
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema(db_path) による初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得ロジック、バックフィル、品質チェック統合（run_daily_etl）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・next/prev_trading_day・calendar_update_job
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL と初期化
- 品質チェック（kabusys.data.quality）
  - 欠損データ、重複、スパイク（前日比）・日付不整合の検出

注意：strategy、execution、monitoring パッケージはプレースホルダ（空の __init__）です。

---

## 動作要件

- Python 3.10 以上（型注釈で | 型を使用しているため）
- 必要なライブラリ（一例）
  - duckdb
  - defusedxml

インストール例（仮）:
```bash
python -m pip install "duckdb" "defusedxml"
# プロジェクトをパッケージ化している場合:
# pip install -e .
```

（実プロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## 環境変数（主要）

以下の環境変数を設定してください（README で触れている主要なもの）:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（本システムで使用する場合）
- SLACK_CHANNEL_ID: Slack チャネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

自動 .env の挙動:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env、.env.local を自動読み込みします。
- OS 環境変数が優先され、.env.local は .env を上書きします。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途等）。

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化
   ```bash
   git clone <this-repo>
   cd <this-repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # （必要に応じて他の依存もインストール）
   ```

3. .env を作成（.env.example がある場合は参照）
   例:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. DuckDB スキーマを初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)  # ファイルを作成して全テーブルを作る
   conn.close()
   ```

5. 監査ログ専用 DB 初期化（任意）
   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   audit_conn.close()
   ```

---

## 使い方（主要な API と実行例）

以下に代表的な使い方のサンプルを示します。

1) 日次 ETL を実行する（市場カレンダー→株価→財務→品質チェック）
```python
from datetime import date
from kabusys.data import pipeline, schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- run_daily_etl は ETLResult を返します。内部で J-Quants への API 呼び出し（fetch_*）や DuckDB への保存（save_*）を行います。
- id_token を外部から注入してテストしやすくできます（pipeline.run_daily_etl(..., id_token=...)）。

2) ニュース収集ジョブを実行する
```python
from kabusys.data import news_collector, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)  # または init_schema で既に初期化済みの接続を使う
# known_codes は銘柄コードの集合（例: {"7203", "6758", ...}）
res = news_collector.run_news_collection(conn, known_codes={"7203", "6758"})
print(res)  # {source_name: inserted_count, ...}
conn.close()
```

3) カレンダー更新ジョブ（夜間バッチ等）
```python
from kabusys.data import calendar_management, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
conn.close()
```

4) 品質チェック単体で実行
```python
from kabusys.data import quality, schema
from datetime import date
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
conn.close()
```

5) J-Quants の低レベル API を直接使う（テストやカスタム取得）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
from kabusys.data import schema

conn = schema.get_connection(settings.duckdb_path)
records = jq.fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
jq.save_daily_quotes(conn, records)
conn.close()
```

---

## 注意点 / 設計に関する補足

- J-Quants API 呼び出しは内部で固定間隔スロットリングを用いて 120 req/min を尊重します。
- ネットワークや HTTP 5xx 等に対して指数バックオフで最大 3 回リトライします（特定のステータスでは Retry-After ヘッダを考慮）。
- 401 Unauthorized を受け取った場合は、リフレッシュトークンから ID トークンを再取得して 1 回だけリトライします。
- DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）とし、重複挿入や再実行で副作用が最小になるよう設計されています。
- RSS ニュース収集は URL 正規化・追跡パラメータ除去・SHA-256 ハッシュで ID を作成し冪等性を確保します。SSRF 対策や受信サイズ上限により安全性を高めています。
- market_calendar が未取得の環境では曜日ベース（平日=営業日）でフォールバックします。

---

## ディレクトリ構成

以下は主要ファイルの一覧（概要）。実際のパスは `src/kabusys/...`。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（取得＋DuckDB保存）
    - news_collector.py        # RSS 収集・保存・銘柄抽出
    - schema.py                # DuckDB のスキーマ定義と init_schema()
    - pipeline.py              # ETL パイプライン（run_daily_etl など）
    - calendar_management.py   # マーケットカレンダー管理（営業日判定、更新ジョブ）
    - audit.py                 # 監査ログスキーマ（signal/order/execution）
    - quality.py               # データ品質チェック
  - strategy/
    - __init__.py              # 戦略関連（プレースホルダ）
  - execution/
    - __init__.py              # 発注/接続関連（プレースホルダ）
  - monitoring/
    - __init__.py              # 監視関連（プレースホルダ）

---

## 開発・テストのヒント

- テスト時に .env の自動ロードを止めたい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- jquants_client の _urlopen 等は内部的に差し替え可能な設計（テストでモックすることで外部 API に依存しないテストが可能）。
- DuckDB の ":memory:" を渡すことでインメモリ DB を使って高速にユニットテストを実行できます。

---

## ライセンス・貢献

（ここにライセンス情報や貢献方法を記載してください。プロジェクト用テンプレートに従って補足してください。）

---

README は以上です。必要であれば、環境変数の .env.example やコミット用の設定、CI 実行例、さらに具体的なスクリプト（cron / systemd timer）での運用方法などを追加できます。どの情報を優先して追記しますか？