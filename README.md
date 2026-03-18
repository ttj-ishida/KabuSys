# KabuSys

日本株自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得（J-Quants）、ETLパイプライン、DuckDBスキーマ、ニュース収集、品質チェック、監査ログ用スキーマなどを提供します。

---

## 概要

KabuSys は以下を目的とした内部ライブラリ群です。

- J-Quants API から株価・財務・マーケットカレンダーを安全かつ冪等に取得して DuckDB に保存
- RSS ベースのニュース収集と銘柄コード紐付け
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day など）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）用テーブル定義
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上のポイント：
- API レート制限（J-Quants: 120 req/min）を守る RateLimiter
- 冪等保存（DuckDB の ON CONFLICT / DO UPDATE / DO NOTHING を活用）
- ネットワークリトライ（指数バックオフ、401 の自動トークンリフレッシュ）
- SSRF や XML Bomb 等の防御（news_collector での検証／defusedxml 利用）
- 全てのタイムスタンプは UTC を想定

---

## 主な機能一覧

- data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - レート制御・リトライ・トークンキャッシュ
- data.schema
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) / get_connection(db_path)
- data.pipeline
  - 日次 ETL（差分更新・バックフィル・品質チェック）
  - run_daily_etl(...) / run_prices_etl / run_financials_etl / run_calendar_etl
- data.news_collector
  - RSS フィード取得、テキスト前処理、記事ID生成、DuckDB 保存（raw_news, news_symbols）
  - SSRF/サイズ/圧縮対策、トラッキングパラメータ除去
  - run_news_collection(conn, sources, known_codes)
- data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job で夜間差分更新
- data.quality
  - 欠損・スパイク・重複・日付不整合のチェック。QualityIssue を返す。
  - run_all_checks(...) を ETL 後に呼び出す
- data.audit
  - 監査用テーブル（signal_events, order_requests, executions）と初期化 helper

その他:
- settings 管理（env 自動ロード、必須 env のチェック、env モード判定）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈の | 演算子を利用）
- DuckDB が使用可能（Python パッケージ `duckdb`）
- defusedxml（XML パースの安全化）

例: 仮想環境作成と必要パッケージのインストールの一例
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# （追加のユーティリティや依存があればここに記載）
```

環境変数
- プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（.git または pyproject.toml を基準にプロジェクトルートを検出）。
- 自動ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

必須環境変数
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 動作モード: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

例 .env
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（簡単な例）

Python スクリプトや REPL から直接利用できます。以下は典型的なワークフロー例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ファイルを自動作成してテーブルを作る
```

2) 日次 ETL 実行（J-Quants から株価・財務・カレンダーを取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # デフォルトは本日
print(result.to_dict())
```

3) ニュース収集ジョブの実行（既知の銘柄リストで紐付け）
```python
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

4) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved", saved)
```

5) 監査スキーマを追加（監査ログを使う場合）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn, transactional=True)
```

6) 品質チェック（個別または ETL 内で実行）
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

注意点
- jquants_client は内部でレート制御と自動リトライを行います。get_id_token() によりトークンを取得し、401 を受けた場合は自動リフレッシュを試みます。
- news_collector は外部 RSS を取得するため SSRF / 圧縮爆弾 / 大きな応答を防ぐ保護を組み込んでいます。

---

## よく使う API（抜粋）

- kabusys.config.settings — 各種設定取得（例: settings.jquants_refresh_token, settings.env, settings.is_live）
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)
- kabusys.data.news_collector.fetch_rss(url, source)
- kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- kabusys.data.calendar_management.is_trading_day(conn, date)
- kabusys.data.audit.init_audit_db(path) / init_audit_schema(conn)
- kabusys.data.quality.run_all_checks(conn, target_date=None)

---

## ディレクトリ構成

プロジェクト内の主要ファイルとパッケージ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理（.env 自動ロード、検証）
  - data/
    - __init__.py
    - schema.py                     — DuckDB スキーマ定義と init_schema / get_connection
    - jquants_client.py             — J-Quants API クライアント（取得・保存・認証・RateLimiter）
    - pipeline.py                   — ETL パイプライン（差分更新・品質チェック）
    - news_collector.py             — RSS ニュース収集と保存（SSRF/圧縮対策・銘柄抽出）
    - calendar_management.py        — マーケットカレンダー管理（営業日ロジック）
    - audit.py                      — 監査ログ用スキーマ・初期化
    - quality.py                    — データ品質チェック
  - strategy/
    - __init__.py                   — （戦略モジュール置き場、実装は拡張）
  - execution/
    - __init__.py                   — （発注実行モジュール置き場、実装は拡張）
  - monitoring/
    - __init__.py                   — （監視・メトリクス等）

README や DataPlatform.md / DataSchema.md のような設計文書をプロジェクトルートに置くことを想定しています（config は .git または pyproject.toml を基準にプロジェクトルートを検出して .env を自動ロードします）。

---

## 開発者向けメモ

- タイプヒントや新構文を使用しているため Python 3.10+ を推奨します。
- DuckDB の SQL 実行においてはプレースホルダ（?）を使用してインジェクションリスクを低減しています。
- ETL は Fail-Fast ではなく、可能な限り全データを収集し品質チェックは別途レポートする設計です（呼び出し側で重大度に応じたアクションを決定してください）。
- news_collector の _urlopen はテスト時に差し替え可能（モックして外部アクセスを抑止）。

---

必要があれば、セットアップ用の requirements.txt の雛形や、cron / Airflow 向けの実行例（run_daily_etl をラップする CLI / job 実装）も追加で作成できます。どの情報を優先して追加しますか？