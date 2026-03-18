# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）の README（日本語）

簡易: J-Quants / RSS などからデータを収集・保存し、ETL・品質チェック・監査ログの管理を行うための内部ライブラリ群です。DuckDB を主な永続化層として利用します。

---

## 目次
- プロジェクト概要
- 主な機能一覧
- 要件
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数（.env）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本市場向けのデータ収集・ETL・品質管理・監査を行うためのライブラリ群です。主な設計方針は以下です。

- J-Quants API 等からの差分取得（レート制限・リトライ・トークン自動リフレッシュを内蔵）
- RSS フィードからのニュース収集（SSRF・XML攻撃・Gzip Bomb 対策、トラッキング除去）
- DuckDB を用いたスキーマ（Raw / Processed / Feature / Execution / Audit）
- ETL の差分更新・バックフィル・品質チェック（欠損・重複・スパイク・日付整合性）
- 発注／監査のための監査ログスキーマ（UUID によるトレーサビリティ）

---

## 主な機能一覧
- data/jquants_client.py
  - J-Quants API クライアント（OHLCV、財務、マーケットカレンダー）
  - レート制御（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- data/news_collector.py
  - RSS から記事収集、テキスト前処理、ID 生成（URL 正規化→SHA256）、DuckDB への冪等保存
  - SSRF／XML 攻撃防止、レスポンスサイズ制限、トラッキングパラメータ除去
  - 銘柄コード抽出（4桁コード）と news_symbols への紐付け
- data/schema.py
  - DuckDB の全スキーマ（Raw/Processed/Feature/Execution 等）を定義・初期化
- data/pipeline.py
  - 日次 ETL パイプライン（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得、バックフィル、品質チェックの統合
- data/calendar_management.py
  - 営業日判定・前後営業日検索・カレンダー更新ジョブ
- data/audit.py
  - 監査ログ用スキーマ（signal, order_request, executions 等）および初期化
- data/quality.py
  - 欠損・重複・スパイク・日付不整合のチェック
- config.py
  - 環境変数管理（.env 自動読み込み、必須変数の検査）、アプリ設定アクセス用オブジェクト `settings`

---

## 要件
- Python 3.10 以上（型アノテーションに `|` を利用）
- 主要依存:
  - duckdb
  - defusedxml
- 実行環境により追加ライブラリが必要になる場合があります（例: HTTP/SSL 標準ライブラリで十分な想定）。

（プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。）

---

## セットアップ手順

1. Python と依存ライブラリのインストール
   - 例（pip）:
     - pip install duckdb defusedxml

   - 開発としてパッケージ化されている場合:
     - pip install -e .

2. リポジトリルートに .env ファイルを作成（後述の環境変数参照）

3. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトで:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")

4. （監査ログを別DBで管理する場合）audit DB 初期化:
   - from kabusys.data.audit import init_audit_db
   - audit_conn = init_audit_db("data/kabusys_audit.duckdb")

注:
- config.py はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、自動的に `.env` / `.env.local` を読み込みます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 簡単な使い方（コード例）

- DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行:
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

- 市場カレンダー更新（夜間バッチ）:
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved:", saved)
```

- RSS ニュース収集（既知の銘柄セットを渡して news_symbols も作成）:
```python
from kabusys.data.news_collector import run_news_collection

# 例: known_codes は銘柄コードセット (str の集合、"7203" など)
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規件数, ...}
```

- J-Quants から ID トークンを明示取得:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用
```

- 品質チェック単体実行:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 環境変数（.env で管理）
config.Settings から参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API パスワード
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV            : "development" | "paper_trading" | "live"（デフォルト "development"）
- LOG_LEVEL              : "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト "INFO"）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を指定すると自動 .env ロードを無効化
- KABUSYS_API_BASE_URL? (not present) — config 内では KABU_API_BASE_URL デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH            : デフォルト "data/kabusys.duckdb"
- SQLITE_PATH            : デフォルト "data/monitoring.db"

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

config.py は .env の読み取り時に export 行やクォートを含む値、コメントを適切に処理します。`.env.local` は `.env` の上書きとして読み込まれます（OS環境変数は保護）。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要モジュールと役割の一覧です。

- src/kabusys/
  - __init__.py  (パッケージ定義、__version__)
  - config.py    (環境変数・設定管理)
  - data/
    - __init__.py
    - schema.py              (DuckDB スキーマ定義 / init_schema)
    - jquants_client.py      (J-Quants API クライアント、保存ユーティリティ)
    - pipeline.py            (ETL パイプラインと run_daily_etl)
    - news_collector.py      (RSS 収集・保存・銘柄抽出)
    - calendar_management.py (市場カレンダー管理、営業日ロジック)
    - quality.py             (データ品質チェック)
    - audit.py               (監査ログスキーマ・初期化)
    - pipeline.py            (ETL パイプライン)
  - strategy/
    - __init__.py            (戦略関連モジュール置き場)
  - execution/
    - __init__.py            (発注実行関連モジュール置き場)
  - monitoring/
    - __init__.py

各ファイルは README に簡潔に記載した責務を持ちます。戦略・実行・監視モジュールは拡張のためのプレースホルダになっています。

---

## 実装上の注意点（短く）
- J-Quants クライアントは 120 req/min のレート制御を行います。大量取得や並列処理時は注意してください。
- jquants_client は 401 で自動的にリフレッシュして 1 回リトライします。多重再帰を避ける実装になっています。
- news_collector は URL 正規化とトラッキング除去を行い、記事 ID を SHA-256 の先頭 32 文字で生成して冪等性を担保します。
- DuckDB の初期化は冪等（CREATE TABLE IF NOT EXISTS）です。既存 DB に対して追加で監査スキーマを導入することもできます。
- テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを回避できます。

---

## サポート / 拡張
- 戦略実装（strategy パッケージ）や発注実行（execution）・監視（monitoring）をプロジェクトの要件に合わせて実装してください。
- 監査ログ（data.audit）を使用して、発注から約定までのトレーサビリティを構築できます。

---

この README はコードベースから生成した概要です。実際に運用する際は適切なアクセス権限管理、API キーの保護、テスト環境・本番環境の分離など運用面の安全策を必ず実施してください。