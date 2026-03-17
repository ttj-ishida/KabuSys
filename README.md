# KabuSys

日本株向けの自動売買/データプラットフォーム用ライブラリ群です。  
J‑Quants / kabuステーション 等からデータを取得し、DuckDB に蓄積して ETL → 品質チェック → 特徴量生成 → 発注フロー（監査）へつなぐための基盤機能を提供します。

バージョン: 0.1.0

---

## 概要（Project overview）

KabuSys は以下を目的とした Python モジュール群です。

- J‑Quants API から株価（日足）、財務データ、マーケットカレンダーを安全かつ効率的に取得
- RSS ベースのニュース収集と銘柄紐付け
- DuckDB を用いた 3 層（Raw / Processed / Feature）+ Execution / Audit のスキーマ管理
- ETL パイプライン（差分取得、バックフィル、品質チェック）の実装
- カレンダー管理（営業日判定、前後営業日探索）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ

設計ポイントとして、API レート制御、リトライ、リプレイ / look‑ahead bias 対策、冪等保存（ON CONFLICT）などを考慮しています。

---

## 機能一覧（Features）

- 環境変数/設定読み込み（.env / .env.local、プロジェクトルート自動検出）
- J‑Quants API クライアント
  - 株価日足（ページネーション対応）
  - 財務（四半期 BS/PL）
  - JPX マーケットカレンダー
  - トークン自動リフレッシュ、レート制御、リトライロジック
- DuckDB のスキーマ定義・初期化（raw / processed / feature / execution / audit）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- ニュース収集（RSS → raw_news、URL 正規化、SSRF 対策、gzip/BOM 対応）
- 銘柄コード抽出（テキスト中の 4 桁コード）
- マーケットカレンダー管理（営業日判定、next/prev/get_trading_days）
- 監査ログ用スキーマ（signal_events / order_requests / executions）
- データ品質チェック（欠損、重複、スパイク、日付不整合）

---

## セットアップ手順（Setup）

推奨 Python バージョン: 3.10+

必須パッケージ（例）
- duckdb
- defusedxml

pip での例:
```
pip install duckdb defusedxml
```

リポジトリをクローンしてパッケージ構成として使う想定です。プロジェクトルート（.git または pyproject.toml が存在する場所）に `.env` / `.env.local` を置くと自動で読み込みます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

環境変数の例（.env）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=...

# kabuステーション (必要に応じて)
KABU_API_PASSWORD=...
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知用)
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...

# DB パス (省略時は data/ 以下)
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
```

自動ロードの挙動:
- 優先順位: OS 環境変数 > .env.local > .env
- テスト等で自動ロードを無効にするには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（Usage）

以下は代表的な利用例です。Python スクリプトからインポートして使用します。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
# デフォルト: "data/kabusys.duckdb"（settings.duckdb_path）
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL（カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")  # 既存DBに接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- run_daily_etl は下記処理を実行します:
  1. カレンダー ETL（先読み）
  2. 株価 ETL（差分・バックフィル）
  3. 財務 ETL（差分・バックフィル）
  4. 品質チェック（品質問題の一覧を返す）

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# sources をカスタマイズ可能（省略時はデフォルト）
results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
print(results)  # {source_name: 新規保存数, ...}
```

- run_news_collection は各 RSS ソースを個別に取得し、raw_news に冪等保存、必要なら銘柄紐付け(news_symbols) も行います。
- known_codes を渡すとテキストから 4 桁コードを抽出して紐付けを行います。

4) マーケットカレンダー更新（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print("market_calendar saved:", saved)
```

5) 監査ログスキーマ初期化（監査用 DB を分ける場合）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

6) J‑Quants の ID トークンを直接取得（テスト用等）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # JQUANTS_REFRESH_TOKEN を環境変数で参照
```

ログレベルや KABUSYS_ENV によって動作モード（development / paper_trading / live）を切り替えられます。settings オブジェクト経由でアクセス可能です。

---

## 環境変数一覧（主要なもの）

- JQUANTS_REFRESH_TOKEN : J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API パスワード（必須で使う場合）
- KABU_API_BASE_URL      : kabuステーション API の base URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack 送信先チャンネル ID
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            : 監視用途の SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV            : 実行環境（development | paper_trading | live）
- LOG_LEVEL              : ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化（"1" 等）

---

## 実装上の注意 / 設計メモ

- J‑Quants API は 120 req/min のレート制限に合わせた RateLimiter を内蔵しています。大量取得時は時間がかかります。
- get_id_token() はリフレッシュトークンから ID トークンを取得し、401 応答時は自動リフレッシュして 1 回だけリトライします。
- DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE など）にしています。
- RSS 収集では SSRF 対策（スキーム検証、プライベートIP拒否、リダイレクト検査）、XML パース時の defusedxml 利用、レスポンスサイズ制限など安全対策を実装しています。
- ニュースの重複判定は URL 正規化後の SHA‑256（先頭32文字）を記事 ID としています（utm_* 等のトラッキングパラメータを除去）。
- audit スキーマは UTC タイムゾーン固定を前提としており、init_audit_schema() 実行時に SET TimeZone='UTC' を行います。

---

## ディレクトリ構成（Directory structure）

主要なファイル・モジュールは以下のとおりです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py       # J‑Quants API クライアント（取得・保存）
    - news_collector.py       # RSS ニュース収集
    - schema.py               # DuckDB スキーマ定義 / 初期化
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  # マーケットカレンダー管理
    - audit.py                # 監査ログスキーマ初期化
    - quality.py              # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記は現状の主要モジュールのみを抜粋しています。strategy / execution / monitoring は将来的にアルゴリズムや発注ロジックを置くための名前空間です。）

---

## 開発 / デバッグのヒント

- 自動環境読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを抑制できます。
- DuckDB の初期化時に親ディレクトリがなければ自動作成されます。
- ETL の差分ロジックは raw テーブルの最終取得日を見て自動計算します（backfill_days を渡して API の後出しを吸収可能）。
- ロギングを有効にしておくと ETL の進行や品質チェックの詳細が見やすくなります。

---

必要であれば、README にサンプル .env.example、Docker / systemd ジョブの例、Airflow や cron でのスケジューリング例なども追加できます。どのような運用想定（オンプレ/クラウド/コンテナ）で使うか教えてください。