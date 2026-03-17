# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ（データ収集・ETL・スキーマ・監査ログ等）

このリポジトリは KabuSys パッケージのコア実装を含みます。J-Quants や RSS などから市況データ・ニュースを取得して DuckDB に保存し、ETL／品質チェック／監査ログの基盤を提供します。

## 主要コンセプト（概要）
- J-Quants API を用いた株価（日足）・財務データ・JPX カレンダーの取得
- RSS フィードからのニュース収集と記事→銘柄紐付け
- DuckDB を用いた 3 層データレイク（Raw / Processed / Feature）および実行・監査スキーマ
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- レート制限・リトライ・トークンリフレッシュなどの堅牢な通信設計
- SSRF／XML ボム等に配慮したニュース収集実装

---

## 機能一覧
- 環境変数管理（.env 自動読み込み、プロジェクトルート検出）
- J-Quants クライアント（認証・ページネーション・リトライ・レート制御）
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への冪等保存（save_daily_quotes / save_financial_statements / save_market_calendar）
- RSS ニュース収集（fetch_rss, save_raw_news, save_news_symbols）
  - URL 正規化、トラッキングパラメータ除去、SSRF 対策、gzip サイズ検査
- DuckDB スキーマ定義・初期化（init_schema / get_connection）
- 監査ログスキーマ（init_audit_schema / init_audit_db）
- ETL パイプライン（run_daily_etl、個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（missing data / spike / duplicates / date consistency）
- マーケットカレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job）

---

## 前提（依存）
このコードベースは主に標準ライブラリで書かれていますが、動作に必要な外部パッケージ：
- duckdb
- defusedxml

インストール例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（プロジェクトで追加の依存があれば requirements.txt を用意してください）

---

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo>
```

2. 仮想環境作成・有効化（任意）
```bash
python -m venv .venv
source .venv/bin/activate
```

3. 依存パッケージをインストール
```bash
pip install duckdb defusedxml
```

4. 環境変数設定
- プロジェクトルートの `.env` または `.env.local` に必要なキーを設定するか、OS 環境変数として設定します。
- 自動読み込みの優先順位: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必要な環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネルID（必須）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: one of development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

例（.env の最小例）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要 API と実行例）

以下は Python スクリプトや REPL で使う際の基本例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイルパス例
conn = init_schema("data/kabusys.duckdb")
# 返り値は duckdb の接続オブジェクト
```

2) 監査ログ用 DB 初期化（別 DB にする場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

3) J-Quants トークン取得（通常は内部で自動取得）
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使用
```

4) 日次 ETL を実行（市場カレンダー・株価・財務の差分取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

5) ニュース収集ジョブ（RSS を取得して raw_news に保存）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# sources を省略すると DEFAULT_RSS_SOURCES を使用
# known_codes は銘柄抽出の際に有効なコード集合を渡す（任意）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)  # ソースごとの新規保存数を返す
```

6) 個別データ取得（例: 日足を取得して保存）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=None, date_to=None)  # 引数でフィルタ可
saved = save_daily_quotes(conn, records)
print("saved:", saved)
```

---

## 実装上のポイント / 注意点
- J-Quants API のレート制限（120 req/min）を考慮した RateLimiter を実装。大量リクエスト時はスロットリングされます。
- HTTP エラー (408 / 429 / 5xx) に対して指数バックオフで最大 3 回リトライします。401 発生時はトークンを自動リフレッシュして 1 回再試行します。
- DuckDB への保存は可能な限り冪等に作られており（ON CONFLICT DO UPDATE / DO NOTHING）、重複挿入による二重データを防止します。
- RSS 処理では XML/SSRF/メモリ DoS（受信サイズ）に対する防御を行っています。外部からの不正な URL またはリダイレクト先に注意してください。
- .env のパースはシェル風のクォーテーション・コメントを考慮して行われます。プロジェクトルート検出は __file__ 起点で .git または pyproject.toml を探すため、CWD 依存ではありません。

---

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（自動 .env ロード）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得 + 保存）
    - news_collector.py         — RSS ニュース収集・保存・銘柄抽出
    - schema.py                 — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — カレンダー（営業日判定・更新ジョブ）
    - audit.py                  — 監査ログ用スキーマ初期化
    - quality.py                — データ品質チェック
  - strategy/
    - __init__.py                — 戦略層のためのプレースホルダ
  - execution/
    - __init__.py                — 実行・注文層のプレースホルダ
  - monitoring/
    - __init__.py                — 監視用モジュールプレースホルダ

---

## 開発・テスト関連
- 自動 .env ロードを無効化したいユニットテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ネットワーク呼び出しをモックする際、news_collector の `_urlopen` を差し替えることでリダイレクトハンドラ等を回避してテストできます。
- DuckDB のインメモリテストには db_path に `":memory:"` を渡してください。

---

## 最後に
この README はコードベースに含まれる主要機能と使い方の要点をまとめたものです。ユースケースに応じて、戦略層（strategy）や実行層（execution）の実装、監視・通知の追加を行ってください。必要であれば README を拡張して、CI/CD・運用手順・デプロイ方法・サンプルジョブ（cron/airflow 等）を追記できます。