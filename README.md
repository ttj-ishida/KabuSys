# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ群です。  
データ取得（J-Quants）、ETL パイプライン、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ（発注→約定トレース）など、戦略・実行層の基盤機能を提供します。

バージョン: 0.1.0

---

## 主要な特徴

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX カレンダーを取得
  - API レート制限（120 req/min）を守る RateLimiter 実装
  - リトライ（指数バックオフ、最大 3 回）、401 受信時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集
  - RSS フィードの取得・パース（defusedxml で安全にパース）
  - URL 正規化（トラッキングパラメータ除去）→ SHA-256（先頭32文字）を記事IDに採用して冪等保存
  - SSRF 対策（スキーム検証、リダイレクト時の内部アドレス検査）
  - gzip 対応、受信サイズ上限でメモリDoS対策
  - 銘柄コード抽出・news_symbols への紐付け

- データベーススキーマ（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義を提供
  - スキーマ初期化ユーティリティ（init_schema, init_audit_db）

- ETL パイプライン
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得、バックフィル（後出し修正の吸収）、営業日調整
  - 品質チェックモジュール（欠損・重複・スパイク・日付不整合）

- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティ
  - 夜間バッチ更新ジョブ（calendar_update_job）

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティを UUID で連鎖
  - order_request_id を冪等キーとして二重発注を防止

---

## 必要要件

- Python 3.10 以上（型注釈に `X | None` 構文を使用）
- 主要依存パッケージ（最低限）:
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

（プロジェクトによっては追加の依存があるかもしれません。セットアップ用の requirements.txt があればそちらを利用してください。）

---

## セットアップ手順

1. リポジトリをクローンまたはソースを用意する。

2. Python 仮想環境を作成・有効化し、依存パッケージをインストールする。
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml
   ```

3. 環境変数を設定する（必須項目は下記参照）。プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（デフォルト: OS 環境変数 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（少なくとも開発で使うもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API パスワード
- SLACK_BOT_TOKEN : Slack 通知用トークン
- SLACK_CHANNEL_ID : Slack チャンネル ID

任意・設定可能な環境変数
- KABUSYS_ENV : one of "development", "paper_trading", "live"（デフォルト: development）
- LOG_LEVEL : "DEBUG","INFO","WARNING","ERROR","CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite 用パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 をセットすると .env 自動読み込みを無効化

.env の一例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 初期化（DB スキーマ作成）

DuckDB スキーマを初期化して接続を得る例:

```python
from kabusys.data import schema

# ファイル DB を初期化して接続を取得
conn = schema.init_schema("data/kabusys.duckdb")
# インメモリの場合
# conn = schema.init_schema(":memory:")
```

監査ログ用 DB を個別に初期化する場合:

```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

既存 DB に接続するだけなら:
```python
conn = schema.get_connection("data/kabusys.duckdb")
```

---

## 使い方（主要 API とサンプル）

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data import schema, pipeline

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 株価・財務・カレンダーの個別 ETL
```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.init_schema("data/kabusys.duckdb")
# 株価のみ
pipeline.run_prices_etl(conn, target_date=date.today())
# 財務のみ
pipeline.run_financials_etl(conn, target_date=date.today())
# カレンダーのみ
pipeline.run_calendar_etl(conn, target_date=date.today())
```

- RSS ニュース収集
```python
from kabusys.data import news_collector, schema

conn = schema.init_schema("data/kabusys.duckdb")
# デフォルト RSS ソースを使って収集（既知銘柄セットを渡すと銘柄紐付けを行う）
known_codes = {"7203", "6758"}  # 例
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data import calendar_management, schema

conn = schema.init_schema("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
```

- マーケットカレンダーのユーティリティ
```python
from datetime import date
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
d = date(2025, 1, 6)
print(calendar_management.is_trading_day(conn, d))
print(calendar_management.next_trading_day(conn, d))
```

- J-Quants API からの直接取得（テスト用）
```python
from kabusys.data import jquants_client as jq
# トークンは settings を使うため通常は不要。ページネーション間で ID トークンを共有する実装済み
quotes = jq.fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
```

---

## ロギング & 環境モード

- KABUSYS_ENV（development / paper_trading / live）に基づくフラグ:
  - settings.is_dev / is_paper / is_live プロパティで判定できます。
- LOG_LEVEL 環境変数でログレベルを制御（入力値は検証されます）。

---

## ディレクトリ構成（主要ファイル）

概略:

- src/kabusys/
  - __init__.py        (パッケージ定義, __version__ = "0.1.0")
  - config.py          (環境変数 / .env 自動読み込み / Settings)
  - data/
    - __init__.py
    - jquants_client.py     (J-Quants API クライアント、取得・保存関数)
    - news_collector.py     (RSS 収集、記事正規化、保存、銘柄抽出)
    - pipeline.py           (ETL パイプライン: run_daily_etl 等)
    - calendar_management.py(カレンダー管理、営業日ユーティリティ、更新ジョブ)
    - schema.py             (DuckDB スキーマ定義・init_schema)
    - audit.py              (監査ログスキーマ、init_audit_db)
    - quality.py            (データ品質チェック)
    - (その他: pipeline から呼ばれる品質・補助モジュール)
  - strategy/
    - __init__.py       (戦略層用名前空間)
  - execution/
    - __init__.py       (発注/実行層用名前空間)
  - monitoring/
    - __init__.py       (監視・モニタリング用名前空間)

各モジュールは明確に層 (Raw/Processed/Feature/Execution/Audit) を分離して実装されています。DuckDB を用いることでローカルでの高速な分析・検証が可能です。

---

## 設計上の注意点 / よくある運用上のポイント

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を検出して行います。テスト等で自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用してください。
- J-Quants の ID トークンはモジュールレベルでキャッシュされ、ページネーション中に共有されます。401 を受け取った場合は一度だけ自動リフレッシュして再試行します。
- DuckDB の初期化は冪等に設計されています（既存テーブルはスキップ）。監査スキーマは別途 init_audit_db / init_audit_schema を使うことで追加できます。
- ニュース収集では SSRF・XMLBomb・メモリDoS に対する防御を行っていますが、外部ソースにアクセスする処理は運用環境でのネットワークポリシーに注意してください。
- 品質チェックは Fail-Fast ではなく問題を収集して返す実装です。呼び出し側で閾値に応じて ETL の停止やアラートを決定してください。

---

## 開発 / 貢献

- テスト・ CI の導入、外部 API クレデンシャルの管理、実行層（kabuステーション連携）や戦略サンプルの追加を歓迎します。
- 外部との接続を伴うコードはモック化しやすい設計（id_token 注入や _urlopen の差し替え）になっています。ユニットテスト作成時はこれらをモックしてテストしてください。

---

必要であれば README の英語版、実行例のスクリプト（cron / systemd 用）や Dockerfile / docker-compose のテンプレートも作成します。どの形式を追加で欲しいか教えてください。