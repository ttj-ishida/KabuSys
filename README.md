# KabuSys

日本株向けの自動売買／データ基盤ライブラリ KabuSys の README（日本語）。

概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を記載します。

---

## プロジェクト概要

KabuSys は、日本株のデータ収集・ETL・品質管理・監査ログ・発注フロー基盤を提供する Python モジュール群です。  
主な用途は以下の通りです。

- J-Quants API からの市場データ（株価・財務・マーケットカレンダー）取得・保存
- RSS フィードからのニュース収集と記事→銘柄の紐付け
- DuckDB を利用したスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- マーケットカレンダー管理・営業日判定ロジック
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）向けスキーマ

設計上のポイント：
- API レート制限（J-Quants: 120 req/min）やリトライ、トークン自動更新を組み込み
- データ保存は冪等（ON CONFLICT を用いた INSERT/UPDATE）
- RSS 収集では SSRF / XML 攻撃 / 大容量レスポンス対策を実装
- DuckDB を永続 DB として利用し高速な SQL ベース処理を想定

---

## 機能一覧

主な機能モジュールと役割
- kabusys.config
  - .env / 環境変数の読み込み、アプリ設定（トークン・DBパス・環境フラグなど）
  - 自動ロード: プロジェクトルート（.git または pyproject.toml）から .env / .env.local を読み込み（無効化可）
- kabusys.data.jquants_client
  - J-Quants API クライアント（認証、日足・財務・カレンダー取得、DuckDB への保存）
  - レートリミット管理、リトライ、401 自動リフレッシュ、fetched_at 記録
- kabusys.data.news_collector
  - RSS フィード取得、記事正規化、記事ID生成（URL正規化 + SHA256先頭32文字）、DuckDB 保存、銘柄抽出
  - SSRF / XML ハードニング、レスポンスサイズ制限、チャンク挿入
- kabusys.data.schema
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit 層）と初期化関数
- kabusys.data.pipeline
  - 日次 ETL（差分取得、保存、バックフィル、品質チェック）を実装
- kabusys.data.calendar_management
  - market_calendar 管理、営業日判定、next/prev_trading_day、バッチ更新ジョブ
- kabusys.data.audit
  - 監査ログ（signal_events / order_requests / executions）スキーマの初期化
- kabusys.data.quality
  - データ品質チェック（欠損、重複、スパイク、日付不整合）の実行と報告

補助モジュール:
- strategy, execution, monitoring パッケージ（空の __init__ があり拡張を想定）

---

## 前提 / 依存関係

- Python 3.10 以上（型注釈に `|` を使用）
- 外部ライブラリ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging 等

インストール例（仮、requirements.txt がある場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# または requirements.txt があれば:
# pip install -r requirements.txt
```

---

## 環境変数 / .env

config.py が自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（優先度: OS 環境 > .env.local > .env）。テストなどで自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須は明記）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token の元になる値。
- KABU_API_PASSWORD (必須)
  - kabuステーションAPI 用パスワード
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須)
  - Slack チャンネル ID
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - DuckDB ファイルパス（:memory: も可）
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, デフォルト: development)
  - 有効値: development, paper_trading, live
- LOG_LEVEL (任意, デフォルト: INFO)
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

サンプル .env (README 用例):
```env
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

セキュリティ: トークンやパスワードはリポジトリにコミットしないでください。

---

## セットアップ手順

1. リポジトリを取得し、仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   ```

2. 環境変数を設定（`.env` をプロジェクトルートに作成）
   - 上記のサンプルを参考に `.env` を作成

3. DuckDB スキーマの初期化
   - Python からスキーマを作成します（例: デフォルトパスを使用）
   ```python
   >>> from kabusys.data.schema import init_schema
   >>> conn = init_schema("data/kabusys.duckdb")
   >>> conn.execute("SELECT name FROM sqlite_master LIMIT 1")  # DuckDB の確認（例）
   ```
   - 監査ログのスキーマを追加する場合:
   ```python
   >>> from kabusys.data.audit import init_audit_schema
   >>> init_audit_schema(conn, transactional=True)
   ```

4. （任意）監査用専用 DB を別で作る場合:
   ```python
   >>> from kabusys.data.audit import init_audit_db
   >>> audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主要な API 使用例）

以下は代表的な利用例です。必要に応じてスクリプトやジョブランナー（cron, systemd, Airflow 等）から呼び出してください。

- J-Quants 日足・財務・カレンダー取得（単発）
```python
from kabusys.data import jquants_client as jq
# id_token を省略すると内部キャッシュ / 自動リフレッシュを使う
prices = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
financials = jq.fetch_financial_statements(date_from=date(2023,1,1), date_to=date(2023,12,31))
calendar = jq.fetch_market_calendar()
```

- 日次 ETL（run_daily_etl）を実行して DuckDB に保存・品質チェック
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- RSS ニュース収集ジョブ（run_news_collection）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes を渡すと記事→銘柄紐付けを行う
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: new_count, ...}
```

- 市場カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved", saved)
```

- データ品質チェック単体実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

---

## 実行上の注意点 / 運用ガイド

- API レート制限を遵守してください（J-Quants: 120 req/min）。jquants_client は内部で RateLimiter を備えていますが、大量の並列リクエストを行う場合は設計に注意してください。
- ID トークンの取得は refresh token を使用して行われます。refresh token は安全に管理してください。
- DuckDB ファイルは複数プロセスで同時書き込みすると問題になる場合があります。運用設計（ロック／単一ライター等）を検討してください。
- RSS 収集では外部 URL を取得するため SSRF 対策やホワイトリスト管理を行ってください。news_collector はいくつかの防御を実装していますが、運用環境に合わせた追加制御を推奨します。
- KABUSYS_ENV により挙動を分けられます（development / paper_trading / live）。本番は `live` に設定してください。

---

## ディレクトリ構成

主要ファイル構成（抜粋）:

```
src/
└── kabusys/
    ├── __init__.py
    ├── config.py
    ├── data/
    │   ├── __init__.py
    │   ├── jquants_client.py
    │   ├── news_collector.py
    │   ├── schema.py
    │   ├── pipeline.py
    │   ├── calendar_management.py
    │   ├── audit.py
    │   └── quality.py
    ├── strategy/
    │   └── __init__.py
    ├── execution/
    │   └── __init__.py
    └── monitoring/
        └── __init__.py
```

モジュール別役割まとめ:
- src/kabusys/config.py: 環境変数読み込み・設定オブジェクト
- src/kabusys/data/*.py: データ取得・保存・ETL・品質・監査関連
- src/kabusys/strategy, execution, monitoring: 戦略・発注・監視の拡張ポイント

---

## 開発 / 貢献

- コードの拡張や戦略実装は `strategy` パッケージ、発注ロジックは `execution` へ追加してください。
- テストは自動環境変数読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用すると再現性が向上します。
- セキュリティに関わる情報（API トークン等）は .env を利用し、リポジトリへコミットしないでください。

---

以上が本プロジェクトの README です。必要であれば、運用手順（cron/systemd 用の実行スクリプト例）、デプロイ手順、監視・アラート設定などの追加ドキュメントを作成します。どの部分を詳しく書くか指示ください。