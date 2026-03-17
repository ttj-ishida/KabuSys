# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）。J-Quants / kabuステーション 等の外部データ・API と連携し、データ収集（ETL）、品質チェック、ニュース収集、監査ログ、マーケットカレンダー管理などを提供します。

主な対象はデータ基盤・戦略開発者で、DuckDB をデータストアとして想定しています。

---

## 目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境変数の設定
  - データベース初期化
  - 日次 ETL 実行例
  - ニュース収集実行例
  - カレンダー更新ジョブ
  - 監査 DB 初期化
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株自動売買システム向けの共通ライブラリ群です。  
主に次を担います。

- J-Quants API を用いた株価・財務・市場カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- RSS からのニュース収集と記事→銘柄の紐付け（SSRF対策・XML安全処理・トラッキング除去）
- DuckDB を用いた 3 層データスキーマ（Raw / Processed / Feature）および Execution / Audit テーブルの定義・初期化
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（signal → order → execution のトレーサビリティ）

設計上、冪等性（ON CONFLICT）、Look-ahead-bias 回避（fetched_at 記録）、セキュリティ（defusedxml・SSRF対策）に配慮しています。

---

## 機能一覧

- data/jquants_client.py
  - J-Quants から日足（OHLCV）、四半期財務、マーケットカレンダーを取得
  - レートリミット（デフォルト 120 req/min）、指数バックオフリトライ、401時のトークン自動リフレッシュ
  - DuckDB へ冪等保存関数（save_*）
- data/news_collector.py
  - RSS フィード取得・解析（defusedxml を使用）
  - URL 正規化・トラッキング除去、記事ID を SHA-256（先頭32文字）で生成
  - SSRF・gzip/Bomb 対策、DuckDB へのバルク挿入（INSERT ... RETURNING）
  - テキストから銘柄コード（4桁）抽出
- data/schema.py
  - Raw / Processed / Feature / Execution 層の DuckDB テーブル定義と初期化（init_schema）
- data/pipeline.py
  - 差分 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）と統合日次 ETL（run_daily_etl）
  - バックフィル、品質チェック呼び出し（quality モジュール）
- data/calendar_management.py
  - market_calendar の差分更新ジョブ、営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
- data/quality.py
  - 欠損、スパイク、重複、日付不整合のチェック（run_all_checks）
- data/audit.py
  - 監査ログ用テーブル（signal_events / order_requests / executions）定義・初期化（init_audit_db / init_audit_schema）
- config.py
  - 環境変数読み込み（.env 自動読み込み、プロジェクトルート検出）
  - settings オブジェクトで各種設定へアクセス
  - 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## セットアップ手順

基本的な手順（環境に合わせて調整してください）。

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2. 依存ライブラリをインストール（リポジトリに requirements がない場合は最低限以下）
   - pip install duckdb defusedxml

   （プロジェクトで requirements.txt や pyproject.toml があればそちらを使用してください）

3. ソースをインストール（開発モード）
   - pip install -e .

4. 環境変数設定（.env をプロジェクトルートに配置するか OS 環境に設定）
   - KABUSYS はパッケージインポート時に自動で .env / .env.local をロードします（プロジェクトルートは .git または pyproject.toml で判定）。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須の環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API 用パスワード
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack 送信先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db

---

## 使い方

以下はライブラリの代表的な使い方例です。Python スクリプトやバッチで呼び出して利用します。

1) 環境変数の例 (.env)
```
# .env (プロジェクトルート)
JQUANTS_REFRESH_TOKEN=xxxxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

2) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成して全テーブルを作成
```

3) 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # 引数で target_date 等を指定可能
print(result.to_dict())
```

- run_daily_etl は
  1. カレンダー ETL（デフォルト先読み 90 日）
  2. 株価 ETL（差分 + デフォルト backfill 3 日）
  3. 財務 ETL（差分 + backfill）
  4. 品質チェック（デフォルト有効）
  を順に行い、ETLResult を返します。

4) RSS ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 銘柄コードセット（抽出時に参照）
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- fetch_rss は defusedxml を使い XML Bomb 等に対処、SSRF 対策・gzip 対応・レスポンスサイズ上限あり。
- save_raw_news は INSERT ... RETURNING を使って実際に挿入された記事IDを返します。

5) カレンダー更新ジョブ（夜間バッチ向け）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

6) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

7) J-Quants client の挙動（ポイント）
- Rate limit: 120 req/min（固定間隔スロットリング）
- リトライ: 最大 3 回（408/429/5xx など）、429 発生時は Retry-After ヘッダ優先
- 401 受信時は内部でリフレッシュトークンから id_token を再取得して 1 回リトライ

---

## ログ / 環境

- ログは環境変数 LOG_LEVEL で制御（デフォルト INFO）
- KABUSYS_ENV により動作モードを切替（development / paper_trading / live）。settings.is_live 等で判定可能。
- settings モジュールは .env を自動ロード（プロジェクトルート検出）し、settings オブジェクトから必要な設定値へアクセスできます。

---

## ディレクトリ構成

プロジェクト（抜粋）:

src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      pipeline.py
      calendar_management.py
      schema.py
      audit.py
      quality.py
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py

主なファイル説明:
- config.py: 環境変数読み込み・settings 定義
- data/schema.py: DuckDB スキーマ定義・初期化
- data/jquants_client.py: J-Quants API クライアント（取得 + 保存）
- data/pipeline.py: ETL パイプライン（差分取得・統合実行）
- data/news_collector.py: RSS 収集・記事保存・銘柄抽出
- data/calendar_management.py: マーケットカレンダー管理・営業日ロジック
- data/quality.py: データ品質チェック
- data/audit.py: 監査ログテーブル定義・初期化

---

## 補足 / 注意事項

- .env の自動読み込みはパッケージ import 時に実行されます。CI・テスト等で自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化は init_schema() を最初に呼んでください。既存テーブルがある場合はスキップされます（冪等）。
- J-Quants の API 利用には有効なリフレッシュトークンが必要です（settings.jquants_refresh_token）。
- RSS 取得時は外部接続を行うため、社内ネットワークのプロキシやアクセス制約に注意してください。
- 本リポジトリはライブラリ部分が中心のため、実行用ラッパー（CLI や scheduler の設定）は別途用意してください（cron / Airflow / systemd タイマー等）。

---

問題や改善案があれば、どの機能についてのドキュメントを拡張したいか教えてください。具体的な使用シナリオに合わせた例や CLI のサンプルも作成できます。