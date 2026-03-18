# KabuSys

バージョン: 0.1.0

日本株向けの自動売買プラットフォーム向けに設計されたライブラリ群です。  
J-Quants からの市場データ取得、RSS ニュース収集、DuckDB ベースのスキーマ定義・初期化、ETL パイプライン、データ品質チェック、監査ログ（発注〜約定トレース）などを提供します。

---

## 概要

KabuSys は次の目的を持つ内部ライブラリ群です。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得・保存する
- RSS フィードからのニュース収集と銘柄紐付け（SSRF・XML Bomb 対策等を組み込んだ実装）
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）スキーマ定義と初期化
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- 監査ログ（信号→発注→約定のトレーサビリティ）の初期化ロジック
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上のポイント:
- J-Quants クライアントはレート制限（120 req/min）・リトライ（指数バックオフ）・トークン自動更新に対応
- ETL は冪等（DuckDB 側で ON CONFLICT を使用）かつ差分更新を行う
- ニュース収集は URL 正規化・トラッキング除去・SSRF 防止・レスポンスサイズ制限を実装

---

## 主な機能一覧

- config
  - 環境変数読み込み（.env / .env.local 自動ロード）と必須設定取得ラッパー（Settings）
- data.jquants_client
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - DuckDB への保存関数: save_daily_quotes(), save_financial_statements(), save_market_calendar()
  - レートリミッタ、リトライ、401 トークン自動更新
- data.news_collector
  - RSS フィードの取得と前処理（preprocess_text）
  - raw_news への冪等保存（save_raw_news）、記事と銘柄の紐付け（save_news_symbols/_save_news_symbols_bulk）
  - SSRF 防止、XML 脆弱性対策、gzip 上限チェック、トラッキングパラメータ除去
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）と init_schema()
- data.pipeline
  - run_daily_etl()：市場カレンダー取得 → 株価差分ETL → 財務差分ETL → 品質チェック
  - run_prices_etl(), run_financials_etl(), run_calendar_etl()
- data.calendar_management
  - 営業日判定・翌前営業日検索・カレンダー夜間更新ジョブ（calendar_update_job）
- data.audit
  - 監査ログ用テーブル DDL と init_audit_schema()/init_audit_db()
- data.quality
  - 欠損・重複・スパイク・日付不整合のチェック（QualityIssue を返す）
- strategy / execution / monitoring
  - パッケージのエントリは用意されており、戦略、発注ロジック、監視実装の拡張ポイント

---

## 動作要件（推奨）

- Python 3.10+
- 主要依存ライブラリ（少なくとも以下をインストール）
  - duckdb
  - defusedxml

プロジェクト内で使用している標準ライブラリ: urllib, logging, datetime, gzip, hashlib, ipaddress, socket, re など。

（プロジェクト配布時は requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb defusedxml

   （将来的には pip install -e . / pip install -r requirements.txt を想定）

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` や `.env.local` を置くと自動で読み込まれます（デフォルトで自動ロード有効）。
   - 自動ロードを無効化するには環境変数を設定: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : SQLite モニタリング DB（デフォルト: data/monitoring.db）
   - KABUSYS_ENV : 実行環境 (development / paper_trading / live)（デフォルト: development）
   - LOG_LEVEL : ログレベル (DEBUG / INFO / WARNING / ERROR / CRITICAL)（デフォルト: INFO）

   設定例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 初期化（DuckDB スキーマ）

DuckDB スキーマを初期化するには data.schema.init_schema() を使用します。

Python 例:
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")   # ファイル作成とテーブル作成
# conn は duckdb.DuckDBPyConnection
```

監査ログ専用 DB を初期化する場合:
```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

既存の DB に接続だけする場合:
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

---

## 使い方（代表的な操作例）

- 日次 ETL 実行（株価・財務・カレンダーの差分取得 + 品質チェック）

```python
from datetime import date
import logging

from kabusys.data import schema, pipeline

logging.basicConfig(level=logging.INFO)

# DB 初期化（初回のみ）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を指定しなければ今日）
result = pipeline.run_daily_etl(conn, target_date=date.today())

print(result.to_dict())
```

- ニュース収集ジョブ（RSS からの記事収集と銘柄紐付け）

```python
from kabusys.data import schema, news_collector

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
known_codes = {"7203","6758","9984"}  # 例: 既知の銘柄コード集合

# 設定済みの RSS ソース DEFAULT_RSS_SOURCES を使う場合
counts = news_collector.run_news_collection(conn, known_codes=known_codes)
print(counts)
```

- J-Quants から ID トークンを取得して直接 API 呼び出し

```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

token = get_id_token()  # settings.jquants_refresh_token を使う
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- カレンダー夜間更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} records")
```

---

## 実装上の注意 / 補足

- 環境変数の自動ロード:
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` と `.env.local` を自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - テスト等で自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- jquants_client の挙動:
  - レート制限: 120 req/min を固定間隔で守る実装（_RateLimiter）
  - リトライ: 指定ステータス（408,429,5xx）やネットワークエラーで最大 3 回、指数バックオフ
  - 401 応答時はリフレッシュトークンを使って一度だけ id_token を再取得して再試行
  - 取得時刻（fetched_at）を UTC で記録し、look-ahead bias を防止できるように設計

- news_collector の安全設計:
  - defusedxml を使用して XML 脆弱性を防ぐ
  - リダイレクト先のホストがプライベート/ループバックであれば拒否（SSRF 防止）
  - レスポンスの最大バイト数を制限（デフォルト 10MB）、gzip 解凍後のサイズも検査
  - 記事ID は正規化 URL の SHA-256（先頭32文字）を使用して冪等性を担保

- DuckDB スキーマ:
  - Raw / Processed / Feature / Execution 層のテーブルを定義済み
  - 主要テーブルは PRIMARY KEY と ON CONFLICT（保存関数実装側）を想定しており、冪等保存が可能

- テスト用のモック:
  - news_collector._urlopen をモックして HTTP レスポンスを差し替えることでネットワークを介さない単体テストが可能

---

## ディレクトリ構成

src 以下の主要ファイル・ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py              (パッケージメタ情報: __version__ = "0.1.0")
  - config.py                (環境変数 / 設定読み込み)
  - data/
    - __init__.py
    - jquants_client.py      (J-Quants API クライアント + 保存ロジック)
    - news_collector.py      (RSS 収集・保存・銘柄抽出)
    - schema.py              (DuckDB スキーマ定義と init_schema)
    - pipeline.py            (ETL パイプライン)
    - calendar_management.py (カレンダー管理 / ジョブ)
    - audit.py               (監査ログ用スキーマ初期化)
    - quality.py             (データ品質チェック)
  - strategy/
    - __init__.py            (戦略実装の拡張ポイント)
  - execution/
    - __init__.py            (発注 / ブローカー連携の拡張ポイント)
  - monitoring/
    - __init__.py            (監視 / アラート用の拡張ポイント)

（README では主要なモジュールのみを抜粋しています）

---

必要に応じて README に追記可能な項目（例）
- 実運用での注意点（paper/live 切り替えやリスク制御）
- CI / テスト実行手順
- 依存パッケージの正確なバージョン (requirements.txt / pyproject.toml)
- ストラテジー実装テンプレートや実行スケジュールの推奨

要望があれば、上記の追加セクションやサンプルワークフロー（cron / Airflow / systemd での実行例）も作成します。