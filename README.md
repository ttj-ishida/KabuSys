# KabuSys

日本株向けの自動売買プラットフォームのライブラリです。データ取り込み（J-Quants）、ニュース収集、ETLパイプライン、データ品質チェック、DuckDBスキーマ、監査ログなど、戦略・実行層の基盤となる機能を提供します。

---

## 特長（概要）

- J-Quants API 経由で株価（OHLCV）、財務データ、JPXマーケットカレンダーを取得
  - API レート制限（120 req/min）を順守する RateLimiter
  - リトライ（指数バックオフ）、401 発生時のトークン自動リフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止
- RSS からニュースを収集して正規化・前処理後に保存（SSRF・XML Bomb 等に配慮）
  - URL 正規化・トラッキングパラメータ除去、記事 ID は正規化 URL の SHA-256（先頭32文字）
  - DuckDB に冪等的に保存（ON CONFLICT / RETURNING を活用）
  - 銘柄コード抽出（4桁数字）と記事→銘柄紐付け機能
- ETL パイプライン（差分更新、バックフィル、品質チェック）
  - 市場カレンダー、株価、財務データの差分取得と保存
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - ETL 実行結果を ETLResult として返却
- DuckDB ベースの多層スキーマ（Raw / Processed / Feature / Execution）
  - 監査ログ用スキーマ（signal → order_request → executions のトレーサビリティ）
- 設定管理モジュールで .env または環境変数から設定を自動読み込み（配布後も動作する探索ロジック）

---

## 機能一覧

主な機能・モジュール

- kabusys.config
  - 環境変数管理、.env 自動読み込み（プロジェクトルート検出）
  - 必須設定の取得（例: JQUANTS_REFRESH_TOKEN 等）
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB に対する save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
  - テキストの前処理、URL 正規化、SSRF 対策
- kabusys.data.schema
  - DuckDB スキーマ定義と init_schema / get_connection
- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
  - ETLResult による実行結果の集約、品質チェック連携
- kabusys.data.calendar_management
  - 営業日判定・前後営業日取得・カレンダー夜間更新ジョブ
- kabusys.data.audit
  - 監査ログ（signal_events, order_requests, executions）スキーマ初期化
- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks

ディレクトリに strategy、execution、monitoring のためのプレースホルダもあります。

---

## 前提条件 / 必要パッケージ

- Python 3.10+
- 以下のパッケージ（例）
  - duckdb
  - defusedxml
- （必要に応じて）urllib, json 等は標準ライブラリで利用可能

インストール例（プロジェクトルートで）:
```bash
pip install duckdb defusedxml
# または requirements.txt を用意している場合
# pip install -r requirements.txt
```

---

## 環境変数（主要）

以下はこのコードベースで期待される主な環境変数。必須のものは明記します。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD : kabuステーション API のパスワード
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack チャネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（モニタリング等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 環境 (development, paper_trading, live)（デフォルト: development）
- LOG_LEVEL : ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)（デフォルト: INFO）

自動 .env ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例（.env）:
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

※ .env.example を参照して .env を作成してください（プロジェクトルートに置くことで自動読み込みされます）。

---

## セットアップ手順

1. リポジトリをクローン / 配置
2. Python 仮想環境を作成 & 有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、OS 環境変数を設定してください
   - 自動読み込みが不要なテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定可能
5. DuckDB スキーマ初期化
   - Python スクリプトまたは REPL で schema.init_schema を呼び出してください（デフォルトのディレクトリを自動作成します）

---

## 使い方（基本例）

以下は主要な操作のサンプルです。実際は独自のスクリプトやスケジューラ（cron、Airflow、GitHub Actions 等）から呼び出して運用します。

1) スキーマ初期化（DuckDB）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH の値に基づく Path オブジェクト
conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

2) 日次 ETL を実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

3) ニュース収集ジョブを実行（RSS → raw_news）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使う有効な銘柄コードのセット（例: 既知のコードリスト）
known_codes = {"7203", "6758", "8306"}  # 例
result = run_news_collection(conn, known_codes=known_codes)
print(result)  # {source_name: 新規保存件数}
```

4) 監査ログスキーマの初期化（order/exec の追跡）
```python
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
init_audit_schema(conn)  # transactional=True も選択可
```

5) J-Quants API の直接利用例
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
# トークンは環境変数から自動的に読み込まれる（settings.jquants_refresh_token）
quotes = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
```

---

## 運用上の注意

- J-Quants のレート制限（120 req/min）に注意してください。jquants_client モジュールは内部でスロットリングを行いますが、並列化すると制限を超える恐れがあります。
- get_id_token ではリフレッシュトークン（JQUANTS_REFRESH_TOKEN）を使用して id_token を取得します。401 発生時は自動リフレッシュ・再試行を行います。
- DuckDB のファイルパスはデフォルトで data/kabusys.duckdb。複数のプロセスから同時に書き込みを行う場合の整合性に注意してください（運用形態に応じてロック戦略や単一 ETL プロセス構成を検討してください）。
- ニュース収集では外部 XML をパースするため defusedxml を使用し、SSRF 対策や受信サイズ上限（10 MB）等の安全対策を講じています。
- 品質チェック（quality.run_all_checks）はエラー・警告を集めて返します。ETL は可能な限り継続する設計ですが、重大な品質問題がある場合は運用側でアラートや停止を判断してください。
- テストや CI で自動環境読み込みを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      -- RSS 収集・前処理・DB 保存
    - schema.py              -- DuckDB スキーマ定義と初期化
    - pipeline.py            -- ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py -- 営業日判定・カレンダー更新ジョブ
    - audit.py               -- 監査ログ（signal/order/execution）スキーマ
    - quality.py             -- データ品質チェック
  - strategy/
    - __init__.py            -- 戦略関連のプレースホルダ（実装はここに追加）
  - execution/
    - __init__.py            -- 発注・ブローカー連携のプレースホルダ
  - monitoring/
    - __init__.py            -- 監視・メトリクスのプレースホルダ

---

## 開発 / テストに関するヒント

- settings（kabusys.config.settings）を使って設定値を取得できます。自動で .env をプロジェクトルートから探すため、CI で明示的に環境を設定する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- 多くの関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。テストでは ":memory:" を使ってインメモリ DB を作成できます。
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  ```
- ネットワークリクエストや外部 API 呼び出しはモック可能な設計になっています（例: news_collector._urlopen を差し替える等）。

---

必要に応じて README に追記します。プロジェクトの利用シナリオ（運用ジョブスケジューリング、Slack 通知の組み込み、Broker 接続方式など）や CI/CD やデプロイ手順を追加したい場合は用途を教えてください。