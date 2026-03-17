# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）のリポジトリ説明書です。  
このREADMEではプロジェクト概要、機能、セットアップ手順、使い方（主要APIの例）、およびディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株を対象としたデータパイプラインと自動売買の基盤ライブラリです。  
主に以下を提供します。

- J-Quants API からのマーケットデータ（株価・財務・取引カレンダー）の取得と DuckDB への保存
- RSS フィードからのニュース収集とテキスト前処理、銘柄紐付け
- ETL（差分更新・バックフィル）パイプラインとデータ品質チェック
- JPX マーケットカレンダー管理（営業日判定や夜間更新ジョブ）
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ
- 環境変数ベースの設定管理（.env 自動ロード機能）

設計方針としては「冪等性」「レート制限」「リトライ」「SSRF/DoS対策」「品質チェック」を重視しています。

---

## 主な機能一覧

- データ取得
  - 株価日足（OHLCV）取得（ページネーション対応、リトライ・レート制御）
  - 財務データ（四半期）取得
  - JPX マーケットカレンダー取得
- データ保存（DuckDB）
  - raw / processed / feature / execution / audit 層のスキーマ定義と初期化
  - ON CONFLICT を用いた冪等保存
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得）
  - バックフィル（API 後出し修正を吸収）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集
  - RSS 取得、defusedxml による安全なパース
  - URL正規化、トラッキングパラメータ除去、記事ID（SHA-256の先頭32文字）
  - raw_news / news_symbols への保存（チャンクINSERT、トランザクション）
  - SSRF / private IP 制限、レスポンスサイズ制限
- カレンダー管理
  - 営業日判定、next/prev 営業日取得、期間の営業日リスト取得
  - 夜間バッチでのカレンダー差分更新
- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査用スキーマ
  - UTC タイムゾーン固定設定サポート
- 設定管理
  - .env/.env.local 自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN）

---

## 前提（Prerequisites）

- Python 3.10 以上（コード内で型ヒントの union 演算子（|）を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - defusedxml

インストール例（仮の venv を作成した後）:
```bash
python -m pip install duckdb defusedxml
```

必要な追加パッケージがあればプロジェクトの requirements に記載してください。

---

## 環境変数 / .env

KabuSys は .env/.env.local または OS 環境変数から設定を読み込みます（自動ロード）。  
自動ロードはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から行われます。自動ロードを無効にするには:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主な環境変数（必須は README 内で明示）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabuAPI の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

.env に書く場合の例（.env.example を作ると良い）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env パーサーは export 形式や引用符、行内コメントに対応しています。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して依存をインストール
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv venv
   source venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml
   ```

2. 必要な環境変数を .env または環境に設定
   - 上記の必須変数を .env に記載するか、シェルで export してください。

3. DuckDB スキーマの初期化
   - デフォルトパスは data/kabusys.duckdb。Python REPL またはスクリプトから初期化できます。
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

4. 監査ログ用スキーマ（必要に応じて）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   # または既存 conn に対して init_audit_schema(conn)
   ```

---

## 使い方（主要API・実行例）

以下は代表的な利用例です。詳細は各モジュールの docstring を参照してください。

- J-Quants API からトークン取得 / データ取得
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を使う
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL（差分更新 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # 引数で target_date, id_token 等を指定可
print(result.to_dict())
```

- 市場カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved:", saved)
```

- RSS ニュース収集と保存
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は既知の銘柄コードセット（extract_stock_codes に使用）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- news_collector の個別呼び出し例（RSS を取得して記事リストを得る）
```python
from kabusys.data.news_collector import fetch_rss, save_raw_news
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
new_ids = save_raw_news(conn, articles)
```

- 監査スキーマ初期化（既存 conn に追加する）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- 設定値の参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

---

## 開発時の留意点

- HTTP/外部アクセスにはレート制御や SSRF/サイズ制限等の安全策を施しています。直接 urllib を使っています。
- J-Quants API のレート制限は 120 req/min に合わせた制御を組み込んでいます。
- 各種保存処理は ON CONFLICT / DO UPDATE（または DO NOTHING）を使い冪等性を担保しています。
- ニュース収集は defusedxml を使い XML 攻撃から保護しています。
- DuckDB を利用するため、データ大量化の際はファイルサイズやパフォーマンスに注意してください。

---

## ディレクトリ構成

（このリポジトリの主要ファイル・ディレクトリ一覧）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理（.env 自動ロード含む）
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
      - news_collector.py      — RSS ニュース収集・正規化・保存
      - schema.py              — DuckDB スキーマ定義・初期化
      - pipeline.py            — ETL (run_daily_etl, run_prices_etl 等)
      - calendar_management.py — マーケットカレンダー管理・営業日判定
      - audit.py               — 監査ログスキーマと初期化
      - quality.py             — データ品質チェック
      - pipeline.py
    - strategy/                 — 戦略層（空のパッケージ / 実装を追加）
      - __init__.py
    - execution/                — 実行（注文）層（空のパッケージ / 実装を追加）
      - __init__.py
    - monitoring/               — 監視関連（空パッケージ）
      - __init__.py

この README に含まれていないモジュールや関数の詳細は、各モジュールの docstring を参照してください。

---

## テスト・CI・デバッグ

- テスト時には自動 .env ロードを無効化することが推奨されます:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- jquants_client 等はネットワーク呼び出しが含まれるため、ユニットテストでは HTTP 呼び出しや内部 _urlopen などをモックするとよいです。

---

もし README に追記して欲しい使用例（具体的な ETL スケジュール設定や crontab/airflow の例、CI テスト手順等）があれば教えてください。必要に応じて README を拡張します。