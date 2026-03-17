# KabuSys

日本株向けの自動売買・データプラットフォーム基盤ライブラリです。  
J-Quants API や RSS フィード等から市場データを取得し、DuckDB に格納・品質チェック・監査ログ管理までを一貫して行うことを目的としています。

主な想定用途
- 株価・財務・市場カレンダーの差分ETL（自動更新・バックフィル）
- ニュース（RSS）収集と銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注〜約定まで追跡可能な監査ログ（audit schema）
- DuckDB を中心としたローカルデータプラットフォーム

---

## 機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、市場カレンダーを取得
  - レート制限（120 req/min）の管理、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録、Idempotent な DB 書き込み（ON CONFLICT）
- ETL パイプライン
  - 差分更新、バックフィル、品質チェックの統合（run_daily_etl）
  - 市場カレンダーの先読み
- ニュース収集 (RSS)
  - RSS から記事を抽出して前処理、ID は正規化 URL の SHA-256（先頭32文字）
  - defusedxml による XML 攻撃防御、SSRF 対策、受信サイズ制限、DB 一括トランザクション挿入
  - 銘柄コード抽出と news_symbols への紐付け
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（init_schema）
  - 監査ログ用スキーマ（init_audit_schema / init_audit_db）
- マーケットカレンダー管理
  - 営業日判定、前後営業日探索、夜間更新ジョブ（calendar_update_job）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合チェック（run_all_checks）

セキュリティ/堅牢性に関する設計
- API レート管理、リトライ、トークンリフレッシュ
- XML パースに defusedxml を使用
- RSS 取得での SSRF 防止（リダイレクト検査・プライベートIP検査）
- DB 書き込みは可能な限り冪等（ON CONFLICT / トランザクション）

---

## 要件 / インストール

推奨 Python バージョン: 3.10+

主な依存パッケージ:
- duckdb
- defusedxml

簡単なセットアップ例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# もしパッケージ配布を想定している場合:
# pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。）

---

## 環境変数（.env）

パッケージはプロジェクトルートの `.env` / `.env.local` を自動ロードします（環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視等で使う SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL

例（.env）:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易ガイド）

1. リポジトリをクローンし仮想環境を作成・有効化
2. 依存パッケージをインストール（duckdb, defusedxml 等）
3. プロジェクトルートに `.env` を作成し必要な環境変数を設定
4. DuckDB スキーマを初期化

Python での DB 初期化例:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path で指定されたパスに DB を作成してスキーマを作成
conn = init_schema(settings.duckdb_path)
```

監査ログスキーマを追加する（既存接続に対して）:

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

監査専用 DB を作る場合:

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（代表的な API / ワークフロー）

以下は代表的な利用例です。実運用では logging の設定や例外処理、スケジューラ（cron / Airflow / APScheduler など）と組み合わせてください。

1) 日次 ETL を実行する

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回のみ）
conn = init_schema(settings.duckdb_path)

# ETL 実行（通常は scheduler から呼ぶ）
result = run_daily_etl(conn)
print(result.to_dict())
```

run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェック の順で処理します。品質チェックの結果やエラーは ETLResult に格納されます。

2) ニュース（RSS）収集

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema(settings.duckdb_path)

# 既知銘柄コードセット（抽出に使用）
known_codes = {"7203", "6758", "9984"}

# デフォルト RSS ソースから収集・保存
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

3) 市場カレンダー夜間バッチ更新

```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

4) J-Quants API を直接利用（デバッグ等）

```python
from kabusys.data import jquants_client as jq
# id_token は自動でキャッシュ・リフレッシュされる
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## ログ・モード

- 環境に応じて `KABUSYS_ENV` を設定してください（development / paper_trading / live）。
- ログレベルは `LOG_LEVEL` で制御します（デフォルト: INFO）。

---

## ディレクトリ構成

リポジトリの主要な構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理、自動 .env ロード
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 / 保存）
    - news_collector.py — RSS ニュース収集・前処理・DB保存
    - schema.py — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（判定・更新ジョブ）
    - audit.py — 監査ログ（signal / order_request / executions）スキーマ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/ — 戦略実装用パッケージ（空 __init__ がある）
  - execution/ — 発注・ブローカー連携用（空 __init__ がある）
  - monitoring/ — 監視関連（空 __init__ がある）

各ファイルは README 内で触れた機能ごとに責務が分かれています。DuckDB のスキーマは DataPlatform.md 相当の層（Raw/Processed/Feature/Execution）に分かれています。

---

## 開発メモ / 注意点

- Python 3.10 以降を想定（型注釈に X | Y を使用）。
- jquants_client は API レート制限を守るため内部で固定間隔のスロットリングを行います（120 req/min）。
- fetch 系はページネーションに対応。401 受信時はリフレッシュを試みて再送します（1 回のみ）。
- news_collector は defusedxml / SSRF 検査 / レスポンスサイズ制限を実装しています。HTTP レスポンスの Content-Encoding（gzip）対応あり。
- DuckDB の SQL はできるだけパラメータバインド（?）を使用しており、トランザクションは必要箇所で利用しています。
- 自動 .env ロードをテストで無効化する場合は、プロセス環境で `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## よくある操作（コマンド例）

- DB 初期化（Python スクリプト）:

  python スクリプトで init_schema(settings.duckdb_path) を呼び出す。

- 日次 ETL を定期実行する:
  - cron / systemd timer / Airflow / Prefect などから上記 Python スクリプトを定期実行。

---

必要に応じて README にサンプルの .env.example や requirements.txt、CI 用のワークフロー例（ETL の定期実行・スモークテスト）を追加できます。追加したい例があれば教えてください。