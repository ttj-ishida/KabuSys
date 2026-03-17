# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群（KabuSys）。  
J-Quants API や RSS を使ったデータ収集、DuckDB ベースのスキーマ定義、ETL パイプライン、品質チェック、監査ログなどを提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数一覧（設定）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は、J-Quants 等から市場データ（株価日足・財務データ・マーケットカレンダー）を取得して DuckDB に格納するためのモジュール群と、RSS からのニュース収集、データ品質チェック、監査ログ管理、カレンダー管理、基本的な ETL パイプラインを提供するライブラリです。設計上のポイントは以下です：

- API レート制御（固定間隔スロットリング）とリトライ、401 時の自動トークンリフレッシュ
- DuckDB への冪等保存（ON CONFLICT 等）による安全な更新
- ニュース収集における SSRF・XML 攻撃対策、ファイルサイズ上限
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（信号→発注→約定まで UUID 連鎖でトレーサビリティ）
- 市場カレンダー管理と営業日判定ユーティリティ

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダーの取得）
  - レートリミット、指数バックオフリトライ、ID トークンの自動リフレッシュ
  - DuckDB への保存（save_daily_quotes / save_financial_statements / save_market_calendar）
- data.news_collector
  - RSS フィードからニュースを収集して raw_news に保存
  - URL 正規化（トラッキングパラメータ除去）、記事ID は SHA-256 の先頭 32 文字
  - SSRF 対策、gzip サイズ制限、defusedxml による XML パース
  - 銘柄コード抽出と news_symbols への紐付け
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) によるテーブル・インデックスの作成
- data.pipeline
  - 差分更新に基づく ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 品質チェックの呼び出し（quality モジュール）
- data.calendar_management
  - カレンダーの夜間更新ジョブ（calendar_update_job）
  - 営業日判定・次営業日/前営業日取得・期間営業日列挙など
- data.quality
  - 欠損・スパイク・重複・日付不整合検出（QualityIssue を返す）
- data.audit
  - 監査ログ用テーブル（signal_events / order_requests / executions）初期化
  - init_audit_schema / init_audit_db
- config
  - .env 自動ロード（プロジェクトルートの .env, .env.local、環境変数優先）
  - アプリ設定ラッパー settings（JQUANTS_REFRESH_TOKEN 等の必須取得）

---

## セットアップ手順

前提:
- Python 3.9+ (型ヒントに union 型を用いているため、実行環境に合わせてください)
- DuckDB を使用するため ネイティブ拡張が必要（pip で duckdb をインストール）

例:

1. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトで requirements.txt があればそちらを使用してください。）

3. 環境変数を作成（プロジェクトルートに .env を置く）
   - 自動で .env（および .env.local）を読み込みます（プロジェクトルートは .git または pyproject.toml で検出）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. DuckDB スキーマ初期化（例は下の「使い方」参照）

---

## 簡単な使い方（コード例）

以下は Python REPL またはスクリプト内での基本的な操作例です。settings は環境変数から値を取得します（未設定だと例外）。

- DuckDB スキーマの初期化

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path はデフォルト "data/kabusys.duckdb"
conn = init_schema(settings.duckdb_path)
```

- run_daily_etl（日次 ETL 実行）

```python
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.data.pipeline import run_daily_etl

conn = get_connection(settings.duckdb_path)
result = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト
print(result.to_dict())
```

- RSS ニュース収集（既知の銘柄コード集合を渡して紐付け）

```python
from kabusys.data.news_collector import run_news_collection
# conn は DuckDB 接続
known_codes = {"7203", "6758"}  # 例: トヨタ、ソニー等
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

- カレンダー夜間ジョブ（先読み）

```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
print(f"saved {saved} records")
```

- 監査スキーマの初期化

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

- J-Quants クライアントを直接使う（トークンは settings から取得）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使ってトークン取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 環境変数（主なもの）

自動読み込みされる .env/.env.local または OS 環境変数:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
- SLACK_BOT_TOKEN : Slack 通知用（本コード内で必須としているプロパティ）
- SLACK_CHANNEL_ID : Slack 投稿先チャンネル ID
- KABU_API_PASSWORD : kabuステーション等の API パスワード（必要箇所で使用）

任意 / デフォルトあり:
- KABUSYS_ENV : 開発環境識別 (development | paper_trading | live) （デフォルト: development）
- LOG_LEVEL : ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : "1" を設定すると自動 .env ロードを無効化
- KABUS_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 (.env):

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定は settings オブジェクト経由で参照できます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## ディレクトリ構成

本リポジトリの主要ファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py        # RSS ニュース収集、SSRF 保護、記事保存
    - pipeline.py              # ETL パイプライン（差分更新・品質チェック）
    - schema.py                # DuckDB スキーマ定義 & 初期化
    - calendar_management.py   # 市場カレンダー管理（営業日判定・更新ジョブ）
    - audit.py                 # 監査ログテーブル定義・初期化
    - quality.py               # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

主要な機能は data パッケージ内に集約されています。strategy / execution / monitoring は拡張ポイントとして設計されています（現状はパッケージ初期化のみ）。

---

## 実運用上の注意・設計上のポイント

- J-Quants API: レート制限（120 req/min）に対応するため固定間隔スロットリングを使用しています。多数の銘柄を一括で取得する場合は注意してください。
- トークン管理: 401 応答時に自動的にリフレッシュし 1 回だけリトライする仕組みがあります。
- DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）にしています。
- news_collector は外部からの攻撃（SSRF、XML Bomb）を考慮して実装されています。URL スキームの検証、プライベート IP の検査、gzip サイズ上限などを行います。
- 品質チェックは Fail-Fast を採らず、検出された問題の一覧（QualityIssue）を返し、呼び出し元で運用ルールに応じて処理を決められるようにしています。
- .env はプロジェクトルート（.git や pyproject.toml）を基準に自動読み込みされます。テスト時等に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。

---

## ライセンス・貢献

本 README はコードベースに基づく利用説明書です。実際のパッケージ化・配布、テスト、および CI/CD の設定等はリポジトリ方針に従って追加してください。

貢献やバグ報告はリポジトリの Issue/PR を通じてお願いします。

---

必要があれば、README にサンプル .env.example、より詳細な ETL 運用手順（cron / Airflow など）やログ設定方法、例外処理のハンドリング方針、テストの書き方等も追記できます。どの情報を追加しましょうか？