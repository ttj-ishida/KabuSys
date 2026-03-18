# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants）、ニュース収集、ETLパイプライン、データ品質チェック、DuckDBスキーマ定義、監査ログなど、取引戦略実行に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援するライブラリ群です。主に以下の機能を提供します。

- J-Quants API 経由での市場データ（株価・財務・市場カレンダー）取得
- RSS フィードからのニュース収集と銘柄紐付け
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- DuckDB ベースのスキーマ定義と初期化
- 監査ログ（シグナル → 発注 → 約定のトレース）用スキーマ
- 市場カレンダー（営業日判定・前後営業日取得）管理
- 簡易設定管理（環境変数 / .env の自動読み込み）

注意: strategy、execution、monitoring パッケージはインターフェースだけ用意されており、具象実装は含みません（拡張用の骨組み）。

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（OHLCV、財務、マーケットカレンダー）
  - レート制御（120 req/min 固定スロットリング）
  - リトライ（指数バックオフ、401 時のトークン自動リフレッシュ対応）
  - DuckDB への冪等な保存（ON CONFLICT ... DO UPDATE）
- data/news_collector.py
  - RSS 取得・XML パース（defusedxml）
  - URL 正規化・トラッキングパラメータ除去・ID 生成（SHA-256）
  - SSRF 対策（スキーム検証、プライベート IP の拒否、リダイレクト検査）
  - raw_news / news_symbols への冪等保存（チャンク挿入、INSERT ... RETURNING）
- data/schema.py
  - Raw / Processed / Feature / Execution / Audit を想定した DuckDB テーブル定義
  - init_schema(db_path) による初期化 API
- data/pipeline.py
  - 差分 ETL（株価・財務・カレンダー）の実行
  - backfill による後出し修正吸収
  - 品質チェックの呼び出し（data/quality.py）
  - run_daily_etl(...) による日次 ETL 実行
- data/quality.py
  - 欠損、重複、スパイク（前日比閾値）、日付不整合のチェック
  - QualityIssue を返す（詳細とサンプル行含む）
- data/calendar_management.py
  - 営業日判定、前後営業日取得、期間内営業日の取得
  - calendar_update_job による夜間バッチ更新
- data/audit.py
  - 監査ログ用の DDL 定義と初期化（init_audit_schema / init_audit_db）
  - signal_events / order_requests / executions 等を含む監査階層

設定管理:
- config.py に Settings クラス。環境変数から各種秘密情報・パス等を提供。
- 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を探索し、`.env` → `.env.local` を順に読み込み。OS 環境変数優先。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

---

## セットアップ手順

前提
- Python 3.10+（タイプヒントで | を利用しているため）
- duckdb、defusedxml などが必要

1. リポジトリをクローン / 解凍
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて他のライブラリを追加）
   - NOTE: 本リポジトリに requirements.txt があればそれを利用してください。
4. 環境変数を設定
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意/デフォルトあり:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト INFO）
   - 環境変数は .env または .env.local に記述することで自動読み込みされます（プロジェクトルートが検出される場合）。
   - .env を読み込ませたくないテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

サンプル .env (プロジェクトルート):
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```
   - 監査ログ専用 DB を別ファイルで作る場合:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方

いくつか代表的な使用例を示します。

1) J-Quants からのデータ取得（直接呼び出す）
```python
from kabusys.data import jquants_client as jq
# id_token を指定しなければ内部で refresh_token を使って取得・キャッシュします
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```
- 注意: API レート制御やリトライは jquants_client 内部で行われます（120 req/min、最大3回リトライ、401 の場合は自動リフレッシュ）。

2) DuckDB に保存（冪等）
```python
import duckdb
from kabusys.data import jquants_client as jq
conn = duckdb.connect("data/kabusys.duckdb")  # 事前に init_schema を実行しておく
records = jq.fetch_daily_quotes(date_from=..., date_to=...)
jq.save_daily_quotes(conn, records)
```

3) 日次 ETL 実行
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を与えなければ今日が対象
print(result.to_dict())
```
- run_daily_etl は市場カレンダー取得 → 株価取得 → 財務取得 → 品質チェック の順に実行します。各ステップは個別にエラーハンドリングされます。

4) RSS ニュース収集
```python
from kabusys.data.news_collector import fetch_rss, save_raw_news, run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# 単一フィード取得
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
new_ids = save_raw_news(conn, articles)

# 全ソース一括収集（known_codes に銘柄セットを渡すと news_symbols への紐付けを行う）
results = run_news_collection(conn, known_codes={"7203", "6758"})
```
- セキュリティ: RSS パーサは defusedxml を使い、SSRF 対策（スキーム・プライベートIPチェック）やレスポンスサイズ上限を設けています。

5) 品質チェックだけ実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

6) マーケットカレンダー操作
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
is_open = is_trading_day(conn, date(2024,3,15))
next_day = next_trading_day(conn, date(2024,3,15))
```

---

## 環境設定（重要な環境変数）

- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) : kabuステーション API パスワード
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) : Slack チャンネル ID
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 実行環境 (development | paper_trading | live)
- LOG_LEVEL : ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動 .env ロードを無効化

自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を起点）を探索して `.env` → `.env.local` を読み込みます。OS 環境変数が優先され、.env.local は上書き（override=True）されます。

---

## ディレクトリ構成

主要ファイル / モジュール一覧（リポジトリの src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py       — RSS ニュース収集と保存ロジック
    - pipeline.py             — ETL パイプライン / run_daily_etl
    - schema.py               — DuckDB スキーマ定義と init_schema
    - calendar_management.py  — 市場カレンダー管理（営業日判定 等）
    - audit.py                — 監査ログスキーマ初期化（order_requests, executions 等）
    - quality.py              — データ品質チェック
  - strategy/
    - __init__.py             — 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py             — 発注 / ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py             — 監視・メトリクス関連（拡張ポイント）

（上記以外にプロジェクトルートに README や pyproject.toml 等がある想定）

---

## 設計上のポイント / 注意点

- データ取得時の Look-ahead バイアス対策として、取得時刻（fetched_at）を UTC で記録します。
- J-Quants の API レート制限（120 req/min）を内部で守ります。高頻度呼び出し時は注意してください。
- データ保存は基本的に冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を考慮しています。
- RSS の XML パースや外部 URL 取得には SSRF・XML Bomb 対策が施されています。
- DuckDB を用いてローカルに高速な分析向けテーブルを管理します。スキーマは init_schema で冪等に作成されます。
- 監査ログ（audit テーブル群）は UTC タイムスタンプで管理され、発注フローの完全トレースを想定しています。

---

## 開発 / 貢献

- 戦略（strategy）や発注実装（execution）、監視（monitoring）をこの基盤上に実装していくことを想定しています。
- バグ報告・機能追加は Issue を立ててください。Pull Request はコーディング規約に沿った形でお願いします。

---

以上がこのコードベースの README.md の概要です。必要であれば具体的なサンプルスクリプト（cron 用 ETL 実行、デバッグ用 CLI、テストのためのモック方法など）を追記します。どの部分のサンプルが欲しいか教えてください。