# KabuSys

日本株向けの自動売買プラットフォームのライブラリ群です。  
J-Quants / kabuステーション 等の外部サービスからデータを収集・保存し、ETL、品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ（発注→約定トレース）などを行うことを目的としています。

主に DuckDB をデータ層に使い、戦略層・実行層・監視層へデータを提供することを想定しています。

## 主要な特徴
- J-Quants API クライアント
  - 株価（日次 OHLCV）、四半期財務（BS/PL）、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）対応、指数バックオフによるリトライ、401 時の自動トークンリフレッシュ
  - 取得日時（fetched_at）を UTC で記録し look-ahead bias を防止
- DuckDB ベースのスキーマ管理
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義、インデックス
  - 冪等性を考慮した保存（ON CONFLICT ... DO UPDATE / DO NOTHING）
- ETL パイプライン
  - 差分取得（DB の最終取得日を起点に backfill を含む）
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - 日次 ETL の一括実行（市場カレンダー→株価→財務→品質チェック）
- ニュース収集モジュール
  - RSS から記事を収集して前処理し raw_news に保存
  - SSRF 防止（リダイレクト先検査、プライベートIP拒否）、XML Bomb 対策（defusedxml）、受信サイズ上限
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性保証
  - 記事と銘柄コードの紐付け（news_symbols）
- マーケットカレンダー管理
  - カレンダー差分更新、営業日判定、next/prev/get_trading_days 等のユーティリティ
- 監査ログ（Audit）
  - signal → order_request → executions まで UUID で追跡できる監査テーブル群
  - 発注の冪等キー、UTC タイムゾーンの徹底
- データ品質チェック
  - 複数チェックを集約して返す（QualityIssue）

---

## セットアップ手順

前提
- Python 3.10 以上（型定義で `X | None` の構文を使用）
- Git リポジトリ（自動 .env ロード時のプロジェクトルート検出に利用）

1. 仮想環境を作成して有効化
```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate      # Windows
```

2. 必要パッケージをインストール
- 最低限の依存：
  - duckdb
  - defusedxml

例:
```bash
pip install duckdb defusedxml
# 任意でパッケージをローカル開発インストール
pip install -e .
```
※ プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください。

3. 環境変数の設定
- .env または OS 環境変数で下記を設定してください（必須項目はエラーになります）:

必須:
- JQUANTS_REFRESH_TOKEN         — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD            — kabuステーション API パスワード
- SLACK_BOT_TOKEN              — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID             — Slack チャンネル ID

任意（デフォルト有り）:
- KABU_API_BASE_URL            — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH                  — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH                  — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV                  — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL                    — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

自動ロードについて:
- パッケージ起動時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、`.env` → `.env.local` を自動で読み込みます。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 .env
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 初期化（DB スキーマ作成など）

Python REPL やスクリプトから以下のように呼び出します。

- DuckDB スキーマ初期化（全テーブル）
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH の値（デフォルト data/kabusys.duckdb）
conn = schema.init_schema(settings.duckdb_path)
```

- 監査ログ用 DB 初期化（監査専用 DB を別ファイルで管理する場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主な API / 実行例）

以下はライブラリを直接使う基本例です。運用スクリプトや Airflow / cron などから呼び出して運用してください。

- 日次 ETL（市場カレンダー、株価、財務、品質チェックを実行）
```python
from kabusys.data import schema, pipeline
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)  # または init_schema で初期化済みの conn
result = pipeline.run_daily_etl(conn)  # 引数で target_date 等を指定可
print(result.to_dict())
```

- 株価差分 ETL を個別に実行
```python
from datetime import date
from kabusys.data import pipeline, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched} saved={saved}")
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードセット（抽出に使う）
known_codes = {"7203", "6758", "9432", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- マーケットカレンダー夜間更新
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

- J-Quants の生データ取得（低レベル）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

id_token = jq.get_id_token()  # refresh トークンから id_token を取得
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

ログレベルや環境は `KABUSYS_ENV` / `LOG_LEVEL` 環境変数で制御できます。

---

## セキュリティ・設計上の注意
- ネットワーク呼び出しはレート制限・リトライ・指数バックオフを実装していますが、実運用では API の使用制限に注意してください。
- ニュース収集は SSRF 対策（リダイレクト時のスキーム/ホスト検査、プライベートIP拒否）や XML パーサの安全実装（defusedxml）を備えています。外部URLの処理を追加する際はこれらの方針を遵守してください。
- すべてのタイムスタンプは UTC を利用する方針です（監査ログ等は SET TimeZone='UTC' を実行します）。
- DB 保存は基本的に冪等（ON CONFLICT を利用）を意識しているため、再実行に耐えます。

---

## ディレクトリ構成（主要ファイル）
（ソースルートが `src/` 配下にある想定）

- src/kabusys/
  - __init__.py                — パッケージエントリ（version 等）
  - config.py                  — 環境変数 / 設定の読み込み・管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント & DuckDB 保存ロジック
    - news_collector.py        — RSS ニュース収集 / 前処理 / DB 保存
    - schema.py                — DuckDB スキーマ定義と init_schema()
    - pipeline.py              — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py   — マーケットカレンダー更新・営業日ユーティリティ
    - audit.py                 — 監査ログ（signal / order_request / executions）
    - quality.py               — 品質チェック（欠損 / 重複 / スパイク / 日付不整合）
  - strategy/
    - __init__.py              — 戦略関連（拡張用エントリ）
  - execution/
    - __init__.py              — 発注・実行関連（拡張用エントリ）
  - monitoring/
    - __init__.py              — 監視関連（拡張用エントリ）

---

## 開発／運用上のヒント
- テスト時に自動 .env 読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ETL 実行はノイズを抑えるため logging 設定と連携して運用することを推奨します（LOG_LEVEL）。
- DuckDB の path を変えることで環境（ローカル／CI／運用）ごとに DB を切り分けられます。CI では `:memory:` を利用すると便利です。
- ニュースの銘柄抽出には known_codes セットが必要です（精度向上 / 誤検出削減のため）。

---

この README はコードベースの主要機能・使い方をまとめたものです。詳細な API ドキュメントや運用手順、外部サービスの設定（J-Quants アカウントの取得方法、kabuステーションの接続設定等）は別途用意してください。必要であれば README を拡張して CLI コマンド例や systemd / cron の設定サンプル、Docker 化手順なども追記できます。