# KabuSys

日本株向け自動売買プラットフォームのライブラリ群（ライブラリベースのコアコンポーネント）。

このリポジトリはデータ収集・ETL、データ品質チェック、ニュース収集、監査ログ／トレーサビリティ、マーケットカレンダー管理など、バックエンドで必要な基盤機能を提供します。戦略や発注実行は別モジュール（strategy / execution）で実装することを想定しています。

---

## 概要

主な設計方針・特徴
- J-Quants API を使った日本株データ（株価日足、財務、JPXカレンダー）の取得と DuckDB への冪等保存
- RSS ベースのニュース収集と前処理、記事 → 銘柄コード紐付け
- ETL の差分更新（最終取得日からの差分＋バックフィル）と日次パイプライン
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査テーブル（signal → order → execution のトレース）と監査DB初期化
- SSRF・XML Bomb・メモリDoS 対策を考慮した安全な外部データ取得実装
- 環境変数管理（.env 自動ロード機構）とアプリケーション設定ラッパー

---

## 機能一覧

- データ（kabusys.data）
  - jquants_client: J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ、ページネーション）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS からのニュース収集・前処理・DB保存・銘柄抽出
  - calendar_management: マーケットカレンダー管理・営業日判定ヘルパー
  - audit: 監査ログ用テーブル定義と初期化（トレーサビリティ）
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
- 設定（kabusys.config）
  - 環境変数の自動ロード（プロジェクトルートの .env/.env.local を読み込み）
  - settings オブジェクト経由の型安全な設定アクセス
- プレースホルダ: strategy / execution / monitoring モジュール（将来の実装対象）

---

## セットアップ手順

前提
- Python 3.10 以上（typing で | を使用）
- DuckDB を使用（ローカルファイルに保存）
- ネットワークアクセス（J-Quants API、RSS）

1. リポジトリを取得
   - git clone などで取得してください。

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 最低限必要な依存:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - 開発中はソースを編集して使うため editable install を使う場合:
     - pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env`（任意）と `.env.local`（任意）を置けます。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト利用等）。

必須の環境変数（Settings で参照されるもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション等の API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）

オプション（デフォルトあり）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用等）パス（デフォルト: data/monitoring.db）

例 .env（簡易）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主な操作例）

以下はライブラリ API を直接インポートして使う場合のサンプルです。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
# デフォルトパスを使う場合:
conn = schema.init_schema("data/kabusys.duckdb")
# あるいは settings を利用:
from kabusys.config import settings
conn = schema.init_schema(settings.duckdb_path)
```

2) 監査テーブルの初期化（audit 層）
```python
from kabusys.data import audit
# 既存接続に監査スキーマを追加する:
audit.init_audit_schema(conn, transactional=True)
# または監査専用DBを初期化:
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # 設定に応じて J-Quants トークンは settings から自動取得
print(result.to_dict())
```

- run_daily_etl は市場カレンダー、株価、財務データの差分取得および品質チェックを行います。
- 引数で target_date, id_token, backfill_days などを指定できます。

4) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に利用する有効な銘柄コードセット
known_codes = {"7203", "6758", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

5) J-Quants API を直接使ってデータ取得
```python
from kabusys.data import jquants_client as jq
# id_token を明示的に渡すことも、jq.get_id_token() に任せることも可能
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
jq.save_daily_quotes(conn, records)
```

6) 設定参照
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
is_live = settings.is_live
db_path = settings.duckdb_path
```

---

## 便利な注意点 / 動作方針

- J-Quants API のレート制御（120 req/min）はクライアント側で制御しています（固定間隔の RateLimiter）。
- HTTP エラー（408, 429, 5xx）やネットワークエラーに対する指数バックオフのリトライ実装があります。401 はトークン自動リフレッシュを一度だけ試行します。
- 全ての DuckDB への保存は冪等性を配慮しているため、ON CONFLICT DO UPDATE / DO NOTHING を多用しています。
- ニュース収集では SSRF や XML の危険性、レスポンスサイズ上限などに対して安全策を実装しています。
- データ品質チェックは Fail-Fast ではなく全ての問題を収集して呼び出し側で判断できるようにしています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（取得 + 保存）
  - news_collector.py       — RSS ニュース収集器 & DB 保存
  - schema.py               — DuckDB スキーマ定義 / init_schema / get_connection
  - pipeline.py             — ETL (run_daily_etl, run_prices_etl, ...)
  - calendar_management.py  — マーケットカレンダーヘルパーと更新ジョブ
  - audit.py                — 監査ログ（signal/order/execution）スキーマ & 初期化
  - quality.py              — データ品質チェック
- strategy/
  - __init__.py             — 戦略層用プレースホルダ
- execution/
  - __init__.py             — 発注実行層用プレースホルダ
- monitoring/
  - __init__.py             — 監視・メトリクス用プレースホルダ

プロジェクトルートには .env / .env.local / pyproject.toml / .git などがあることを期待しています（config._find_project_root により自動検出）。

---

## 依存関係（主要）

- Python 3.10+
- duckdb
- defusedxml
- 標準ライブラリ: urllib, logging, datetime, hashlib, socket, ipaddress など

必要に応じてプロジェクト用の requirements.txt を作成して管理してください。

---

## 貢献 / 拡張ポイント

- strategy / execution / monitoring の実装（戦略本体、ブローカー接続、Prometheus など監視連携）
- CLI やジョブランナー（ETL を cron・Airflow・GitHub Actions などで実行するためのラッパー）
- テストカバレッジ追加（ネットワーク依存箇所のモック・ユニットテスト）
- ドキュメント（DataPlatform.md, API 使用例、DB スキーマ仕様ドキュメント等）の整備

---

この README はコードベースの現在の実装を元にまとめた概要ドキュメントです。実運用前に必ず .env と権限管理、ネットワーク／シークレットの取り扱いを見直してください。