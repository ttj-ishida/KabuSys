# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）です。  
データ収集（J-Quants / RSS）、ETLパイプライン、DuckDBベースのスキーマ、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的に設計された内部ライブラリ群です。

- J-Quants API からの株価・財務・市場カレンダーの取得（レート制御・リトライ・トークン自動リフレッシュ対応）。
- RSS からのニュース収集（正規化・SSRF対策・メモリ保護・冪等保存）。
- DuckDB によるデータスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）。
- 日次 ETL（差分更新・バックフィル・品質チェック）とカレンダー管理。
- データ品質チェック（欠損・スパイク・重複・日付不整合）。
- 監査ログ（signal → order_request → execution のトレース）を行うテーブル定義・初期化。

設計上のポイント：
- API レート制限と指数バックオフで堅牢な取得を実現。
- 取得時刻（fetched_at）をUTCで保存し、Look-ahead Bias を防止。
- DuckDB の ON CONFLICT / RETURNING を活用して冪等性と正確な挿入カウントを実現。
- ニュース収集は SSRF / XML Bomb / Gzip bomb 等の攻撃に対する対策を備えています。

---

## 主な機能一覧

- J-Quants クライアント
  - 株価日足（OHLCV）取得: fetch_daily_quotes / save_daily_quotes
  - 財務データ取得: fetch_financial_statements / save_financial_statements
  - マーケットカレンダー取得: fetch_market_calendar / save_market_calendar
  - トークン取得・自動リフレッシュ: get_id_token（モジュール内でキャッシュ）

- ニュース収集
  - RSS フィード取得と正規化: fetch_rss
  - raw_news への冪等保存: save_raw_news
  - 記事と銘柄コードの紐付け: save_news_symbols / _save_news_symbols_bulk
  - 銘柄コード抽出: extract_stock_codes

- DuckDB スキーマ管理
  - init_schema: 全テーブルとインデックスを作成
  - get_connection: 既存 DB への接続

- ETL パイプライン
  - run_daily_etl: 市場カレンダー→株価→財務→品質チェック（差分更新、バックフィル対応）
  - 個別 ETL: run_prices_etl, run_financials_etl, run_calendar_etl

- カレンダー管理
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job（夜間バッチで calendar を差分更新）

- 監査ログ（Audit）
  - init_audit_schema / init_audit_db: signal / order_request / executions テーブル初期化

- データ品質チェック
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks（まとめ実行）

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.10+）
   - 仮想環境を作成・有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必須:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクト全体を配布パッケージ化している場合は pip install -e . や requirements.txt を利用してください。）

3. 環境変数の設定
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネルID
   - 任意 / デフォルトあり:
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
     - LOG_LEVEL — "DEBUG"/"INFO"/...（デフォルト: INFO）

   - .env 自動ロード:
     - パッケージはプロジェクトルート（.git または pyproject.toml を探索）にある .env と .env.local を自動で読み込みます。
       読み込み順は: OS 環境変数 > .env.local > .env
     - 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 例 .env（参考）
     - JQUANTS_REFRESH_TOKEN=your_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

4. データベース初期化（DuckDB）
   - Python REPL などで:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - 監査ログ専用初期化:
     - from kabusys.data.audit import init_audit_db
     - audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（簡単な例）

- スキーマを作成して日次 ETL を実行する例:

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（ファイルがなければ作成）
conn = init_schema("data/kabusys.duckdb")

# ETL 実行（今日分）
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブの実行例:

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# known_codes は銘柄抽出で参照する有効コードのセット
known_codes = {"7203", "6758", "9984"}  # 例

results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: new_count, ...}
```

- J-Quants から特定銘柄の日足を直接取得して保存する例:

```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,1))
saved = jq.save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

- 監査ログ（audit）初期化:

```python
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 知っておくべき設計上の注意点

- J-Quants API のレート制限（120 req/min）に合わせて内部でスロットリングを行います。大量データ取得時は遅延が発生します。
- ネットワークエラーや HTTP 408/429/5xx に対して指数バックオフで最大 3 回リトライします。401 はトークン自動更新を行い 1 回リトライします。
- ニュース収集は XML パースに defusedxml を利用し、SSRF や XML/Gzip bomb を防ぐための検査と上限チェックを実装しています。
- DuckDB スキーマは初期化関数が冪等（すでに存在するテーブルは無視）です。init_schema を初回のみ呼べば OK。
- ETL は Fail-Fast ではなく、可能な限りデータを収集し、品質チェック結果から呼び出し元が停止判断できる設計です。
- すべての時刻は UTC の取り扱いを基本にしています（fetched_at 等）。

---

## ディレクトリ構成（抜粋）

プロジェクト内の主なファイル/モジュール:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得/保存/リトライ/レート制御）
    - news_collector.py             — RSS ニュース収集・前処理・保存
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - schema.py                     — DuckDB スキーマ定義・初期化
    - calendar_management.py        — カレンダー管理・営業日判定・calendar_update_job
    - audit.py                      — 監査ログ（signal/order_request/executions）初期化
    - quality.py                    — データ品質チェック
  - strategy/
    - __init__.py                   — 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py                   — 実行（発注）モジュール（拡張ポイント）
  - monitoring/
    - __init__.py                   — モニタリング・監視（拡張ポイント）

---

## 開発上のヒント

- 自動 .env ロードはプロジェクトルートを .git または pyproject.toml で探索します。パッケージ配布後やテストで自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 単体テストでは jquants_client の _urlopen / ネットワーク層や news_collector の外部呼び出しをモックすると安定します（コード内にもモック可能なポイントがあります）。
- DuckDB の接続はスレッド/プロセス間での共有に注意してください。長時間のジョブでは接続の再取得を検討してください。

---

## 依存関係（主なもの）

- duckdb
- defusedxml

その他は標準ライブラリ（urllib, json, logging, datetime, hashlib, socket, ipaddress など）を使用しています。

---

このリポジトリはコアのデータ収集・ETL・スキーマ構成を提供します。戦略（strategy）、発注実行（execution）、監視（monitoring）層は拡張ポイントとして設計されています。必要に応じて各モジュールを拡張して運用ワークフローに合わせてください。