# KabuSys

日本株向け自動売買・データ基盤ライブラリ (KabuSys)

---

## プロジェクト概要

KabuSys は日本株の自動売買およびデータ基盤を構築するための内部ライブラリ群です。  
J-Quants API から市場データ（株価・財務・マーケットカレンダー）を取得して DuckDB に格納し、データ品質チェック・ニュース収集・監査ログなどの機能を提供します。戦略層、実行（ブローカー）層、監視層と連携するための基盤処理（ETL、スキーマ、トレーサビリティ）を含みます。

主な設計方針：
- API レート制限・リトライ・トークン自動リフレッシュ対応
- DuckDB へ冪等（idempotent）に保存（ON CONFLICT / DO UPDATE）
- SSRF や XML Bomb 等のセキュリティ考慮（ニュース収集）
- 品質チェックで欠損・スパイク・重複・日付不整合を検出
- 監査ログ（signal → order → execution）を追跡可能にする設計

---

## 機能一覧

- 環境設定読み込み・管理（.env / 環境変数）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - トークン自動リフレッシュ・リトライ・レート制御
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）と raw_news / news_symbols 保存
  - URL 正規化、トラッキングパラメータ除去、SSRF 対策、gzip 上限チェック
- データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
- 監査ログ（信号・発注要求・約定）のスキーマと初期化機能

---

## 必要条件

- Python 3.10 以上（typing の union 表記などを使用）
- 主要依存パッケージ（例）:
  - duckdb
  - defusedxml

実際の要件はプロジェクトの packaging / requirements ファイルを参照してください。最小限は上記パッケージが必要です。

---

## セットアップ手順

1. リポジトリをクローンする

   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成・有効化（任意）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell)

3. 依存パッケージをインストール

   pip install duckdb defusedxml

   （パッケージ化されている場合は `pip install -e .` などでインストールできます）

4. 環境変数を設定

   プロジェクトルートに `.env` または `.env.local` を配置することで自動読み込みされます（Package 配布後も __file__ を基点にプロジェクトルートを探索する実装）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   任意:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB DB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用途の SQLite パス（デフォルト: data/monitoring.db）

---

## 使い方（主要ワークフロー例）

ここでは Python REPL やスクリプトから利用する基本例を示します。

1) DuckDB スキーマ初期化

Python で DuckDB のスキーマを作成します（ファイル DB または :memory:）:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ディレクトリは自動作成されます
```

2) 監査ログスキーマの初期化（追加）

既存の DuckDB 接続に監査ログを追加する:

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

または専用DBを作る:

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

3) 日次 ETL を実行する

ETL パイプラインを動かして株価・財務・カレンダーを取得・保存・品質チェックを行います:

```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())
```

引数例:
- target_date: date オブジェクトで ETL 対象日を指定
- run_quality_checks: 品質チェックを行うか（既定 True）
- backfill_days: 最終取得日の何日前から再取得するか（デフォルト 3）

4) ニュース収集ジョブ

RSS からニュースを収集して raw_news / news_symbols に保存します:

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は抽出に使う有効な銘柄コード集合（例: DB から取得）
known_codes = {"7203", "6758", "9432"}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数, ...}
```

5) J-Quants API を直接利用する（トークン取得・データ取得）

```python
from kabusys.data import jquants_client as jq
token = jq.get_id_token()  # settings.jquants_refresh_token を使用して idToken を取得
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,31))
# 保存: jq.save_daily_quotes(conn, records)
```

6) 品質チェックを単独で実行する

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## 環境変数 / 設定の挙動

- .env 自動ロードの優先順位: OS 環境 > .env.local > .env
- テストや特殊用途で自動読み込みを無効化したい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセット
- Settings で取得できるプロパティ:
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev

未設定の必須環境変数を参照すると ValueError が発生します（開発時は .env.example を参照して .env を作成してください）。

---

## ディレクトリ構成

（主要ファイル抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・Settings 定義（自動 .env ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、取得・保存関数（fetch_*, save_*）
    - news_collector.py
      - RSS 収集、URL 正規化、SSRF 対策、raw_news/news_symbols 保存
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - schema.py
      - DuckDB のスキーマ定義と init_schema / get_connection
    - audit.py
      - 監査ログ用スキーマ（signal_events / order_requests / executions）と初期化
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - strategy/
    - __init__.py （戦略層の実装を想定）
  - execution/
    - __init__.py （発注実行・ブローカー接続を想定）
  - monitoring/
    - __init__.py （監視・アラート用機能を想定）

---

## 開発・テスト時の注意点

- 型注釈で Python 3.10 の union 型（A | B）を使っているため Python 3.10 以上を推奨します。
- news_collector は外部ネットワークを使用するため、テストでは _urlopen をモックして外部依存を切り離して下さい。
- .env のパースや自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。パッケージ配布後も __file__ ベースで動作するよう設計されています。
- J-Quants の API レート制限（120 req/min）やリトライロジックは jquants_client に実装済みですが、複数プロセス・複数インスタンスで呼ぶ場合は追加の制御が必要です。

---

## 参考（よく使う関数）

- data.schema.init_schema(db_path)
- data.audit.init_audit_schema(conn) / init_audit_db(db_path)
- data.jquants_client.get_id_token(refresh_token=None)
- data.jquants_client.fetch_daily_quotes(...)
- data.jquants_client.save_daily_quotes(conn, records)
- data.pipeline.run_daily_etl(conn, target_date=None)
- data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- data.quality.run_all_checks(conn, target_date=None)

---

この README はコードベースの主要部分を要約したものです。詳細な設計・データ仕様（DataPlatform.md / DataSchema.md 等）や実運用に関する手順は別ドキュメントを参照してください。必要であれば README の英語版や CI / デプロイ手順、サンプルスクリプトを追加します。