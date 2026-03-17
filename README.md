# KabuSys

日本株向け自動売買基盤のコアライブラリ（KabuSys）。  
データ取得・ETL、データ品質チェック、マーケットカレンダー管理、ニュース収集、監査ログスキーマなどを提供します。

バージョン: 0.1.0 (パッケージ内 __version__)

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・カレンダーデータ取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB による冪等的なデータ保存スキーマ（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集（SSRF 対策・トラッキングパラメータ除去・記事ID冪等性）
- マーケットカレンダー管理（営業日判定・前後営業日取得）
- 監査ログ（シグナル→発注→約定のトレーサビリティ用スキーマ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上のポイント:
- API レート制御、指数バックオフリトライ、401 時のトークン自動更新
- DuckDB へは冪等な INSERT（ON CONFLICT）で保存
- RSS 取得は SSRF・XML Bom 等の脅威に配慮
- ETL は差分更新・バックフィル・品質チェックを備える

---

## 機能一覧

主要なモジュールと機能:

- kabusys.config
  - 環境変数読み込み（プロジェクトルートの `.env` / `.env.local` 自動ロード、無効化フラグあり）
  - 必須設定の取得ラッパー（settings オブジェクト）
  - 主要環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABUSYS_ENV (development|paper_trading|live)
    - LOG_LEVEL (DEBUG|INFO|...)
    - DUCKDB_PATH, SQLITE_PATH

- kabusys.data.jquants_client
  - J-Quants API クライアント（価格、財務、カレンダー）
  - レートリミッタ、再試行、ID トークン管理
  - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar

- kabusys.data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema(db_path) によりテーブル・インデックスを作成

- kabusys.data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 部分的 ETL: run_prices_etl, run_financials_etl, run_calendar_etl

- kabusys.data.news_collector
  - RSS 取得・前処理（URL除去・空白正規化）・記事ID生成（正規化URLのSHA256）
  - DuckDB への保存（save_raw_news, save_news_symbols）
  - 銘柄コード抽出（extract_stock_codes）

- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job による夜間カレンダー更新

- kabusys.data.quality
  - 各種品質チェック（欠損、スパイク、重複、日付不整合）
  - run_all_checks でまとめて実行し QualityIssue のリストを返す

- kabusys.data.audit
  - 監査ログ用スキーマ（signal_events, order_requests, executions）と初期化関数 init_audit_schema / init_audit_db

---

## セットアップ手順

環境:
- Python 3.10 以上（型ヒントの | 演算子を使用）
- DuckDB を利用（duckdb Python パッケージ）

推奨パッケージ（例）:
- duckdb
- defusedxml

例: pip でインストールする場合

1. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 開発環境にインストール
   - プロジェクトルートに pyproject.toml がある前提で:
     - pip install -e .
     - もしくは依存のみを入れる:
       pip install duckdb defusedxml

3. 環境変数 (.env) の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にすると無効化可能）。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 推奨例（.env.example を参考に作成）:

     JQUANTS_REFRESH_TOKEN=your-refresh-token
     KABU_API_PASSWORD=your-kabu-password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

4. DB スキーマ初期化（DuckDB）
   - Python REPL やスクリプトから:

     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ファイルは自動作成され、テーブルが作成される

   - 監査ログスキーマ（既存接続に追加）:

     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)

テスト実行時:
- 自動 .env ロードを無効にするには環境変数を設定:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（基本例）

以下は代表的な使い方例です。適宜ログ設定や例外ハンドリングを加えてください。

1) DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 今日を対象に ETL を実行
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS を取得して保存、銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}
```

4) J-Quants から個別の株価を取得して保存する（テストや補助処理）

```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
jq.save_daily_quotes(conn, records)
```

5) マーケットカレンダーの判定ユーティリティ

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
d = date(2025, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

6) 品質チェックの実行（ETL 後の監査）

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn)
for issue in issues:
    print(issue)
```

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベースURL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン（通知用）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID（通知先）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

設定は `.env` / `.env.local` または OS 環境変数で行えます。`.env.local` は上書き優先で読み込まれます。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（src 配下）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/               (発注・実行関連: 未実装ファイル群の入り口)
      - __init__.py
    - strategy/                (戦略関連: 未実装ファイル群の入り口)
      - __init__.py
    - monitoring/              (監視・メトリクス: 未実装ファイル群の入り口)
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py      (J-Quants API クライアント & 保存)
      - news_collector.py      (RSS 収集・正規化・保存)
      - schema.py              (DuckDB スキーマ定義・初期化)
      - pipeline.py            (ETL パイプライン: run_daily_etl 等)
      - calendar_management.py (市場カレンダー管理ユーティリティ)
      - audit.py               (監査ログスキーマの初期化)
      - quality.py             (データ品質チェック)

---

## 開発・運用メモ

- DuckDB の INSERT 文は ON CONFLICT を多用しており、ETL は冪等に設計されています。
- J-Quants へのリクエストは 120 req/min を目安にレート制御されています（モジュール内 RateLimiter）。
- ニュース収集は外部の RSS を扱うため、SSRF 対策や XML パースの安全化（defusedxml）を行っています。
- ETL は Fail-Fast ではなく各ステップでエラーを集約し、結果オブジェクト（ETLResult）で状態を返す設計です。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してテスト用環境変数を注入することを推奨します。

---

必要に応じて README に追記したい項目（例）:
- フルな依存パッケージ一覧 / requirements.txt
- CI ワークフロー例（ETL のスケジューリング、夜間カレンダー更新ジョブの実行方法）
- 発注（execution）や戦略（strategy）モジュールの使用例（実装次第で追加）
- 運用手順（バックアップ、DB 管理、ログの扱い）

必要ならばこれらのセクションを追記します。