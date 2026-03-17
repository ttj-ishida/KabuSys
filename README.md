# KabuSys

日本株向けの自動売買・データ基盤ライブラリ KabuSys のリポジトリ向け README（日本語）。

概要・使い方・セットアップ・ディレクトリ構成など、開発者が素早く利用開始できる情報をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／データ基盤を目的とした Python パッケージです。  
主な目的は以下です。

- J-Quants API からの株価・財務・マーケットカレンダー取得
- RSS からのニュース収集と銘柄紐付け
- DuckDB を用いたデータスキーマの管理（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 発注・監査ログのための監査スキーマ（order／execution のトレーサビリティ）

設計上のポイント：
- API レート制御とリトライ（指数バックオフ、401 の自動トークンリフレッシュ）
- データ保存は冪等（ON CONFLICT 句）で重複を書き換え・排除
- RSS 収集での SSRF 対策、XML セキュリティ対策（defusedxml）、レスポンスサイズ制限
- DuckDB による高速なクエリ・トランザクション設計

---

## 機能一覧

- データ取得
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
- データ保存（DuckDB）
  - raw_prices, raw_financials, market_calendar などの Raw テーブル
  - processed / feature / execution / audit 層のテーブル定義と初期化
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得）
  - backfill による後出し修正の吸収
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集
  - RSS 取得、URL 正規化、記事ID（SHA-256先頭32文字）生成、raw_news への冪等保存
  - 銘柄コード抽出と news_symbols への紐付け
- マーケットカレンダー管理
  - 営業日判定（フォールバックあり）、next/prev trading day 等
  - 夜間バッチでのカレンダー更新ジョブ
- 監査ログ（Audit）
  - signal -> order_request -> execution のトレーサビリティテーブル群
- 設定・環境管理
  - .env 自動読み込み（プロジェクトルートを検出）と Settings API

---

## 要求（依存）パッケージ

基本的に標準ライブラリ中心ですが、以下をインストールしてください：

- Python 3.9+（ソースは型ヒントにより 3.9+ 想定）
- duckdb
- defusedxml

例（pip）:
```
pip install duckdb defusedxml
```

その他、実運用で Slack 通知などを使う場合は別途 Slack SDK 等が必要です。

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   requirements.txt が無い場合は最低限:
   ```
   pip install duckdb defusedxml
   ```
4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成するか、環境変数を直接設定します（下記参照）。
   - 自動ロードを無効化したいテスト等では環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. DuckDB スキーマ初期化
   - デフォルトの DuckDB ファイルは `data/kabusys.duckdb`（設定で変更可）。
   - 初期化例は後述。

---

## 必要な環境変数（主なもの）

config.Settings で参照される主な環境変数：

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- Slack (通知等)
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベース
  - DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- システム設定
  - KABUSYS_ENV (development | paper_trading | live) (任意, default=development)
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (任意)

例（.env の最小例）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- config モジュールはプロジェクトルート（.git または pyproject.toml の存在）を基に自動で .env, .env.local を読み込みます。必要に応じて自動ロードを無効化できます。
- 必須キーが未設定の場合 settings 参照時に ValueError が発生します。

---

## 初期化手順（DuckDB）

Python REPL またはスクリプトで実行例：

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, init_audit_schema, init_audit_db

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)  # 全テーブル（Raw/Processed/Feature/Execution）を作成

# 監査ログを追加する場合
init_audit_schema(conn)  # 既存接続へ監査テーブルを追加

# 監査専用 DB を作る場合
# audit_conn = init_audit_db("data/audit.duckdb")
```

上記は冪等（既にテーブルがあればスキップ）です。

---

## 使い方（代表的な API）

以下は主要な操作のサンプルコード例です。

- 日次 ETL 実行（カレンダー取得 → 株価・財務差分取得 → 品質チェック）

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)  # 初回のみ
result = run_daily_etl(conn)  # 引数で target_date, id_token 等を指定可能
print(result.to_dict())
```

- ニュース収集ジョブ（RSS 取得と DB 保存、銘柄紐付け）

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema(settings.duckdb_path)
# known_codes: 銘柄抽出に使う有効コードセット（例: 証券コードの集合）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- 単体ジョブ（カレンダー更新）

```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved:", saved)
```

- jquants_client の直接利用（トークン再取得・HTTP 再試行等の機能付き）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # refresh token から id_token を取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 注意事項 / 実装上の留意点

- J-Quants の API レート制限（120 req/min）を内部で制御しますが、並列実行時は注意してください。
- get_id_token は refresh token を使って idToken を取得します。401 受信時は自動リフレッシュして再試行します（1 回）。
- RSS 取得では SSRF・XML_Attack・Gzip bomb を考慮した実装が入っています。外部入力を扱う際は安全性を維持してください。
- DB 保存は基本的に冪等です（ON CONFLICT ... DO UPDATE / DO NOTHING を利用）。
- テスト時に .env の自動ロードを止めたい場合は環境変数で `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- settings は環境変数の存在を前提とするプロパティ群を提供します。未設定の必須キーアクセス時は ValueError が発生します。

---

## ディレクトリ構成

主要なソースツリー（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py               # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py             # DuckDB スキーマ定義・初期化
      - jquants_client.py     # J-Quants API クライアント（取得 / 保存）
      - pipeline.py          # ETL パイプライン
      - news_collector.py    # RSS 収集・前処理・DB保存
      - calendar_management.py # カレンダー管理・バッチ更新
      - quality.py           # 品質チェック
      - audit.py             # 監査ログのDDL・初期化
    - strategy/
      - __init__.py
      # 戦略関連モジュールを配置
    - execution/
      - __init__.py
      # 実行（発注）関連モジュールを配置
    - monitoring/
      - __init__.py
      # モニタリング関連（例: Slack, DB監視）を配置

補足：
- データファイルのデフォルト配置: data/kabusys.duckdb, data/monitoring.db
- ソースはモジュール化されており、各層（data/strategy/execution/monitoring）を独立して拡張できます。

---

## 開発メモ / さらに詳しい設計

- jquants_client: レートリミッタ、リトライ（408/429/5xx）、401 リフレッシュ、fetched_at による Look-ahead bias 対策、DuckDB への冪等保存。
- news_collector: URL 正規化（utm パラメータ除去）、記事 ID は正規化 URL の SHA-256 先頭32文字、defusedxml で XML セキュリティ対応、SSRF 対策（リダイレクトの検査、プライベートIP拒否）、レスポンスサイズ上限、チャンク INSERT、INSERT RETURNING による正確な挿入数取得。
- pipeline: 差分更新・backfill、calendar の先読み（lookahead）、品質チェックを一貫実行する run_daily_etl を提供。
- calendar_management: DB にデータがない場合の曜日ベースフォールバック、next/prev_trading_day 等の探索は最大検索日数を制限して安全に動作。

---

必要であれば、README に含める具体的な .env.example、CI 実行例、Dockerfile、systemd ユニット例、Slack 通知のサンプルなどを追記できます。どの部分を優先して追加しますか？