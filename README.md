# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。J-Quants や RSS を用いたデータ取得、DuckDB ベースのスキーマ定義、ETL パイプライン、データ品質チェック、監査ログ管理などを提供します。

## 特徴（概要）
- J-Quants API からの株価・財務・マーケットカレンダー取得（ページネーション対応・自動トークンリフレッシュ・リトライ・レート制御）
- RSS からのニュース収集と前処理（SSRF対策、XML攻撃対策、トラッキングパラメータ除去、記事ID の冪等化）
- DuckDB を利用した三層データレイヤ（Raw / Processed / Feature）と実行・監査用テーブル群のスキーマ定義・初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）と日次実行エントリポイント
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- マーケットカレンダー管理（営業日判定、前後営業日取得、夜間カレンダー更新ジョブ）
- 監査ログ（シグナル〜発注〜約定までのトレーサビリティ）を備えた監査DB初期化機能

## 主要機能一覧
- 環境変数管理（.env/.env.local の自動ロード、必須変数チェック）
- J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar、save_* を含む）
- RSS ニュース収集（fetch_rss / save_raw_news / extract_stock_codes / run_news_collection）
- DuckDB スキーマ初期化（init_schema / get_connection）
- ETL（run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl）
- カレンダー計算ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
- 監査ログ初期化（init_audit_schema / init_audit_db）
- 品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）

---

## 必要要件（依存ライブラリ）
（プロジェクトの pyproject.toml / requirements に従ってください。主要な依存例）
- Python 3.9+
- duckdb
- defusedxml

開発環境では以下も推奨:
- coverage / pytest など（テスト用）

---

## セットアップ

1. リポジトリをクローンしてパッケージをインストール
   - 開発中であれば編集可能インストール:
     ```
     pip install -e .
     ```
   - または通常インストール:
     ```
     pip install .
     ```

2. 必要な環境変数を設定
   - プロジェクトルートの `.env` または `.env.local` を用意することで自動的に読み込まれます（自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

3. 必要な Python パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   ```

---

## 環境変数（主要）
アプリケーション設定は環境変数から取得します（kabusys.config.settings）。必須項目とデフォルト:

- 必須
  - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（get_id_token に使用）
  - KABU_API_PASSWORD：kabuステーション API のパスワード
  - SLACK_BOT_TOKEN：Slack 通知用ボットトークン
  - SLACK_CHANNEL_ID：Slack チャネル ID

- オプション（デフォルト値あり）
  - KABUSYS_ENV：実行環境 ("development", "paper_trading", "live")。デフォルト "development"。
  - LOG_LEVEL：ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")。デフォルト "INFO"。
  - KABU_API_BASE_URL：kabu API のベース URL。デフォルト "http://localhost:18080/kabusapi"
  - DUCKDB_PATH：DuckDB ファイルパス。デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH：モニタリング用 SQLite パス。デフォルト "data/monitoring.db"

未設定の必須変数を参照すると ValueError が発生します（settings がチェックします）。.env.example を用意しておくと設定が楽です。

---

## 初期化（DuckDB スキーマ作成）

DuckDB にスキーマを作成するには data.schema.init_schema を使います。

例:
```python
from kabusys.data import schema

# ファイル DB を初期化
conn = schema.init_schema("data/kabusys.duckdb")
# :memory: を渡すとインメモリ DB
# conn = schema.init_schema(":memory:")
```

監査ログ用スキーマ（signal_events / order_requests / executions）を別DBに作る場合:
```python
from kabusys.data import audit

conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

既存接続に監査スキーマを追加する場合は:
```python
from kabusys.data import schema, audit

conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=True)
```

---

## 使い方（主要 API と実行例）

- J-Quants トークン取得
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用して取得
```

- 日次 ETL の実行（市場カレンダー取得→株価→財務→品質チェック）
```python
from datetime import date
from kabusys.data import schema, pipeline

conn = schema.get_connection("data/kabusys.duckdb")  # 事前に init_schema を実行しておく
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 単体 ETL（株価差分のみ）
```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
```

- RSS ニュース収集（既知銘柄コードセットを渡して銘柄紐付け）
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn, lookahead_days=90)
print(f"saved={saved}")
```

- 品質チェックの実行
```python
from kabusys.data import quality, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today(), reference_date=date.today())
for issue in issues:
    print(issue)
```

---

## 自動ロードと挙動について（注意点）
- kabusys.config はパッケージの設置位置からプロジェクトルート（.git または pyproject.toml）を探索し、プロジェクトルートの `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API コールは内部でレートリミット（120 req/min）を守るためのスロットリング、リトライ（指数バックオフ）、401 受信時の自動トークンリフレッシュを実装しています。
- news_collector は SSRF や XML Bomb、巨大レスポンスに対する対策を行っています。

---

## ディレクトリ構成
（主要ファイル・モジュールの一覧）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py  — RSS ニュース収集・前処理・DB保存
    - schema.py  — DuckDB スキーマ定義・初期化
    - pipeline.py  — ETL パイプライン（差分取得・日次ETL）
    - calendar_management.py  — マーケットカレンダー管理・ユーティリティ
    - audit.py  — 監査ログ（トレーサビリティ）テーブル初期化
    - quality.py — データ品質チェック
  - strategy/
    - __init__.py  — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py  — 発注/約定/ポジション管理（拡張ポイント）
  - monitoring/
    - __init__.py  — 監視関連（拡張ポイント）

---

## 拡張ポイント / 今後の実装候補
- strategy / execution / monitoring パッケージに戦略ロジック、証券会社APIラッパー、監視アラート処理を実装して接続する想定です。
- Slack 通知や外部ジョブスケジューラ（Airflow / cron）との統合など。

---

## 参考 / 備考
- 各モジュールにはログ出力（Python logging）を散布しており、LOG_LEVEL 環境変数で出力レベルを制御できます。
- データベーススキーマは冪等的に作成されるため、既存 DB に対して何度でも init を実行できます。
- セキュリティ面（SSRF、XML 注入、レスポンスサイズ制限等）を考慮した実装になっていますが、運用時には外部通信先の許可リストやネットワーク制限も併用してください。

---

ご不明点や README に追加したいサンプル（CLI 例や systemd / cron での運用方法など）があれば教えてください。README を用途に合わせて拡張します。