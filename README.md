# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants / RSS / kabuステーション など外部データソースからデータを収集し、DuckDB に保存して ETL・品質チェック・監査ログまで提供するモジュール群です。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／データパイプライン向けの基盤ライブラリです。主な役割は以下です。

- J-Quants API から株価（OHLCV）、財務データ、マーケットカレンダーを取得して DuckDB に保存
- RSS フィードからニュースを収集し前処理・記事ID生成・銘柄紐付けを行う
- ETL パイプライン（差分取得・バックフィル・保存・品質チェック）を実行
- マーケットカレンダー管理（営業日判定、next/prev/trading days 等）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）スキーマの初期化
- 環境設定の管理（.env の自動読込、環境変数アクセス）

設計面では、API レート制限遵守、リトライ、リフレッシュトークン自動更新、冪等性（ON CONFLICT 処理）、SSRF 対策、XML インジェクション防止、受信サイズ制限などを考慮しています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（取得、リトライ、トークン自動更新）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
- data.news_collector
  - RSS 取得・前処理・記事ID生成（SHA-256 ベース）・SSRF・gzip 対策
  - DB 保存（save_raw_news, save_news_symbols）と銘柄抽出
- data.schema
  - DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - init_schema / get_connection
- data.pipeline
  - ETL パイプライン（run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl）
  - 差分更新・バックフィル・品質チェック連携
- data.calendar_management
  - 営業日判定、next/prev_trading_day、get_trading_days、calendar_update_job
- data.audit
  - 監査ログ（signal_events, order_requests, executions）スキーマ初期化
  - init_audit_schema / init_audit_db
- data.quality
  - 品質チェック（欠損、スパイク、重複、日付整合性）と QualityIssue レポート
- config
  - .env 自動読み込み（プロジェクトルート検出）
  - Settings クラス経由の環境変数アクセス（必須変数は未設定だと例外）

---

## 要件

- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - defusedxml

必要なパッケージはプロジェクトの packaging / requirements を参照してください。最低限 duckdb と defusedxml は動作に必要です。

---

## セットアップ手順

1. リポジトリをクローン / ワークスペースに配置

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - pip install duckdb defusedxml

   （プロジェクトで requirements.txt / pyproject.toml がある場合はそちらを使用してください）

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると、自動で読み込まれます。
   - 自動読み込みを無効にする場合：
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - 任意 / デフォルト値:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 初期化（DB スキーマ）

DuckDB スキーマを作成するには `kabusys.data.schema.init_schema` を使います。

例（Python スクリプト）:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

監査ログ専用 DB を初期化する場合:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

既存 DB に接続のみ行う場合は:
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

---

## 使い方（代表的な例）

- 日次 ETL（市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 単独で株価 ETL（差分更新ルールに従う）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.data.pipeline import run_prices_etl

conn = get_connection("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

- RSS ニュース収集（raw_news 保存 + 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes: 有効な銘柄コードセットを渡すと本文から抽出して紐付け
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

- J-Quants の ID トークンを直接取得する
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()
```

- 設定取得
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

---

## 自動 .env 読み込み動作

- 起点は本モジュールのファイル位置（CWD ではありません）。親ディレクトリを上がって `.git` または `pyproject.toml` を基準にプロジェクトルートを検出します。そこで `.env` / `.env.local` を順に読み込みます。
- 読み込み優先度:
  1. OS 環境変数（既存）
  2. .env.local（override=True で既存 OS 環境変数を上書きしない）
  3. .env（override=False、未設定キーのみセット）
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに利用）。

.env パーサは export KEY=val 形式やクォート、インラインコメントの扱いもサポートしています。

---

## ログとデバッグ

- Settings.log_level で LOG_LEVEL を参照します（環境変数 LOG_LEVEL）。有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL。
- jquants_client はレート制限（120 req/min）を内部で守り、リトライやトークンリフレッシュのログを出します。
- news_collector は RSS のパース失敗やセキュリティ上の問題（SSRF／サイズ超過等）で警告ログを出します。

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - execution/             (発注・ブローカー連携等の実装ディレクトリ)
  - strategy/              (戦略実装用ディレクトリ)
  - monitoring/            (監視・メトリクス用ディレクトリ)
  - data/
    - __init__.py
    - jquants_client.py    (J-Quants API クライアント)
    - news_collector.py    (RSS ニュース収集)
    - schema.py            (DuckDB スキーマ定義・初期化)
    - pipeline.py          (ETL パイプライン)
    - calendar_management.py
    - audit.py             (監査ログスキーマ)
    - quality.py           (品質チェック)

（実ファイルは上の一覧に含まれる各機能を実装しています）

---

## 開発・テストメモ

- テスト時に .env の自動読み込みを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- news_collector の _urlopen はテストでモック可能に設計されています（ネットワークの差替え）。
- DuckDB に対する DDL は idempotent（IF NOT EXISTS / ON CONFLICT）で書かれているため、何度初期化しても安全です。
- 監査ログの init_audit_schema は transactional オプションを持ちます。DuckDB はネストトランザクションをサポートしないため、呼び出し側のトランザクション状態に注意してください。

---

## ライセンス / 貢献

この README はコードベースの説明に基づく概要です。実運用前に各 API キー、通信先、発注ロジックの安全性・法令順守を確認してください。貢献やバグレポートはリポジトリの issue / PR にてお願いします。

--- 

必要であれば、README に例となる .env.example、実行用 CLI スクリプト例、より詳しい API ドキュメント（各関数の引数・戻り値の詳細）を追加します。どの情報を優先して追加しましょうか？