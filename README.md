# KabuSys

日本株向けの自動売買 / データプラットフォーム基盤ライブラリです。
J-Quants や RSS などから市場データ・ニュースを取得し、DuckDB に蓄積・品質チェック・監査ログ管理を行うためのモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された Python モジュール群です。

- J-Quants API を用いた株価（日足）・財務データ・JPX カレンダー取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- RSS からのニュース収集と銘柄紐付け（SSRF 対策、トラッキングパラメータ除去、受信サイズ制限）
- DuckDB によるスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev 等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上のポイント:
- 冪等性を意識した保存（ON CONFLICT 等）
- Look-ahead Bias を避けるため fetched_at を UTC で記録
- 外部接続に対するセキュリティ対策（URL スキーム検証、プライベートアドレス検出、XML の安全パース）
- テストしやすい設計（ID トークン注入、ネットワーク呼び出しの差し替え可能箇所）

---

## 主な機能一覧

- data/jquants_client.py
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ保存する save_* 関数（冪等化）
  - レートリミッター、リトライ、401 自動リフレッシュ

- data/news_collector.py
  - RSS フィード取得（gzip 対応）、記事正規化、ID 生成、DuckDB へ保存
  - SSRF 対策、応答サイズ上限、トラッキングパラメータ除去
  - 銘柄コード抽出・news_symbols への保存

- data/schema.py
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）
  - init_schema / get_connection

- data/pipeline.py
  - 差分 ETL（市場カレンダー、株価、財務）と品質チェック（run_daily_etl）
  - run_prices_etl / run_financials_etl / run_calendar_etl

- data/calendar_management.py
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間カレンダー更新）

- data/audit.py
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）

- data/quality.py
  - 欠損・スパイク・重複・日付不整合検査と QualityIssue 表現
  - run_all_checks

- config.py
  - .env 自動読込（プロジェクトルート探索）、Settings クラス（環境変数アクセス）
  - 自動 env ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 要求環境 / 依存

- Python 3.10 以上（`|` 型アノテーションなどを使用）
- 必要ライブラリ（一例）
  - duckdb
  - defusedxml
- その他標準ライブラリ（urllib / datetime / logging 等）

インストール例（最小）:
```bash
python -m pip install "duckdb" "defusedxml"
# プロジェクトを editable install する場合（パッケージ化されていれば）
# python -m pip install -e .
```

※ 実行環境に合わせて追加の依存がある場合があります（ログ・Slack 通知等）。

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置。

2. Python 仮想環境を作成して有効化（推奨）。
```bash
python -m venv .venv
source .venv/bin/activate    # Unix/macOS
.venv\Scripts\activate       # Windows
```

3. 必要パッケージをインストール。
```bash
pip install duckdb defusedxml
```

4. 環境変数を設定（.env をプロジェクトルートに作成するのが簡単です）。
必須の環境変数（Settings 参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知に使用（必須）
- SLACK_CHANNEL_ID — Slack チャンネル（必須）

任意／デフォルトあり:
- KABU_API_BASE_URL — デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
- SQLITE_PATH — デフォルト "data/monitoring.db"
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト development）
- LOG_LEVEL — "DEBUG" | "INFO" | ...（デフォルト INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. 自動 env ロードを無効にしたい場合:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（基本例）

以下は Python スクリプト / REPL から主要機能を使う例です。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# またはメモリ DB
# conn = schema.init_schema(":memory:")
```

- 監査ログ専用 DB 初期化
```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

- 日次 ETL 実行（市場カレンダー、株価、財務、品質チェック）
```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 市場カレンダーの夜間更新ジョブ
```python
from kabusys.data import calendar_management
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved calendar rows:", saved)
```

- RSS ニュース収集（既知銘柄セットを渡すと自動で紐付け）
```python
from kabusys.data import news_collector
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- J-Quants から株価を直接取得して保存
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
import duckdb
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

注意点:
- jquants_client は API レート制限（120 req/min）に従うため連続大量リクエストは避けてください。
- get_id_token は内部で settings.jquants_refresh_token を参照します（Settings は環境変数を使用）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1（.env 自動読込を無効化）

---

## ディレクトリ構成

以下はリポジトリ内の主要ファイル・モジュールの構成です（抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

モジュール説明:
- kabusys.config: 環境変数と .env のロード / Settings
- kabusys.data: データ取得・ETL・スキーマ・品質・監査・ニュース収集を含む主要ロジック群
- kabusys.strategy: 戦略ロジック（未実装のため拡張ポイント）
- kabusys.execution: 発注・ブローカー連携（拡張ポイント）
- kabusys.monitoring: 監視関連（拡張ポイント）

---

## 開発上の注意 / セキュリティ

- .env に機密情報（トークン / パスワード）を保存する場合は Git 管理に含めないでください（.gitignore に追加）。
- news_collector は外部 URL を扱うため、SSRF 対策・受信サイズ制限・DefusedXML による安全パースを実装しています。これらの挙動を変更する場合はリスクを理解してください。
- J-Quants API のレート制限を遵守してください。ライブラリは固定間隔スロットリングとリトライを備えていますが、設計どおりの利用をお願いします。
- DuckDB ファイルのバックアップやローテーション、ディスク容量管理を運用面で設計してください。

---

## 拡張 / TODO（利用者向けガイド）

- strategy と execution パッケージは拡張箇所です。戦略ロジックの実装、リスク管理、注文送信フローを組み込んでください。
- Slack 通知や監視ダッシュボードと連携するための小さなラッパーを追加すると運用が楽になります。
- CI テストやモックを用いた単体テスト（ネットワーク呼び出しの差し替え）を整備することを推奨します。

---

もし README に追加したい具体的なサンプル（例えば cron / systemd でのジョブ実行例や Dockerfile、pyproject/requirements のテンプレート）があれば、用途に合わせた例を追記します。