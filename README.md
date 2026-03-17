# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants / kabuステーション 等の外部 API からデータを収集・保存し、ETL、データ品質チェック、ニュース収集、監査ログ等を提供します。

Version: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを安全に取得
- DuckDB に対するスキーマ定義・初期化・差分 ETL（冪等保存）
- RSS ベースのニュース収集と銘柄コード抽出（SSRF / XML 攻撃対策含む）
- データ品質チェック（欠損、重複、日付不整合、スパイク検出）
- 監査ログ（signal → order → execution のトレーサビリティ）テーブル群の初期化

設計上のポイント：
- API レートリミットの遵守（J-Quants: 120 req/min）
- リトライ（指数バックオフ）、401 の自動トークンリフレッシュ
- DuckDB へは冪等的に保存（ON CONFLICT を利用）
- RSS 取得は SSRF／Gzip-bomb 等の対策を実装

---

## 機能一覧

- 環境設定管理（.env 自動読み込み、必須キー取得）
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンからの ID トークン取得）
  - 保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
- DuckDB スキーマ管理
  - init_schema / get_connection（Raw / Processed / Feature / Execution レイヤー）
- ETL パイプライン
  - 差分取得（backfill による保険）、run_daily_etl（統合エントリ）
- ニュース収集
  - fetch_rss / save_raw_news / save_news_symbols
  - URL 正規化・トラッキング除去・記事ID（SHA-256 先頭32文字）
  - SSRF / XML 攻撃対策、サイズ制限
- マーケットカレンダー管理（営業日判定、next/prev_trading_day）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal_events, order_requests, executions 等）初期化ユーティリティ

---

## 前提・依存関係

- Python 3.10+
  - 型注釈で X | None を使用しているため Python 3.10 以上を推奨します
- 主要依存ライブラリ（少なくとも以下をインストールしてください）:
  - duckdb
  - defusedxml

インストール例:
pip install duckdb defusedxml

（パッケージ配布がある場合は pip install . や pip install -e . を利用してください）

---

## 環境変数 / .env

自動でプロジェクトルート（.git または pyproject.toml を探索）配下の `.env` / `.env.local` を読み込みます。  
自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 送信先チャンネル（必須）

オプション:
- KABUSYS_ENV — 環境: `development` / `paper_trading` / `live` （デフォルト: development）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

簡易 .env 例（`.env.example` を参考にしてください）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python と依存ライブラリをインストール
   - python >= 3.10 を用意
   - pip install duckdb defusedxml

2. レポジトリをクローン / パッケージをインストール
   - git clone ...
   - pip install -e .  (パッケージ化されている場合)

3. 環境変数設定
   - プロジェクトルートに `.env`（および必要であれば `.env.local`）を作成
   - 必須キー（上記参照）を設定

4. DuckDB スキーマ初期化
   - Python スクリプト／REPL で schema.init_schema を実行して DB を作成します。

例:
```python
from kabusys.data import schema
from pathlib import Path

conn = schema.init_schema(Path("data/kabusys.duckdb"))
```

5. 監査ログ DB（任意）
```python
from kabusys.data import audit
from pathlib import Path

audit_conn = audit.init_audit_db(Path("data/kabusys_audit.duckdb"))
```

---

## 使い方（代表的な API）

- J-Quants ID トークン取得
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を参照して POST 実行
```

- 日次 ETL 実行（統合）
```python
from datetime import date
import duckdb
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 個別 ETL（株価 / 財務 / カレンダー）
```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
```

- ニュース収集ジョブ（RSS -> raw_news 保存）
```python
from kabusys.data import news_collector, schema
from pathlib import Path

conn = schema.get_connection(Path("data/kabusys.duckdb"))
results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(results)  # {source_name: 新規保存数}
```

- カレンダー関連ユーティリティ
```python
from kabusys.data import calendar_management, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
print(calendar_management.is_trading_day(conn, date.today()))
print(calendar_management.next_trading_day(conn, date.today()))
```

- データ品質チェック
```python
from kabusys.data import quality, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

注意点:
- ニュース収集の URL オープン部分はテスト用にモック可能（kabusys.data.news_collector._urlopen を差し替え）。
- J-Quants クライアントは内部でレートリミット・リトライ・401 リフレッシュを処理します。必要に応じて id_token を明示的に注入できます（テスト用）。

---

## ディレクトリ構成

主要ファイル・モジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py         — RSS ニュース収集・正規化・DB 保存
    - schema.py                 — DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py               — ETL の差分更新・run_daily_etl 等
    - calendar_management.py    — カレンダー取得・営業日判定・更新ジョブ
    - audit.py                  — 監査ログテーブル定義 / 初期化
    - quality.py                — データ品質チェック
  - strategy/
    - __init__.py               — 戦略関連のエントリ（拡張ポイント）
  - execution/
    - __init__.py               — 発注・ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py               — 監視 / メトリクス（拡張ポイント）

（上記は現在の実装で提供されているモジュール構成です。strategy、execution、monitoring は拡張向けに空のパッケージとして存在します。）

---

## 開発・テストに関するメモ

- config.py はプロジェクトルート検出に .git または pyproject.toml を使用します。CI やテストで自動 .env ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- news_collector は外部ネットワークアクセスを行うため、単体テスト時には `_urlopen` をモックして HTTP レスポンスを制御するのが容易です。
- DuckDB へは明示的にスキーマを初期化してください（init_schema）。get_connection は初期化済み DB に接続するためのユーティリティです。
- audit.init_audit_db は UTC タイムゾーン固定やトランザクション実行を行います（監査ログ用途）。

---

## セキュリティと運用上の注意

- リフレッシュトークン・API パスワード等は .env やシークレットマネージャで安全に管理してください。リポジトリには含めないでください。
- ニュース取得時は SSRF や XML 攻撃対策を行っていますが、万一のため外部入力 URL を直接受け付ける処理には細心の注意を払ってください。
- 本番（live）環境では KABUSYS_ENV を `live` に設定し、ログレベルや通知設定を適切に管理してください。

---

README に書かれている API をベースに、戦略ロジックの実装・ブローカー連携・モニタリング実装を行うことができます。追加の使用例や CLI、デプロイ手順が必要であれば教えてください。